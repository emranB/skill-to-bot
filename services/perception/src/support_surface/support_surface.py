# Purpose: Compare a tracked object with the surface that supports it.
import cv2
import numpy as np


def surface_pose(surface: dict, config: dict) -> dict:
    """Calibrate a measured rectangle: near-left, near-right, far-right, far-left."""
    corners = np.asarray(surface["corners"], dtype=float)
    size = np.asarray(surface["size"], dtype=float)
    values = np.r_[
        corners.ravel(),
        size,
        surface["horizontal_fov"],
        surface["object_height"],
        surface["image_aspect"],
    ]
    if not np.isfinite(values).all():
        raise ValueError("Surface calibration must contain finite measurements.")
    contour = corners.astype(np.float32)
    if (
        corners.shape != (4, 2)
        or not cv2.isContourConvex(contour)
        or cv2.contourArea(contour, oriented=True) >= -0.005
        or np.min(np.linalg.norm(np.roll(corners, -1, axis=0) - corners, axis=1)) < 0.025
    ):
        raise ValueError("Select four distinct surface corners in near-left to far-left order.")
    width, depth = size
    plane = np.array([[0, 0], [width, 0], [width, depth], [0, depth]], dtype=np.float64)
    homography = cv2.getPerspectiveTransform(contour, plane.astype(np.float32))
    if np.linalg.cond(homography) > 1e6:
        raise ValueError("Surface corners are too compressed for a reliable mapping.")
    focal = 0.5 / np.tan(np.radians(surface["horizontal_fov"]) / 2)
    intrinsics = np.array([[focal, 0, 0.5], [0, focal * surface["image_aspect"], 0.5], [0, 0, 1]])
    world = np.column_stack((plane, np.zeros(4)))
    ok, rotations, translations, _ = cv2.solvePnPGeneric(
        world, corners, intrinsics, None, flags=cv2.SOLVEPNP_IPPE
    )
    candidates = []
    if ok:
        for rotation_vector, translation in zip(rotations, translations):
            rotation = cv2.Rodrigues(rotation_vector)[0]
            camera = -rotation.T @ translation.ravel()
            projected = cv2.projectPoints(world, rotation_vector, translation, intrinsics, None)[0]
            error = float(np.max(np.linalg.norm(projected[:, 0] - corners, axis=1)))
            if camera[2] > surface["object_height"] + config["surface_height_tolerance"]:
                candidates.append((error, rotation, camera))
    if not candidates:
        raise ValueError("Surface calibration must describe a camera above the support plane.")
    error, rotation, camera = min(candidates, key=lambda value: value[0])
    if error > config["surface_reprojection_limit"]:
        raise ValueError("Surface dimensions, corners and camera field of view disagree.")
    return {
        "intrinsics": intrinsics,
        "rotation": rotation,
        "camera": camera,
        "reprojection_error": error,
    }


def assign_calibrated_surface(samples: list[dict], calibration: dict, config: dict) -> None:
    """Separate table motion and height for an upright rigid, fixed-view foreground."""
    surface = calibration["surface"]
    pose = surface_pose(surface, config)
    if any(abs(sample["image_aspect"] - surface["image_aspect"]) > 0.01 for sample in samples):
        raise ValueError("Camera aspect changed. Recalibrate using the recorded frame.")
    if any(not sample.get("flow_valid", False) for sample in samples):
        raise ValueError(
            "Calibrated motion needs continuous foreground scale. Use a clear, rigid object without occlusion or rotation."
        )
    uv = np.array([sample["reference_uv"] for sample in samples])
    scales = np.array([sample["foreground_scale"] for sample in samples])
    if (
        not np.isfinite(uv).all()
        or not np.isfinite(scales).all()
        or np.any(scales <= 0)
        or np.any(uv < 0)
        or np.any(uv > 1)
    ):
        raise ValueError("Foreground position and scale must be finite and positive.")
    if np.max(np.linalg.norm(uv[:5] - uv[0], axis=1)) > 0.01 or np.ptp(scales[:5]) > 0.02:
        raise ValueError("Start with the object resting still on the calibrated surface.")
    rays = np.column_stack((uv, np.ones(len(uv)))) @ np.linalg.inv(pose["intrinsics"]).T
    rays = rays @ pose["rotation"]
    initial_ray = np.median(rays[:5], axis=0)
    camera = pose["camera"]
    center_height = surface["object_height"] / 2
    if initial_ray[2] >= -0.02:
        raise ValueError("The initial object ray does not intersect its resting plane reliably.")
    initial_depth = (center_height - camera[2]) / initial_ray[2]
    # For an unchanged rigid foreground, apparent scale is inverse camera depth.
    positions = camera + rays * (initial_depth * np.median(scales[:5]) / scales)[:, None]
    height = positions[:, 2] - center_height
    width, depth = surface["size"]
    margin = config["surface_motion_tolerance"]
    if (
        not np.isfinite(positions).all()
        or np.any(positions[:, :2] < -margin)
        or np.any(positions[:, :2] > np.array([width, depth]) + margin)
        or height.min() < -config["surface_height_tolerance"]
        or height.max() > min(0.5, camera[2] - surface["object_height"])
    ):
        raise ValueError(
            "Tracked geometry leaves the calibrated surface envelope. Check measurements, object pose and occlusion."
        )
    if abs(float(np.median(height[-5:]))) > config["surface_height_tolerance"]:
        raise ValueError("The ending object does not return to the calibrated support plane.")
    for sample, position, separation in zip(samples, positions, height):
        sample["surface_position"] = position[:2].tolist()
        sample["height_m"] = float(separation)
        sample["separation"] = float(max(0, separation) / max(width, depth))
        sample["on_surface"] = sample["separation"] < config["separation_threshold"]
        sample["support_confidence"] = (
            1.0 - pose["reprojection_error"] / config["surface_reprojection_limit"]
        )


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
