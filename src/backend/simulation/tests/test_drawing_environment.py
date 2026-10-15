# Purpose: Verify real scene state, contact-gated measured ink, reset and nonblank offscreen rendering.
import numpy as np

from src.drawing_environment.drawing_environment import CONFIG, DrawingEnvironment


def test_real_scene_ink_gate_and_reset():
    environment = DrawingEnvironment(CONFIG)
    try:
        first = environment.tip_position()
        frame = environment.render()
        assert frame.shape == (CONFIG["height"], CONFIG["width"], 3) and frame.std() > 10
        assert environment.deposit(0, [0, 0, CONFIG["pen_up_height"]], 0.5, "draw") is None
        assert environment.deposit(0, [0, 0, CONFIG["pen_tip_radius"]], 0.5, "lift") is None
        assert environment.deposit(0, [1, 0, CONFIG["pen_tip_radius"]], 0.5, "draw") is None
        a = environment.deposit(0, [0, 0, CONFIG["pen_tip_radius"]], 0, "draw")
        b = environment.deposit(1, [0.01, 0, CONFIG["pen_tip_radius"]], 1, "draw")
        assert b["radius"] > a["radius"]
        assert np.allclose(
            environment.env.sim.model.geom_pos[environment.ink_ids[1]][:2], [0.01, 0]
        )
        for index in range(1001):
            environment.deposit(index + 2, [0, 0, CONFIG["pen_tip_radius"]], 0.5, "draw")
        assert environment.render().std() > 10
        assert environment.env.sim._render_context_offscreen.scn.ngeom > 1000
        environment.reset()
        assert not environment.ink
        assert np.all(environment.env.sim.model.geom_rgba[environment.ink_ids, 3] == 0)
        assert np.allclose(first, environment.tip_position())
    finally:
        environment.close()
