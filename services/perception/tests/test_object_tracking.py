# Purpose: Verify invalid selection, weak texture, and lost-track failures.
import cv2
import numpy as np
import pytest
from src.object_tracking.object_tracking import _appearance, _clip_box, track_object
from src.skill_extraction.skill_extraction import CONFIG


@pytest.mark.parametrize("roi", [[0, 0, 0, 0], [0.9, 0.9, 0.2, 0.2], [float("nan"), 0, 0.2, 0.2]])
def test_invalid_rectangle(roi):
    with pytest.raises(ValueError):
        track_object([], roi, CONFIG)


def test_textureless_selection():
    with pytest.raises(ValueError, match="texture"):
        track_object([(0, np.zeros((100, 100, 3), dtype=np.uint8))], [0.1, 0.1, 0.4, 0.4], CONFIG)


def test_lost_track(monkeypatch):
    class LostTracker:
        def init(self, frame, box):
            return None

        def update(self, frame):
            return False, (10, 10, 40, 40)

    monkeypatch.setattr("cv2.TrackerCSRT_create", LostTracker)
    frame = np.full((100, 100, 3), 30, dtype=np.uint8)
    frame[20:40, 20:40] = np.random.default_rng(7).integers(100, 255, (20, 20, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="lost"):
        track_object([(i / 20, frame) for i in range(10)], [0.1, 0.1, 0.4, 0.4], CONFIG)


def test_periodic_masks_refresh_geometry_without_identity_jump(monkeypatch):
    class Tracker:
        def init(self, frame, box):
            self.box = box

        def update(self, frame):
            return True, self.box

    monkeypatch.setattr("cv2.TrackerCSRT_create", Tracker)

    class Segmenter:
        index = 0

        def instances(self, frame):
            self.index += 1
            mask = np.zeros(frame.shape[:2], dtype=bool)
            x = 40 + min(self.index, 8)
            mask[30:70, x : x + 25] = True
            if self.index > 1:
                distractor = np.zeros_like(mask)
                distractor[30:70, x + 21 : x + 45] = True
                return [
                    {"mask": distractor, "confidence": 1.0},
                    {"mask": mask, "confidence": 0.9},
                ]
            return [{"mask": mask, "confidence": 0.9}]

    frame = np.full((100, 120, 3), (30, 40, 220), dtype=np.uint8)
    samples = track_object(
        [(i / 25, frame) for i in range(25)],
        [0.2, 0.2, 0.6, 0.6],
        {**CONFIG, "segment_interval": 1},
        Segmenter(),
    )
    assert {sample["object_id"] for sample in samples} == {1}
    assert samples[-1]["box"][0] > samples[0]["box"][0]
    assert samples[-1]["u"] < 0.55
    assert samples[-1]["geometry_source"] == "yolo"


def test_clipping_preserves_visible_intersection():
    assert _clip_box((-10, -20, 30, 40), 100, 100) == (0, 0, 20, 20)
    assert _clip_box((90, 80, 30, 40), 100, 100) == (90, 80, 10, 20)


def test_refresh_rejects_a_larger_similarly_colored_foreground(monkeypatch):
    class Tracker:
        def init(self, frame, box):
            self.box = box

        def update(self, frame):
            return True, self.box

    monkeypatch.setattr("cv2.TrackerCSRT_create", Tracker)

    class Segmenter:
        def instances(self, frame):
            target = np.zeros(frame.shape[:2], dtype=bool)
            target[30:70, 40:64] = True
            distractor = np.zeros_like(target)
            distractor[18:88, 32:72] = True
            return [{"mask": distractor}, {"mask": target}]

    frame = np.full((100, 120, 3), (30, 40, 220), dtype=np.uint8)
    samples = track_object(
        [(i / 25, frame) for i in range(25)],
        [0.3, 0.25, 0.27, 0.5],
        {**CONFIG, "segment_interval": 1},
        Segmenter(),
    )
    assert samples[-1]["box"] == samples[0]["box"]
    assert samples[-1]["geometry_source"] == "yolo"


def test_mask_refresh_accepts_legitimate_scale_change(monkeypatch):
    class Tracker:
        def init(self, frame, box):
            self.box = box

        def update(self, frame):
            return True, self.box

    monkeypatch.setattr("cv2.TrackerCSRT_create", Tracker)

    class Segmenter:
        calls = 0

        def instances(self, frame):
            self.calls += 1
            mask = np.zeros(frame.shape[:2], dtype=bool)
            if self.calls == 1:
                mask[30:70, 40:64] = True
            else:
                mask[40:60, 46:58] = True
            return [{"mask": mask, "confidence": 0.9}]

    frame = np.full((100, 120, 3), 30, dtype=np.uint8)
    frame[30:70, 40:64] = (30, 40, 220)
    samples = track_object(
        [(i / 25, frame) for i in range(25)],
        [0.2, 0.2, 0.6, 0.6],
        {**CONFIG, "segment_interval": 1},
        Segmenter(),
    )
    assert samples[-1]["box"][2] < samples[0]["box"][2]
    assert samples[-1]["geometry_source"] == "yolo"
    assert samples[-1]["object_id"] == samples[0]["object_id"]


def test_neutral_object_appearance_is_not_its_support():
    frame = np.full((100, 120, 3), 30, dtype=np.uint8)
    mask = np.zeros(frame.shape[:2], dtype=bool)
    mask[20:60, 40:70] = True
    frame[mask] = 200
    reference = _appearance(frame, mask)
    darker = (frame.astype(float) * 0.55).astype(np.uint8)
    assert (
        cv2.compareHist(reference, _appearance(darker, mask), cv2.HISTCMP_BHATTACHARYYA)
        < CONFIG["appearance_distance"]
    )
    assert (
        cv2.compareHist(reference, _appearance(frame, ~mask), cv2.HISTCMP_BHATTACHARYYA)
        > CONFIG["appearance_distance"]
    )


def test_foreground_flow_corrects_a_drifting_box(monkeypatch):
    class Tracker:
        def init(self, frame, box):
            self.box = box

        def update(self, frame):
            return True, self.box

    monkeypatch.setattr("cv2.TrackerCSRT_create", Tracker)
    texture = np.random.default_rng(9).integers(100, 255, (60, 60, 3), dtype=np.uint8)
    frames = []
    for index in range(25):
        frame = np.full((180, 320, 3), 30, dtype=np.uint8)
        frame[30:90, 40 + index * 2 : 100 + index * 2] = texture
        frames.append((index / 25, frame))
    samples = track_object(frames, [0.1, 0.1, 0.3, 0.6], CONFIG)
    assert abs(samples[-1]["u"] - 118 / 320) < 0.01
    assert samples[-1]["geometry_source"] == "flow"
