# Purpose: Verify immutable raw persistence, request bounds, safe artifact paths and human library isolation.
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api import api


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "DATA", tmp_path)
    monkeypatch.setenv("SIMULATION_URL", "http://127.0.0.1:1")
    with TestClient(api.app) as client:
        yield client


def raw():
    path = Path("/fixtures/drawings/star.json")
    if not path.exists():
        path = Path(__file__).resolve().parents[3] / "tests/fixtures/drawings/star.json"
    return json.loads(path.read_text())


def test_immutable_capture_and_library(client, tmp_path):
    value = raw()
    payload = json.dumps(value, indent=1).encode()
    saved = client.post(
        "/demonstrations", content=payload, headers={"Content-Type": "application/json"}
    )
    assert saved.status_code == 201, saved.text
    identity = saved.json()["id"]
    assert (tmp_path / "demonstrations" / f"{identity}.json").read_bytes() == payload
    assert client.get(f"/demonstrations/{identity}").json() == value
    assert client.get("/demonstrations").json() == []
    value["source"]["type"] = "human_capture"
    assert client.post("/demonstrations", json=value).status_code == 201
    assert len(client.get("/demonstrations").json()) == 1
    assert (tmp_path / "demonstrations" / f"{identity}.json").read_bytes() == payload


def test_api_failures(client):
    for value in (
        {},
        {"strokes": []},
        raw() | {"extra": "bad"},
        raw() | {"source": {"type": "unsupported"}},
    ):
        assert client.post("/demonstrations", json=value).status_code == 422
    assert (
        client.post(
            "/demonstrations", content=b"x" * (api.CONFIG["max_body_bytes"] + 1)
        ).status_code
        == 413
    )
    assert client.get("/demonstrations/invalid").status_code == 404
    assert client.get("/runs/invalid/artifacts/.env").status_code == 404
    assert (
        client.post("/runs", json={"demonstration_id": "a" * 32, "request_id": "x"}).status_code
        == 404
    )
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 503


def test_delete_history_preserves_source_and_evidence(client, tmp_path):
    identity = client.post("/demonstrations", json=raw()).json()["id"]
    run_id = "b" * 32
    record = {
        "run_id": run_id,
        "demonstration_id": identity,
        "request_id": "delete-test",
        "status": "running",
        "phase": "draw",
        "created_at": 1,
    }
    workflow = api.app.state.workflow
    workflow.runs[run_id] = record
    workflow.save(record)
    artifact = tmp_path / "runs" / run_id / "trace.json"
    artifact.write_text('{"samples": []}')
    source = (tmp_path / "demonstrations" / f"{identity}.json").read_bytes()
    assert client.delete(f"/runs/{run_id}").status_code == 409
    record["status"] = "completed"
    record["skill"] = {"strokes": []}
    summary = client.get(f"/runs/{run_id}?summary=true").json()
    assert summary["skill_available"] and "skill" not in summary
    assert client.get("/runs?summary=true").json()[0]["thumbnail_available"] is False
    assert client.get(f"/runs/{run_id}").json()["skill"] == record["skill"]
    assert client.delete(f"/runs/{run_id}").status_code == 204
    timestamp = record["deleted_at"]
    assert client.delete(f"/runs/{run_id}").status_code == 204
    assert record["deleted_at"] == timestamp
    assert client.get("/runs").json() == client.get("/runs?summary=true").json() == []
    assert json.loads((artifact.parent / "run.json").read_text())["deleted_at"] == timestamp
    assert client.get(f"/runs/{run_id}/artifacts/trace.json").json() == {"samples": []}
    assert client.get(f"/demonstrations/{identity}").content == source
    assert client.delete("/runs/invalid").status_code == 404
