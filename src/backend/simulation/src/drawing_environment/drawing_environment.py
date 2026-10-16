# Purpose: Own the Panda drawing scene, measured tip/contact ink and asynchronous simulation API.
import asyncio
import json
import math
import os
import re
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from xml.etree import ElementTree as ET

import mujoco
import numpy as np
from fastapi import FastAPI, HTTPException
from jsonschema import ValidationError
from robosuite import load_controller_config
from robosuite.environments.manipulation.single_arm_env import SingleArmEnv
from robosuite.models.arenas import TableArena
from robosuite.models.tasks import ManipulationTask

from src.skill_to_robot.skill_to_robot import paper_pose, robot_plan, validate_skill

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / "config.json").read_text())
DATA = Path(os.environ.get("DATA_DIR", str(ROOT.parent.parent / "data"))).resolve()
CONTRACTS = Path(os.environ.get("CONTRACTS_DIR", str(ROOT.parent.parent / "contracts")))


def validate_config(config: dict):
    for key, value in config.items():
        if key == "default_color":
            if not isinstance(value, str) or not re.fullmatch(r"#[a-fA-F0-9]{6}", value):
                raise ValueError("Invalid default ink color.")
            continue
        vector = key in ("paper_center", "camera_position", "camera_target", "park_offset")
        if vector != isinstance(value, list):
            raise ValueError(f"Invalid simulation setting shape: {key}.")
        values = value if isinstance(value, list) else [value]
        if any(
            isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
            for v in values
        ):
            raise ValueError(f"Invalid simulation setting: {key}.")
        if key in ("tracking_lead_seconds", "tracking_integral_gain"):
            if value < 0:
                raise ValueError(f"Tracking compensation must be nonnegative: {key}.")
            continue
        if (
            key
            not in ("paper_center", "paper_yaw", "camera_position", "camera_target", "park_offset")
            and value <= 0
        ):
            raise ValueError(f"Simulation setting must be positive: {key}.")
    if (
        len(config["paper_center"]) != 3
        or abs(config["paper_center"][2] - config["table_height"] - 0.002) > 1e-6
    ):
        raise ValueError("Paper must rest on the table.")
    if 2 * config["paper_margin"] >= min(config["paper_width"], config["paper_height"]):
        raise ValueError("Paper margins leave no drawing area.")
    if (
        config["contact_tolerance"] >= config["pen_up_height"]
        or config["contact_depth"] >= config["pen_tip_radius"]
    ):
        raise ValueError("Invalid ink/contact limits.")
    if (
        config["min_contact_coverage"] > 1
        or config["min_visible_paper"] > 1
        or config["drawing_tolerance"] > config["max_path_error"]
    ):
        raise ValueError("Invalid drawing acceptance limits.")
    if not 0 < config["default_pressure"] <= 1 or not 0.002 <= config["default_brush_size"] <= 0.05:
        raise ValueError("Invalid default brush settings.")
    if (
        len(config["camera_position"]) != 3
        or len(config["camera_target"]) != 3
        or not 10 <= config["camera_fov"] <= 100
    ):
        raise ValueError("Invalid drawing camera.")
    if np.linalg.norm(np.asarray(config["camera_position"]) - config["camera_target"]) < 1e-6:
        raise ValueError("Camera position and target must differ.")
    if len(config["park_offset"]) != 3 or config["park_offset"][2] < config["pen_up_height"]:
        raise ValueError("Park position must keep the pen lifted.")
    for key in (
        "control_freq",
        "max_ink_points",
        "max_skill_points",
        "width",
        "height",
        "video_fps",
    ):
        if not isinstance(config[key], int):
            raise ValueError(f"Simulation setting must be an integer: {key}.")


class DrawingScene(SingleArmEnv):
    def __init__(self, config):
        self.config = config
        controller = load_controller_config(default_controller="OSC_POSE")
        controller.update(control_delta=False, kp=config["controller_kp"])
        super().__init__(
            robots="Panda",
            controller_configs=controller,
            initialization_noise=None,
            use_camera_obs=False,
            has_renderer=False,
            has_offscreen_renderer=True,
            control_freq=config["control_freq"],
            horizon=100000,
            ignore_done=True,
            hard_reset=False,
        )

    def _load_model(self):
        super()._load_model()
        config = self.config
        robot = self.robots[0].robot_model
        robot.set_base_xpos(robot.base_xpos_offset["table"](0.8))
        arena = TableArena(
            table_full_size=(0.8, 0.8, 0.05), table_offset=(0, 0, config["table_height"])
        )
        arena.set_origin([0, 0, 0])
        camera_z = np.asarray(config["camera_position"]) - config["camera_target"]
        camera_z /= np.linalg.norm(camera_z)
        camera_x = np.cross([0, 0, 1], camera_z)
        if np.linalg.norm(camera_x) < 1e-6:
            raise ValueError("Drawing camera must have a defined horizontal direction.")
        camera_x /= np.linalg.norm(camera_x)
        camera_y = np.cross(camera_z, camera_x)
        camera = arena.worldbody.find("camera[@name='agentview']")
        camera.attrib.pop("quat", None)
        camera.set("pos", " ".join(map(str, config["camera_position"])))
        camera.set("xyaxes", " ".join(map(str, [*camera_x, *camera_y])))
        camera.set("fovy", str(config["camera_fov"]))
        paper = ET.SubElement(
            arena.worldbody, "body", name="paper", pos=" ".join(map(str, config["paper_center"]))
        )
        ET.SubElement(
            paper,
            "geom",
            name="paper_surface",
            type="box",
            size=f"{config['paper_width'] / 2} {config['paper_height'] / 2} 0.001",
            pos="0 0 -0.001",
            rgba="1 1 1 1",
            friction="0.1 0.005 0.0001",
            solref="0.01 1",
            group="1",
        )
        for index in range(config["max_ink_points"]):
            ET.SubElement(
                paper,
                "geom",
                name=f"ink_{index}",
                type="ellipsoid",
                size="0.0001 0.0001 0.00003",
                pos="0 0 0.0002",
                rgba="0.08 0.12 0.18 0",
                contype="0",
                conaffinity="0",
                group="1",
                mass="0",
            )
        # The gripper is already merged into the robot model by SingleArmEnv.
        gripper = robot.worldbody.find(".//body[@name='gripper0_eef']")
        if gripper is None:
            raise ValueError("Pinned Panda gripper is missing its tool attachment frame.")
        length = config["pen_length"]
        ET.SubElement(
            gripper,
            "geom",
            name="pen_body",
            type="cylinder",
            pos=f"0 0 {length / 2}",
            size=f"0.004 {length / 2}",
            rgba="0.1 0.35 0.8 1",
            contype="0",
            conaffinity="0",
            group="1",
            mass="0.02",
        )
        ET.SubElement(
            gripper,
            "geom",
            name="pen_tip",
            type="sphere",
            pos=f"0 0 {length}",
            size=str(config["pen_tip_radius"]),
            rgba="0.1 0.1 0.1 1",
            group="1",
            friction="0.1 0.005 0.0001",
            solref="0.01 1",
            mass="0.001",
        )
        ET.SubElement(
            gripper, "site", name="pen_tip_site", pos=f"0 0 {length}", size="0.001", rgba="0 0 0 0"
        )
        self.model = ManipulationTask(mujoco_arena=arena, mujoco_robots=[robot])

    def reward(self, action=None):
        return 0.0

    def _check_success(self):
        return False


class DrawingEnvironment:
    def __init__(self, config: dict):
        validate_config(config)
        self.config = config
        self.env = DrawingScene(config)
        self.tip_id = self.env.sim.model.site_name2id("pen_tip_site")
        self.paper_id = self.env.sim.model.body_name2id("paper")
        self.tip_geom = self.env.sim.model.geom_name2id("pen_tip")
        self.paper_geom = self.env.sim.model.geom_name2id("paper_surface")
        self.ink_ids = [
            self.env.sim.model.geom_name2id(f"ink_{i}") for i in range(config["max_ink_points"])
        ]
        self.reset()

    def reset(self, pose=None):
        self.center, self.rotation = paper_pose(self.config, pose)
        self.env.reset()
        model = self.env.sim.model
        model.body_pos[self.paper_id] = self.center
        yaw = math.atan2(self.rotation[1, 0], self.rotation[0, 0])
        model.body_quat[self.paper_id] = [math.cos(yaw / 2), 0, 0, math.sin(yaw / 2)]
        model.geom_rgba[self.ink_ids, 3] = 0
        self.ink = []
        self.last_mark = None
        self.env.sim.forward()
        context = self.env.sim._render_context_offscreen
        capacity = model.ngeom + model.nsite + model.nbody
        if context.scn.maxgeom < capacity:
            context.scn = mujoco.MjvScene(model._model, maxgeom=capacity)

    def tip_position(self):
        return self.env.sim.data.site_xpos[self.tip_id].copy()

    def local_position(self, world):
        return self.rotation.T @ (np.asarray(world) - self.center)

    def contact(self, local):
        sim = self.env.sim
        physical = any(
            {int(c.geom1), int(c.geom2)} == {self.tip_geom, self.paper_geom}
            for c in sim.data.contact[: sim.data.ncon]
        )
        gap = local[2] - self.config["pen_tip_radius"]
        return physical, abs(gap) <= self.config["contact_tolerance"]

    def deposit(self, stroke: int, local, pressure, phase: str, style=None):
        local = np.asarray(local, dtype=float)
        physical, near = self.contact(local)
        inside = (
            abs(local[0]) <= self.config["paper_width"] / 2
            and abs(local[1]) <= self.config["paper_height"] / 2
        )
        if phase != "draw" or not near or not inside:
            self.last_mark = None
            return None
        previous = self.last_mark if self.last_mark and self.last_mark["stroke"] == stroke else None
        effective = self.config["default_pressure"] if pressure is None else pressure
        base_radius = (
            style["brush_radius"]
            if style
            else self.config["default_brush_size"]
            * (self.config["paper_height"] - 2 * self.config["paper_margin"])
            / 2
        )
        radius = base_radius * (0.5 + effective)
        if (
            previous
            and np.linalg.norm(np.asarray(previous["local"])[:2] - local[:2])
            < self.config["ink_spacing"]
        ):
            return None
        if len(self.ink) >= len(self.ink_ids):
            raise ValueError("Drawing exhausted the bounded ink pool.")
        color = style["color"] if style else self.config["default_color"]
        delta = local[:2] - np.asarray(previous["local"])[:2] if previous else np.zeros(2)
        midpoint = local[:2] - delta / 2
        angle = math.atan2(delta[1], delta[0])
        length = float(np.linalg.norm(delta))
        point = {
            "stroke": stroke,
            "local": local.tolist(),
            "segment_start": previous["local"] if previous else local.tolist(),
            "radius": radius,
            "color": color,
            "pressure": effective,
            "pressure_source": "constant" if pressure is None else "input",
            "physical_contact": physical,
        }
        self.ink.append(point)
        self.last_mark = point
        geom = self.ink_ids[len(self.ink) - 1]
        self.env.sim.model.geom_pos[geom] = [*midpoint, 0.00005 + len(self.ink) * 1e-8]
        self.env.sim.model.geom_size[geom, :2] = [radius + length / 2, radius]
        self.env.sim.model.geom_quat[geom] = [math.cos(angle / 2), 0, 0, math.sin(angle / 2)]
        self.env.sim.model.geom_rgba[geom] = [
            int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)
        ] + [1]
        # Ink is visual-only; update its world position without an extra physics forward pass.
        self.env.sim.data.geom_xpos[geom] = (
            self.center + self.rotation @ self.env.sim.model.geom_pos[geom]
        )
        c, s = math.cos(angle), math.sin(angle)
        self.env.sim.data.geom_xmat[geom] = (
            self.rotation @ np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
        ).ravel()
        return point

    def render(self):
        frame = self.env.sim.render(
            width=self.config["width"], height=self.config["height"], camera_name="agentview"
        )
        if self.env.sim.data._data.warning[mujoco.mjtWarning.mjWARN_VGEOMFULL].number:
            raise ValueError("Simulator camera geometry capacity was exhausted.")
        return np.ascontiguousarray(frame[::-1])

    def visibility(self):
        pixels = self.env.sim.render(
            width=self.config["width"],
            height=self.config["height"],
            camera_name="agentview",
            segmentation=True,
        )
        objects = np.where(pixels[:, :, 0] == int(mujoco.mjtObj.mjOBJ_GEOM), pixels[:, :, 1], -1)
        ink = np.isin(objects, self.ink_ids[: len(self.ink)])
        return {
            "paper_fraction": float(np.mean((objects == self.paper_geom) | ink)),
            "ink_pixels": int(ink.sum()),
            "visible_ink_marks": len(set(objects.flat) & set(self.ink_ids[: len(self.ink)])),
        }

    def close(self):
        self.env.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_config(CONFIG)
    app.state.pool = ThreadPoolExecutor(max_workers=1)
    app.state.environment, app.state.error = None, None
    app.state.jobs, app.state.lock = {}, asyncio.Lock()
    app.state.task = None
    for path in (DATA / "runs").glob("*/simulation-result.json"):
        try:
            saved = json.loads(path.read_text())
            if (
                saved["run_id"] != path.parent.name
                or not re.fullmatch(r"[a-f0-9]{32}", saved["run_id"])
                or "request" not in saved
            ):
                continue
            if saved["status"] == "running":
                saved.update(
                    status="failed",
                    phase="interrupted",
                    error="Simulation restarted; drawing was interrupted. No replay was requested.",
                )
                path.write_text(json.dumps(saved, indent=2))
            app.state.jobs[saved["run_id"]] = saved
        except (ValueError, OSError, KeyError):
            continue
    try:
        app.state.environment = await asyncio.get_running_loop().run_in_executor(
            app.state.pool, DrawingEnvironment, CONFIG
        )
    except Exception as error:
        app.state.error = str(error)
    yield
    if app.state.task:
        await app.state.task
    if app.state.environment:
        await asyncio.get_running_loop().run_in_executor(
            app.state.pool, app.state.environment.close
        )
    app.state.pool.shutdown(wait=True)


app = FastAPI(title="skill-to-bot simulation", version="0.2.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"service": "simulation", "status": "ok"}


@app.get("/ready")
def ready():
    if app.state.environment is None:
        raise HTTPException(503, app.state.error or "Drawing environment is initializing.")
    return {"service": "simulation", "status": "ready"}


@app.get("/version")
def version():
    return {"service": "simulation", "version": "0.2.0"}


async def run_job(run_id, skill, pose):
    from src.robot_control.robot_control import execute

    job = app.state.jobs[run_id]
    directory = DATA / "runs" / run_id
    directory.mkdir(parents=True, exist_ok=True)
    try:
        env = app.state.environment
        await asyncio.get_running_loop().run_in_executor(app.state.pool, env.reset, pose)
        plan = robot_plan(skill, CONFIG, pose)
        (directory / "robot-plan.json").write_text(json.dumps(plan, indent=2))

        def progress(phase, stroke):
            job.update(phase=phase, stroke_index=stroke, stroke_count=len(skill["strokes"]))

        result = await asyncio.get_running_loop().run_in_executor(
            app.state.pool, execute, env, plan, directory, CONFIG, progress
        )
        job.update(
            status="completed" if result["success"] else "failed",
            phase="completed" if result["success"] else "failed",
            result=result,
        )
        if not result["success"]:
            job["error"] = result["error"]
    except Exception as error:
        job.update(status="failed", phase="failed", error=str(error))
    finally:
        (directory / "simulation-result.json").write_text(json.dumps(job, indent=2))


@app.post("/execute", status_code=202)
async def start(request: dict):
    ready()
    if set(request) - {"run_id", "skill", "paper_pose"} or not re.fullmatch(
        r"[a-f0-9]{32}", str(request.get("run_id", ""))
    ):
        raise HTTPException(422, "Invalid execution request or run ID.")
    try:
        validate_skill(request["skill"], CONTRACTS, CONFIG)
        paper_pose(CONFIG, request.get("paper_pose"))
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise HTTPException(422, str(error)) from error
    async with app.state.lock:
        run_id = request["run_id"]
        if run_id in app.state.jobs:
            if app.state.jobs[run_id]["request"] != request:
                raise HTTPException(409, "Run ID was already used with different inputs.")
            return {k: v for k, v in app.state.jobs[run_id].items() if k != "request"}
        if any(job["status"] == "running" for job in app.state.jobs.values()):
            raise HTTPException(409, "Simulation is already drawing.")
        app.state.jobs[run_id] = {
            "run_id": run_id,
            "status": "running",
            "phase": "initializing",
            "request": request,
        }
        directory = DATA / "runs" / run_id
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "simulation-result.json").write_text(
            json.dumps(app.state.jobs[run_id], indent=2)
        )
        app.state.task = asyncio.create_task(
            run_job(run_id, request["skill"], request.get("paper_pose"))
        )
    return {"run_id": run_id, "status": "running", "phase": "initializing"}


@app.get("/jobs/{run_id}")
def job(run_id: str):
    if run_id not in app.state.jobs:
        raise HTTPException(404, "Unknown drawing run.")
    return {k: v for k, v in app.state.jobs[run_id].items() if k != "request"}
