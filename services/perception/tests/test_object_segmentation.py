# Purpose: Verify hint selection chooses the overlapping object, not a larger detection.
import os
from pathlib import Path

import numpy as np
import pytest
from src.object_segmentation.object_segmentation import (
    YoloSegmenter,
    _decode_instances,
    choose_instance,
    load_segmenter,
    segment_selection,
    select_object,
)
from src.skill_extraction.skill_extraction import CONFIG
from src.video_input.video_input import read_video


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

    _chosen, box = segment_selection(frame, [0.2, 0.1, 0.7, 0.8], CONFIG, FixedSegmenter())
    assert box[2] < 50
    assert 40 <= box[0] <= 46


def test_loose_hint_and_click_accept_object_not_background():
    mask = np.zeros((200, 200), dtype=bool)
    mask[75:115, 85:115] = True
    unrelated = np.zeros_like(mask)
    unrelated[10:50, 10:50] = True
    for hint in ((40, 40, 120, 120), (90, 90, 4, 4)):
        chosen = choose_instance([{"mask": unrelated}, {"mask": mask}], hint)
        assert np.array_equal(chosen, mask)


def test_identity_filter_keeps_searching_after_rejecting_a_candidate():
    wrong = np.zeros((100, 120), dtype=bool)
    wrong[20:80, 20:90] = True
    target = np.zeros_like(wrong)
    target[30:60, 40:60] = True
    chosen = choose_instance(
        [{"mask": wrong}, {"mask": target}],
        (10, 10, 100, 80),
        lambda mask: np.array_equal(mask, target),
    )
    assert np.array_equal(chosen, target)


def test_crop_masks_return_to_full_frame():
    segmenter = object.__new__(YoloSegmenter)
    calls = []

    def instances(image):
        calls.append(image.shape)
        if len(calls) == 1:
            return []
        mask = np.zeros(image.shape[:2], dtype=bool)
        mask[5:-5, 5:-5] = True
        if len(calls) == 2:
            mask[:, -1] = True
        return [{"mask": mask, "confidence": 0.8}]

    segmenter.instances = instances
    frame = np.zeros((200, 300, 3), dtype=np.uint8)
    result = segmenter.selected_instances(frame, [0.3, 0.2, 0.2, 0.4])
    assert len(calls) == 3
    mask = result[0]["mask"]
    assert mask.shape == frame.shape[:2]
    assert mask[80, 120] and not mask[0, 0]


def test_letterbox_decoder_preserves_mask_and_classes():
    prediction = np.zeros((2, 116), dtype=np.float32)
    prediction[:, :4] = [320, 320, 128, 160]
    prediction[0, 4], prediction[1, 5] = 0.8, 0.9
    prediction[:, 84] = 10
    prototypes = np.ones((32, 160, 160), dtype=np.float32)
    instances = _decode_instances((160, 320), prediction, prototypes, 2, 0, 160)
    assert len(instances) == 2
    ys, xs = np.nonzero(instances[0]["mask"])
    assert (xs.min(), xs.max(), ys.min(), ys.max()) == (128, 191, 40, 119)


def test_fallback_provenance():
    frame = np.full((80, 100, 3), 30, dtype=np.uint8)
    frame[25:50, 30:50] = (30, 40, 220)

    class EmptySegmenter:
        def instances(self, frame):
            return []

    selected = select_object(frame, [0.2, 0.2, 0.4, 0.5], CONFIG, EmptySegmenter())
    assert selected["source"] == "grabcut"
    assert selected["mask"].any()


def test_unresolved_foreground_does_not_become_the_hint():
    frame = np.full((80, 100, 3), 30, dtype=np.uint8)
    with pytest.raises(ValueError, match="foreground"):
        select_object(frame, [0.2, 0.2, 0.4, 0.5], CONFIG)


def test_production_model_on_supplied_real_frame():
    segmenter = load_segmenter()
    if segmenter is None and not os.environ.get("SEGMENTATION_MODEL"):
        pytest.skip("Production weights are installed in the perception image.")
    assert segmenter is not None, "The configured production segmenter must load."
    assert "CPUExecutionProvider" in segmenter.session.get_providers()
    path = Path("/data/demonstrations/pop-can-pick-up-right-to-left-1.mp4")
    if not path.exists():
        path = (
            Path(__file__).resolve().parents[3]
            / "data/demonstrations/pop-can-pick-up-right-to-left-1.mp4"
        )
    _, frame = next(read_video(path, CONFIG))
    selected = select_object(frame, [0.65, 0.2, 0.21, 0.55], CONFIG, segmenter)
    assert selected["source"] == "yolo"
    x, y, width, height = selected["box"]
    assert 420 <= x <= 470 and 70 <= y <= 125
    assert 50 <= width <= 130 and 90 <= height <= 205
