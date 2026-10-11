# Purpose: Extract ordered manipulation intent from tracked object motion and serve perception.
import json
import math
import os
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException
from jsonschema import Draft202012Validator, ValidationError
from src.object_tracking.object_tracking import track_object
from src.video_input.video_input import read_video

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / "config.json").read_text())
for key, value in CONFIG.items():
    if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"Invalid positive perception setting: {key}")
CONTRACTS = Path(os.environ.get("CONTRACTS_DIR", str(ROOT.parent.parent / "contracts")))
VALIDATOR = Draft202012Validator(json.loads((CONTRACTS / "skill.schema.json").read_text()))
DATA = Path(os.environ.get("DATA_DIR", str(ROOT.parent.parent / "data"))).resolve()
app = FastAPI(title="skill-to-bot perception", version="0.1.0")


def extract_skill(samples: list[dict], calibration: dict, video: str, config: dict) -> dict:
    if calibration.get("method") != "operator_planar" or calibration.get("plane") != "front":
        raise ValueError("Explicit front-plane operator calibration is required.")
    span = calibration.get("workspace_span", 0)
    if not isinstance(span, (int, float)) or not math.isfinite(span) or not 0.05 <= span <= 0.5:
        raise ValueError("Workspace span must be between 0.05 and 0.5 meters.")
    if len(samples) < config["min_samples"]:
        raise ValueError("Too few observations to extract a skill.")
    uv = np.array([[s["u"], s["v"]] for s in samples])
    # A short median window suppresses single-frame tracker jumps without hiding sustained motion.
    smooth = np.array([np.median(uv[max(0, i - 2) : i + 3], axis=0) for i in range(len(uv))])
    start_uv = np.median(smooth[:5], axis=0)
    goal_uv = np.median(smooth[-5:], axis=0)
    motion = np.linalg.norm(smooth - start_uv, axis=1)
    moving = np.flatnonzero(motion > config["motion_threshold"])
    if len(moving) < 5:
        raise ValueError("No sustained manipulation motion was detected.")
    grasp_index = max(0, int(moving[0]) - 1)
    lift = start_uv[1] - smooth[:, 1]
    if float(np.max(lift)) < config["lift_threshold"]:
        raise ValueError("The selected object does not show a visible lift.")
    settled = np.linalg.norm(smooth - goal_uv, axis=1) < config["settle_threshold"]
    place_index = len(samples) - 1
    for i in range(int(moving[0]) + 3, len(samples) - config["settle_frames"]):
        if settled[i : i + config["settle_frames"]].all():
            place_index = i
            break
    if place_index >= len(samples) - config["settle_frames"]:
        raise ValueError("No stable placement and release interval was observed.")
    if abs(float(goal_uv[1] - start_uv[1])) > config["placement_vertical_tolerance"]:
        raise ValueError("Final object position is not on the original placement plane.")
    goal_y = -float(goal_uv[0] - start_uv[0]) * span
    if abs(goal_y) < config["min_transfer_distance"]:
        raise ValueError("Demonstration has insufficient sideways transport.")
    skill = {
        "version": "1.0",
        "object": "can",
        "frame": "world",
        "units": "meters",
        "start": [0.0, 0.0, config["object_center_height"]],
        "goal": [0.0, goal_y, config["object_center_height"]],
        "approach_height": max(0.08, min(0.2, float(np.max(lift)) * span)),
        "events": [
            {"type": "grasp", "time": samples[grasp_index]["time"]},
            {"type": "transport", "time": samples[min(grasp_index + 2, place_index - 1)]["time"]},
            {"type": "place", "time": samples[place_index]["time"]},
            {"type": "release", "time": samples[place_index + config["settle_frames"]]["time"]},
        ],
        "calibration": calibration,
        "source": {"video": video, "confidence": 0.75, "samples": len(samples)},
    }
    VALIDATOR.validate(skill)
    return skill


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
        samples = track_object(read_video(path, CONFIG), calibration["roi"], CONFIG)
        skill = extract_skill(samples, calibration, video, CONFIG)
        return {
            "skill": skill,
            "observations": samples,
            "limitations": [
                "Front-plane intent mapping uses operator scale; depth is not measured.",
                "Grasp and release are motion-derived event estimates, not hand-contact measurements.",
                "Confidence is a heuristic, not a calibrated probability.",
            ],
        }
    except (ValueError, KeyError, TypeError, ValidationError) as error:
        raise HTTPException(422, str(error)) from error
