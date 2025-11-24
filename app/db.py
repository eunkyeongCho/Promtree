import pymongo
from pydantic import BaseModel
from beanie import Document, init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from app.models.user import User
from app.models.chat import Chat
from app.models.message import Message
from app.models.collection import KnowledgeCollection, CollectionDocument
from dotenv import load_dotenv
import os

load_dotenv()

mongo_url = (
    f"mongodb://{os.getenv('MONGO_INITDB_ROOT_USERNAME')}:"
    f"{os.getenv('MONGO_INITDB_ROOT_PASSWORD')}@"
    f"{os.getenv('MONGO_HOST')}:{os.getenv('MONGO_PORT')}"
)

async def init_db():
    """데이터베이스 초기화"""
    # MongoDB 연결 (실제 환경에서는 환경변수로 관리)
    client = AsyncIOMotorClient(mongo_url)

    # Beanie 초기화
    await init_beanie(
        database=client.promtree,
        document_models=[User, Chat, Message, KnowledgeCollection, CollectionDocument]
    )