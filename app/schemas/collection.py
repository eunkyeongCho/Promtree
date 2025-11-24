from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CollectionCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    type: Literal["msds", "tds"]


class CollectionUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    type: Literal["msds", "tds"] | None = None


class CollectionResponse(BaseModel):
    collection_id: str
    name: str
    description: str
    user_id: str
    type: Literal["msds", "tds"]
    created_at: datetime
    updated_at: datetime


class DocumentResponse(BaseModel):
    document_id: str
    filename: str
    size: str
    uploaded_at: datetime
    status: Literal["processing", "failure", "success"]
    collection_id: str

