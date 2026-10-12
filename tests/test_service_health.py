# Purpose: Prove isolated dependency outages and recovery against the running Docker application.
import os
import subprocess
import time

import httpx
import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("RUN_INTEGRATION") != "1",
        reason="Set RUN_INTEGRATION=1 with the Docker stack running.",
    ),
]


@pytest.mark.parametrize("service,unaffected_port", [("perception", 8002), ("simulation", 8001)])
def test_dependency_failure_isolation(service, unaffected_port):
    try:
        subprocess.run(["docker", "compose", "stop", service], check=True, timeout=120)
        with httpx.Client(timeout=5) as client:
            assert client.get("http://localhost:8000/health").status_code == 200
            assert client.get("http://localhost:5173").status_code == 200
            assert client.get(f"http://localhost:{unaffected_port}/health").status_code == 200
            assert client.get("http://localhost:8000/ready").status_code == 503
            status = client.get("http://localhost:8000/services").json()
            assert status[service]["status"] == "unavailable"
    finally:
        subprocess.run(["docker", "compose", "start", service], check=True, timeout=120)
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
                pytest.fail("Dependency did not become ready after restart.")
