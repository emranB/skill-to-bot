# Purpose: Verify API input boundaries, upload validation, health isolation, and WebSocket snapshots.
import httpx
import pytest
from fastapi.testclient import TestClient
from src.api import api


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "DATA", tmp_path)
    with TestClient(api.app) as client:
        original = api.app.state.workflow.client

        async def unavailable(request):
            raise httpx.ConnectError("offline", request=request)

        api.app.state.workflow.client = httpx.AsyncClient(
            transport=httpx.MockTransport(unavailable)
        )
        yield client
        client.portal.call(original.aclose)


def test_health_survives_missing_dependencies(client):
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 503
    assert client.get("/services").json()["simulation"]["status"] == "unavailable"


def test_invalid_and_corrupt_upload(client, tmp_path):
    assert (
        client.post("/demonstrations", files={"file": ("bad.txt", b"invalid")}).status_code == 422
    )
    assert (
        client.post("/demonstrations", files={"file": ("bad.mp4", b"invalid")}).status_code == 422
    )
    assert client.get("/demonstrations").json() == []
    assert (
        client.post("/live-demonstrations", files={"file": ("bad.txt", b"invalid")}).status_code
        == 422
    )
    assert (
        client.post("/live-demonstrations", files={"file": ("bad.webm", b"invalid")}).status_code
        == 422
    )
    assert list((tmp_path / "live_demos").iterdir()) == []


def test_paths_missing_runs_and_calibration(client, tmp_path):
    assert client.get("/runs/unknown").status_code == 404
    assert client.get("/runs/" + "a" * 32 + "/artifacts/.env").status_code == 404
    path = tmp_path / "demonstrations" / "demo.mp4"
    path.write_bytes(b"dummy")
    assert (
        client.post(
            "/runs", json={"video": "demo.mp4", "request_id": "test", "calibration": {}}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/runs", json={"video": "../demo.mp4", "request_id": "test", "calibration": {}}
        ).status_code
        == 422
    )


def test_reset_unavailable_and_active(client):
    assert client.post("/reset").status_code == 503
    api.app.state.workflow.runs["active"] = {"status": "running"}
    assert client.post("/reset").status_code == 409


def test_websocket_snapshot(client):
    with client.websocket_connect("/ws", headers={"origin": "http://localhost:5173"}) as socket:
        snapshot = socket.receive_json()
        assert snapshot["type"] == "snapshot"
        assert snapshot["services"]["perception"]["status"] == "unavailable"


def test_calibration_boundary_reports_missing_geometry_and_dependency(client):
    legacy = {
        "method": "operator_planar",
        "plane": "front",
        "workspace_span": 0.3,
        "roi": [0.1, 0.1, 0.2, 0.4],
    }
    assert (
        client.post(
            "/calibration", json={**legacy, "method": "support_plane", "plane": "table"}
        ).status_code
        == 422
    )
    assert client.post("/calibration", json=legacy).status_code == 503
    assert client.post("/calibration", json={**legacy, "extra": "ignored"}).status_code == 422
