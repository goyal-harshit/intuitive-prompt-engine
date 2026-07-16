"""Repository: the only module that touches the database (SQLite via SQLAlchemy)."""

from __future__ import annotations

import json
import time
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import sessionmaker

from backend.gestures.schema import SequenceSegment
from backend.imagegen.base import GeneratedImage
from backend.intent.schema import IntentFrame
from backend.prompting.base import OptimizedPrompt
from backend.scene.schema import SceneGraph
from backend.storage import models as m


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
                    ts=seg.t_end,
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
                        ts=f.ts,
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
