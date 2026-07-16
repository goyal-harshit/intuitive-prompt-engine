"""SQLAlchemy ORM models — append-only event log enables full session replay."""

from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    started_at: Mapped[float] = mapped_column(Float)
    ended_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    config_json: Mapped[str] = mapped_column(Text, default="{}")


class GestureEvent(Base):
    __tablename__ = "gesture_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    ts: Mapped[float] = mapped_column(Float)
    primitive: Mapped[str] = mapped_column(String)
    confidence: Mapped[float] = mapped_column(Float)
    params_json: Mapped[str] = mapped_column(Text, default="{}")


class IntentEvent(Base):
    __tablename__ = "intent_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    ts: Mapped[float] = mapped_column(Float)
    target: Mapped[str] = mapped_column(String)
    attribute: Mapped[str] = mapped_column(String)
    value: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)


class SceneSnapshot(Base):
    __tablename__ = "scene_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    ts: Mapped[float] = mapped_column(Float)
    graph_json: Mapped[str] = mapped_column(Text)
    completeness: Mapped[float] = mapped_column(Float)


class Generation(Base):
    __tablename__ = "generations"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    backend: Mapped[str] = mapped_column(String)
    prompt_positive: Mapped[str] = mapped_column(Text)
    generator: Mapped[str] = mapped_column(String)
    image_path: Mapped[str] = mapped_column(String)
    latency_ms: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[float] = mapped_column(Float)
