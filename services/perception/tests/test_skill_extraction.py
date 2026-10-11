# Purpose: Verify motion-derived intent, event order, and rejection of insufficient evidence.
import numpy as np
import pytest
from src.skill_extraction.skill_extraction import CONFIG, extract_skill

CALIBRATION = {
    "method": "operator_planar",
    "plane": "front",
    "workspace_span": 0.3,
    "roi": [0.1, 0.1, 0.2, 0.4],
}


def observations():
    u = np.r_[np.full(20, 0.6), np.linspace(0.6, 0.2, 40), np.full(40, 0.2)]
    v = np.r_[
        np.full(20, 0.6),
        np.linspace(0.6, 0.4, 15),
        np.full(10, 0.4),
        np.linspace(0.4, 0.6, 15),
        np.full(40, 0.6),
    ]
    return [{"time": i / 20, "u": float(x), "v": float(y)} for i, (x, y) in enumerate(zip(u, v))]


def test_motion_derived_goal_and_order():
    skill = extract_skill(observations(), CALIBRATION, "fixture.mp4", CONFIG)
    assert skill["goal"][1] == pytest.approx(0.12)
    assert [e["type"] for e in skill["events"]] == ["grasp", "transport", "place", "release"]
    times = [e["time"] for e in skill["events"]]
    assert all(a < b for a, b in zip(times, times[1:]))


def test_stationary_and_missing_calibration():
    with pytest.raises(ValueError, match="calibration"):
        extract_skill(observations(), {}, "fixture.mp4", CONFIG)
    stationary = [{"time": i / 20, "u": 0.5, "v": 0.5} for i in range(100)]
    with pytest.raises(ValueError, match="motion"):
        extract_skill(stationary, CALIBRATION, "fixture.mp4", CONFIG)


def test_no_lift_or_stable_placement():
    samples = observations()
    for sample in samples:
        sample["v"] = 0.5
    with pytest.raises(ValueError, match="lift"):
        extract_skill(samples, CALIBRATION, "fixture.mp4", CONFIG)
    with pytest.raises(ValueError, match="placement"):
        extract_skill(observations()[:45], CALIBRATION, "fixture.mp4", CONFIG)
