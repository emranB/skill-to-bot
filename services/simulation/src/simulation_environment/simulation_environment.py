# Purpose: Own the LIBERO Panda world and expose isolated asynchronous simulation operations.
import asyncio
import json
import math
import os
import re
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException
from jsonschema import ValidationError
from src.robot_control.robot_control import execute
from src.skill_to_robot.skill_to_robot import validate_skill

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / "config.json").read_text())
DATA = Path(os.environ.get("DATA_DIR", "/data")).resolve()
SCHEMA = Path(os.environ.get("CONTRACTS_DIR", "/app/contracts")) / "skill.schema.json"


class SimulationEnvironment:
    def __init__(self, config: dict):
        for key, value in config.items():
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"Invalid simulation setting: {key}")
            if key not in ("seed", "grasp_z_offset") and value <= 0:
                raise ValueError(f"Simulation setting must be positive: {key}")
        if config["hold_steps"] >= config["max_phase_steps"]:
            raise ValueError("Hold steps must be below the phase step limit.")
        for key in (
            "width",
            "height",
            "control_freq",
            "render_every",
            "max_phase_steps",
            "hold_steps",
        ):
            if not isinstance(config[key], int):
                raise ValueError(f"Simulation setting must be an integer: {key}")
        from libero.libero.envs import TASK_MAPPING
        from robosuite import load_controller_config

        np.random.seed(config["seed"])
        self.config = config
        self.env = TASK_MAPPING["libero_tabletop_manipulation"](
            bddl_file_name=str(ROOT / "can_transfer.bddl"),
            robots=["Panda"],
            controller_configs=load_controller_config(default_controller="OSC_POSE"),
            has_renderer=False,
            has_offscreen_renderer=True,
            use_camera_obs=False,
            control_freq=config["control_freq"],
            horizon=config["max_phase_steps"] * 10,
            ignore_done=True,
            hard_reset=False,
            initialization_noise=None,
        )
        self.reset()

    def reset(self):
        np.random.seed(self.config["seed"])
        self.env.reset()
        for _ in range(10):
            self.env.step(np.r_[np.zeros(6), -1])
        return self.object_position().tolist()

    def object_position(self):
        return self.env.sim.data.body_xpos[self.env.obj_body_id["alphabet_soup_1"]].copy()

    def render(self):
        frame = self.env.sim.render(
            width=self.config["width"], height=self.config["height"], camera_name="agentview"
        )
        return np.ascontiguousarray(frame[::-1])

    def close(self):
        self.env.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = ThreadPoolExecutor(max_workers=1)
    app.state.environment = None
    app.state.error = None
    app.state.jobs = {}
    app.state.lock = asyncio.Lock()
    try:
        app.state.environment = await asyncio.get_running_loop().run_in_executor(
            app.state.pool, SimulationEnvironment, CONFIG
        )
    except Exception as error:
        app.state.error = str(error)
    yield
    if app.state.environment is not None:
        await asyncio.get_running_loop().run_in_executor(
            app.state.pool, app.state.environment.close
        )
    app.state.pool.shutdown(wait=True)


app = FastAPI(title="skill-to-bot simulation", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"service": "simulation", "status": "ok"}


@app.get("/ready")
def ready():
    if app.state.environment is None:
        raise HTTPException(503, app.state.error or "Simulation is initializing.")
    return {"service": "simulation", "status": "ready"}


@app.get("/version")
def version():
    return {"service": "simulation", "version": "0.1.0"}


async def run_job(run_id: str, skill: dict):
    job = app.state.jobs[run_id]
    directory = DATA / "runs" / run_id
    directory.mkdir(parents=True, exist_ok=True)
    try:
        env = app.state.environment
        await asyncio.get_running_loop().run_in_executor(app.state.pool, env.reset)

        def progress(phase):
            job["phase"] = phase

        result = await asyncio.get_running_loop().run_in_executor(
            app.state.pool, execute, env, skill, directory / "simulation.mp4", CONFIG, progress
        )
        job.update(status="completed" if result["success"] else "failed", result=result)
        if not result["success"]:
            job["error"] = "Physics outcome did not meet the placement and release criteria."
    except Exception as error:
        job.update(status="failed", error=str(error))
    finally:
        (directory / "simulation-result.json").write_text(json.dumps(job, indent=2))


@app.post("/execute", status_code=202)
async def start(request: dict):
    ready()
    run_id = request.get("run_id", "")
    if not isinstance(run_id, str) or not re.fullmatch(r"[a-f0-9]{32}", run_id):
        raise HTTPException(422, "Invalid run ID.")
    try:
        validate_skill(request["skill"], SCHEMA, CONFIG)
    except (ValueError, KeyError, ValidationError) as error:
        raise HTTPException(422, str(error)) from error
    async with app.state.lock:
        if run_id in app.state.jobs:
            return app.state.jobs[run_id]
        if any(job["status"] == "running" for job in app.state.jobs.values()):
            raise HTTPException(409, "Simulation is already executing a run.")
        app.state.jobs[run_id] = {"run_id": run_id, "status": "running", "phase": "initializing"}
        app.state.task = asyncio.create_task(run_job(run_id, request["skill"]))
    return app.state.jobs[run_id]


@app.get("/jobs/{run_id}")
def job(run_id: str):
    if run_id not in app.state.jobs:
        raise HTTPException(404, "Unknown simulation run.")
    return app.state.jobs[run_id]


@app.post("/reset")
async def reset():
    ready()
    async with app.state.lock:
        if any(job["status"] == "running" for job in app.state.jobs.values()):
            raise HTTPException(409, "Cannot reset an active run.")
        position = await asyncio.get_running_loop().run_in_executor(
            app.state.pool, app.state.environment.reset
        )
    return {"status": "ready", "object_position": position}
