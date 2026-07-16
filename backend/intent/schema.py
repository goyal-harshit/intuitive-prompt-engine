"""Runtime models for the intent layer."""

from __future__ import annotations

from pydantic import BaseModel


class IntentFrame(BaseModel):
    """A semantic hypothesis about the user's creative intent — never a command."""

    id: str
    ts: float
    target: str  # "global" | object id | "new_object"
    category: str | None = None  # for new_object targets
    attribute: str
    value: str
    confidence: float
    evidence: list[str] = []  # segment ids
    modifiers: list[str] = []  # context modifiers applied (repetition, post_render, ...)
