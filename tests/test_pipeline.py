# Purpose: Verify the complete supplied-human-video to Panda pipeline and honest invalid-input failures.
import json
import os
import time
import uuid
from pathlib import Path

import httpx
import pytest
from fixtures.generate_video import generate_calibrated_transport, generate_transport

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("RUN_INTEGRATION") != "1",
        reason="Set RUN_INTEGRATION=1 with the Docker stack running.",
    ),
]
BASE = os.environ.get("ORCHESTRATOR_URL", "http://localhost:8000")
CALIBRATION = {
    "method": "operator_planar",
    "plane": "front",
    "workspace_span": 0.3,
    "roi": [0.67, 0.23, 0.17, 0.5],
}


def test_complete_pipeline():
    with httpx.Client(base_url=BASE, timeout=10) as client:
        assert client.get("/ready").status_code == 200
        payload = {
            "video": "pop-can-pick-up-right-to-left-1.mp4",
            "calibration": CALIBRATION,
            "request_id": uuid.uuid4().hex,
        }
        response = client.post("/runs", json=payload)
        assert response.status_code == 202, response.text
        run_id = response.json()["run_id"]
        assert client.post("/runs", json=payload).json()["run_id"] == run_id
        assert client.post("/reset").status_code == 409
        deadline = time.monotonic() + 480
        while time.monotonic() < deadline:
            run = client.get("/runs/" + run_id).json()
            if run["status"] != "running":
                break
            time.sleep(0.5)
        assert run["status"] == "completed", run
        assert run["result"]["success"] and run["result"]["lifted"] and run["result"]["released"]
        assert run["result"]["position_error_m"] <= 0.035
        assert client.get(f"/runs/{run_id}/artifacts/skill.json").status_code == 200
        assert len(client.get(f"/runs/{run_id}/artifacts/simulation.mp4").content) > 1000
        observations = client.get(f"/runs/{run_id}/artifacts/observations.json").json()
        held = min(observations, key=lambda sample: abs(sample["time"] - 7))
        assert observations[0]["segmentation_source"] == "yolo"
        assert 0.08 < held["u"] < 0.18, "The held object must not switch to the demonstrator."
        assert held["box"][0] < 0.1 and held["box"][2] < 0.25
        assert client.post("/reset").status_code == 200


def test_failed_physical_manipulation_is_not_success():
    skill = json.loads((Path(__file__).parent / "fixtures/skill.json").read_text())
    skill["approach_height"] = 0.04
    run_id = uuid.uuid4().hex
    with httpx.Client(base_url="http://localhost:8002", timeout=10) as client:
        response = client.post("/execute", json={"run_id": run_id, "skill": skill})
        assert response.status_code == 202, response.text
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            job = client.get("/jobs/" + run_id).json()
            if job["status"] != "running":
                break
            time.sleep(0.5)
        assert job["status"] == "failed", job
        assert job.get("error") and not job.get("result", {}).get("success", False)
        assert client.post("/reset").status_code == 200


def test_invalid_video_and_selection():
    with httpx.Client(base_url=BASE, timeout=10) as client:
        assert (
            client.post(
                "/demonstrations", files={"file": ("invalid.mp4", b"not video")}
            ).status_code
            == 422
        )
        invalid = {**CALIBRATION, "roi": [0.9, 0.9, 0.3, 0.3]}
        assert (
            client.post(
                "/runs",
                json={
                    "video": "pop-can-pick-up-right-to-left-1.mp4",
                    "calibration": invalid,
                    "request_id": uuid.uuid4().hex,
                },
            ).status_code
            == 422
        )


def test_recorded_return_path_reaches_panda_in_order(tmp_path):
    video = generate_transport(tmp_path / "return.mp4")
    with httpx.Client(base_url=BASE, timeout=15) as client:
        with video.open("rb") as stream:
            response = client.post(
                "/demonstrations", files={"file": ("return.mp4", stream, "video/mp4")}
            )
        assert response.status_code == 201, response.text
        saved = response.json()["name"]
        payload = {
            "video": saved,
            "request_id": uuid.uuid4().hex,
            "calibration": {**CALIBRATION, "roi": [0.65, 0.2, 0.22, 0.58]},
        }
        started = client.post("/runs", json=payload)
        assert started.status_code == 202, started.text
        run_id = started.json()["run_id"]
        deadline = time.monotonic() + 480
        while time.monotonic() < deadline:
            run = client.get("/runs/" + run_id).json()
            if run["status"] != "running":
                break
            time.sleep(0.5)
        assert run["status"] == "completed", run
        path = run["skill"]["transport"]
        assert len(path) >= 3 and abs(path[-1][1]) < 0.02
        assert max(point[1] for point in path) > 0.07
        measured = run["result"]["transport"]
        assert len(measured) == len(path) - 1
        assert all(point["error_m"] <= 0.035 for point in measured)
        assert max(point["actual"][1] - run["result"]["initial"][1] for point in measured) > 0.05
        assert client.post("/reset").status_code == 200


@pytest.mark.parametrize(
    "path,endpoint",
    [
        ([[0, 0], [0, 0.08]], "/demonstrations"),
        ([[0, 0], [0, -0.08]], "/live-demonstrations"),
        ([[0, 0], [0, 0.08], [0.08, 0.08], [0.08, 0], [0.001, 0]], "/demonstrations"),
    ],
)
def test_calibrated_lift_depth_and_order_reach_physics(tmp_path, path, endpoint):
    video, calibration = generate_calibrated_transport(tmp_path / "calibrated.mp4", path)
    with httpx.Client(base_url=BASE, timeout=15) as client:
        checked = client.post("/calibration", json=calibration)
        assert checked.status_code == 200, checked.text
        with video.open("rb") as stream:
            uploaded = client.post(
                endpoint, files={"file": ("calibrated.mp4", stream, "video/mp4")}, timeout=105
            )
        assert uploaded.status_code == 201, uploaded.text
        started = client.post(
            "/runs",
            json={
                "video": uploaded.json()["name"],
                "request_id": uuid.uuid4().hex,
                "calibration": calibration,
            },
        )
        assert started.status_code == 202, started.text
        run_id = started.json()["run_id"]
        deadline = time.monotonic() + 480
        while time.monotonic() < deadline:
            run = client.get("/runs/" + run_id).json()
            if run["status"] != "running":
                break
            time.sleep(0.5)
        assert run["status"] == "completed", run
        expected = [[depth * 0.75, -lateral * 0.75] for lateral, depth in path]
        actual = [point[:2] for point in run["skill"]["transport"]]
        assert len(actual) == len(expected)
        for point, truth in zip(actual, expected):
            assert point == pytest.approx(truth, abs=0.008)
        result = run["result"]
        assert result["lifted"] and result["grasped"] and result["released"] and result["success"]
        assert len(result["transport"]) == len(expected) - 1
        assert all(point["error_m"] <= 0.035 for point in result["transport"])
        assert result["position_error_m"] <= 0.035
        assert client.post("/reset").status_code == 200
