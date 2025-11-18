from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.chat import Chat
from app.models.message import Message
from app.models.user import User
from app.schemas.chat import (
    ChatCreateRequest,
    ChatHistoryResponse,
    ChatRenameRequest,
    ChatSummaryResponse,
    MessageCreateRequest,
    MessageResponse,
    MessageSendResponse,
)
from app.services.chat import ChatAIServiceError, request_chat_ai
from app.utils.auth import get_current_user_email

chat_router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _get_user(email: str) -> User:
    user = await User.find_one(User.email == email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다.",
        )
    return user


async def _get_chat_or_404(chat_id: str, user_id: str) -> Chat:
    chat = await Chat.find_one(Chat.chat_id == chat_id, Chat.user_id == user_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="채팅을 찾을 수 없습니다.",
        )
    return chat


def _to_chat_summary(chat: Chat) -> ChatSummaryResponse:
    return ChatSummaryResponse(
        chat_id=chat.chat_id,
        title=chat.title,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
    )


def _to_message_response(message: Message) -> MessageResponse:
    return MessageResponse(
        message_id=message.message_id,
        chat_id=message.chat_id,
        role=message.role,
        contents=message.contents,
        timestamp=message.timestamp,
        sources=message.sources,
    )


@chat_router.get("/help")
async def help():
    return {
        "message": [
            "POST /chats - 새 채팅 생성",
            "GET /chats - 내 채팅 목록",
            "PATCH /chats/{chat_id} - 채팅 제목 수정",
            "DELETE /chats/{chat_id} - 채팅 삭제",
            "GET /chats/{chat_id} - 채팅 메시지 조회",
            "POST /chats/{chat_id} - 챗봇과 대화",
        ]
    }


@chat_router.get("", response_model=list[ChatSummaryResponse])
async def chat_list(current_user_email: str = Depends(get_current_user_email)):
    user = await _get_user(current_user_email)
    chats = (
        await Chat.find(Chat.user_id == str(user.id))
        .sort("-updated_at")
        .to_list()
    )
    return [_to_chat_summary(chat) for chat in chats]


@chat_router.post("", response_model=ChatSummaryResponse, status_code=status.HTTP_201_CREATED)
async def chat_add(
    payload: ChatCreateRequest,
    current_user_email: str = Depends(get_current_user_email),
):
    user = await _get_user(current_user_email)
    now = _utcnow()
    chat = Chat(
        user_id=str(user.id),
        title=payload.title or "New Chat",
        created_at=now,
        updated_at=now,
    )
    await chat.insert()
    return _to_chat_summary(chat)


@chat_router.patch("/{chat_id}", response_model=ChatSummaryResponse)
async def chat_title_patch(
    chat_id: str,
    payload: ChatRenameRequest,
    current_user_email: str = Depends(get_current_user_email),
):
    user = await _get_user(current_user_email)
    chat = await _get_chat_or_404(chat_id, str(user.id))
    chat.title = payload.title
    chat.updated_at = _utcnow()
    await chat.save()
    return _to_chat_summary(chat)


@chat_router.delete("/{chat_id}")
async def chat_delete(
    chat_id: str,
    current_user_email: str = Depends(get_current_user_email),
):
    user = await _get_user(current_user_email)
    chat = await _get_chat_or_404(chat_id, str(user.id))
    await Message.find(Message.chat_id == chat.chat_id).delete()
    await chat.delete()
    return {"success": True}


@chat_router.get("/{chat_id}", response_model=ChatHistoryResponse)
async def message_history(
    chat_id: str,
    current_user_email: str = Depends(get_current_user_email),
):
    user = await _get_user(current_user_email)
    chat = await _get_chat_or_404(chat_id, str(user.id))
    messages = (
        await Message.find(Message.chat_id == chat.chat_id)
        .sort("timestamp")
        .to_list()
    )
    return ChatHistoryResponse(
        chat=_to_chat_summary(chat),
        messages=[_to_message_response(msg) for msg in messages],
    )


@chat_router.post("/{chat_id}", response_model=MessageSendResponse)
async def message_send(
    chat_id: str,
    payload: MessageCreateRequest,
    current_user_email: str = Depends(get_current_user_email),
):
    user = await _get_user(current_user_email)
    chat = await _get_chat_or_404(chat_id, str(user.id))

    user_message = Message(
        chat_id=chat.chat_id,
        role="user",
        contents=payload.contents,
    )
    await user_message.insert()

    recent_messages = (
        await Message.find(Message.chat_id == chat.chat_id)
        .sort("-timestamp")
        .limit(20)
        .to_list()
    )
    history = [
        {"role": msg.role, "contents": msg.contents}
        for msg in reversed(recent_messages)
    ]

    try:
        answer, sources = await request_chat_ai(payload.contents, history=history)
    except ChatAIServiceError as exc:
        await user_message.delete()  # rollback user message if AI fails
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    bot_message = Message(
        chat_id=chat.chat_id,
        role="chatbot",
        contents=answer,
        sources=sources,
    )
    await bot_message.insert()

    chat.updated_at = _utcnow()
    await chat.save()

    return MessageSendResponse(
        chat_id=chat.chat_id,
        user_message=_to_message_response(user_message),
        bot_message=_to_message_response(bot_message),
    )
