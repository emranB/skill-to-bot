# Purpose: Verify coordination, duplicate protection, timeouts, persistence, and restart handling.
import asyncio
import json
from pathlib import Path

import httpx
import pytest
from src.workflow.workflow import Workflow

CONFIG = {
    "request_timeout": 2,
    "health_timeout": 0.1,
    "simulation_timeout": 1,
    "poll_seconds": 0.001,
}
FIXTURE = (
    Path("/fixtures/skill.json")
    if Path("/fixtures/skill.json").exists()
    else Path(__file__).resolve().parents[3] / "tests/fixtures/skill.json"
)
SKILL = json.loads(FIXTURE.read_text())


def test_success_and_idempotency(tmp_path):
    async def check():
        workflow = Workflow(tmp_path, CONFIG, "http://perception", "http://simulation")
        await workflow.client.aclose()
        calls = []

        def handle(request):
            calls.append(request.url.path)
            if request.url.path == "/process":
                return httpx.Response(
                    200, json={"skill": SKILL, "observations": [], "limitations": []}
                )
            if request.url.path == "/execute":
                return httpx.Response(202, json={"status": "running"})
            return httpx.Response(
                200, json={"status": "completed", "phase": "retreat", "result": {"success": True}}
            )

        workflow.client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        run = await workflow.start("fixture.mp4", SKILL["calibration"], "same-request")
        duplicate = await workflow.start("fixture.mp4", SKILL["calibration"], "same-request")
        assert duplicate["run_id"] == run["run_id"]
        with pytest.raises(ValueError):
            await workflow.start("other.mp4", SKILL["calibration"], "same-request")
        with pytest.raises(RuntimeError):
            await workflow.start("fixture.mp4", SKILL["calibration"], "another-request")
        await asyncio.gather(*workflow.tasks)
        assert run["status"] == "completed"
        assert run["logs"][-1]["message"] == "Run completed. Physical result verified."
        saved = json.loads((tmp_path / "runs" / run["run_id"] / "run.json").read_text())
        assert saved["logs"] == run["logs"]
        assert calls.count("/execute") == 1
        assert (tmp_path / "runs" / run["run_id"] / "skill.json").exists()
        await workflow.close()

    asyncio.run(check())


def test_dependency_failure_and_restart(tmp_path):
    async def check():
        workflow = Workflow(tmp_path, CONFIG, "http://perception", "http://simulation")
        await workflow.client.aclose()

        def unavailable(request):
            raise httpx.ReadTimeout("Perception timeout", request=request)

        workflow.client = httpx.AsyncClient(transport=httpx.MockTransport(unavailable))
        run = await workflow.start("fixture.mp4", SKILL["calibration"], "timeout")
        await asyncio.gather(*workflow.tasks)
        assert run["status"] == "failed" and "timeout" in run["error"]
        run["status"] = "running"
        workflow.save(run)
        await workflow.close()
        restored = Workflow(tmp_path, CONFIG, "http://perception", "http://simulation")
        assert restored.runs[run["run_id"]]["status"] == "failed"
        assert "unknown" in restored.runs[run["run_id"]]["error"]
        assert "unknown" in restored.runs[run["run_id"]]["logs"][-1]["message"]
        await restored.close()

    asyncio.run(check())


def test_invalid_skill_never_executes(tmp_path):
    async def check():
        workflow = Workflow(tmp_path, CONFIG, "http://perception", "http://simulation")
        await workflow.client.aclose()
        calls = []

        def handle(request):
            calls.append(request.url.path)
            return httpx.Response(200, json={"skill": {}, "observations": [], "limitations": []})

        workflow.client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        run = await workflow.start("fixture.mp4", SKILL["calibration"], "invalid")
        await asyncio.gather(*workflow.tasks)
        assert run["status"] == "failed"
        assert "/execute" not in calls
        await workflow.close()

    asyncio.run(check())
