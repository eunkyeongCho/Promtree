
from __future__ import annotations

from typing import Sequence
import os

import httpx
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()


class ChatAIServiceError(RuntimeError):
    """채팅 AI 호출 실패"""


async def request_chat_ai(
    question: str,
    history: Sequence[dict[str, str]] | None = None,
) -> str:
    """
    외부 챗봇 API에 질문을 전달하고 응답을 받아옵니다.
    RAG 검색 없이 대화 기록만으로 답변을 생성합니다.

    Args:
        question: 사용자 질문
        history: 직전 대화 기록 (role, contents)

    Returns:
        answer: 챗봇 응답 문자열
    """
    upstage_key = os.getenv("UPSTAGE_API_KEY")
    if not upstage_key:
        raise ChatAIServiceError("UPSTAGE_API_KEY가 설정되지 않았습니다.")

    # 이전 대화 맥락을 messages 형식으로 변환
    messages = []
    
    if history:
        for msg in history:
            role = msg.get("role", "user")
            contents = msg.get("contents", "")
            # role이 "chatbot"이면 "assistant"로 변환
            if role == "chatbot":
                role = "assistant"
            elif role not in ["user", "assistant", "system"]:
                role = "user"
            messages.append({
                "role": role,
                "content": contents
            })
    
    # 현재 질문 추가
    messages.append({"role": "user", "content": question})

    try:
        # Upstage API 클라이언트 초기화
        client = AsyncOpenAI(
            api_key=upstage_key,
            base_url="https://api.upstage.ai/v1",
            http_client=httpx.AsyncClient(timeout=30)
        )
        
        # 답변 요청
        response = await client.chat.completions.create(
            model="solar-pro",
            messages=messages,
            temperature=0.7,
            stream=False
        )
        
        answer = response.choices[0].message.content
        
        if not isinstance(answer, str) or not answer.strip():
            raise ChatAIServiceError("챗봇 서비스가 유효한 답변을 반환하지 않았습니다.")
        
        # 응답 맨 처음에 안내 메시지 추가
        notice_message = "해당 응답은 지식 베이스 속 문서 검색 기반의 응답이 아닌 llm 자체의 응답입니다. rag 검색 기능을 켜주십시오.\n\n"
        answer = notice_message + answer
        
        return answer
        
    except Exception as exc:
        raise ChatAIServiceError(f"챗봇 서비스 호출에 실패했습니다: {str(exc)}") from exc