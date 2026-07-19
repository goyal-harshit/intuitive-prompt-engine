"""FastAPI application: REST + WebSocket + static frontend."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.core.bus import EventBus, Topics
from backend.core.config import get_config
from backend.core.logging import configure_logging
from backend.pipeline.orchestrator import PipelineSession
from backend.storage.repo import Repository

configure_logging()
log = logging.getLogger(__name__)

# Optional shared-secret gate for the REST/WS API. Unset (default) means the
# API is open, matching today's local/dev-only usage; set API_KEY before
# exposing the backend beyond localhost.
API_KEY = os.environ.get("API_KEY") or None

cfg = get_config()
bus = EventBus()
repo = Repository(cfg.data_dir)
sessions: dict[str, PipelineSession] = {}
_last_seen: dict[str, float] = {}
_started_at = time.time()
# Built-frontend location; FRONTEND_DIST overrides for deployments (and tests)
# where the static build lives outside the repo tree.
FRONTEND = Path(
    os.environ.get("FRONTEND_DIST") or Path(__file__).resolve().parents[2] / "frontend" / "dist"
)

APP_VERSION = "0.1.0"


async def _sweep_idle_sessions() -> None:
    """Background TTL sweep: sessions are in-memory and die with the process,
    so a client that never sends DELETE would otherwise leak a camera/thread
    forever. Runs for the app's lifetime; cancelled on shutdown."""
    ttl = cfg.server.session_ttl_s
    while True:
        await asyncio.sleep(60)
        now = time.time()
        stale = [(sid, now - last) for sid, last in _last_seen.items() if now - last > ttl]
        for sid, idle_s in stale:
            session = sessions.pop(sid, None)
            _last_seen.pop(sid, None)
            if session:
                log.info(
                    "session %s idle for >%.0fs, stopping",
                    sid,
                    ttl,
                    extra={"session_id": sid, "idle_s": round(idle_s, 1)},
                )
                await session.stop()


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    sweep_task = asyncio.create_task(_sweep_idle_sessions())
    try:
        yield
    finally:
        sweep_task.cancel()


app = FastAPI(title="GestureGPT", version=APP_VERSION, lifespan=_lifespan)

# Sliding one-minute window of request timestamps per client IP. Guards the
# endpoints that allocate real resources (camera/pipeline threads, image
# generation). In-memory on purpose: sessions themselves are in-memory, so a
# multi-process deployment already needs a fronting proxy — put real rate
# limiting there and leave this as the single-process safety net.
_rate_window: dict[str, deque[float]] = defaultdict(deque)


@app.middleware("http")
async def _rate_limit(request: Request, call_next):  # noqa: ANN001, ANN201
    limit = cfg.server.rate_limit_per_minute
    if limit > 0 and request.method == "POST" and request.url.path.startswith("/api/"):
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = _rate_window[ip]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= limit:
            retry_after = max(1, int(61 - (now - window[0])))
            return JSONResponse(
                {
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": f"limit of {limit} requests/minute exceeded; retry later",
                    }
                },
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )
        window.append(now)
    return await call_next(request)


# Registered after the rate limiter so auth wraps outside it: a request with a
# bad key is rejected with 401 before it can consume rate-limit budget.
@app.middleware("http")
async def _require_api_key(request: Request, call_next):  # noqa: ANN001, ANN201
    if API_KEY and request.url.path.startswith("/api") and request.url.path != "/api/health":
        if request.headers.get("X-API-Key") != API_KEY:
            return JSONResponse(
                {"error": {"code": "UNAUTHORIZED", "message": "invalid or missing X-API-Key"}},
                status_code=401,
            )
    return await call_next(request)


# Registered after the API-key middleware so it wraps outermost: CORS headers
# land on every response, including a 401 from the check above. Otherwise a
# browser reports a CORS failure instead of surfacing the real 401.
app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.server.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _touch(session_id: str) -> None:
    _last_seen[session_id] = time.time()


# ---------- REST ----------


class HealthResponse(BaseModel):
    """Formal health schema — uptime monitors and deploy smoke tests rely on it."""

    status: str
    version: str
    uptime_s: float
    active_sessions: int
    imagegen: str
    prompting: str


@app.get("/api/health")
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=APP_VERSION,
        uptime_s=round(time.time() - _started_at, 1),
        active_sessions=len(sessions),
        imagegen=cfg.imagegen.backend,
        prompting=cfg.prompting.strategy,
    )


@app.post("/api/session")
async def create_session() -> dict:
    session = PipelineSession(cfg, bus, repo)
    await session.start()
    sessions[session.id] = session
    _touch(session.id)
    return {"session_id": session.id}


@app.delete("/api/session/{session_id}")
async def end_session(session_id: str) -> dict:
    session = _get(session_id)
    await session.stop()
    del sessions[session_id]
    _last_seen.pop(session_id, None)
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
    return Response(content=jpeg, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


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
                yield (
                    b"--frame\r\nContent-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n" + jpeg + b"\r\n"
                )
            else:
                # Camera not producing yet (warm-up) or shutting down.
                blank_waits += 1
                if blank_waits > 200 and not session.camera_active:
                    break
            await asyncio.sleep(0.04)  # ~25 fps ceiling

    return StreamingResponse(frames(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/api/images/{image_id}")
async def get_image(image_id: str) -> FileResponse:
    path = repo.image_path(image_id)
    if not path or not Path(path).exists():
        raise HTTPException(404, "image not found")
    return FileResponse(path, media_type="image/png")


@app.get("/api/config")
async def get_app_config() -> dict:
    # data_dir is a host filesystem path — not useful to a client and not
    # something to expose if this backend is reachable beyond localhost.
    return cfg.model_dump(mode="json", exclude={"data_dir"})


def _get(session_id: str) -> PipelineSession:
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(404, "session not found")
    _touch(session_id)
    return session


# ---------- WebSocket ----------

_WS_TOPICS = (
    Topics.FEATURES,
    Topics.PRIMITIVE,
    Topics.INTENT,
    Topics.SCENE_UPDATE,
    Topics.GENERATION_STARTED,
    Topics.GENERATION_DONE,
    Topics.STATUS,
    Topics.ERROR,
    Topics.DRAW_STROKE,
    Topics.DRAW_SHAPE,
    Topics.DRAW_CLEAR,
    Topics.GESTURE_DEBUG,
)


@app.websocket("/ws/{session_id}")
async def ws_endpoint(ws: WebSocket, session_id: str) -> None:
    await ws.accept()
    # Browsers can't set custom headers on a WebSocket handshake, so the key
    # travels as a query param here instead of X-API-Key.
    if API_KEY and ws.query_params.get("api_key") != API_KEY:
        await ws.close(code=4401)
        return
    session = sessions.get(session_id)
    if not session:
        await ws.close(code=4004)
        return
    _touch(session_id)

    queue: asyncio.Queue = asyncio.Queue(maxsize=200)

    def make_handler(topic: str):
        async def handler(payload) -> None:  # noqa: ANN001
            if not queue.full():
                queue.put_nowait({"type": topic, "data": payload})

        return handler

    handlers = {topic: make_handler(topic) for topic in _WS_TOPICS}
    for topic, handler in handlers.items():
        bus.subscribe(topic, handler)

    async def sender() -> None:
        while True:
            await ws.send_json(await queue.get())

    send_task = asyncio.create_task(sender())
    try:
        while True:
            msg = await ws.receive_json()
            kind = msg.get("type")
            _touch(session_id)
            if kind == "pause":
                session.pause(True)
            elif kind == "resume":
                session.pause(False)
            elif kind == "reset_scene":
                session.reset_scene()
            elif kind == "draw_clear":
                session.clear_draw()
    except WebSocketDisconnect:
        pass
    finally:
        send_task.cancel()
        for topic, handler in handlers.items():
            bus.unsubscribe(topic, handler)


# ---------- frontend ----------

if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
