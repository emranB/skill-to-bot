# Purpose: Verify drawing and unchanged-skill retargeting through real Panda physics.
import json
import os
import tempfile
import time
import uuid
from pathlib import Path

import httpx
import imageio.v2 as imageio
import numpy as np
import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("RUN_INTEGRATION") != "1",
        reason="Set RUN_INTEGRATION=1 with the drawing stack running.",
    ),
]
ROOT = Path(__file__).resolve().parents[1]


def wait_run(client, run_id):
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        response = client.get("/runs/" + run_id)
        response.raise_for_status()
        run = response.json()
        if run["status"] != "running":
            return run
        time.sleep(0.5)
    pytest.fail("Drawing did not finish within the bounded deadline.")


def verify(client, run):
    assert run["status"] == "completed", run.get("error")
    result = run["result"]
    assert result["success"]
    assert result["mean_path_error_m"] <= 0.001 and result["max_path_error_m"] <= 0.002
    assert result["max_shape_error_m"] <= 0.0008
    assert result["visibility"]["paper_fraction"] >= 0.05 and result["visibility"]["ink_pixels"] > 0
    assert result["contact_coverage"] >= 0.95
    assert result["strokes_completed"] == result["stroke_count"]
    prefix = "/runs/" + run["run_id"] + "/artifacts/"
    for name in (
        "run.json",
        "skill.json",
        "trace.json",
        "robot-plan.json",
        "simulation-result.json",
    ):
        assert client.get(prefix + name).status_code == 200
    trace = client.get(prefix + "trace.json").json()
    assert trace["ink"] and trace["samples"]
    measured = {
        (sample["t"], sample["stroke"], *sample["actual_local"])
        for sample in trace["samples"]
        if sample["phase"] == "draw" and sample["contact"]
    }
    positions = {(stroke, *local) for _, stroke, *local in measured}
    for mark in trace["ink"]:
        assert (mark["t"], mark["stroke"], *mark["local"]) in measured
        assert (mark["stroke"], *mark["segment_start"]) in positions
        stroke = run["skill"]["strokes"][mark["stroke"]]
        assert mark["color"] == stroke.get("color", "#202124")
        if "pressure" not in stroke["points"][0]:
            assert mark["pressure_source"] == "constant" and mark["pressure"] == 0.5
    frames = trace["video"]["frames"]
    assert trace["video"]["renderer"] == "MuJoCo"
    assert frames[0]["ink_count"] == 0 and frames[-1]["ink_count"] == len(trace["ink"])
    assert trace["samples"][-1]["t"] == result["execution_duration_s"]
    assert all(a["t"] < b["t"] for a, b in zip(trace["samples"], trace["samples"][1:]))
    assert all(s["ink_radius"] is None for s in trace["samples"] if s["phase"] != "draw")
    assert set(s["stroke"] for s in trace["samples"] if s["phase"] == "draw") == set(
        range(result["stroke_count"])
    )
    video = client.get(prefix + "simulation.mp4")
    assert video.status_code == 200 and len(video.content) > 10000
    preview = client.get(prefix + "simulator-final.png")
    assert preview.status_code == 200 and len(preview.content) > 1000
    # Decode on a host-writable temp path. Docker-owned data/runs is often root-owned in CI.
    with tempfile.TemporaryDirectory(prefix="skill-to-bot-frames-") as temporary:
        directory = Path(temporary)
        movie = directory / "simulation.mp4"
        movie.write_bytes(video.content)
        rendered_path = directory / "simulator-final.png"
        rendered_path.write_bytes(preview.content)
        reader = imageio.get_reader(
            str(movie),
            input_params=["-threads", "1"],
            output_params=["-threads", "1"],
        )
        try:
            count = reader.count_frames()
            assert count > 10
            first, final = reader.get_data(0), reader.get_data(count - 1)
            assert count == len(frames)
            assert first.std() > 10 and final.std() > 10
            assert abs(first.astype(float) - final).mean() > 0.5
            # The decoded MP4 final frame matches the independently saved simulator render.
            rendered = imageio.imread(rendered_path)
            assert np.abs(final.astype(float) - rendered).mean() < 5
            imageio.imwrite(directory / "first-frame.png", first)
            imageio.imwrite(directory / "final-frame.png", final)
        finally:
            reader.close()
    return result


@pytest.mark.parametrize(
    "name", sorted(p.stem for p in (ROOT / "tests/fixtures/drawings").glob("*.json"))
)
def test_full_drawing_pipeline(name):
    raw = json.loads((ROOT / "tests/fixtures/drawings" / f"{name}.json").read_text())
    with httpx.Client(base_url="http://localhost:8000", timeout=20) as client:
        saved = client.post("/demonstrations", json=raw)
        assert saved.status_code == 201, saved.text
        identity = saved.json()["id"]
        payload = {"demonstration_id": identity, "request_id": uuid.uuid4().hex}
        started = client.post("/runs", json=payload)
        assert started.status_code == 202, started.text
        run_id = started.json()["run_id"]
        assert client.post("/runs", json=payload).json()["run_id"] == run_id
        run = wait_run(client, run_id)
        result = verify(client, run)
        assert client.get("/demonstrations/" + identity).json() == raw
        print(name, run_id, json.dumps(result))
        if name == "star":
            shifted = client.post(
                "/runs",
                json={
                    "demonstration_id": identity,
                    "request_id": uuid.uuid4().hex,
                    "reuse_run_id": run_id,
                    "paper_pose": {"offset": [0.015, -0.01], "yaw": 0.12},
                },
            )
            assert shifted.status_code == 202, shifted.text
            second = wait_run(client, shifted.json()["run_id"])
            verify(client, second)
            assert (
                client.get("/runs/" + second["run_id"] + "/artifacts/skill.json").json()
                == run["skill"]
            )
            print("shifted-star", second["run_id"], json.dumps(second["result"]))


@pytest.mark.parametrize("identity", os.environ.get("DRAWING_DEMONSTRATIONS", "").split(","))
def test_saved_human_drawing(identity):
    if not identity:
        pytest.skip("Set DRAWING_DEMONSTRATIONS to replay personal local captures.")
    with httpx.Client(base_url="http://localhost:8000", timeout=20) as client:
        raw = client.get("/demonstrations/" + identity)
        assert raw.status_code == 200
        assert raw.json()["source"]["type"] == "human_capture"
        started = client.post(
            "/runs", json={"demonstration_id": identity, "request_id": uuid.uuid4().hex}
        )
        assert started.status_code == 202, started.text
        run = wait_run(client, started.json()["run_id"])
        verify(client, run)
        assert client.get("/demonstrations/" + identity).content == raw.content
        print("personal-capture", identity, run["run_id"], json.dumps(run["result"]))
