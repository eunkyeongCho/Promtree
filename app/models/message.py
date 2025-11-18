from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from beanie import Document
from pydantic import Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Message(Document):
    message_id: str = Field(default_factory=lambda: str(uuid4()), unique=True)
    chat_id: str
    role: Literal["user", "chatbot"]
    contents: str
    timestamp: datetime = Field(default_factory=_utcnow)
    sources: list[str] = Field(default_factory=list)

    class Settings:
        name = "messages"
        indexes = [
            "message_id",
            "chat_id",
        ]

