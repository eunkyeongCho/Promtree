"""
Pydantic models for API requests/responses
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# ========== Common ==========
class APIResponse(BaseModel):
    """Standard API response wrapper"""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


# ========== Chat Models ==========
class ChatCreate(BaseModel):
    """Create new chat request"""
    userId: str
    title: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response"""
    chatId: str
    title: str
    createdAt: datetime
    updatedAt: Optional[datetime] = None


class ChatListResponse(BaseModel):
    """Chat list response"""
    chats: List[ChatResponse]


class ChatUpdateRequest(BaseModel):
    """Update chat title request"""
    title: str


# ========== Message Models ==========
class MessageSendRequest(BaseModel):
    """Send message request"""
    message: str
    collectionIds: Optional[List[str]] = None
    useWebSearch: bool = False


class SourceDocument(BaseModel):
    """Source document reference"""
    title: str
    url: Optional[str] = None
    snippet: str


class MessageResponse(BaseModel):
    """Message response"""
    messageId: str
    response: str
    sources: Optional[List[SourceDocument]] = None
    timestamp: datetime


class ChatMessage(BaseModel):
    """Chat message"""
    messageId: str
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    sources: Optional[List[SourceDocument]] = None


class MessageHistoryResponse(BaseModel):
    """Message history response"""
    messages: List[ChatMessage]


# ========== Collection Models ==========
class CollectionCreate(BaseModel):
    """Create collection request"""
    name: str
    description: Optional[str] = None
    userId: str


class CollectionResponse(BaseModel):
    """Collection response"""
    collectionId: str
    name: str
    description: Optional[str] = None
    documentCount: int = 0
    createdAt: datetime
    updatedAt: Optional[datetime] = None


class CollectionListResponse(BaseModel):
    """Collection list response"""
    collections: List[CollectionResponse]


# ========== Document Models ==========
class DocumentUploadResponse(BaseModel):
    """Document upload response"""
    documentId: str
    filename: str
    size: int
    uploadedAt: datetime
    status: str  # "processing", "completed", "failed"


class DocumentListResponse(BaseModel):
    """Document list response"""
    uploadedCount: int
    documents: List[DocumentUploadResponse]


# ========== User Models ==========
class UserSettings(BaseModel):
    """User settings"""
    theme: str = "dark"
    language: str = "ko"


class UserResponse(BaseModel):
    """User response"""
    userId: str
    username: str
    email: str
    settings: UserSettings


class UserSettingsUpdate(BaseModel):
    """User settings update request"""
    theme: Optional[str] = None
    language: Optional[str] = None
