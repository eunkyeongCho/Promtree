"""
Chat routes - Phase 1 implementation
"""
from fastapi import APIRouter, HTTPException, status
from datetime import datetime
from typing import Dict
import uuid

from app.models.schemas import (
    ChatCreate, ChatResponse, ChatListResponse,
    ChatUpdateRequest, APIResponse
)
from app.core.database import get_mongodb_database

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(chat: ChatCreate):
    """Create a new chat"""
    chat_id = f"chat_{uuid.uuid4().hex[:8]}"
    title = chat.title or "새로운 채팅"
    now = datetime.now()

    chat_data = {
        "chatId": chat_id,
        "userId": chat.userId,
        "title": title,
        "createdAt": now,
        "updatedAt": now
    }

    # MongoDB에 저장
    db = get_mongodb_database()
    chats_collection = db["chats"]
    chats_collection.insert_one(chat_data)

    return APIResponse(
        success=True,
        data={
            "chatId": chat_id,
            "title": title,
            "createdAt": now.isoformat()
        }
    )


@router.get("", response_model=APIResponse)
async def get_chats(userId: str):
    """Get all chats for a user"""
    db = get_mongodb_database()
    chats_collection = db["chats"]

    # MongoDB에서 사용자 채팅 목록 조회
    user_chats = []
    for chat in chats_collection.find({"userId": userId}).sort("createdAt", -1):
        user_chats.append({
            "chatId": chat["chatId"],
            "title": chat["title"],
            "createdAt": chat["createdAt"].isoformat(),
            "updatedAt": chat["updatedAt"].isoformat()
        })

    return APIResponse(
        success=True,
        data={"chats": user_chats}
    )


@router.delete("/{chat_id}", response_model=APIResponse)
async def delete_chat(chat_id: str):
    """Delete a chat"""
    db = get_mongodb_database()
    chats_collection = db["chats"]
    messages_collection = db["messages"]

    # 채팅 존재 확인
    chat = chats_collection.find_one({"chatId": chat_id})
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )

    # 채팅방 및 관련 메시지 삭제
    chats_collection.delete_one({"chatId": chat_id})
    messages_collection.delete_many({"chatId": chat_id})

    return APIResponse(success=True)


@router.patch("/{chat_id}", response_model=APIResponse)
async def update_chat(chat_id: str, update: ChatUpdateRequest):
    """Update chat title"""
    db = get_mongodb_database()
    chats_collection = db["chats"]

    # 채팅 존재 확인
    chat = chats_collection.find_one({"chatId": chat_id})
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )

    # 제목 업데이트
    chats_collection.update_one(
        {"chatId": chat_id},
        {"$set": {"title": update.title, "updatedAt": datetime.now()}}
    )

    return APIResponse(success=True)
