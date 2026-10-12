# Purpose: Verify hint selection chooses the overlapping object, not a larger detection.
import numpy as np
from src.object_segmentation.object_segmentation import (
    choose_instance,
    segment_selection,
)
from src.skill_extraction.skill_extraction import CONFIG


def test_hint_prefers_the_object_inside_the_selection():
    person = np.zeros((100, 120), dtype=bool)
    person[5:95, 5:70] = True
    target = np.zeros((100, 120), dtype=bool)
    target[30:70, 78:108] = True
    hint = (76, 28, 34, 44)
    chosen = choose_instance(
        [
            {"mask": person, "confidence": 0.95},
            {"mask": target, "confidence": 0.6},
        ],
        hint,
    )
    assert chosen is not None
    assert int(chosen.sum()) == int(target.sum())


def test_segmenter_result_overrides_the_rough_rectangle():
    frame = np.full((80, 100, 3), 30, dtype=np.uint8)
    frame[20:60, 40:70] = (20, 20, 220)
    mask = np.zeros((80, 100), dtype=bool)
    mask[22:58, 42:68] = True

    class FixedSegmenter:
        def instances(self, image):
            return [{"mask": mask, "confidence": 0.9}]

    _chosen, box = segment_selection(
        frame, [0.2, 0.1, 0.7, 0.8], CONFIG, FixedSegmenter()
    )
    assert box[2] < 50
    assert 40 <= box[0] <= 46
