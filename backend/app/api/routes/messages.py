"""
Message routes - Phase 1 implementation with RAG integration
"""
from fastapi import APIRouter, HTTPException, status
from datetime import datetime
from typing import Dict, List
import uuid

from app.models.schemas import (
    MessageSendRequest, MessageResponse, MessageHistoryResponse,
    ChatMessage, APIResponse
)
from app.services.rag_service import rag_service
from app.core.database import get_mongodb_database

router = APIRouter(tags=["messages"])


@router.post("/chats/{chat_id}/messages", response_model=APIResponse)
async def send_message(chat_id: str, request: MessageSendRequest):
    """Send a message and get RAG response"""

    db = get_mongodb_database()
    messages_collection = db["messages"]

    # Save user message
    user_msg_id = f"msg_{uuid.uuid4().hex[:8]}"
    user_message = {
        "messageId": user_msg_id,
        "chatId": chat_id,
        "role": "user",
        "content": request.message,
        "timestamp": datetime.now()
    }
    messages_collection.insert_one(user_message)

    # Query RAG system
    try:
        print(f"📨 Calling RAG service for chat {chat_id}, message: {request.message}")
        rag_result = await rag_service.query(
            question=request.message,
            collection_ids=request.collectionIds
        )
        print(f"✅ RAG result received: {rag_result['response'][:100]}...")

        # Save assistant message
        assistant_msg_id = f"msg_{uuid.uuid4().hex[:8]}"
        assistant_message = {
            "messageId": assistant_msg_id,
            "chatId": chat_id,
            "role": "assistant",
            "content": rag_result["response"],
            "sources": rag_result["sources"],
            "timestamp": datetime.now()
        }
        messages_collection.insert_one(assistant_message)

        return APIResponse(
            success=True,
            data={
                "messageId": assistant_msg_id,
                "response": rag_result["response"],
                "sources": rag_result["sources"],
                "timestamp": assistant_message["timestamp"].isoformat(),
                "llm_info": rag_result.get("llm_info", {})
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG query failed: {str(e)}"
        )


@router.get("/chats/{chat_id}/messages", response_model=APIResponse)
async def get_messages(chat_id: str):
    """Get chat message history"""
    db = get_mongodb_database()
    messages_collection = db["messages"]

    # MongoDB에서 채팅 메시지 조회 (시간순 정렬)
    messages = []
    for msg in messages_collection.find({"chatId": chat_id}).sort("timestamp", 1):
        messages.append({
            "messageId": msg["messageId"],
            "role": msg["role"],
            "content": msg["content"],
            "timestamp": msg["timestamp"].isoformat(),
            "sources": msg.get("sources")
        })

    return APIResponse(
        success=True,
        data={"messages": messages}
    )
