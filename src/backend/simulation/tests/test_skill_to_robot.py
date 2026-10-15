# Purpose: Verify strict skills, paper transforms, disconnected phases and rigid tool compensation.

import numpy as np
import pytest
from jsonschema import ValidationError

from src.drawing_environment.drawing_environment import CONFIG, CONTRACTS, validate_config
from src.skill_to_robot.skill_to_robot import eef_target, paper_pose, robot_plan, validate_skill


def skill():
    return {
        "version": "2.0",
        "primitive": "draw",
        "frame": "paper_normalized",
        "aspect_ratio": 1.5,
        "source": {
            "demonstration_id": "a" * 32,
            "type": "synthetic_fixture",
            "pointer_type": "mouse",
            "pressure_observed": False,
        },
        "strokes": [
            {
                "points": [
                    {"x": 0, "y": 0, "t": 0},
                    {"x": 1, "y": 0, "t": 1},
                    {"x": 1, "y": 1, "t": 2},
                    {"x": 0, "y": 1, "t": 3},
                ]
            }
        ],
    }


def test_paper_corners_pose_and_tool():
    value = skill()
    validate_skill(value, CONTRACTS, CONFIG)
    for pose in (None, {"offset": [0.015, -0.01], "yaw": 0.12}):
        plan = robot_plan(value, CONFIG, pose)
        center, rotation = paper_pose(CONFIG, pose)
        assert [p["phase"] for p in plan["phases"]] == ["approach", "descend", "draw", "lift"]
        for point in plan["phases"][2]["points"]:
            local = np.asarray(point["local"])
            assert np.allclose(point["tip"], center + rotation @ local)
            assert abs(local[0]) == pytest.approx(0.075)
            assert abs(local[1]) == pytest.approx(0.05)
        orientation = np.diag([1, -1, -1])
        target = np.array(plan["phases"][1]["target"])
        assert np.allclose(
            eef_target(target, orientation, plan["tool_offset"])
            + orientation @ np.array(plan["tool_offset"]),
            target,
        )
        assert plan["phases"][0]["target"][2] - target[2] == pytest.approx(CONFIG["pen_up_height"])
    value["strokes"] *= 2
    assert [p["phase"] for p in robot_plan(value, CONFIG)["phases"]] == [
        "approach",
        "descend",
        "draw",
        "lift",
    ] * 2
    value = skill()
    value["source"]["pointer_type"] = "pen"
    for stroke in value["strokes"]:
        stroke.update(color="#dc5278", brush_size=0.025)
        for point in stroke["points"]:
            point["pressure"] = 0.8
    validate_skill(value, CONTRACTS, CONFIG)
    draw = robot_plan(value, CONFIG)["phases"][2]
    assert draw["color"] == "#dc5278" and draw["brush_radius"] == pytest.approx(0.00125)
    assert all(p["pressure"] == 0.8 for p in draw["points"])


@pytest.mark.parametrize(
    "kind", ["primitive", "leak", "finite", "timing", "pressure", "bound", "source"]
)
def test_invalid_skill(kind):
    value = skill()
    if kind == "primitive":
        value["primitive"] = "pick_place"
    if kind == "leak":
        value["table_height"] = 0.8
    if kind == "finite":
        value["strokes"][0]["points"][0]["x"] = float("nan")
    if kind == "timing":
        value["strokes"][0]["points"][1]["t"] = 4
    if kind == "pressure":
        value["strokes"][0]["points"][0]["pressure"] = 0.5
    if kind == "source":
        value["source"]["type"] = "unsupported"
    if kind == "bound":
        value["strokes"][0]["points"][0]["x"] = 1.1
    with pytest.raises((ValueError, ValidationError)):
        validate_skill(value, CONTRACTS, CONFIG)


@pytest.mark.parametrize(
    "change",
    [
        {"paper_margin": 0.2},
        {"contact_tolerance": 0.1},
        {"width": 1.2},
        {"drawing_speed": float("nan")},
        {"min_contact_coverage": 2},
        {"min_visible_paper": 2},
    ],
)
def test_invalid_config(change):
    with pytest.raises(ValueError):
        validate_config(CONFIG | change)


def test_reject_unreachable_pose():
    with pytest.raises(ValueError):
        paper_pose(CONFIG, {"offset": [1, 0], "yaw": 0})
