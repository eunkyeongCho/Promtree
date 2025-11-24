from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from beanie import Document
from pydantic import Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class KnowledgeCollection(Document):
    collection_id: str = Field(default_factory=lambda: str(uuid4()), unique=True)
    name: str
    description: str = ""
    user_id: str
    type: Literal["msds", "tds"]
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "collections"
        indexes = [
            "collection_id",
            "user_id",
            "name",
        ]


class CollectionDocument(Document):
    document_id: str = Field(default_factory=lambda: str(uuid4()), unique=True)
    collection_id: str
    filename: str
    size: str
    status: Literal["processing", "failure", "success"] = "processing"
    uploaded_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "docs"
        indexes = [
            "document_id",
            "collection_id",
        ]

