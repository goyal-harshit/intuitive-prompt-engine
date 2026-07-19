"""Repository: the only module that touches the database (SQLite via SQLAlchemy)."""

from __future__ import annotations

import json
import time
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import sessionmaker

from backend.gestures.schema import SequenceSegment
from backend.imagegen.base import GeneratedImage
from backend.intent.schema import IntentFrame
from backend.prompting.base import OptimizedPrompt
from backend.scene.schema import SceneGraph
from backend.storage import models as m

# Pipeline timestamps (frames → segments → intents) are time.monotonic(),
# deliberately immune to wall-clock jumps mid-session. The event log stores
# wall-clock so all kinds merge onto one axis for replay; convert at this
# boundary. (Rows written before this conversion existed keep their raw
# monotonic values — tools/replay.py can't line those up across kinds.)
_MONO_TO_WALL = time.time() - time.monotonic()


def _wall(monotonic_ts: float) -> float:
    return monotonic_ts + _MONO_TO_WALL


class Repository:
    def __init__(self, data_dir: Path) -> None:
        self._engine = create_engine(
            f"sqlite:///{data_dir / 'gesturegpt.db'}", connect_args={"check_same_thread": False}
        )
        m.Base.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(self._engine, expire_on_commit=False)

    def _db(self) -> OrmSession:
        return self._session_factory()

    def create_session(self, session_id: str, config_json: str = "{}") -> None:
        with self._db() as db:
            db.add(m.Session(id=session_id, started_at=time.time(), config_json=config_json))
            db.commit()

    def end_session(self, session_id: str) -> None:
        with self._db() as db:
            row = db.get(m.Session, session_id)
            if row:
                row.ended_at = time.time()
                db.commit()

    def add_gesture(self, session_id: str, seg: SequenceSegment) -> None:
        with self._db() as db:
            db.add(
                m.GestureEvent(
                    session_id=session_id,
                    ts=_wall(seg.t_end),
                    primitive=seg.primitive.value,
                    confidence=seg.confidence,
                    params_json=json.dumps(seg.params),
                )
            )
            db.commit()

    def add_intents(self, session_id: str, frames: list[IntentFrame]) -> None:
        if not frames:
            return
        with self._db() as db:
            for f in frames:
                db.add(
                    m.IntentEvent(
                        session_id=session_id,
                        ts=_wall(f.ts),
                        target=f.target,
                        attribute=f.attribute,
                        value=f.value,
                        confidence=f.confidence,
                    )
                )
            db.commit()

    def add_snapshot(self, session_id: str, graph: SceneGraph) -> None:
        with self._db() as db:
            db.add(
                m.SceneSnapshot(
                    session_id=session_id,
                    revision=graph.meta.revision,
                    ts=time.time(),
                    graph_json=graph.model_dump_json(),
                    completeness=graph.meta.completeness,
                )
            )
            db.commit()

    def add_generation(self, session_id: str, img: GeneratedImage, prompt: OptimizedPrompt) -> None:
        with self._db() as db:
            db.add(
                m.Generation(
                    id=img.id,
                    session_id=session_id,
                    backend=img.backend,
                    prompt_positive=prompt.positive,
                    generator=prompt.generator,
                    image_path=img.path,
                    latency_ms=img.latency_ms,
                    created_at=img.created_at,
                )
            )
            db.commit()

    def list_generations(self, session_id: str) -> list[dict]:
        with self._db() as db:
            rows = db.scalars(
                select(m.Generation)
                .where(m.Generation.session_id == session_id)
                .order_by(m.Generation.created_at.desc())
            ).all()
            return [
                {
                    "id": r.id,
                    "backend": r.backend,
                    "prompt": r.prompt_positive,
                    "latency_ms": r.latency_ms,
                    "created_at": r.created_at,
                }
                for r in rows
            ]

    def image_path(self, image_id: str) -> str | None:
        with self._db() as db:
            row = db.get(m.Generation, image_id)
            return row.image_path if row else None

    # ---------- read side for tools/replay.py ----------

    def list_sessions(self) -> list[dict]:
        """All recorded sessions, newest first, with per-kind event counts."""
        with self._db() as db:
            sessions = db.scalars(select(m.Session).order_by(m.Session.started_at.desc())).all()
            counts: dict[str, dict[str, int]] = {}
            for model, kind in (
                (m.GestureEvent, "gestures"),
                (m.IntentEvent, "intents"),
                (m.SceneSnapshot, "snapshots"),
                (m.Generation, "generations"),
            ):
                for sid, n in db.execute(
                    select(model.session_id, func.count()).group_by(model.session_id)
                ):
                    counts.setdefault(sid, {})[kind] = n
            return [
                {
                    "id": s.id,
                    "started_at": s.started_at,
                    "ended_at": s.ended_at,
                    "gestures": counts.get(s.id, {}).get("gestures", 0),
                    "intents": counts.get(s.id, {}).get("intents", 0),
                    "snapshots": counts.get(s.id, {}).get("snapshots", 0),
                    "generations": counts.get(s.id, {}).get("generations", 0),
                }
                for s in sessions
            ]

    def session_timeline(self, session_id: str) -> list[dict]:
        """Chronologically merged event log for one session.

        Each entry carries a ``kind`` discriminator plus the fields of the
        underlying row — the exact shape tools/replay.py renders.
        """
        with self._db() as db:
            events: list[dict] = []
            for g in db.scalars(
                select(m.GestureEvent).where(m.GestureEvent.session_id == session_id)
            ):
                events.append(
                    {
                        "kind": "gesture",
                        "ts": g.ts,
                        "primitive": g.primitive,
                        "confidence": g.confidence,
                        "params": json.loads(g.params_json),
                    }
                )
            for i in db.scalars(
                select(m.IntentEvent).where(m.IntentEvent.session_id == session_id)
            ):
                events.append(
                    {
                        "kind": "intent",
                        "ts": i.ts,
                        "target": i.target,
                        "attribute": i.attribute,
                        "value": i.value,
                        "confidence": i.confidence,
                    }
                )
            for s in db.scalars(
                select(m.SceneSnapshot).where(m.SceneSnapshot.session_id == session_id)
            ):
                events.append(
                    {
                        "kind": "scene",
                        "ts": s.ts,
                        "revision": s.revision,
                        "completeness": s.completeness,
                        "graph": json.loads(s.graph_json),
                    }
                )
            for r in db.scalars(select(m.Generation).where(m.Generation.session_id == session_id)):
                events.append(
                    {
                        "kind": "generation",
                        "ts": r.created_at,
                        "image_id": r.id,
                        "backend": r.backend,
                        "prompt": r.prompt_positive,
                        "latency_ms": r.latency_ms,
                    }
                )
            events.sort(key=lambda e: e["ts"])
            return events
