# Purpose: Verify serialized idempotent drawing runs, command uncertainty and restart persistence.
import asyncio
import json
from pathlib import Path

import httpx
import pytest

from src.workflow.workflow import Workflow

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config.json").read_text()) | {
    "poll_seconds": 0.001,
    "simulation_timeout": 0.1,
}
CONTRACTS = (
    Path("/app/contracts") if Path("/app/contracts").exists() else ROOT.parents[1] / "contracts"
)
FIXTURE = (
    Path("/fixtures/drawings/star.json")
    if Path("/fixtures/drawings/star.json").exists()
    else ROOT.parents[1] / "tests/fixtures/drawings/star.json"
)


@pytest.mark.parametrize("failure", [False, True, "read_reset"])
def test_execution_idempotency_failure_and_restart(tmp_path, failure):
    async def check():
        wf = Workflow(tmp_path, CONFIG, CONTRACTS, "http://simulation")
        identity = "a" * 32
        (tmp_path / "demonstrations" / f"{identity}.json").write_bytes(FIXTURE.read_bytes())
        calls = []

        def handle(request):
            calls.append(request.url.path)
            if request.url.path == "/execute":
                if failure is True:
                    raise httpx.ReadTimeout("uncertain", request=request)
                return httpx.Response(202, json={"status": "running"})
            if failure == "read_reset" and calls.count(request.url.path) == 1:
                raise httpx.ReadError("connection reset", request=request)
            return httpx.Response(
                200,
                json={
                    "status": "completed",
                    "phase": "completed",
                    "result": {"success": True, "mean_path_error_m": 0.001},
                },
            )

        await wf.client.aclose()
        wf.client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        run = await wf.start(identity, "request")
        assert (await wf.start(identity, "request"))["run_id"] == run["run_id"]
        with pytest.raises(ValueError):
            await wf.start(identity, "request", {"offset": [0, 0], "yaw": 0})
        with pytest.raises(RuntimeError):
            await wf.start(identity, "other")
        with pytest.raises(RuntimeError, match="active"):
            await wf.delete(run["run_id"])
        await asyncio.gather(*wf.tasks)
        assert run["status"] == ("failed" if failure is True else "completed")
        assert calls.count("/execute") == 1
        if failure is True:
            assert "unknown" in run["error"]
        await wf.delete(run["run_id"])
        deleted_at = run["deleted_at"]
        await wf.delete(run["run_id"])
        assert run["deleted_at"] == deleted_at
        assert (await wf.start(identity, "request"))["run_id"] == run["run_id"]
        assert calls.count("/execute") == 1
        run["status"] = "running"
        wf.save(run)
        if failure is False:
            (tmp_path / "runs" / run["run_id"] / "simulator-final.png").touch()
        await wf.close()
        restored = Workflow(tmp_path, CONFIG, CONTRACTS, "http://simulation")
        assert restored.runs[run["run_id"]]["status"] == "failed"
        assert "unknown" in restored.runs[run["run_id"]]["error"]
        assert restored.runs[run["run_id"]]["deleted_at"] == deleted_at
        assert restored.runs[run["run_id"]]["thumbnail_available"] is (failure is False)
        await restored.close()

    asyncio.run(check())
