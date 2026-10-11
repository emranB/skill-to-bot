# Purpose: Track an operator-selected object with OpenCV CSRT and reject lost tracks.
import math

import cv2
import numpy as np


def track_object(frames, roi: list[float], config: dict) -> list[dict]:
    if len(roi) != 4 or not all(math.isfinite(v) and 0 <= v <= 1 for v in roi):
        raise ValueError("Select a valid normalized object rectangle.")
    x, y, width, height = roi
    if min(width, height) < 0.01 or x + width > 1 or y + height > 1:
        raise ValueError("Object rectangle must fit inside the video.")
    tracker = cv2.TrackerCSRT_create()
    samples = []
    initial_area = None
    failures = 0
    for timestamp, frame in frames:
        h, w = frame.shape[:2]
        if initial_area is None:
            box = tuple(int(round(v)) for v in (x * w, y * h, width * w, height * h))
            patch = frame[box[1] : box[1] + box[3], box[0] : box[0] + box[2]]
            if patch.size == 0 or float(np.std(patch)) < config["min_texture"]:
                raise ValueError("Selected object has insufficient texture for reliable tracking.")
            tracker.init(frame, box)
            initial_area = box[2] * box[3]
            ok = True
        else:
            ok, box = tracker.update(frame)
        bx, by, bw, bh = box
        valid = (
            ok and 0.25 <= bw * bh / initial_area <= 4 and 0 <= bx <= w - bw and 0 <= by <= h - bh
        )
        if not valid:
            failures += 1
            if failures > config["max_lost_frames"]:
                raise ValueError(
                    "Object tracking was lost. Select a tighter rectangle or use a clearer video."
                )
            continue
        failures = 0
        samples.append(
            {
                "time": timestamp,
                "u": (bx + bw / 2) / w,
                "v": (by + bh / 2) / h,
                "confidence": 1.0,
                "box": [bx / w, by / h, bw / w, bh / h],
            }
        )
    if len(samples) < config["min_samples"]:
        raise ValueError("Not enough reliable object observations.")
    return samples
