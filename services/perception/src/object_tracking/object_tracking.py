# Purpose: Snap a selection hint to an object and keep that identity across frames.
import math

import cv2
import numpy as np
from src.object_segmentation.object_segmentation import select_object
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
    right, bottom = left + box_width, top + box_height
    left = min(max(0.0, left), width - 2)
    top = min(max(0.0, top), height - 2)
    box_width = min(width, max(left + 2, right)) - left
    box_height = min(height, max(top + 2, bottom)) - top
    return left, top, box_width, box_height


def _appearance(frame, mask):
    colors = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    colors[:, :, 0][colors[:, :, 1] < 32] = 0
    lightness = colors[:, :, 2].astype(np.float32)
    colors[:, :, 2] = np.clip(
        lightness * 255 / max(1, np.percentile(lightness, 99)), 0, 255
    ).astype(np.uint8)
    histogram = cv2.calcHist(
        [colors], [0, 1, 2], mask.astype(np.uint8), [12, 8, 8], [0, 180, 0, 256, 0, 256]
    )
    histogram = histogram.reshape(-1, 1)
    return cv2.normalize(histogram, histogram)


def _mask_bounds(mask, width, height):
    left, top, wide, high = cv2.boundingRect(mask.astype(np.uint8))
    return tuple(
        int(round(value))
        for value in _clip_box((left - 4, top - 4, wide + 8, high + 8), width, height)
    )


def _touches_edge(box, width, height):
    left, top, wide, high = box
    return left == 0 or top == 0 or left + wide >= width or top + high >= height


def _flow_box(previous, gray, points, box):
    """Estimate foreground motion with forward/backward checked optical flow."""
    if points is None or len(points) < 6:
        return None, None, None
    moved, status, _ = cv2.calcOpticalFlowPyrLK(previous, gray, points, None)
    if moved is None:
        return None, None, None
    returned, back_status, _ = cv2.calcOpticalFlowPyrLK(gray, previous, moved, None)
    if returned is None:
        return None, None, None
    good = (
        (status.ravel() > 0)
        & (back_status.ravel() > 0)
        & (np.linalg.norm(returned - points, axis=2).ravel() < 2)
    )
    if good.sum() < 6:
        return None, None, None
    transform, inliers = cv2.estimateAffinePartial2D(
        points[good], moved[good], method=cv2.RANSAC, ransacReprojThreshold=2
    )
    if transform is None or inliers.sum() < 6:
        return None, None, None
    scale = math.hypot(transform[0, 0], transform[0, 1])
    if not 0.8 <= scale <= 1.25:
        return None, None, None
    left, top, wide, high = box
    corners = np.array(
        [[left, top], [left + wide, top], [left, top + high], [left + wide, top + high]],
        dtype=np.float32,
    )
    mapped = cv2.transform(corners[None], transform)[0]
    low, high = mapped.min(axis=0), mapped.max(axis=0)
    if np.linalg.norm((low + high) / 2 - [left + wide / 2, top + box[3] / 2]) > max(box[2:]) / 2:
        return None, None, None
    return (*low, *(high - low)), moved[good][inliers.ravel() > 0], transform


def _foreground_points(gray, mask):
    return cv2.goodFeaturesToTrack(gray, 80, 0.01, 3, mask=mask.astype(np.uint8))


def track_object(frames, roi: list[float], config: dict, segmenter=None) -> list[dict]:
    """Track the segmented object. The rectangle is a hint, not the object geometry."""
    _valid_hint(roi)
    cv2.setRNGSeed(7)
    tracker = cv2.TrackerCSRT_create()
    samples = []
    initial_area = None
    initial_shape = None
    mask_area = None
    mask_clipped = False
    support = None
    rest_contact = 0.0
    failures = 0
    source = "grabcut"
    appearance = None
    previous_gray = None
    points = None
    reference_point = None
    foreground_scale = 1.0
    foreground_rotation = 0.0
    for index, (timestamp, frame) in enumerate(frames):
        height, width = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        compatible = False
        geometry_source = "tracker"
        flow_valid = False
        if initial_area is None:
            hint = (
                int(round(roi[0] * width)),
                int(round(roi[1] * height)),
                int(round(roi[2] * width)),
                int(round(roi[3] * height)),
            )
            patch = frame[hint[1] : hint[1] + hint[3], hint[0] : hint[0] + hint[2]]
            if patch.size == 0 or float(np.std(patch)) < config["min_texture"]:
                raise ValueError("Selected object has insufficient texture for reliable tracking.")
            selected = select_object(frame, roi, config, segmenter)
            _mask = selected["mask"]
            source = selected["source"]
            geometry_source = source
            points = _foreground_points(gray, _mask)
            appearance = _appearance(frame, _mask)
            box = _mask_bounds(_mask, width, height)
            reference_point = np.array([box[0] + box[2] / 2, box[1] + box[3] / 2])
            flow_valid = points is not None and len(points) >= 6
            support = estimate_support(frame, _mask, config)
            rest_contact = contact_below_box(
                frame, box, support["reference"], config["support_color_distance"]
            )
            tracker.init(frame, box)
            initial_area = box[2] * box[3]
            initial_shape = box[2] / box[3]
            mask_area = initial_area
            mask_clipped = _touches_edge(box, width, height)
            ok = True
        else:
            previous = box
            ok, box = tracker.update(frame)
            box = _clip_box(box if ok else previous, width, height)
            flowed, points, transform = _flow_box(previous_gray, gray, points, previous)
            if flowed is not None:
                box = _clip_box(flowed, width, height)
                geometry_source = "flow"
                reference_point = transform[:, :2] @ reference_point + transform[:, 2]
                foreground_scale *= math.hypot(transform[0, 0], transform[0, 1])
                foreground_rotation += math.atan2(transform[1, 0], transform[0, 0])
                flow_valid = abs(foreground_rotation) < math.radians(
                    config["foreground_rotation_limit"]
                )
            refresh = index % int(config["segment_interval"]) == 0 or (
                points is None and index % int(config["max_lost_frames"]) == 0
            )
            if segmenter is not None and (not ok or refresh):
                search_box = _clip_box(
                    (box[0] - box[2] / 2, box[1] - box[3] / 2, box[2] * 2, box[3] * 2),
                    width,
                    height,
                )
                current_roi = [
                    search_box[0] / width,
                    search_box[1] / height,
                    search_box[2] / width,
                    search_box[3] / height,
                ]

                def matches(mask):
                    bounds = _mask_bounds(mask, width, height)
                    wide = max(
                        0, min(bounds[0] + bounds[2], box[0] + box[2]) - max(bounds[0], box[0])
                    )
                    high = max(
                        0, min(bounds[1] + bounds[3], box[1] + box[3]) - max(bounds[1], box[1])
                    )
                    intersection = wide * high
                    overlap = intersection / (
                        bounds[2] * bounds[3] + box[2] * box[3] - intersection
                    )
                    distance = cv2.compareHist(
                        appearance, _appearance(frame, mask), cv2.HISTCMP_BHATTACHARYYA
                    )
                    if (
                        0.25 <= bounds[2] * bounds[3] / initial_area <= 4
                        and 0.25 <= bounds[2] * bounds[3] / mask_area <= (4 if mask_clipped else 2)
                        and 0.5 <= (bounds[2] / bounds[3]) / initial_shape <= 2
                        and 0.25 <= bounds[2] * bounds[3] / (box[2] * box[3]) <= 4
                        and overlap >= 0.25
                        and distance < config["appearance_distance"]
                    ):
                        return 1.0 - distance
                    return 0.0

                try:
                    candidate = select_object(frame, current_roi, config, segmenter, matches)
                except ValueError:
                    candidate = None
                compatible = candidate is not None and candidate["source"] == "yolo"
                if compatible:
                    box = _mask_bounds(candidate["mask"], width, height)
                    mask_area = box[2] * box[3]
                    mask_clipped = _touches_edge(box, width, height)
                    points = _foreground_points(gray, candidate["mask"])
                    tracker = cv2.TrackerCSRT_create()
                    tracker.init(frame, box)
                    ok = True
        previous_gray = gray
        if compatible:
            geometry_source = "yolo"
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
                "segmentation_source": source,
                "geometry_source": geometry_source,
                "area": (box_width * box_height) / (width * height),
                "scale": scale,
                "contact": contact,
                "separation": 0.0,
                "on_surface": True,
                "support_confidence": support["confidence"],
                "reference_uv": [
                    float(reference_point[0] / width),
                    float(reference_point[1] / height),
                ],
                "foreground_scale": float(foreground_scale),
                "flow_valid": flow_valid and not _touches_edge(box, width, height),
                "image_aspect": width / height,
            }
        )
    if len(samples) < config["min_samples"]:
        raise ValueError("Not enough reliable object observations.")
    assign_surface_state(samples, config)
    return samples
