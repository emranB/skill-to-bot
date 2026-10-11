# Purpose: Verify the controller runs against physics and reports measured outcomes.
import json
from pathlib import Path

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
