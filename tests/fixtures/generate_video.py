# Purpose: Create a small deterministic test video from the supplied can demonstration.
from pathlib import Path

import cv2


def generate():
    root = Path(__file__).resolve().parents[2]
    source = root / "data/demonstrations/pop-can-pick-up-1.mp4"
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


if __name__ == "__main__":
    print(generate())
