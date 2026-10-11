# Purpose: Expose demonstration, run, artifact, health, and status-streaming interfaces.
import asyncio
import json
import logging
import math
import os
import re
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import cv2
import httpx
from fastapi import FastAPI, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from src.workflow.workflow import Workflow

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / "config.json").read_text())
logging.basicConfig(level=logging.INFO, format="%(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
DATA = Path(os.environ.get("DATA_DIR", str(ROOT.parent.parent / "data"))).resolve()


@asynccontextmanager
async def lifespan(app: FastAPI):
    DATA.joinpath("demonstrations").mkdir(parents=True, exist_ok=True)
    app.state.workflow = Workflow(
        DATA,
        CONFIG,
        os.environ.get("PERCEPTION_URL", "http://localhost:8001"),
        os.environ.get("SIMULATION_URL", "http://localhost:8002"),
    )
    yield
    await app.state.workflow.close()


app = FastAPI(title="skill-to-bot orchestrator", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("WEB_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class RunRequest(BaseModel):
    video: str = Field(min_length=1, max_length=100)
    calibration: dict
    request_id: str = Field(min_length=1, max_length=100)


def demo_path(video: str) -> Path:
    if (
        Path(video).name != video
        or "/" in video
        or "\\" in video
        or not video.lower().endswith(".mp4")
    ):
        raise HTTPException(422, "Invalid demonstration name.")
    path = (DATA / "demonstrations" / video).resolve()
    if path.parent != DATA / "demonstrations" or not path.is_file():
        raise HTTPException(404, "Demonstration not found.")
    return path


def validate_calibration(calibration: dict):
    roi = calibration.get("roi")
    span = calibration.get("workspace_span")
    if calibration.get("method") != "operator_planar" or calibration.get("plane") != "front":
        raise HTTPException(422, "Explicit front-plane calibration is required.")
    if not isinstance(span, (int, float)) or not math.isfinite(span) or not 0.05 <= span <= 0.5:
        raise HTTPException(422, "Workspace span must be 0.05 to 0.5 meters.")
    if (
        not isinstance(roi, list)
        or len(roi) != 4
        or not all(isinstance(v, (int, float)) and math.isfinite(v) and 0 <= v <= 1 for v in roi)
    ):
        raise HTTPException(422, "Select a valid object rectangle.")
    if min(roi[2:]) < 0.01 or roi[0] + roi[2] > 1 or roi[1] + roi[3] > 1:
        raise HTTPException(422, "Object rectangle must fit inside the video.")


@app.get("/health")
def health():
    return {"service": "orchestrator", "status": "ok"}


@app.get("/ready")
async def ready():
    services = await app.state.workflow.service_status()
    if any(value["status"] != "ready" for value in services.values()):
        raise HTTPException(503, {"status": "degraded", "services": services})
    return {"service": "orchestrator", "status": "ready", "services": services}


@app.get("/version")
def version():
    return {"service": "orchestrator", "version": "0.1.0"}


@app.get("/services")
async def services():
    return await app.state.workflow.service_status()


@app.get("/demonstrations")
def demonstrations():
    return [
        {"name": path.name, "bytes": path.stat().st_size, "url": "/demonstrations/" + path.name}
        for path in sorted(DATA.joinpath("demonstrations").glob("*.mp4"))
        if path.resolve().parent == DATA / "demonstrations"
    ]


def preview_image(path: Path):
    capture = cv2.VideoCapture(str(path))
    try:
        ok, frame = capture.read()
        if not ok:
            raise HTTPException(422, "Video cannot be decoded.")
        height, width = frame.shape[:2]
        frame = cv2.resize(frame, (960, round(height * 960 / width)))
        ok, jpeg = cv2.imencode(".jpg", frame)
        if not ok:
            raise HTTPException(422, "Preview could not be rendered.")
        return Response(jpeg.tobytes(), media_type="image/jpeg")
    finally:
        capture.release()


@app.get("/demonstrations/{video}/preview")
def preview(video: str):
    return preview_image(demo_path(video))


@app.get("/demonstrations/{video}")
def demonstration(video: str):
    return FileResponse(demo_path(video), media_type="video/mp4")


@app.post("/demonstrations", status_code=201)
async def upload(file: UploadFile):
    if not (file.filename or "").lower().endswith(".mp4"):
        raise HTTPException(422, "Upload an MP4 video.")
    path = DATA / "demonstrations" / (uuid.uuid4().hex + ".mp4")
    size = 0
    try:
        with path.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > CONFIG["max_upload_bytes"]:
                    raise HTTPException(413, "Video exceeds 100 MB.")
                output.write(chunk)
        capture = cv2.VideoCapture(str(path))
        try:
            fps, frames = capture.get(cv2.CAP_PROP_FPS), capture.get(cv2.CAP_PROP_FRAME_COUNT)
            valid = (
                capture.isOpened()
                and fps > 0
                and frames >= 4
                and frames / fps <= CONFIG["max_video_seconds"]
            )
        finally:
            capture.release()
        if not valid:
            raise HTTPException(422, "Video is unreadable, empty, or longer than 60 seconds.")
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()
    return {"name": path.name, "bytes": size, "url": "/demonstrations/" + path.name}


@app.post("/runs", status_code=202)
async def start(request: RunRequest):
    demo_path(request.video)
    validate_calibration(request.calibration)
    try:
        return await app.state.workflow.start(
            request.video, request.calibration, request.request_id
        )
    except RuntimeError as error:
        raise HTTPException(409, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@app.get("/runs")
def runs():
    return sorted(app.state.workflow.runs.values(), key=lambda run: run["created_at"], reverse=True)


@app.get("/runs/{run_id}")
def run(run_id: str):
    if run_id not in app.state.workflow.runs:
        raise HTTPException(404, "Run not found.")
    return app.state.workflow.runs[run_id]


@app.get("/runs/{run_id}/artifacts/{name}")
def artifact(run_id: str, name: str):
    if not re.fullmatch(r"[a-f0-9]{32}", run_id) or name not in {
        "skill.json",
        "observations.json",
        "simulation.mp4",
        "simulation-result.json",
        "run.json",
    }:
        raise HTTPException(404, "Artifact not found.")
    path = (DATA / "runs" / run_id / name).resolve()
    if not path.is_relative_to(DATA / "runs") or not path.is_file():
        raise HTTPException(404, "Artifact not found.")
    return FileResponse(
        path, media_type="video/mp4" if name.endswith(".mp4") else "application/json"
    )


@app.get("/runs/{run_id}/preview")
def simulation_preview(run_id: str):
    if not re.fullmatch(r"[a-f0-9]{32}", run_id):
        raise HTTPException(404, "Run preview not found.")
    path = (DATA / "runs" / run_id / "simulation.mp4").resolve()
    if not path.is_relative_to(DATA / "runs") or not path.is_file():
        raise HTTPException(404, "Run preview not found.")
    return preview_image(path)


@app.post("/reset")
async def reset():
    workflow = app.state.workflow
    async with workflow.lock:
        if any(run["status"] == "running" for run in workflow.runs.values()):
            raise HTTPException(409, "Cannot reset while a run is active.")
        try:
            response = await workflow.client.post(
                workflow.urls["simulation"] + "/reset", timeout=15
            )
            Workflow.require_success(response)
            return response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise HTTPException(503, str(error)) from error


@app.websocket("/ws")
async def websocket(socket: WebSocket):
    allowed = os.environ.get("WEB_ORIGINS", "http://localhost:5173").split(",")
    if socket.headers.get("origin") not in allowed:
        await socket.close(code=1008)
        return
    await socket.accept()
    try:
        while True:
            await socket.send_json(
                {
                    "type": "snapshot",
                    "services": await app.state.workflow.service_status(),
                    "runs": runs(),
                }
            )
            await asyncio.sleep(CONFIG["status_seconds"])
    except (WebSocketDisconnect, RuntimeError, OSError):
        return
