# Purpose: Verify simulation outages do not terminate drawing capture or trigger command replay.
import os
import subprocess
import time

import httpx
import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("RUN_INTEGRATION") != "1",
        reason="Set RUN_INTEGRATION=1 with Docker running.",
    ),
]


def test_dependency_isolation_and_recovery():
    with httpx.Client(base_url="http://localhost:8000", timeout=10) as client:
        completed = [r for r in client.get("/runs").json() if r["status"] == "completed"]
        assert completed
        record = completed[0]
        saved = client.get(f"/runs/{record['run_id']}/artifacts/simulation-result.json").json()
    try:
        subprocess.run(["docker", "compose", "stop", "simulation"], check=True, timeout=120)
        with httpx.Client(timeout=5) as client:
            assert client.get("http://localhost:8000/health").status_code == 200
            assert client.get("http://localhost:5173/health").status_code == 200
            assert client.get("http://localhost:8000/ready").status_code == 503
            assert (
                client.get("http://localhost:8000/services").json()["simulation"]["status"]
                == "unavailable"
            )
    finally:
        subprocess.run(["docker", "compose", "start", "simulation"], check=True, timeout=120)
        deadline = time.monotonic() + 180
        with httpx.Client(timeout=5) as client:
            while time.monotonic() < deadline:
                try:
                    if client.get("http://localhost:8000/ready").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.5)
            else:
                pytest.fail("Drawing dependency did not recover.")
    with httpx.Client(timeout=10) as client:
        response = client.post("http://localhost:8002/execute", json=saved["request"])
        assert response.status_code == 202 and response.json()["status"] == "completed"
        conflicting = {**saved["request"], "paper_pose": {"offset": [0, 0], "yaw": 0.1}}
        assert client.post("http://localhost:8002/execute", json=conflicting).status_code == 409
