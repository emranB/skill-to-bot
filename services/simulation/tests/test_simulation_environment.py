# Purpose: Verify real LIBERO initialization, deterministic reset, and nonblank rendering.
import numpy as np
import pytest
from src.simulation_environment.simulation_environment import CONFIG, SimulationEnvironment


@pytest.mark.parametrize(
    "setting,value",
    [("width", 1.5), ("execution_timeout", -1), ("hold_steps", CONFIG["max_phase_steps"])],
)
def test_invalid_configuration(setting, value):
    with pytest.raises(ValueError):
        SimulationEnvironment({**CONFIG, setting: value})


def test_real_environment_reset_render():
    environment = SimulationEnvironment(CONFIG)
    try:
        first = environment.object_position()
        second = np.array(environment.reset())
        assert np.allclose(first, second, atol=0.003)
        frame = environment.render()
        assert frame.shape == (CONFIG["height"], CONFIG["width"], 3)
        assert frame.std() > 10
        assert np.isfinite(first).all()
    finally:
        environment.close()
