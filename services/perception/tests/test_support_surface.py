# Purpose: Verify support separation, viewpoint lifts, slides, and stable placement.
import math

import cv2
import numpy as np
import pytest
from src.object_tracking.object_tracking import track_object
from src.skill_extraction.skill_extraction import CONFIG, extract_skill
from src.support_surface.support_surface import (
    contact_below_box,
    estimate_support,
    surface_separation,
)

CALIBRATION = {
    "method": "operator_planar",
    "plane": "front",
    "workspace_span": 0.3,
    "roi": [0.2, 0.2, 0.3, 0.4],
}
VIEWPOINTS = [
    ("front", 0, 16),
    ("front-left", -45, 16),
    ("front-right", 45, 16),
    ("elevated-front", 0, 55),
    ("elevated-left", -45, 55),
    ("elevated-right", 45, 55),
]


def test_plane_coupling_accepts_lifts_and_rejects_slides():
    assert surface_separation(1.0, 0.12, 1.0, 1.0, CONFIG) >= CONFIG["separation_threshold"]
    assert surface_separation(1.16, 0.01, 1.0, 1.0, CONFIG) >= CONFIG["separation_threshold"]
    assert surface_separation(0.84, 0.12, 1.0, 1.0, CONFIG) < CONFIG["separation_ambiguous"]
    assert surface_separation(1.14, -0.11, 1.0, 1.0, CONFIG) < CONFIG["separation_ambiguous"]
    assert surface_separation(1.02, 0.03, 0.2, 0.9, CONFIG) >= CONFIG["separation_threshold"]


def _camera(azimuth_deg: float, elevation_deg: float):
    azimuth = math.radians(azimuth_deg)
    elevation = math.radians(elevation_deg)
    target = np.array([0.0, 0.6, 0.02])
    eye = target + 1.2 * np.array(
        [
            math.sin(azimuth) * math.cos(elevation),
            -math.cos(azimuth) * math.cos(elevation),
            math.sin(elevation),
        ]
    )
    forward = target - eye
    forward /= np.linalg.norm(forward)
    right = np.cross(forward, np.array([0.0, 0.0, 1.0]))
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    return eye, right, up, forward


def _project(point, camera, focal: float, size: tuple[int, int]):
    eye, right, up, forward = camera
    offset = np.asarray(point, dtype=float) - eye
    depth = float(np.dot(offset, forward))
    if depth < 0.05:
        return None
    width, height = size
    u = focal * float(np.dot(offset, right)) / depth + width / 2
    v = height / 2 - focal * float(np.dot(offset, up)) / depth
    return u, v, depth


def _texture() -> np.ndarray:
    image = np.zeros((72, 48, 3), dtype=np.uint8)
    image[:, :] = (30, 40, 210)
    image[8:64, 8:40] = (240, 240, 240)
    image[18:28, 12:36] = (20, 20, 180)
    image[36:46, 12:36] = (20, 120, 20)
    image[54:64, 12:36] = (180, 40, 40)
    return image


def _pose(index: int, motion: str) -> tuple[float, float, float]:
    if motion == "slide":
        phase = min(1.0, max(0.0, (index - 12) / 28))
        return 0.18 - 0.36 * phase, 0.62, 0.0
    if motion == "slanted":
        phase = min(1.0, max(0.0, (index - 10) / 30))
        height = math.sin(phase * math.pi) * 0.18
        return 0.18 - 0.36 * phase, 0.62, height
    lift = min(1.0, max(0.0, (index - 12) / 8)) - min(1.0, max(0.0, (index - 36) / 8))
    travel = min(1.0, max(0.0, (index - 18) / 16))
    return 0.18 - 0.36 * travel, 0.62, 0.18 * lift


def render_motion(azimuth: float, elevation: float, motion: str, frames: int = 56):
    size = (320, 240)
    focal = 340.0
    camera = _camera(azimuth, elevation)
    texture = _texture()
    output = []
    truth = []
    table = [(-0.5, 0.28, 0.0), (0.5, 0.28, 0.0), (0.5, 1.0, 0.0), (-0.5, 1.0, 0.0)]
    for index in range(frames):
        frame = np.full((size[1], size[0], 3), (226, 226, 220), dtype=np.uint8)
        projected = [_project(point, camera, focal, size) for point in table]
        if all(projected):
            polygon = np.array([[p[0], p[1]] for p in projected], dtype=np.int32)
            cv2.fillConvexPoly(frame, polygon, (70, 74, 78))
        x, y, height = _pose(index, motion)
        center = _project((x, y, height + 0.07), camera, focal, size)
        if center is None:
            raise RuntimeError("Object left the synthetic camera frustum.")
        _u, _v, depth = center
        box_h = max(12, int(round(focal * 0.14 / depth)))
        box_w = max(8, int(round(focal * 0.075 / depth)))
        left = int(round(center[0] - box_w / 2))
        top = int(round(center[1] - box_h / 2))
        sprite = cv2.resize(texture, (box_w, box_h))
        x0, y0 = max(0, left), max(0, top)
        x1, y1 = min(size[0], left + box_w), min(size[1], top + box_h)
        if x1 > x0 and y1 > y0:
            frame[y0:y1, x0:x1] = sprite[y0 - top : y1 - top, x0 - left : x1 - left]
        truth.append(
            [
                max(0.0, left / size[0]),
                max(0.0, top / size[1]),
                min(1.0, box_w / size[0]),
                min(1.0, box_h / size[1]),
            ]
        )
        output.append((index / 20, frame))
    return output, truth


def _hint(truth_box: list[float]) -> list[float]:
    x, y, width, height = truth_box
    wide = min(0.7, width * 1.8)
    high = min(0.75, height * 1.45)
    left = min(1 - wide, max(0.0, x - width * 0.25))
    top = min(1 - high, max(0.0, y - height * 0.15))
    return [left, top, wide, high]


def _track(azimuth: float, elevation: float, motion: str):
    frames, truth = render_motion(azimuth, elevation, motion)
    hint = _hint(truth[0])
    samples = track_object(frames, hint, CONFIG)
    return samples, truth, hint


@pytest.mark.parametrize(("name", "azimuth", "elevation"), VIEWPOINTS)
def test_vertical_lift_from_supported_viewpoints(name, azimuth, elevation):
    samples, _truth, _hint = _track(azimuth, elevation, "lift")
    skill = extract_skill(samples, {**CALIBRATION, "roi": _hint}, f"{name}.mp4", CONFIG)
    assert [event["type"] for event in skill["events"]] == [
        "grasp",
        "transport",
        "place",
        "release",
    ]
    assert all(samples[i]["object_id"] == samples[0]["object_id"] for i in range(len(samples)))


def test_slanted_lift_is_a_lift():
    samples, _truth, hint = _track(20, 35, "slanted")
    skill = extract_skill(samples, {**CALIBRATION, "roi": hint}, "slanted.mp4", CONFIG)
    assert skill["events"][0]["type"] == "grasp"
    assert skill["events"][2]["type"] == "place"


@pytest.mark.parametrize(("name", "azimuth", "elevation"), [("front", 0, 16), ("elevated", 0, 55)])
def test_sliding_stays_on_the_support(name, azimuth, elevation):
    samples, _truth, hint = _track(azimuth, elevation, "slide")
    with pytest.raises(ValueError, match="support surface|evidence"):
        extract_skill(samples, {**CALIBRATION, "roi": hint}, f"{name}-slide.mp4", CONFIG)


def test_rough_hint_snaps_and_keeps_identity():
    samples, truth, hint = _track(0, 20, "lift")
    snapped = samples[0]["box"]
    assert snapped[2] * snapped[3] < hint[2] * hint[3]
    intersection_w = min(snapped[0] + snapped[2], truth[0][0] + truth[0][2]) - max(
        snapped[0], truth[0][0]
    )
    intersection_h = min(snapped[1] + snapped[3], truth[0][1] + truth[0][3]) - max(
        snapped[1], truth[0][1]
    )
    intersection = max(0.0, intersection_w) * max(0.0, intersection_h)
    union = snapped[2] * snapped[3] + truth[0][2] * truth[0][3] - intersection
    assert intersection / union > 0.35
    truth_u = [box[0] + box[2] / 2 for box in truth]
    tracked_u = [sample["u"] for sample in samples]
    assert abs(float(np.mean(np.array(tracked_u) - np.array(truth_u[: len(tracked_u)])))) < 0.08


def test_repeated_tracking_keeps_the_same_observations():
    frames, truth = render_motion(0, 20, "lift")
    hint = _hint(truth[0])
    first = track_object(frames, hint, CONFIG)
    second = track_object(frames, hint, CONFIG)
    assert first == second


def test_support_contact_survives_exposure_change():
    frame = np.full((100, 120, 3), 120, dtype=np.uint8)
    mask = np.zeros((100, 120), dtype=bool)
    mask[20:60, 40:70] = True
    frame[mask] = (30, 40, 200)
    support = estimate_support(frame, mask, CONFIG)
    darker = (frame.astype(float) * 0.55).astype(np.uint8)
    box = (40, 20, 30, 40)
    assert (
        contact_below_box(darker, box, support["reference"], CONFIG["support_color_distance"]) == 1
    )
    darker[63:64, 40:70] = (10, 180, 10)
    assert (
        contact_below_box(darker, box, support["reference"], CONFIG["support_color_distance"]) == 0
    )
