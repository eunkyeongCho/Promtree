"""
Pydantic models for API requests/responses.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """기본 성공 응답 스키마"""

    success: bool = Field(..., description="요청 성공 여부")
    message: str = Field(..., description="사용자에게 전달할 메시지")


class ParsedFileResult(BaseModel):
    """파일별 처리 결과"""

    filename: str = Field(..., description="업로드된 원본 파일명")
    saved_path: Optional[str] = Field(
        default=None, description="(미사용) 저장 경로. 즉시 응답 시 None"
    )
    content: Optional[str] = Field(
        default=None, description="응답으로 내려줄 Markdown 본문"
    )


class ParsedFilesResponse(BaseResponse):
    """여러 파일 처리 시 사용"""

    results: List[ParsedFileResult] = Field(
        default_factory=list, description="파일별 처리 결과"
    )


class ErrorResponse(BaseResponse):
    """에러 응답 스키마"""

    success: Literal[False] = Field(default=False, description="항상 False")
    status_code: int = Field(..., description="HTTP 상태 코드")


def error_response(detail: str, status_code: int) -> ErrorResponse:
    return ErrorResponse(success=False, message=detail, status_code=status_code)


error_responses = {
    400: {"model": ErrorResponse, "description": "Bad Request"},
    404: {"model": ErrorResponse, "description": "Not Found"},
    500: {"model": ErrorResponse, "description": "Internal Server Error"},
}
