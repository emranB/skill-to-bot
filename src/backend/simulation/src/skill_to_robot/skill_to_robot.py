# Purpose: Validate DRAW skills and map paper-local strokes to Panda pen-tip targets.
import json
import math
from pathlib import Path

import numpy as np
from jsonschema import Draft202012Validator


def validate_skill(skill: dict, contracts: Path, config: dict) -> None:
    json.dumps(skill, allow_nan=False)
    Draft202012Validator(json.loads((contracts / "skill.schema.json").read_text())).validate(skill)
    all_points = [p for stroke in skill["strokes"] for p in stroke["points"]]
    if len(all_points) > config["max_skill_points"]:
        raise ValueError("Drawing skill has too many samples.")
    if any(a["t"] > b["t"] for a, b in zip(all_points, all_points[1:])):
        raise ValueError("Skill timestamps must be monotonic.")
    for stroke in skill["strokes"]:
        points = stroke["points"]
        if (
            points[-1]["t"] <= points[0]["t"]
            or sum(math.hypot(b["x"] - a["x"], b["y"] - a["y"]) for a, b in zip(points, points[1:]))
            < 1e-6
        ):
            raise ValueError("Drawing stroke has no executable motion.")
    pressure = skill["source"]["pressure_observed"]
    available = any("pressure" in p for p in all_points)
    if pressure and not available or skill["source"]["pointer_type"] == "mouse" and available:
        raise ValueError("Skill pressure must agree with source metadata.")
    if any(len({"pressure" in p for p in s["points"]}) != 1 for s in skill["strokes"]):
        raise ValueError("Pressure availability must remain consistent within each stroke.")
    if not pressure:
        for stroke in skill["strokes"]:
            values = [p["pressure"] for p in stroke["points"] if "pressure" in p]
            if values and max(values) - min(values) > config["pressure_tolerance"]:
                raise ValueError("Variable pressure needs observed-pressure metadata.")


def paper_pose(config: dict, pose: dict | None = None):
    pose = {"offset": [0, 0], "yaw": 0} if pose is None else pose
    if (
        not isinstance(pose, dict)
        or set(pose) != {"offset", "yaw"}
        or not isinstance(pose["offset"], list)
        or len(pose["offset"]) != 2
    ):
        raise ValueError("Paper pose needs two offset coordinates and yaw.")
    values = [*pose["offset"], pose["yaw"]]
    if any(
        isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
        for v in values
    ):
        raise ValueError("Paper pose must be finite.")
    if any(abs(v) > 0.025 for v in pose["offset"]) or abs(pose["yaw"]) > math.radians(15):
        raise ValueError("Paper pose is outside the supported reachable region.")
    center = np.asarray(config["paper_center"]) + [*pose["offset"], 0]
    yaw = config["paper_yaw"] + pose["yaw"]
    c, s = math.cos(yaw), math.sin(yaw)
    rotation = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    return center, rotation


def robot_plan(skill: dict, config: dict, pose: dict | None = None) -> dict:
    center, rotation = paper_pose(config, pose)
    width = config["paper_width"] - 2 * config["paper_margin"]
    height = config["paper_height"] - 2 * config["paper_margin"]
    scale = min(width / skill["aspect_ratio"], height)
    phases = []
    draw_z = config["pen_tip_radius"] - config["contact_depth"]
    for stroke_id, stroke in enumerate(skill["strokes"]):
        points = []
        for p in stroke["points"]:
            local = np.array(
                [(p["x"] - 0.5) * scale * skill["aspect_ratio"], (p["y"] - 0.5) * scale, draw_z]
            )
            if abs(local[0]) > width / 2 + 1e-9 or abs(local[1]) > height / 2 + 1e-9:
                raise ValueError("Mapped drawing point lies outside paper margins.")
            points.append(
                {
                    "local": local.tolist(),
                    "tip": (center + rotation @ local).tolist(),
                    "t": p["t"],
                    "pressure": p.get("pressure"),
                }
            )
        start, end = np.array(points[0]["tip"]), np.array(points[-1]["tip"])
        phases.extend(
            [
                {
                    "phase": "approach",
                    "stroke": stroke_id,
                    "target": (start + [0, 0, config["pen_up_height"]]).tolist(),
                },
                {"phase": "descend", "stroke": stroke_id, "target": start.tolist()},
                {
                    "phase": "draw",
                    "stroke": stroke_id,
                    "points": points,
                    "color": stroke.get("color", config["default_color"]),
                    "brush_radius": stroke.get("brush_size", config["default_brush_size"])
                    * scale
                    / 2,
                },
                {
                    "phase": "lift",
                    "stroke": stroke_id,
                    "target": (end + [0, 0, config["pen_up_height"]]).tolist(),
                },
            ]
        )
    return {
        "frame": "world",
        "units": "meters",
        "embodiment": "Panda",
        "tool_offset": [0, 0, config["pen_length"]],
        "paper_center": center.tolist(),
        "paper_rotation": rotation.tolist(),
        "park_tip": (center + rotation @ config["park_offset"]).tolist(),
        "phases": phases,
    }


def eef_target(tip, orientation, tool_offset):
    return np.asarray(tip) - np.asarray(orientation) @ np.asarray(tool_offset)
