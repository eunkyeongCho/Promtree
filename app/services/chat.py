
from __future__ import annotations

from typing import Sequence

import httpx

chat_ai_url = "https://bcb7tjvf0wm6jb-11434.proxy.runpod.net"


class ChatAIServiceError(RuntimeError):
    """채팅 AI 호출 실패"""


async def request_chat_ai(
    question: str,
    history: Sequence[dict[str, str]] | None = None,
) -> tuple[str, list[str]]:
    """
    외부 챗봇 API에 질문을 전달하고 응답을 받아옵니다.

    Args:
        question: 사용자 질문
        history: 직전 대화 기록 (role, contents)

    Returns:
        (answer, sources)
    """

    messages = [
        {"role": item["role"], "content": item["contents"]}
        for item in history or []
    ]
    messages.append({"role": "user", "content": question})

    payload = {
        "model": "gpt-oss:20b",
        "messages": messages,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(f"{chat_ai_url}/api/chat", json=payload)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ChatAIServiceError("챗봇 서비스 호출에 실패했습니다.") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise ChatAIServiceError("챗봇 응답을 파싱할 수 없습니다.") from exc

    message = data.get("message") or {}
    answer = (
        message.get("content")
        or data.get("answer")
        or data.get("response")
        or data.get("message")
    )

    if isinstance(answer, dict):
        answer = answer.get("content")

    if not isinstance(answer, str) or not answer.strip():
        raise ChatAIServiceError("챗봇 서비스가 유효한 답변을 반환하지 않았습니다.")

    sources_raw = data.get("sources") or message.get("sources") or []
    if not isinstance(sources_raw, list):
        sources_raw = []
    sources = [str(source) for source in sources_raw]

    return answer, sources