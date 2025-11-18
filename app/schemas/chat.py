from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChatCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=100)


class ChatRenameRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)


class MessageCreateRequest(BaseModel):
    contents: str = Field(..., min_length=1)


class ChatSummaryResponse(BaseModel):
    chat_id: str
    title: str
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    message_id: str
    chat_id: str
    role: Literal["user", "chatbot"]
    contents: str
    timestamp: datetime
    sources: list[str]


class ChatHistoryResponse(BaseModel):
    chat: ChatSummaryResponse
    messages: list[MessageResponse]


class MessageSendResponse(BaseModel):
    chat_id: str
    user_message: MessageResponse
    bot_message: MessageResponse

