"""FastAPI application: REST + WebSocket + static frontend."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from backend.core.bus import EventBus, Topics
from backend.core.config import get_config
from backend.pipeline.orchestrator import PipelineSession
from backend.storage.repo import Repository

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")

app = FastAPI(title="GestureGPT", version="0.1.0")
cfg = get_config()
bus = EventBus()
repo = Repository(cfg.data_dir)
sessions: dict[str, PipelineSession] = {}
FRONTEND = Path(__file__).resolve().parents[2] / "frontend"


# ---------- REST ----------

@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "imagegen": cfg.imagegen.backend,
            "prompting": cfg.prompting.strategy}


@app.post("/api/session")
async def create_session() -> dict:
    session = PipelineSession(cfg, bus, repo)
    await session.start()
    sessions[session.id] = session
    return {"session_id": session.id}


@app.delete("/api/session/{session_id}")
async def end_session(session_id: str) -> dict:
    session = _get(session_id)
    await session.stop()
    del sessions[session_id]
    return {"ended": session_id}


@app.get("/api/session/{session_id}/scene")
async def get_scene(session_id: str) -> dict:
    return _get(session_id).scene.graph.model_dump()


@app.get("/api/session/{session_id}/generations")
async def list_generations(session_id: str) -> list[dict]:
    _get(session_id)
    return repo.list_generations(session_id)


@app.post("/api/session/{session_id}/generate")
async def force_generate(session_id: str) -> dict:
    _get(session_id).force_generate()
    return {"queued": True}


@app.get("/api/session/{session_id}/frame")
async def frame(session_id: str) -> Response:
    """Latest camera frame (with gesture overlay) as a single JPEG.

    The frontend polls this in a tight onload loop — far more reliable across
    browsers than an MJPEG stream in an <img>.
    """
    session = _get(session_id)
    jpeg = session.latest_jpeg
    if not jpeg:
        return Response(status_code=204)  # camera warming up
    return Response(content=jpeg, media_type="image/jpeg",
                    headers={"Cache-Control": "no-store"})


@app.get("/api/session/{session_id}/video")
async def video_feed(session_id: str) -> StreamingResponse:
    """MJPEG stream of the live camera with the gesture-tracking overlay.

    Runs only while the session (and therefore the camera) is alive; ends
    automatically when the session is stopped.
    """
    session = _get(session_id)

    async def frames():
        blank_waits = 0
        while sessions.get(session_id) is session:
            jpeg = session.latest_jpeg
            if jpeg:
                blank_waits = 0
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n"
                       b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n"
                       + jpeg + b"\r\n")
            else:
                # Camera not producing yet (warm-up) or shutting down.
                blank_waits += 1
                if blank_waits > 200 and not session.camera_active:
                    break
            await asyncio.sleep(0.04)  # ~25 fps ceiling

    return StreamingResponse(
        frames(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/api/images/{image_id}")
async def get_image(image_id: str) -> FileResponse:
    path = repo.image_path(image_id)
    if not path or not Path(path).exists():
        raise HTTPException(404, "image not found")
    return FileResponse(path, media_type="image/png")


@app.get("/api/config")
async def get_app_config() -> dict:
    return cfg.model_dump(mode="json")


def _get(session_id: str) -> PipelineSession:
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(404, "session not found")
    return session


# ---------- WebSocket ----------

_WS_TOPICS = (Topics.FEATURES, Topics.PRIMITIVE, Topics.INTENT, Topics.SCENE_UPDATE,
              Topics.GENERATION_STARTED, Topics.GENERATION_DONE, Topics.STATUS,
              Topics.ERROR)


@app.websocket("/ws/{session_id}")
async def ws_endpoint(ws: WebSocket, session_id: str) -> None:
    await ws.accept()
    session = sessions.get(session_id)
    if not session:
        await ws.close(code=4004)
        return

    queue: asyncio.Queue = asyncio.Queue(maxsize=200)

    def make_handler(topic: str):
        async def handler(payload) -> None:  # noqa: ANN001
            if not queue.full():
                queue.put_nowait({"type": topic, "data": payload})
        return handler

    for topic in _WS_TOPICS:
        bus.subscribe(topic, make_handler(topic))

    async def sender() -> None:
        while True:
            await ws.send_json(await queue.get())

    send_task = asyncio.create_task(sender())
    try:
        while True:
            msg = await ws.receive_json()
            kind = msg.get("type")
            if kind == "pause":
                session.pause(True)
            elif kind == "resume":
                session.pause(False)
            elif kind == "reset_scene":
                session.reset_scene()
    except WebSocketDisconnect:
        pass
    finally:
        send_task.cancel()


# ---------- frontend ----------

if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
