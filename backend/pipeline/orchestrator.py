"""Orchestrator: wires vision → gestures → intent → scene → prompt → image.

Owns the vision thread and the async generation loop. All cross-stage
communication goes through the EventBus, so any stage can be observed or
replaced without touching this wiring beyond construction.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid

from backend.core.bus import EventBus, Topics
from backend.core.config import AppConfig
from backend.gestures.draw import DrawModeGate, StrokeBuffer
from backend.gestures.features import FeatureExtractor
from backend.gestures.sequence import PrototypeSegmenter
from backend.gestures.shape import classify_shape
from backend.imagegen.base import ImageGenerator
from backend.imagegen.factory import create_image_generator
from backend.intent.engine import RuleBasedIntentModel
from backend.prompting.base import PromptGenerator
from backend.prompting.factory import create_prompt_generator
from backend.scene.graph import SceneGraphManager
from backend.scene.schema import SceneGraph
from backend.storage.repo import Repository
from backend.vision.capture import OpenCVCamera
from backend.vision.landmarks import MediaPipeExtractor

log = logging.getLogger(__name__)


class PipelineSession:
    def __init__(self, cfg: AppConfig, bus: EventBus, repo: Repository) -> None:
        self.id = f"ses_{uuid.uuid4().hex[:8]}"
        self._cfg = cfg
        self._bus = bus
        self._repo = repo

        self._features = FeatureExtractor(
            window_s=cfg.intent.window_s, smoothing_alpha=cfg.gesture.smoothing_alpha_position
        )
        self._segmenter = PrototypeSegmenter()
        self._intent = RuleBasedIntentModel(cfg.intent)
        self.scene = SceneGraphManager(cfg.scene, cfg.intent.decay_half_life_s)

        self._draw_gate = DrawModeGate(
            cfg.gesture.pinch_enter_threshold,
            cfg.gesture.pinch_exit_threshold,
            cfg.gesture.pinch_enter_hold_s,
        )
        self._stroke = StrokeBuffer(
            cfg.gesture.smoothing_alpha_position,
            cfg.gesture.stroke_min_point_dist,
            cfg.gesture.stroke_max_points,
        )
        self._last_debug_emit = 0.0
        self._extractor: MediaPipeExtractor | None = None

        self._prompter: PromptGenerator | None = None
        self._imagegen: ImageGenerator | None = None

        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop = threading.Event()
        self._paused = False
        self._thread: threading.Thread | None = None
        self._last_snapshot: SceneGraph | None = None
        self._generating = False
        self._last_feature_emit = 0.0
        # Latest camera frame with landmark overlay, JPEG-encoded, for the video feed.
        self.latest_jpeg: bytes | None = None
        self.camera_active = False

    # ---------- lifecycle ----------

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._prompter = await create_prompt_generator(self._cfg.prompting)
        self._imagegen = create_image_generator(self._cfg.imagegen, self._cfg.data_dir / "images")
        self._repo.create_session(self.id)
        self._thread = threading.Thread(target=self._vision_loop, daemon=True, name="vision-loop")
        self._thread.start()
        asyncio.create_task(self._maintenance_loop())
        log.info(
            "session %s started (prompter=%s, imagegen=%s)",
            self.id,
            self._prompter.name,
            self._imagegen.name,
            extra={
                "session_id": self.id,
                "prompter": self._prompter.name,
                "imagegen": self._imagegen.name,
            },
        )

    async def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
        self._repo.add_snapshot(self.id, self.scene.graph)
        self._repo.end_session(self.id)

    def pause(self, paused: bool) -> None:
        self._paused = paused

    def reset_scene(self) -> None:
        self._repo.add_snapshot(self.id, self.scene.graph)
        self.scene.reset()
        self._publish(Topics.SCENE_UPDATE, self.scene.graph.model_dump())

    def clear_draw(self) -> None:
        self._draw_gate.reset()
        self._stroke.reset()
        self._publish(Topics.DRAW_CLEAR, {})

    # ---------- vision thread ----------

    def _vision_loop(self) -> None:
        import cv2

        try:
            camera = OpenCVCamera(self._cfg.camera)
            extractor = MediaPipeExtractor(self._cfg.vision, self._cfg.face_calibration)
        except Exception as exc:  # noqa: BLE001
            self._publish(Topics.ERROR, {"code": "CAMERA_UNAVAILABLE", "message": str(exc)})
            return
        self._extractor = extractor
        self.camera_active = True
        try:
            for ts, frame in camera.frames():
                if self._stop.is_set():
                    break
                lm = extractor.extract(ts, frame)
                overlay = extractor.annotate(frame)
                ok, buf = cv2.imencode(".jpg", overlay, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if ok:
                    self.latest_jpeg = buf.tobytes()
                self._process(lm)
        finally:
            extractor.close()
            camera.close()
            self.camera_active = False
            self.latest_jpeg = None  # signal the video stream to stop

    def _process(self, lm) -> None:  # noqa: ANN001 — LandmarkFrame
        fv = self._features.update(lm)
        if time.monotonic() - self._last_feature_emit > 0.1:  # 10 Hz to UI
            self._last_feature_emit = time.monotonic()
            self._publish(Topics.FEATURES, fv.model_dump())
        if self._paused:
            return

        frames = self._intent.on_features(fv)

        gate = self._draw_gate.update(fv)
        if gate.just_entered:
            self._segmenter.reset()
            self._stroke.reset()

        if gate.drawing:
            pt = self._stroke.add_from_frame(lm)
            if pt is not None:
                self._publish(Topics.DRAW_STROKE, pt.model_dump())
        else:
            seg = self._segmenter.update(fv)
            if seg:
                self._publish(Topics.PRIMITIVE, seg.model_dump())
                self._repo.add_gesture(self.id, seg)
                frames += self._intent.on_segment(seg, fv)

        if gate.just_exited:
            shape = classify_shape(self._stroke.points, self._features.last_shoulder_w)
            self._stroke.reset()
            if shape:
                self._publish(Topics.DRAW_SHAPE, shape.model_dump())
                frames += self._intent.on_drawn_shape(shape)

        self._emit_gesture_debug(fv, gate.drawing)

        if frames:
            self._publish(Topics.INTENT, [f.model_dump() for f in frames])
            self._repo.add_intents(self.id, frames)
            if self._loop:
                asyncio.run_coroutine_threadsafe(self._apply(frames), self._loop)

    def _emit_gesture_debug(self, fv, drawing: bool) -> None:  # noqa: ANN001
        hz = self._cfg.gesture.debug_emit_hz or 1.0
        now = time.monotonic()
        if now - self._last_debug_emit < 1.0 / hz:
            return
        self._last_debug_emit = now
        candidates = self._segmenter.peek(fv)
        self._publish(
            Topics.GESTURE_DEBUG,
            {
                "drawing": drawing,
                "matches": self._intent.explain(fv, candidates),
            },
        )

    # ---------- async side ----------

    async def _apply(self, frames) -> None:  # noqa: ANN001 — list[IntentFrame]
        if self.scene.apply(frames) or self.scene.commit_requested:
            await self._bus.publish(Topics.SCENE_UPDATE, self.scene.graph.model_dump())
            await self._maybe_generate()

    async def _maybe_generate(self) -> None:
        if self._generating or not self.scene.ready_to_generate():
            return
        if self.scene.diff_score(self._last_snapshot) < self._cfg.scene.regen_diff:
            return
        self._generating = True
        snapshot = self.scene.snapshot()
        self._last_snapshot = snapshot
        asyncio.create_task(self._generate(snapshot))

    async def _generate(self, snapshot: SceneGraph) -> None:
        try:
            assert self._prompter and self._imagegen
            prompt = await self._prompter.generate(snapshot)
            await self._bus.publish(Topics.GENERATION_STARTED, prompt.model_dump())
            self._repo.add_snapshot(self.id, snapshot)
            img = await self._imagegen.generate(
                prompt, self._cfg.imagegen.width, self._cfg.imagegen.height
            )
            self._repo.add_generation(self.id, img, prompt)
            self._intent.notify_render(time.monotonic())
            log.info(
                "generation complete",
                extra={"session_id": self.id, "backend": img.backend, "latency_ms": img.latency_ms},
            )
            await self._bus.publish(
                Topics.GENERATION_DONE,
                {
                    "image_id": img.id,
                    "url": f"/api/images/{img.id}",
                    "prompt": prompt.positive,
                    "latency_ms": img.latency_ms,
                    "backend": img.backend,
                },
            )
        except Exception as exc:  # noqa: BLE001 — pipeline survives backend failures
            log.exception(
                "generation failed",
                extra={
                    "session_id": self.id,
                    "backend": self._imagegen.name if self._imagegen else None,
                },
            )
            await self._bus.publish(Topics.ERROR, {"code": "BACKEND_DOWN", "message": str(exc)})
        finally:
            self._generating = False

    async def _maintenance_loop(self) -> None:
        while not self._stop.is_set():
            await asyncio.sleep(1.0)
            self.scene.decay()
            await self._bus.publish(
                Topics.STATUS,
                {
                    "session_id": self.id,
                    "paused": self._paused,
                    "completeness": self.scene.graph.meta.completeness,
                    "revision": self.scene.graph.meta.revision,
                    "generating": self._generating,
                    "face_calibrating": self._extractor.face_calibrating
                    if self._extractor
                    else False,
                    "ambient": self._intent.ambient_snapshot(),
                },
            )
            await self._maybe_generate()  # stability-based trigger

    def force_generate(self) -> None:
        self.scene.commit_requested = True

    def _publish(self, topic: str, payload) -> None:  # noqa: ANN001
        if self._loop:
            self._bus.publish_threadsafe(self._loop, topic, payload)
