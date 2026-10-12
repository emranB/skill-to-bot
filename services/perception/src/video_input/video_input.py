# Purpose: Decode and validate bounded human demonstration videos.
from pathlib import Path

import cv2


def read_video(path: Path, config: dict):
    """Yield every decoded frame, preserving timestamps for tracking."""
    if not path.is_file() or path.stat().st_size > config["max_bytes"]:
        raise ValueError("Video is missing or exceeds the upload size limit.")
    capture = cv2.VideoCapture(str(path))
    try:
        fps = capture.get(cv2.CAP_PROP_FPS)
        count = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        if not capture.isOpened() or fps <= 0 or count < 4:
            raise ValueError("Video cannot be decoded or contains too few frames.")
        if count / fps > config["max_seconds"]:
            raise ValueError("Video exceeds the duration limit.")
        index = 0
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if index > fps * config["max_seconds"]:
                raise ValueError("Decoded video exceeds the duration limit.")
            height, width = frame.shape[:2]
            if width > config["tracking_width"]:
                frame = cv2.resize(
                    frame,
                    (
                        config["tracking_width"],
                        round(height * config["tracking_width"] / width),
                    ),
                )
            if index % int(config.get("frame_stride", 1)) == 0:
                yield index / fps, frame
            index += 1
        if index < 4 or index < count * 0.95:
            raise ValueError("Video ended before all expected frames could be decoded.")
    finally:
        capture.release()
