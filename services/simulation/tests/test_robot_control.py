# Purpose: Verify the controller runs against physics and reports measured outcomes.
import json
from pathlib import Path

import numpy as np
import pytest
from src.robot_control.robot_control import execute
from src.simulation_environment.simulation_environment import CONFIG, SimulationEnvironment


def test_physics_transfer(tmp_path):
    fixture = Path("/fixtures/skill.json")
    if not fixture.exists():
        fixture = Path(__file__).resolve().parents[3] / "tests/fixtures/skill.json"
    environment = SimulationEnvironment(CONFIG)
    try:
        result = execute(
            environment,
            json.loads(fixture.read_text()),
            tmp_path / "simulation.mp4",
            CONFIG,
            lambda phase: None,
        )
        assert result["success"], result
        assert result["lifted"] and result["grasped"] and result["released"]
        assert result["position_error_m"] <= CONFIG["placement_tolerance"]
        assert (tmp_path / "simulation.mp4").stat().st_size > 1000
    finally:
        environment.close()


@pytest.mark.parametrize(
    "path",
    [
        [[0, 0], [0, 0.08]],
        [[0, 0], [0.05, 0], [0, 0]],
        [[0, 0], [0.05, 0], [0.05, 0.08]],
        [[0, 0], [0.05, 0], [0.05, 0.08], [-0.03, 0.08], [-0.03, 0.03]],
        [[0, 0], [0.05, 0], [0.05, 0.08], [0, 0.08], [0.001, 0]],
    ],
)
def test_physics_follows_ordered_transport(tmp_path, path):
    skill = json.loads(Path("/fixtures/skill.json").read_text())
    skill["calibration"]["plane"] = "table"
    skill["approach_height"] = 0.08
    skill["transport"] = [[x, y, 0.95] for x, y in path]
    skill["goal"] = skill["transport"][-1]
    environment = SimulationEnvironment(CONFIG)
    try:
        result = execute(environment, skill, tmp_path / "transport.mp4", CONFIG, lambda phase: None)
        assert result["success"], result
        assert len(result["transport"]) == len(path) - 1
        initial = np.array(result["initial"])
        for measured, point in zip(result["transport"], path[1:]):
            assert np.allclose(np.array(measured["target"])[:2] - initial[:2], point)
            assert measured["error_m"] <= CONFIG["placement_tolerance"]
    finally:
        environment.close()
