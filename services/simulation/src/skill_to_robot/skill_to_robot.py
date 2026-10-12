# Purpose: Validate skill intent and produce bounded robot manipulation targets.
import json
from pathlib import Path

import numpy as np
from jsonschema import Draft202012Validator


def validate_skill(skill: dict, schema_path: Path, config: dict) -> None:
    validator = Draft202012Validator(json.loads(schema_path.read_text()))
    validator.validate(skill)
    times = [event["time"] for event in skill["events"]]
    if any(a >= b for a, b in zip(times, times[1:])):
        raise ValueError("Manipulation events must be strictly ordered.")
    points = [skill["start"], skill["goal"], *skill.get("transport", [])]
    for coordinates in points:
        point = np.asarray(coordinates, dtype=float)
        if not np.isfinite(point).all() or np.any(np.abs(point[:2]) > config["workspace_limit"]):
            raise ValueError("Skill target is outside the supported robot workspace.")
        if not config["table_height"] <= point[2] <= config["table_height"] + 0.12:
            raise ValueError("Skill must start and end on the supported table plane.")
    if abs(skill["goal"][2] - skill["start"][2]) > config["placement_tolerance"]:
        raise ValueError("Unsupported change in placement height.")
    if skill["calibration"]["plane"] == "front" and any(
        abs(point[0] - skill["start"][0]) > 0.000001 for point in points
    ):
        raise ValueError("Front-plane mapping does not support world X displacement.")
    path = skill.get("transport")
    if path is not None:
        if not np.allclose(path[0], skill["start"], atol=1e-6, rtol=0) or not np.allclose(
            path[-1], skill["goal"], atol=1e-6, rtol=0
        ):
            raise ValueError("Transport endpoints must match skill start and goal.")
        if any(abs(point[2] - skill["start"][2]) > 1e-6 for point in path):
            raise ValueError("Transport waypoints must share the table-height anchor.")
    if not np.isfinite(skill["approach_height"]):
        raise ValueError("Approach clearance must be finite.")


def robot_targets(skill: dict, object_position: np.ndarray, config: dict) -> list[dict]:
    start = np.array(object_position, dtype=float)
    goal = start + np.array(skill["goal"]) - np.array(skill["start"])
    height = skill["approach_height"]
    grasp = start + [0, 0, config["grasp_z_offset"]]
    place = goal + [0, 0, config["grasp_z_offset"] + 0.003]
    path = skill.get("transport", [skill["start"], skill["goal"]])
    transport = [
        {
            "phase": "transport",
            "target": start
            + np.array(point)
            - np.array(skill["start"])
            + [0, 0, config["grasp_z_offset"] + 0.003 + height],
            "gripper": 1,
        }
        for point in path[1:]
    ]
    return [
        {"phase": "approach", "target": grasp + [0, 0, height], "gripper": -1},
        {"phase": "descend", "target": grasp, "gripper": -1},
        {"phase": "grasp", "target": grasp, "gripper": 1},
        {"phase": "lift", "target": grasp + [0, 0, height], "gripper": 1},
        *transport,
        {"phase": "place", "target": place, "gripper": 1},
        {"phase": "release", "target": place, "gripper": -1},
        {"phase": "retreat", "target": place + [0, 0, height], "gripper": -1},
    ]
