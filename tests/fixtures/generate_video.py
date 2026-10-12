# Purpose: Create a small deterministic test video from the supplied can demonstration.
from pathlib import Path

import cv2
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


if __name__ == "__main__":
    print(generate())
