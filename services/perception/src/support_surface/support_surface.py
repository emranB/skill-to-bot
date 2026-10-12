# Purpose: Compare a tracked object with the surface that supports it.
import cv2
import numpy as np


def surface_separation(
    scale: float, image_up: float, contact: float, rest_contact: float, config: dict
) -> float:
    """Score departure from the support plane.

    Image motion alone is not a lift. Sliding away rises in the image and shrinks.
    Sliding closer grows and moves downward. A residual after that coupling, or a
    lost contact with the support color, is the separation evidence.
    """
    coupling = config["planar_coupling"]
    shrink = max(0.0, 1.0 - scale)
    rise = image_up - shrink * coupling
    growth = (scale - 1.0) - max(0.0, -image_up) * coupling
    geometric = max(0.0, float(rise), float(growth))
    contact_drop = max(0.0, rest_contact - contact)
    if contact_drop >= 0.45 and (abs(image_up) >= 0.02 or abs(scale - 1.0) >= 0.06):
        return max(geometric, float(contact_drop))
    return geometric


def _lab(frame) -> np.ndarray:
    colors = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB).astype(np.float32)
    colors[:, :, 0] -= np.median(colors[:, :, 0])
    return colors


def estimate_support(frame, mask: np.ndarray, config: dict) -> dict:
    """Learn the support color from the band touching the resting object."""
    ys, xs = np.nonzero(mask)
    if len(xs) < 30:
        raise ValueError("The selection hint does not contain a segmentable object.")
    cutoff = np.percentile(ys, 70)
    band = mask.copy()
    band[: int(cutoff)] = False
    dilated = cv2.dilate(band.astype(np.uint8), np.ones((7, 7), np.uint8), iterations=2) > 0
    ring = dilated & ~mask
    if int(ring.sum()) < 20:
        return {"reference": None, "confidence": 0.0}
    colors = _lab(frame)[ring]
    reference = np.median(colors, axis=0)
    spread = np.median(np.linalg.norm(colors - reference, axis=1))
    confidence = 1.0 if spread <= config["support_color_distance"] else 0.35
    return {
        "reference": reference.astype(float).tolist(),
        "confidence": float(confidence),
    }


def assign_surface_state(samples: list[dict], config: dict) -> None:
    """Mark lift against the resting poses, not against the first frame alone.

    The clip starts on the support. A stable, still-touching ending is a second
    resting pose. Rising above both, growing past the on-plane size, or losing
    contact is separation. Moving between the two resting poses is not.
    """
    if len(samples) < 5:
        return
    start_v = float(np.median([sample["v"] for sample in samples[:5]]))
    start_scale = float(np.median([sample["scale"] for sample in samples[:5]]))
    start_contact = float(np.median([sample["contact"] for sample in samples[:5]]))
    ending = samples[-5:]
    end_v = float(np.median([sample["v"] for sample in ending]))
    end_scale = float(np.median([sample["scale"] for sample in ending]))
    end_contact = float(np.median([sample["contact"] for sample in ending]))
    end_motion = max(sample["u"] for sample in ending) - min(sample["u"] for sample in ending)
    end_motion += max(sample["v"] for sample in ending) - min(sample["v"] for sample in ending)
    anchors_v = [start_v]
    anchors_scale = [start_scale]
    if end_contact >= start_contact - 0.3 and end_motion < 0.05:
        anchors_v.append(end_v)
        anchors_scale.append(end_scale)
    for sample in samples:
        above = min(anchors_v) - sample["v"]
        separation = 0.0
        # A point on the segment between two resting poses cannot rise above both.
        # Tracker box size drifts, so size alone is not separation.
        if above >= 0.05:
            higher_scale = anchors_scale[int(np.argmin(anchors_v))]
            if sample["scale"] >= higher_scale * 0.85:
                separation = above
        if start_contact - sample["contact"] >= 0.45:
            separation = max(
                separation,
                surface_separation(1.0, max(above, 0.03), sample["contact"], start_contact, config),
            )
        sample["separation"] = float(separation)
        sample["on_surface"] = sample["separation"] < config["separation_threshold"]


def contact_below_box(frame, box: tuple, reference, distance: float) -> float:
    """Fraction of samples just under the box that still match the support."""
    if not reference:
        return 0.0
    height, width = frame.shape[:2]
    left, top, wide, high = (int(round(v)) for v in box)
    sample_y = top + high + 3
    if sample_y >= height - 1 or wide < 2:
        return 0.0
    xs = np.linspace(max(0, left), min(width - 1, left + wide - 1), 11).astype(int)
    row = _lab(frame)[sample_y, xs]
    distances = np.linalg.norm(row - np.asarray(reference, dtype=np.float32), axis=1)
    return float(np.mean(distances <= distance))
