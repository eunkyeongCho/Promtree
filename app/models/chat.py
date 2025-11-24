from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from beanie import Document
from pydantic import Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Chat(Document):
    chat_id: str = Field(default_factory=lambda: str(uuid4()), unique=True)
    user_id: str
    title: str = "New Chat"
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "chats"
        indexes = [
            "chat_id",
            "user_id",
        ]

