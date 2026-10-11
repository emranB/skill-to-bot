# Purpose: Verify invalid selection, weak texture, and lost-track failures.
import numpy as np
import pytest
from src.object_tracking.object_tracking import track_object
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
    frame = np.random.default_rng(7).integers(0, 255, (100, 100, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="lost"):
        track_object([(i / 20, frame) for i in range(10)], [0.1, 0.1, 0.4, 0.4], CONFIG)
