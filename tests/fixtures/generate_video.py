# Purpose: Create a small deterministic test video from the supplied can demonstration.
import math
from pathlib import Path

import cv2
import imageio_ffmpeg
import numpy as np


def generate():
    root = Path(__file__).resolve().parents[2]
    source = root / "data/demonstrations/pop-can-pick-up-right-to-left-1.mp4"
    target = root / "data/fixtures/can_transfer.mp4"
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise ValueError("The supplied can demonstration is required to regenerate the fixture.")
    fps = capture.get(cv2.CAP_PROP_FPS)
    writer = cv2.VideoWriter(str(target), cv2.VideoWriter_fourcc(*"mp4v"), fps, (320, 180))
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            writer.write(cv2.resize(frame, (320, 180)))
    finally:
        writer.release()
        capture.release()
    return target


def generate_transport(target: Path):
    """Render a synthetic out-and-back demonstration using the real object texture."""
    root = Path(__file__).resolve().parents[2]
    capture = cv2.VideoCapture(
        str(root / "data/demonstrations/pop-can-pick-up-right-to-left-1.mp4")
    )
    ok, source = capture.read()
    capture.release()
    if not ok:
        raise ValueError("The supplied object texture is required.")
    source = cv2.resize(source, (640, 360))
    texture = source[83:270, 435:544]
    writer = cv2.VideoWriter(str(target), cv2.VideoWriter_fourcc(*"mp4v"), 25, (640, 360))
    try:
        for index in range(225):
            seconds = index / 25
            lift = max(0, min(1, seconds - 2)) - max(0, min(1, seconds - 6))
            outbound = max(0, min(1, seconds - 3)) - max(0, min(1, seconds - 5))
            frame = np.full((360, 640, 3), 220, dtype=np.uint8)
            frame[280:] = (120, 125, 130)
            left = round(435 - outbound * 190)
            top = round(83 - lift * 58)
            frame[top : top + 187, left : left + 109] = texture
            writer.write(frame)
    finally:
        writer.release()
    return target


def generate_calibrated_transport(target: Path, path: list[list[float]]):
    """Render controlled rigid-scale motion with known camera/support geometry."""
    root = Path(__file__).resolve().parents[2]
    capture = cv2.VideoCapture(
        str(root / "data/demonstrations/pop-can-pick-up-right-to-left-1.mp4")
    )
    ok, frame = capture.read()
    capture.release()
    if not ok:
        raise ValueError("The supplied object texture is required.")
    texture = cv2.resize(frame, (640, 360))[83:270, 435:544]
    eye = np.array([0.2, -0.05, 0.8])
    center = np.array([0.2, 0.175, 0.0])
    forward = (center - eye) / np.linalg.norm(center - eye)
    right = np.cross(forward, [0, 0, 1])
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    rotation = np.array([right, -up, forward])
    translation = -rotation @ eye
    intrinsics = np.array([[550, 0, 320], [0, 550, 180], [0, 0, 1]], dtype=float)

    def project(point):
        camera_point = rotation @ point + translation
        pixel = intrinsics @ camera_point
        return pixel[:2] / pixel[2], camera_point[2]

    corners = [[0, 0, 0], [0.4, 0, 0], [0.4, 0.35, 0], [0, 0.35, 0]]
    surface = {
        "corners": [(project(np.array(point))[0] / [640, 360]).tolist() for point in corners],
        "size": [0.4, 0.35],
        "horizontal_fov": math.degrees(2 * math.atan(320 / 550)),
        "object_height": 0.12,
        "image_aspect": 640 / 360,
    }
    route = [(path[0], 0.0)] * 25
    route += [(path[0], height) for height in np.linspace(0, 0.12, 20)]
    route += [(point, 0.12) for a, b in zip(path, path[1:]) for point in np.linspace(a, b, 30)]
    route += [(path[-1], height) for height in np.linspace(0.12, 0, 20)]
    route += [(path[-1], 0.0)] * 35
    _, initial_depth = project(np.array([0.2 + path[0][0], 0.175 + path[0][1], 0.06]))
    initial_box = None
    writer = imageio_ffmpeg.write_frames(
        str(target),
        (640, 360),
        fps=25,
        codec="libx264",
        pix_fmt_in="bgr24",
        macro_block_size=1,
        ffmpeg_log_level="error",
        output_params=["-movflags", "+faststart"],
    )
    writer.send(None)
    try:
        for point, height in route:
            pixel, depth = project(np.array([0.2 + point[0], 0.175 + point[1], 0.06 + height]))
            wide, high = round(60 * initial_depth / depth), round(100 * initial_depth / depth)
            left, top = round(pixel[0] - wide / 2), round(pixel[1] - high / 2)
            image = np.full((360, 640, 3), (70, 74, 78), dtype=np.uint8)
            cv2.polylines(
                image,
                [np.int32(np.array(surface["corners"]) * [640, 360])],
                True,
                (130, 130, 130),
                2,
            )
            image[top : top + high, left : left + wide] = cv2.resize(texture, (wide, high))
            writer.send(image)
            if initial_box is None:
                initial_box = [
                    (left - 10) / 640,
                    (top - 10) / 360,
                    (wide + 20) / 640,
                    (high + 20) / 360,
                ]
    finally:
        writer.close()
    capture = cv2.VideoCapture(str(target))
    encoded_size = (
        int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
        int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    )
    capture.release()
    if encoded_size != (640, 360):
        raise ValueError("Calibration fixture encoding changed the frame dimensions.")
    calibration = {
        "method": "support_plane",
        "plane": "table",
        "workspace_span": 0.3,
        "roi": initial_box,
        "surface": surface,
    }
    return target, calibration


if __name__ == "__main__":
    print(generate())
