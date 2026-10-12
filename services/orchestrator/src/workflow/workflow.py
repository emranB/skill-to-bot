# Purpose: Coordinate bounded perception and simulation calls and preserve run state.
import asyncio
import json
import logging
import math
import os
import re
import time
import uuid
from pathlib import Path

import httpx
from jsonschema import Draft202012Validator

LOGGER = logging.getLogger("skill-to-bot.workflow")


class Workflow:
    def __init__(self, data: Path, config: dict, perception_url: str, simulation_url: str):
        for key in ("request_timeout", "health_timeout", "simulation_timeout", "poll_seconds"):
            if (
                not isinstance(config[key], (int, float))
                or not math.isfinite(config[key])
                or config[key] <= 0
            ):
                raise ValueError(f"Invalid positive workflow setting: {key}")
        self.data = data
        self.config = config
        self.urls = {"perception": perception_url, "simulation": simulation_url}
        self.client = httpx.AsyncClient(timeout=config["request_timeout"])
        self.runs = {}
        self.tasks = set()
        self.lock = asyncio.Lock()
        self.services = {}
        schema_root = Path(
            os.environ.get(
                "CONTRACTS_DIR",
                str(Path(__file__).resolve().parent.parent.parent.parent.parent / "contracts"),
            )
        )
        self.validator = Draft202012Validator(
            json.loads((schema_root / "skill.schema.json").read_text())
        )
        self.data.joinpath("runs").mkdir(parents=True, exist_ok=True)
        for path in self.data.joinpath("runs").glob("*/run.json"):
            try:
                run = json.loads(path.read_text())
                if (
                    not re.fullmatch(r"[a-f0-9]{32}", run["run_id"])
                    or run["run_id"] != path.parent.name
                ):
                    raise ValueError("Saved run ID does not match its directory.")
                if run["status"] == "running":
                    run.update(
                        status="failed",
                        phase="interrupted",
                        error="Orchestrator restarted. Execution outcome is unknown; inspect simulation before starting another run.",
                    )
                    self.record(run, run["error"])
                self.runs[run["run_id"]] = run
            except (OSError, ValueError, KeyError):
                LOGGER.warning("Invalid saved run: %s", path.name)

    def save(self, run: dict):
        directory = self.data / "runs" / run["run_id"]
        directory.mkdir(parents=True, exist_ok=True)
        temporary = directory / "run.tmp"
        temporary.write_text(json.dumps(run, indent=2))
        temporary.replace(directory / "run.json")

    def record(self, run: dict, message: str):
        run.setdefault("logs", []).append({"time": time.time(), "message": message})
        self.save(run)
        LOGGER.info(json.dumps({"run_id": run["run_id"], "message": message}))

    async def service_status(self):
        async def check(name, url):
            try:
                response = await self.client.get(
                    url + "/ready", timeout=self.config["health_timeout"]
                )
                return name, {
                    "status": "ready" if response.is_success else "unavailable",
                    "detail": None if response.is_success else response.text[:400],
                }
            except httpx.HTTPError:
                return name, {"status": "unavailable", "detail": "Service cannot be reached."}

        self.services = dict(
            await asyncio.gather(*(check(name, url) for name, url in self.urls.items()))
        )
        return self.services

    async def start(self, video: str, calibration: dict, request_id: str):
        async with self.lock:
            for run in self.runs.values():
                if run["request_id"] == request_id:
                    if run["video"] != video or run["calibration"] != calibration:
                        raise ValueError("Request ID was already used with different inputs.")
                    return run
            if any(run["status"] == "running" for run in self.runs.values()):
                raise RuntimeError("A run is already active.")
            run = {
                "run_id": uuid.uuid4().hex,
                "request_id": request_id,
                "video": video,
                "calibration": calibration,
                "status": "running",
                "phase": "processing",
                "created_at": time.time(),
                "error": None,
                "result": None,
            }
            self.runs[run["run_id"]] = run
            self.record(run, "Reading video and tracking the selected object.")
            task = asyncio.create_task(self.execute(run))
            self.tasks.add(task)
            task.add_done_callback(self.tasks.discard)
            return run

    async def execute(self, run: dict):
        directory = self.data / "runs" / run["run_id"]
        try:
            response = await self.client.post(
                self.urls["perception"] + "/process",
                json={"video": run["video"], "calibration": run["calibration"]},
            )
            self.require_success(response)
            perception = response.json()
            self.validator.validate(perception["skill"])
            for name, value in [
                ("skill.json", perception["skill"]),
                ("observations.json", perception["observations"]),
            ]:
                (directory / name).write_text(json.dumps(value, indent=2))
            run["skill"] = perception["skill"]
            run["limitations"] = perception["limitations"]
            observations = perception["observations"]
            if observations and observations[0].get("segmentation_source"):
                source = observations[0]["segmentation_source"]
                refreshed = sum(sample.get("geometry_source") == "yolo" for sample in observations)
                self.record(
                    run, f"Object acquisition: {source}. Mask-based geometry updates: {refreshed}."
                )
            if perception["skill"].get("transport"):
                self.record(
                    run,
                    f"Transport: {len(perception['skill']['transport']) - 1} ordered waypoint targets.",
                )
            run["phase"] = "executing"
            self.record(run, "Skill extracted. Starting Panda simulation.")
            response = await self.client.post(
                self.urls["simulation"] + "/execute",
                json={"run_id": run["run_id"], "skill": perception["skill"]},
                timeout=10,
            )
            self.require_success(response)
            deadline = time.monotonic() + self.config["simulation_timeout"]
            while time.monotonic() < deadline:
                response = await self.client.get(
                    self.urls["simulation"] + "/jobs/" + run["run_id"], timeout=5
                )
                self.require_success(response)
                job = response.json()
                if run["phase"] != job["phase"]:
                    run["phase"] = job["phase"]
                    self.record(run, "Simulation: " + job["phase"] + ".")
                if job["status"] != "running":
                    run.update(
                        status=job["status"], result=job.get("result"), error=job.get("error")
                    )
                    break
                await asyncio.sleep(self.config["poll_seconds"])
            else:
                raise TimeoutError(
                    "Simulation status deadline exceeded; execution outcome is unknown."
                )
        except asyncio.CancelledError:
            run.update(
                status="failed",
                error="Run interrupted by orchestrator shutdown; execution outcome is unknown.",
            )
            raise
        except httpx.TimeoutException:
            run.update(
                status="failed",
                error=(
                    "Perception timeout; no robot execution was requested."
                    if run["phase"] == "processing"
                    else "Simulation timeout; execution outcome is unknown. Inspect/reset simulation before another run."
                ),
            )
        except Exception as error:
            run.update(status="failed", error=str(error) or type(error).__name__)
        finally:
            run["finished_at"] = time.time()
            run["video_available"] = (directory / "simulation.mp4").is_file()
            self.record(run, run["error"] or "Run completed. Physical result verified.")

    @staticmethod
    def require_success(response: httpx.Response):
        if not response.is_success:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise ValueError(
                f"Service request failed ({response.status_code}): {str(detail)[:500]}"
            )

    async def close(self):
        tasks = list(self.tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await self.client.aclose()
