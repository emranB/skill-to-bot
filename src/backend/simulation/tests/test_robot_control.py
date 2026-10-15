# Purpose: Verify all usable paper corners and continuous measured drawing under real Panda physics.
import json

import numpy as np

from src.drawing_environment.drawing_environment import CONFIG, DrawingEnvironment
from src.robot_control.robot_control import execute, path_distance
from src.skill_to_robot.skill_to_robot import robot_plan


def test_shape_evaluation_detects_a_missing_loop():
    desired = [[0, 0], [0.01, 0.01], [0.02, 0]]
    actual = [[0, 0], [0.02, 0]]
    assert path_distance(actual, desired) == 0
    assert path_distance(desired, actual) > CONFIG["shape_tolerance"]


def test_physics_reaches_all_usable_corners(tmp_path):
    skill = {
        "source": {"type": "synthetic_fixture"},
        "aspect_ratio": 1.6,
        "strokes": [
            {
                "points": [
                    {"x": x, "y": y, "t": i}
                    for i, (x, y) in enumerate([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
                ]
            }
        ],
    }
    environment = DrawingEnvironment(CONFIG)
    try:
        plan = robot_plan(skill, CONFIG)
        result = execute(environment, plan, tmp_path, CONFIG, lambda phase, stroke: None)
        assert result["success"], result
        trace = json.loads((tmp_path / "trace.json").read_text())
        assert len(trace["ink"]) > 100
        assert all(s["ink_radius"] is None for s in trace["samples"] if s["phase"] != "draw")
        assert result["max_path_error_m"] <= CONFIG["max_path_error"]
        assert abs(result["execution_duration_s"] - environment.env.sim.data.time) < 1e-6
        assert trace["samples"][-1]["t"] == result["execution_duration_s"]
        for a, b in zip(trace["samples"], trace["samples"][1:]):
            if a["phase"] == b["phase"] == "draw":
                speed = np.linalg.norm(np.asarray(b["desired_local"]) - a["desired_local"]) / (
                    b["t"] - a["t"]
                )
                assert speed <= CONFIG["drawing_speed"] + 1e-8
        assert (tmp_path / "simulation.mp4").stat().st_size > 10000
    finally:
        environment.close()


def test_partial_drawing_fails_without_losing_trace(tmp_path):
    config = {**CONFIG, "max_ink_points": 2}
    skill = {
        "source": {"type": "synthetic_fixture"},
        "aspect_ratio": 1.5,
        "strokes": [{"points": [{"x": 0.4, "y": 0.5, "t": 0}, {"x": 0.6, "y": 0.5, "t": 1}]}],
    }
    environment = DrawingEnvironment(config)
    try:
        result = execute(
            environment, robot_plan(skill, config), tmp_path, config, lambda phase, stroke: None
        )
        assert not result["success"] and "ink pool" in result["error"]
        trace = json.loads((tmp_path / "trace.json").read_text())
        assert trace["samples"] and len(trace["ink"]) == 2
        assert result["strokes_completed"] == 0
    finally:
        environment.close()
