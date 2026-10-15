# Purpose: Persist drawing runs and coordinate one bounded simulation execution without command retries.
import asyncio
import json
import logging
import math
import re
import time
import uuid
from pathlib import Path

import httpx

from src.stroke_processing.stroke_processing import extract_skill

LOGGER = logging.getLogger("skill-to-bot.workflow")


class Workflow:
    def __init__(self, data: Path, config: dict, contracts: Path, simulation_url: str):
        for key, value in config.items():
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value <= 0
            ):
                raise ValueError(f"Invalid positive workflow setting: {key}.")
        if not isinstance(config["poll_attempts"], int):
            raise ValueError("Poll attempts must be an integer.")
        self.data, self.config, self.contracts = data, config, contracts
        self.url = simulation_url
        self.client = httpx.AsyncClient(timeout=config["request_timeout"])
        self.runs, self.tasks = {}, set()
        self.lock = asyncio.Lock()
        for folder in ("runs", "demonstrations"):
            (data / folder).mkdir(parents=True, exist_ok=True)
        for path in (data / "runs").glob("*/run.json"):
            try:
                run = json.loads(path.read_text())
                if (
                    not re.fullmatch(r"[a-f0-9]{32}", run["run_id"])
                    or run["run_id"] != path.parent.name
                ):
                    raise ValueError("Saved ID mismatch.")
                if run["status"] == "running":
                    run.update(
                        status="failed",
                        phase="interrupted",
                        error="Orchestrator restarted; robot outcome is unknown. Inspect simulation before another run.",
                    )
                    self.record(run, run["error"])
                run["video_available"] = (path.parent / "simulation.mp4").is_file()
                run["thumbnail_available"] = (path.parent / "simulator-final.png").is_file()
                self.runs[run["run_id"]] = run
            except (ValueError, OSError, KeyError):
                LOGGER.warning("Invalid saved drawing run: %s", path)

    def save(self, run):
        directory = self.data / "runs" / run["run_id"]
        directory.mkdir(parents=True, exist_ok=True)
        temporary = directory / "run.tmp"
        temporary.write_text(json.dumps(run, indent=2, allow_nan=False))
        temporary.replace(directory / "run.json")

    def record(self, run, message):
        run.setdefault("logs", []).append({"time": time.time(), "message": message})
        self.save(run)
        LOGGER.info(json.dumps({"run_id": run["run_id"], "message": message}))

    async def service_status(self):
        try:
            response = await self.client.get(
                self.url + "/ready", timeout=self.config["health_timeout"]
            )
            return {
                "simulation": {
                    "status": "ready" if response.is_success else "unavailable",
                    "detail": None if response.is_success else response.text[:400],
                }
            }
        except httpx.HTTPError:
            return {
                "simulation": {"status": "unavailable", "detail": "Simulation cannot be reached."}
            }

    async def start(self, demonstration_id, request_id, paper_pose=None, reuse_run_id=None):
        async with self.lock:
            inputs = {
                "demonstration_id": demonstration_id,
                "paper_pose": paper_pose,
                "reuse_run_id": reuse_run_id,
            }
            for run in self.runs.values():
                if run["request_id"] == request_id:
                    if any(run.get(key) != value for key, value in inputs.items()):
                        raise ValueError("Request ID was already used with different inputs.")
                    return run
            if any(run["status"] == "running" for run in self.runs.values()):
                raise RuntimeError("A drawing run is already active.")
            if reuse_run_id:
                previous = self.runs.get(reuse_run_id)
                if (
                    previous is None
                    or previous["demonstration_id"] != demonstration_id
                    or not (self.data / "runs" / reuse_run_id / "skill.json").is_file()
                ):
                    raise ValueError("The selected run has no reusable drawing skill.")
            run = {
                "run_id": uuid.uuid4().hex,
                "request_id": request_id,
                **inputs,
                "status": "running",
                "phase": "processing",
                "created_at": time.time(),
                "error": None,
                "result": None,
            }
            self.runs[run["run_id"]] = run
            self.record(run, "Drawing demonstration loaded.")
            task = asyncio.create_task(self.execute(run))
            self.tasks.add(task)
            task.add_done_callback(self.tasks.discard)
            return run

    async def delete(self, run_id):
        """Remove a finished run from history while retaining evidence and deduplication."""
        async with self.lock:
            run = self.runs[run_id]
            if run["status"] == "running":
                raise RuntimeError("An active run cannot be deleted from history.")
            if not run.get("deleted_at"):
                updated = {**run, "deleted_at": time.time()}
                self.save(updated)
                run.update(updated)

    async def execute(self, run):
        directory = self.data / "runs" / run["run_id"]
        try:
            if run.get("reuse_run_id"):
                skill = json.loads(
                    (self.data / "runs" / run["reuse_run_id"] / "skill.json").read_text()
                )
                self.record(run, "Reusing saved DRAW skill without reprocessing.")
            else:
                raw = json.loads(
                    (self.data / "demonstrations" / (run["demonstration_id"] + ".json")).read_text()
                )
                skill = await asyncio.to_thread(
                    extract_skill, raw, run["demonstration_id"], self.contracts, self.config
                )
            (directory / "skill.json").write_text(json.dumps(skill, indent=2))
            run["skill"] = skill
            self.record(
                run,
                f"Drawing skill extracted: {len(skill['strokes'])} strokes, {sum(len(s['points']) for s in skill['strokes'])} points.",
            )
            run["phase"] = "executing"
            self.record(run, "Starting Panda drawing execution.")
            response = await self.client.post(
                self.url + "/execute",
                json={"run_id": run["run_id"], "skill": skill, "paper_pose": run["paper_pose"]},
            )
            self.require_success(response)
            deadline = time.monotonic() + self.config["simulation_timeout"]
            while time.monotonic() < deadline:
                response = await self.poll_job(run["run_id"])
                self.require_success(response)
                job = response.json()
                state = (job["phase"], job.get("stroke_index"))
                if state != (run["phase"], run.get("stroke_index")):
                    run.update(
                        phase=state[0], stroke_index=state[1], stroke_count=job.get("stroke_count")
                    )
                    self.record(
                        run,
                        f"Panda: {job['phase']}"
                        + (
                            f", stroke {state[1] + 1} of {job['stroke_count']}."
                            if state[1] is not None
                            else "."
                        ),
                    )
                if job["status"] != "running":
                    result = job.get("result")
                    run.update(status=job["status"], result=result, error=job.get("error"))
                    break
                await asyncio.sleep(self.config["poll_seconds"])
            else:
                raise TimeoutError(
                    "Simulation deadline exceeded; robot outcome is unknown. No replay was requested."
                )
        except asyncio.CancelledError:
            run.update(
                status="failed",
                phase="interrupted",
                error="Workflow stopped; robot outcome is unknown. No replay was requested.",
            )
            raise
        except httpx.HTTPError as error:
            run.update(
                status="failed",
                error=f"Simulation communication failed ({type(error).__name__}); robot outcome is unknown. Inspect simulation before another run.",
            )
        except Exception as error:
            run.update(status="failed", error=str(error) or type(error).__name__)
        finally:
            run["finished_at"] = time.time()
            run["video_available"] = (directory / "simulation.mp4").is_file()
            run["thumbnail_available"] = (directory / "simulator-final.png").is_file()
            self.record(
                run,
                run["error"]
                or f"Drawing completed. Mean path error: {run['result']['mean_path_error_m'] * 1000:.2f} mm.",
            )

    @staticmethod
    def require_success(response):
        if not response.is_success:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise ValueError(
                f"Simulation request failed ({response.status_code}): {str(detail)[:500]}"
            )

    async def poll_job(self, run_id):
        # Read-only recovery never resubmits a robot command.
        for attempt in range(self.config["poll_attempts"]):
            try:
                return await self.client.get(self.url + "/jobs/" + run_id)
            except (httpx.ReadError, httpx.ConnectError):
                if attempt + 1 == self.config["poll_attempts"]:
                    raise
                await asyncio.sleep(self.config["poll_seconds"])

    async def close(self):
        tasks = list(self.tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await self.client.aclose()
