# Purpose: Verify motion-derived intent, event order, and rejection of insufficient evidence.
import numpy as np
import pytest
from src.skill_extraction.skill_extraction import CONFIG, extract_skill, simplify_transport

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
    separation = np.r_[np.zeros(20), np.full(30, 0.12), np.zeros(50)]
    return [
        {"time": i / 20, "u": float(x), "v": float(y), "separation": float(s)}
        for i, (x, y, s) in enumerate(zip(u, v, separation))
    ]


def test_motion_derived_goal_and_order():
    skill = extract_skill(observations(), CALIBRATION, "fixture.mp4", CONFIG)
    assert skill["goal"][1] == pytest.approx(0.12)
    assert [e["type"] for e in skill["events"]] == [
        "grasp",
        "transport",
        "place",
        "release",
    ]
    times = [e["time"] for e in skill["events"]]
    assert all(a < b for a, b in zip(times, times[1:]))


def test_stationary_and_missing_calibration():
    with pytest.raises(ValueError, match="calibration"):
        extract_skill(observations(), {}, "fixture.mp4", CONFIG)
    stationary = [{"time": i / 20, "u": 0.5, "v": 0.5} for i in range(100)]
    with pytest.raises(ValueError, match="motion"):
        extract_skill(stationary, CALIBRATION, "fixture.mp4", CONFIG)


def test_slide_and_unstable_placement_are_rejected():
    samples = observations()
    for sample in samples:
        sample["separation"] = 0.0
    with pytest.raises(ValueError, match="support surface"):
        extract_skill(samples, CALIBRATION, "fixture.mp4", CONFIG)
    ambiguous = observations()
    for sample in ambiguous:
        sample["separation"] = 0.04
    with pytest.raises(ValueError, match="Not enough evidence"):
        extract_skill(ambiguous, CALIBRATION, "fixture.mp4", CONFIG)
    with pytest.raises(ValueError, match="placement"):
        extract_skill(observations()[:45], CALIBRATION, "fixture.mp4", CONFIG)


def test_uploaded_and_live_video_share_processing(monkeypatch, tmp_path):
    from src.skill_extraction import skill_extraction as service

    monkeypatch.setattr(service, "DATA", tmp_path)
    (tmp_path / "demonstrations").mkdir()
    (tmp_path / "live_demos").mkdir()
    seen = []

    def fake_read(path, config):
        seen.append(path.parent.name)
        return []

    def fake_track(frames, roi, config, segmenter=None):
        seen.append(segmenter)
        return observations()

    monkeypatch.setattr(service, "read_video", fake_read)
    monkeypatch.setattr(service, "track_object", fake_track)
    monkeypatch.setattr(service, "load_segmenter", lambda: "shared-segmenter")
    for name in ("uploaded.mp4", "live_demo_example.mp4"):
        result = service.process({"video": name, "calibration": CALIBRATION})
        assert result["skill"]["version"] == "1.0"
    assert seen == [
        "demonstrations",
        "shared-segmenter",
        "live_demos",
        "shared-segmenter",
    ]


def test_temporal_spikes_do_not_move_placement():
    samples = observations()
    samples[4]["separation"] = 0.2
    samples[30]["separation"] = 0.0
    skill = extract_skill(samples, CALIBRATION, "fixture.mp4", CONFIG)
    assert skill["events"][2]["time"] > 2.0
    assert [event["type"] for event in skill["events"]] == [
        "grasp",
        "transport",
        "place",
        "release",
    ]


@pytest.mark.parametrize(
    "corners",
    [
        [[0, 0], [0.1, 0]],
        [[0, 0], [0.1, 0], [0.1, 0.1]],
        [[0, 0], [0.1, 0], [0, 0]],
        [[0, 0], [0.1, 0], [0.1, 0.1], [-0.1, 0.1], [-0.1, 0]],
        [[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0.001, 0]],
    ],
)
def test_ordered_transport_preserves_excursions(corners):
    points = np.vstack([np.linspace(a, b, 20) for a, b in zip(corners, corners[1:])])
    result = simplify_transport(points, CONFIG)
    assert np.allclose(result, corners, atol=0.008)


def test_transport_removes_jitter_without_inventing_turns():
    x = np.linspace(0, 0.12, 100)
    points = np.column_stack((x, np.sin(x * 500) * 0.001))
    assert len(simplify_transport(points, CONFIG)) == 2
    with pytest.raises(ValueError, match="jitter"):
        simplify_transport(points * 0.01, CONFIG)


def test_return_to_origin_is_not_zero_transport():
    samples = observations()
    for index, sample in enumerate(samples):
        sample["u"] = 0.6 - 0.3 * max(0, 1 - abs(index - 40) / 20)
    skill = extract_skill(samples, CALIBRATION, "return.mp4", CONFIG)
    assert skill["goal"][1] == pytest.approx(0)
    assert len(skill["transport"]) >= 3
    assert max(point[1] for point in skill["transport"]) > 0.08


def test_delayed_lift_confirmation_keeps_earlier_excursion():
    samples = observations()
    for index, sample in enumerate(samples):
        sample["u"] = 0.6 - 0.3 * max(0, 1 - abs(index - 40) / 20)
        sample["separation"] = 0.12 if 45 <= index <= 55 else 0
    skill = extract_skill(samples, CALIBRATION, "delayed-lift.mp4", CONFIG)
    assert max(point[1] for point in skill["transport"]) > 0.085
    assert skill["events"][0]["time"] < 45 / 20
