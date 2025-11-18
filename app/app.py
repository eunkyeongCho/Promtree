from fastapi import FastAPI
from starlette import status
from contextlib import asynccontextmanager
from app.routers.users import user_router
from app.routers.chats import chat_router
from app.routers.collections import collection_router
from app.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 데이터베이스 초기화
    await init_db()
    yield
    # 종료 시 정리 작업 (필요한 경우)


app = FastAPI(
    title="PROMTREE",
    summary="물성 전용 RAG",
    version="0.0.1",
    lifespan=lifespan
)

@app.get("/", status_code=status.HTTP_200_OK)
async def health_check():
    return {"success": True}


@app.get("/help")
async def help():
    return {"message": [
        "사용 가능한 api의 prefix는 다음과 같습니다.",
        "/user",
        "/chat",
        "/collection"
    ]}


app.include_router(user_router, prefix="/users", tags=["User"])
app.include_router(chat_router, prefix="/chats", tags=["Chat"])
app.include_router(collection_router, prefix="/collections", tags=["Collection"])