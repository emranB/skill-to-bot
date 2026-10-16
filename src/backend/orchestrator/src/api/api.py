# Purpose: Persist validated drawing demonstrations and expose runs, health and artifacts.
import json
import logging
import os
import re
import time
import uuid
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from jsonschema import ValidationError
from pydantic import BaseModel, Field

from src.stroke_processing.stroke_processing import validate_demonstration
from src.workflow.workflow import Workflow

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / "config.json").read_text())
DATA = Path(os.environ.get("DATA_DIR", str(ROOT.parent.parent / "data"))).resolve()
CONTRACTS = Path(os.environ.get("CONTRACTS_DIR", str(ROOT.parent.parent / "contracts")))
logging.basicConfig(level=logging.INFO, format="%(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app):
    app.state.workflow = Workflow(
        DATA, CONFIG, CONTRACTS, os.environ.get("SIMULATION_URL", "http://localhost:8002")
    )
    yield
    await app.state.workflow.close()


WEB_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("WEB_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
WEB_ORIGIN_REGEX = re.compile(
    os.environ.get(
        "WEB_ORIGIN_REGEX",
        r"https://([a-z0-9-]+\.)?skill-to-bot\.pages\.dev",
    )
)


def allowed_origin(origin: str | None) -> str | None:
    """Return origin when it matches WEB_ORIGINS or WEB_ORIGIN_REGEX."""
    if not origin:
        return None
    if origin in WEB_ORIGINS or WEB_ORIGIN_REGEX.fullmatch(origin):
        return origin
    return None


app = FastAPI(title="skill-to-bot orchestrator", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=WEB_ORIGINS,
    allow_origin_regex=WEB_ORIGIN_REGEX.pattern,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def allow_private_network(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Allow Chrome private-network preflights from hosted Pages to loopback."""
    origin = allowed_origin(request.headers.get("Origin"))
    if (
        request.method == "OPTIONS"
        and request.headers.get("Access-Control-Request-Private-Network") == "true"
    ):
        if not origin:
            return Response(status_code=403)
        return Response(
            status_code=204,
            headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "GET, POST, DELETE",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Private-Network": "true",
                "Vary": "Origin",
            },
        )
    response = await call_next(request)
    if origin:
        response.headers["Access-Control-Allow-Private-Network"] = "true"
    return response


@app.middleware("http")
async def bounded_body(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    if request.method == "POST":
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > CONFIG["max_body_bytes"]:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Demonstration exceeds the request size limit."},
                )
        request._body = bytes(body)
    return await call_next(request)


def demo_path(demonstration_id):
    if not re.fullmatch(r"[a-f0-9]{32}", demonstration_id):
        raise HTTPException(404, "Drawing demonstration not found.")
    path = DATA / "demonstrations" / (demonstration_id + ".json")
    if not path.is_file() or path.is_symlink():
        raise HTTPException(404, "Drawing demonstration not found.")
    return path


@app.get("/health")
def health():
    return {"service": "orchestrator", "status": "ok"}


@app.get("/ready")
async def ready():
    services = await app.state.workflow.service_status()
    if any(s["status"] != "ready" for s in services.values()):
        raise HTTPException(503, {"status": "degraded", "services": services})
    return {"service": "orchestrator", "status": "ready", "services": services}


@app.get("/version")
def version():
    return {"service": "orchestrator", "version": "0.2.0"}


@app.get("/services")
async def services():
    return await app.state.workflow.service_status()


@app.post("/demonstrations", status_code=201)
async def save_demonstration(request: Request):
    body = await request.body()
    try:
        raw = json.loads(body)
        validate_demonstration(raw, CONTRACTS, CONFIG)
    except (ValueError, TypeError, KeyError, ValidationError) as error:
        raise HTTPException(422, f"Invalid drawing: {str(error)[:400]}") from error
    demonstration_id = uuid.uuid4().hex
    path = DATA / "demonstrations" / (demonstration_id + ".json")
    with path.open("xb") as output:
        output.write(body)
    return {
        "id": demonstration_id,
        "created_at": time.time(),
        "source": raw["source"],
        "device": raw["device"],
        "strokes": len(raw["strokes"]),
        "samples": sum(len(s["points"]) for s in raw["strokes"]),
    }


@app.get("/demonstrations")
def demonstrations():
    result = []
    for path in sorted(
        (DATA / "demonstrations").glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    ):
        if not re.fullmatch(r"[a-f0-9]{32}", path.stem) or path.is_symlink():
            continue
        try:
            raw = json.loads(path.read_text())
            # Synthetic requests remain reusable by ID but do not pollute the human library.
            if raw["source"]["type"] != "human_capture":
                continue
            result.append(
                {
                    "id": path.stem,
                    "source": raw["source"],
                    "created_at": path.stat().st_mtime,
                    "device": raw["device"],
                    "strokes": len(raw["strokes"]),
                    "samples": sum(len(s["points"]) for s in raw["strokes"]),
                }
            )
        except (OSError, ValueError, KeyError):
            continue
    return result


@app.get("/demonstrations/{demonstration_id}")
def demonstration(demonstration_id: str):
    return FileResponse(demo_path(demonstration_id), media_type="application/json")


class PaperPose(BaseModel):
    model_config = {"extra": "forbid", "allow_inf_nan": False, "strict": True}
    offset: list[float] = Field(min_length=2, max_length=2)
    yaw: float = Field(ge=-0.2617993877991494, le=0.2617993877991494)


class RunRequest(BaseModel):
    model_config = {"extra": "forbid"}
    demonstration_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    request_id: str = Field(min_length=1, max_length=100)
    paper_pose: PaperPose | None = None
    reuse_run_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")


@app.post("/runs", status_code=202)
async def start(request: RunRequest):
    demo_path(request.demonstration_id)
    if request.paper_pose and any(abs(v) > 0.025 for v in request.paper_pose.offset):
        raise HTTPException(422, "Paper offset is outside the supported region.")
    try:
        return await app.state.workflow.start(
            request.demonstration_id,
            request.request_id,
            request.paper_pose.model_dump() if request.paper_pose else None,
            request.reuse_run_id,
        )
    except RuntimeError as error:
        raise HTTPException(409, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@app.get("/runs")
def runs(summary: bool = False):
    records = sorted(
        (r for r in app.state.workflow.runs.values() if not r.get("deleted_at")),
        key=lambda r: r["created_at"],
        reverse=True,
    )
    if not summary:
        return records
    return [
        {
            **{
                key: r[key]
                for key in ("run_id", "demonstration_id", "status", "phase", "created_at")
            },
            "stroke_count": len(r.get("skill", {}).get("strokes", [])),
            "source_type": r.get("skill", {}).get("source", {}).get("type"),
            "video_available": r.get("video_available", False),
            "thumbnail_available": r.get("thumbnail_available", False),
        }
        for r in records
    ]


@app.get("/runs/{run_id}")
def run(run_id: str, summary: bool = False):
    if run_id not in app.state.workflow.runs:
        raise HTTPException(404, "Drawing run not found.")
    record = app.state.workflow.runs[run_id]
    if summary:
        return {
            **{key: value for key, value in record.items() if key != "skill"},
            "skill_available": "skill" in record,
        }
    return record


@app.delete("/runs/{run_id}", status_code=204)
async def delete_run(run_id: str):
    try:
        await app.state.workflow.delete(run_id)
    except KeyError as error:
        raise HTTPException(404, "Drawing run not found.") from error
    except RuntimeError as error:
        raise HTTPException(409, str(error)) from error


@app.get("/runs/{run_id}/artifacts/{name}")
def artifact(run_id: str, name: str):
    if run_id not in app.state.workflow.runs or name not in {
        "run.json",
        "skill.json",
        "trace.json",
        "robot-plan.json",
        "simulation-result.json",
        "simulation.mp4",
        "simulator-final.png",
    }:
        raise HTTPException(404, "Drawing artifact not found.")
    path = (DATA / "runs" / run_id / name).resolve()
    if not path.is_relative_to((DATA / "runs").resolve()) or not path.is_file():
        raise HTTPException(404, "Drawing artifact not found.")
    return FileResponse(
        path,
        media_type="video/mp4"
        if name.endswith(".mp4")
        else "image/png"
        if name.endswith(".png")
        else "application/json",
        content_disposition_type="inline",
    )
