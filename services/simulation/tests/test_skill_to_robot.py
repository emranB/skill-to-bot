# Purpose: Verify skill boundaries and target generation without executing physics.
import copy
import json
import os
from pathlib import Path

import numpy as np
import pytest
from jsonschema import ValidationError
from src.skill_to_robot.skill_to_robot import robot_targets, validate_skill

ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCHEMA = Path(os.environ.get("CONTRACTS_DIR", str(ROOT / "contracts"))) / "skill.schema.json"
CONFIG = json.loads((Path(__file__).resolve().parents[1] / "config.json").read_text())


@pytest.fixture
def skill():
    path = (
        Path("/fixtures/skill.json")
        if Path("/fixtures/skill.json").exists()
        else ROOT / "tests/fixtures/skill.json"
    )
    return json.loads(path.read_text())


def test_target_transfer(skill):
    validate_skill(skill, SCHEMA, CONFIG)
    targets = robot_targets(skill, np.array([0.02, -0.03, 0.95]), CONFIG)
    assert targets[4]["target"][1] == pytest.approx(0.12)
    assert (
        targets[0]["gripper"] == -1 and targets[2]["gripper"] == 1 and targets[-1]["gripper"] == -1
    )


@pytest.mark.parametrize(
    "field,value", [("version", "99"), ("goal", [0, 2, 0.95]), ("goal", [0, 0.15, float("nan")])]
)
def test_invalid_contract_or_workspace(skill, field, value):
    invalid = copy.deepcopy(skill)
    invalid[field] = value
    with pytest.raises((ValueError, ValidationError)):
        validate_skill(invalid, SCHEMA, CONFIG)


def test_event_order(skill):
    skill["events"][1]["time"] = 1
    with pytest.raises(ValueError, match="ordered"):
        validate_skill(skill, SCHEMA, CONFIG)


def test_unsupported_object_and_depth(skill):
    skill["object"] = "unknown-object"
    with pytest.raises(ValidationError):
        validate_skill(skill, SCHEMA, CONFIG)
    skill["object"] = "can"
    skill["goal"][0] = 0.05
    with pytest.raises(ValueError, match="world X"):
        validate_skill(skill, SCHEMA, CONFIG)


def test_waypoints_are_bounded_ordered_and_backward_compatible(skill):
    skill["calibration"]["plane"] = "table"
    skill["transport"] = [skill["start"], [0.05, 0.08, 0.95], [-0.04, 0.12, 0.95], skill["goal"]]
    validate_skill(skill, SCHEMA, CONFIG)
    initial = np.array([0, 0, 0.95])
    targets = [
        target for target in robot_targets(skill, initial, CONFIG) if target["phase"] == "transport"
    ]
    assert len(targets) == 3
    assert all(target["gripper"] == 1 for target in targets)
    assert np.allclose(targets[0]["target"][:2], [0.05, 0.08])
    for point in ([0.3, 0, 0.95], [0, 0.1, float("nan")], [0, 0.1, 1.0]):
        skill["transport"][1] = point
        with pytest.raises((ValueError, ValidationError)):
            validate_skill(skill, SCHEMA, CONFIG)
