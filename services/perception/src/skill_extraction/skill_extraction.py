# Purpose: Extract ordered manipulation intent from tracked object motion and serve perception.
import json
import logging
import math
import os
from itertools import chain
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from jsonschema import Draft202012Validator, ValidationError
from src.object_segmentation.object_segmentation import load_segmenter
from src.object_tracking.object_tracking import track_object
from src.support_surface.support_surface import assign_calibrated_surface, surface_pose
from src.video_input.video_input import read_video

logger = logging.getLogger("perception")

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / "config.json").read_text())
for key, value in CONFIG.items():
    if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"Invalid positive perception setting: {key}")
CONTRACTS = Path(os.environ.get("CONTRACTS_DIR", str(ROOT.parent.parent / "contracts")))
VALIDATOR = Draft202012Validator(json.loads((CONTRACTS / "skill.schema.json").read_text()))
CALIBRATION_VALIDATOR = Draft202012Validator(VALIDATOR.schema["properties"]["calibration"])
DATA = Path(os.environ.get("DATA_DIR", str(ROOT.parent.parent / "data"))).resolve()
app = FastAPI(title="skill-to-bot perception", version="0.1.0")


def _median_series(values: np.ndarray, radius: int) -> np.ndarray:
    return np.array(
        [np.median(values[max(0, i - radius) : i + radius + 1]) for i in range(len(values))]
    )


def _true_runs(flags: np.ndarray) -> list[tuple[int, int]]:
    runs = []
    start = None
    for index, flag in enumerate(flags):
        if flag and start is None:
            start = index
        elif not flag and start is not None:
            runs.append((start, index - 1))
            start = None
    if start is not None:
        runs.append((start, len(flags) - 1))
    return runs


def extract_skill(samples: list[dict], calibration: dict, video: str, config: dict) -> dict:
    validate_calibration(calibration, config)
    span = calibration["workspace_span"]
    if len(samples) < config["min_samples"]:
        raise ValueError("Too few observations to extract a skill.")
    calibrated = calibration["method"] == "support_plane"
    if calibrated:
        assign_calibrated_surface(samples, calibration, config)
    uv = np.array([s["surface_position"] if calibrated else [s["u"], s["v"]] for s in samples])
    # A short median window suppresses single-frame tracker jumps without hiding sustained motion.
    smooth = np.array([np.median(uv[max(0, i - 2) : i + 3], axis=0) for i in range(len(uv))])
    start_uv = np.median(smooth[:5], axis=0)
    goal_uv = np.median(smooth[-5:], axis=0)
    motion = np.linalg.norm(smooth - start_uv, axis=1)
    moving = np.flatnonzero(
        motion > (config["surface_motion_tolerance"] if calibrated else config["motion_threshold"])
    )
    if len(moving) < 5:
        raise ValueError("No sustained manipulation motion was detected.")
    if any("separation" not in sample for sample in samples):
        raise ValueError("Support-surface evidence is required to judge lift and placement.")
    separation = _median_series(np.array([float(sample["separation"]) for sample in samples]), 2)
    lifted = separation >= config["separation_threshold"]
    lift_runs = [
        run for run in _true_runs(lifted) if run[1] - run[0] + 1 >= config["separation_frames"]
    ]
    if not lift_runs:
        if float(np.max(separation)) >= config["separation_ambiguous"]:
            raise ValueError(
                "Not enough evidence that the object separated from the support surface."
            )
        raise ValueError("The selected object stays on the support surface.")
    grasp_index = max(0, min(lift_runs[0][0], int(moving[0])) - 1)
    settled = np.linalg.norm(smooth - goal_uv, axis=1) < (
        config["surface_motion_tolerance"] if calibrated else config["settle_threshold"]
    )
    place_index = len(samples) - 1
    for index in range(lift_runs[-1][1] + 1, len(samples) - config["settle_frames"]):
        window = slice(index, index + config["settle_frames"])
        if (~lifted[window]).all() and settled[window].all():
            place_index = index
            break
    if place_index >= len(samples) - config["settle_frames"]:
        raise ValueError("No stable placement and release interval was observed.")
    scale = span / calibration["surface"]["size"][0] if calibrated else span
    delta = (smooth[grasp_index : place_index + 1] - start_uv) * scale
    depth_sign = 1 if calibrated else -1 if calibration["plane"] == "table" else 0
    path = np.column_stack((delta[:, 1] * depth_sign, -delta[:, 0]))
    goal_delta = (goal_uv - start_uv) * scale
    goal = [
        float(goal_delta[1] * depth_sign),
        -float(goal_delta[0]),
        config["object_center_height"],
    ]
    path = simplify_transport(np.vstack(([0.0, 0.0], path, goal[:2])), config)
    transport_index = min(grasp_index + 2, place_index - 1)
    events = [
        {"type": "grasp", "time": samples[grasp_index]["time"]},
        {"type": "transport", "time": samples[transport_index]["time"]},
        {"type": "place", "time": samples[place_index]["time"]},
        {
            "type": "release",
            "time": samples[place_index + config["settle_frames"]]["time"],
        },
    ]
    if any(events[i]["time"] >= events[i + 1]["time"] for i in range(3)):
        raise ValueError("No stable placement and release interval was observed.")
    # The skill object name is the simulated can required by the existing contract.
    skill = {
        "version": "1.0",
        "object": "can",
        "frame": "world",
        "units": "meters",
        "start": [0.0, 0.0, config["object_center_height"]],
        "goal": goal,
        "transport": [[float(x), float(y), config["object_center_height"]] for x, y in path],
        "approach_height": config["approach_clearance"],
        "events": events,
        "calibration": calibration,
        "source": {"video": video, "confidence": 0.75, "samples": len(samples)},
    }
    VALIDATOR.validate(skill)
    return skill


def simplify_transport(points, config: dict) -> np.ndarray:
    """Simplify against finite segments so collinear reversals cannot disappear."""
    points = np.asarray(points, dtype=float)
    keep = {0, len(points) - 1}
    pending = [(0, len(points) - 1)]
    while pending:
        first, last = pending.pop()
        if last - first <= 1:
            continue
        segment = points[first : last + 1]
        direction = segment[-1] - segment[0]
        length_squared = float(direction @ direction)
        fraction = (
            np.clip((segment - segment[0]) @ direction / length_squared, 0, 1)
            if length_squared
            else np.zeros(len(segment))
        )
        distances = np.linalg.norm(segment - (segment[0] + fraction[:, None] * direction), axis=1)
        index = int(np.argmax(distances))
        if distances[index] <= config["trajectory_tolerance"]:
            continue
        middle = first + index
        keep.add(middle)
        if len(keep) > 32:
            raise ValueError("Transport is too complex for the bounded 32-waypoint execution.")
        pending.extend([(first, middle), (middle, last)])
    path = points[sorted(keep)]
    if (
        len(path) < 2
        or np.linalg.norm(np.diff(path, axis=0), axis=1).sum() < config["min_transfer_distance"]
    ):
        raise ValueError("Demonstration has insufficient transport beyond tracking jitter.")
    if len(path) > 32:
        raise ValueError("Transport is too complex for the bounded 32-waypoint execution.")
    path[0], path[-1] = points[0], points[-1]
    return path


@app.get("/health")
def health():
    return {"service": "perception", "status": "ok"}


@app.get("/ready")
def ready():
    return {"service": "perception", "status": "ready"}


@app.get("/version")
def version():
    return {"service": "perception", "version": "0.1.0"}


@app.post("/process")
def process(request: dict):
    try:
        video = request["video"]
        if (
            Path(video).name != video
            or "/" in video
            or "\\" in video
            or Path(video).suffix.lower() != ".mp4"
        ):
            raise ValueError("Use a valid MP4 demonstration name.")
        directory = "live_demos" if video.startswith("live_demo_") else "demonstrations"
        path = (DATA / directory / video).resolve()
        if path.parent != (DATA / directory).resolve():
            raise ValueError("Demonstration must stay inside its data directory.")
        calibration = request["calibration"]
        validate_calibration(calibration)
        frames = read_video(path, CONFIG)
        if calibration["method"] == "support_plane":
            frames = iter(frames)
            first = next(frames)
            height, width = first[1].shape[:2]
            if abs(width / height - calibration["surface"]["image_aspect"]) > 0.01:
                raise ValueError("Camera aspect changed. Recalibrate using the recorded frame.")
            frames = chain([first], frames)
        samples = track_object(frames, calibration["roi"], CONFIG, load_segmenter())
        skill = extract_skill(samples, calibration, video, CONFIG)
        logger.info("Extracted skill from %s using %s observations", video, len(samples))
        return {
            "skill": skill,
            "observations": samples,
            "limitations": [
                "The selection rectangle is a hint. Segmentation snaps it to the object mask.",
                "Lift means separation from the support surface, not upward image motion.",
                "A stationary monocular view can leave slide and lift ambiguous; weak evidence is rejected.",
                "Calibrated mapping requires measured support corners, fixed camera intrinsics, a rigid upright object and continuous foreground scale. Rotation, occlusion and arbitrary metric 3D are unsupported."
                if calibration["method"] == "support_plane"
                else "Transport follows the selected projected mapping and operator span; metric depth, perspective and rotation are not recovered.",
                "Grasp and release are object-motion estimates, not hand-contact measurements.",
                "Early motion is retained when lift evidence arrives later; its exact pickup/contact state is not measured.",
                "Confidence is a heuristic, not a calibrated probability.",
            ],
        }
    except (ValueError, KeyError, TypeError, ValidationError, cv2.error, StopIteration) as error:
        raise HTTPException(422, str(error)) from error


def validate_calibration(calibration: dict, config: dict = CONFIG) -> None:
    try:
        CALIBRATION_VALIDATOR.validate(calibration)
    except ValidationError as error:
        raise ValueError(f"Invalid calibration: {error.message}") from error
    roi = calibration["roi"]
    if (
        not all(math.isfinite(value) for value in roi)
        or min(roi[2:]) < 0.01
        or roi[0] + roi[2] > 1
        or roi[1] + roi[3] > 1
    ):
        raise ValueError("Object rectangle must fit inside the video.")
    if not math.isfinite(calibration["workspace_span"]):
        raise ValueError("Workspace span must be finite.")
    if calibration["method"] == "support_plane":
        surface_pose(calibration["surface"], config)


@app.post("/calibration")
def check_calibration(calibration: dict):
    try:
        validate_calibration(calibration)
        return {"status": "valid"}
    except (ValueError, KeyError, TypeError, cv2.error) as error:
        raise HTTPException(422, str(error)) from error
