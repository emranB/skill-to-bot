# Purpose: Snap a selection hint to an object and keep that identity across frames.
import math

import cv2
import numpy as np
from src.object_segmentation.object_segmentation import segment_selection
from src.support_surface.support_surface import (
    assign_surface_state,
    contact_below_box,
    estimate_support,
)

OBJECT_ID = 1


def _valid_hint(roi: list[float]) -> None:
    if len(roi) != 4 or not all(math.isfinite(v) and 0 <= v <= 1 for v in roi):
        raise ValueError("Select a valid normalized object rectangle.")
    x, y, width, height = roi
    if min(width, height) < 0.01 or x + width > 1 or y + height > 1:
        raise ValueError("Object rectangle must fit inside the video.")


def _clip_box(box, width: int, height: int) -> tuple[float, float, float, float]:
    left, top, box_width, box_height = (float(v) for v in box)
    left = min(max(0.0, left), width - 2)
    top = min(max(0.0, top), height - 2)
    box_width = min(max(2.0, box_width), width - left)
    box_height = min(max(2.0, box_height), height - top)
    return left, top, box_width, box_height


def track_object(frames, roi: list[float], config: dict, segmenter=None) -> list[dict]:
    """Track the segmented object. The rectangle is a hint, not the object geometry."""
    _valid_hint(roi)
    tracker = cv2.TrackerCSRT_create()
    samples = []
    initial_area = None
    support = None
    rest_contact = 0.0
    failures = 0
    for timestamp, frame in frames:
        height, width = frame.shape[:2]
        if initial_area is None:
            hint = (
                int(round(roi[0] * width)),
                int(round(roi[1] * height)),
                int(round(roi[2] * width)),
                int(round(roi[3] * height)),
            )
            patch = frame[hint[1] : hint[1] + hint[3], hint[0] : hint[0] + hint[2]]
            if patch.size == 0 or float(np.std(patch)) < config["min_texture"]:
                raise ValueError(
                    "Selected object has insufficient texture for reliable tracking."
                )
            _mask, tight = segment_selection(frame, roi, config, segmenter)
            pad = 4
            box = tuple(
                int(round(v))
                for v in _clip_box(
                    (
                        tight[0] - pad,
                        tight[1] - pad,
                        tight[2] + pad * 2,
                        tight[3] + pad * 2,
                    ),
                    width,
                    height,
                )
            )
            support = estimate_support(frame, _mask, config)
            rest_contact = contact_below_box(
                frame, box, support["reference"], config["support_color_distance"]
            )
            tracker.init(frame, box)
            initial_area = box[2] * box[3]
            ok = True
        else:
            ok, box = tracker.update(frame)
            box = _clip_box(box, width, height)
        left, top, box_width, box_height = box
        valid = (
            ok
            and 0.25 <= box_width * box_height / initial_area <= 4
            and 0 <= left <= width - box_width
            and 0 <= top <= height - box_height
        )
        if not valid:
            failures += 1
            if failures > config["max_lost_frames"]:
                raise ValueError(
                    "Object tracking was lost. Select a tighter rectangle or use a clearer video."
                )
            continue
        failures = 0
        scale = math.sqrt((box_width * box_height) / initial_area)
        center_v = (top + box_height / 2) / height
        contact = contact_below_box(
            frame, box, support["reference"], config["support_color_distance"]
        )
        if support["confidence"] < 0.5:
            contact = rest_contact
        samples.append(
            {
                "time": timestamp,
                "u": (left + box_width / 2) / width,
                "v": center_v,
                "confidence": 1.0,
                "box": [
                    left / width,
                    top / height,
                    box_width / width,
                    box_height / height,
                ],
                "object_id": OBJECT_ID,
                "area": (box_width * box_height) / (width * height),
                "scale": scale,
                "contact": contact,
                "separation": 0.0,
                "on_surface": True,
                "support_confidence": support["confidence"],
            }
        )
    if len(samples) < config["min_samples"]:
        raise ValueError("Not enough reliable object observations.")
    assign_surface_state(samples, config)
    return samples
