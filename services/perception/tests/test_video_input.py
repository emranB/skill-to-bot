# Purpose: Verify video bounds, corruption handling, and actual decoding.
import cv2
import numpy as np
import pytest
from src.skill_extraction.skill_extraction import CONFIG
from src.video_input.video_input import read_video


def test_missing_and_corrupt(tmp_path):
    with pytest.raises(ValueError):
        list(read_video(tmp_path / "missing.mp4", CONFIG))
    corrupt = tmp_path / "bad.mp4"
    corrupt.write_bytes(b"not a video")
    with pytest.raises(ValueError, match="decoded"):
        list(read_video(corrupt, CONFIG))


def test_real_decoding_and_duration_limit(tmp_path):
    path = tmp_path / "valid.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 20, (64, 48))
    for i in range(20):
        writer.write(np.full((48, 64, 3), i * 10, dtype=np.uint8))
    writer.release()
    frames = list(read_video(path, CONFIG))
    assert len(frames) == 20
    assert frames[-1][0] == pytest.approx(0.95)
    with pytest.raises(ValueError, match="duration"):
        list(read_video(path, {**CONFIG, "max_seconds": 0.5}))
