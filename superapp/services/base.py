"""공통 파서 서비스 로직"""
from __future__ import annotations

from typing import List, Optional, Tuple

from fastapi import UploadFile

from app.models.schemas import ErrorResponse, error_response

PDF_MIME_KEYWORD = "pdf"


def files_exist(files: List[UploadFile]) -> Optional[ErrorResponse]:
    """업로드된 파일 리스트가 비어 있으면 에러를 반환합니다."""
    if not files:
        return error_response("업로드할 파일을 선택해 주세요.", 400)
    return None


def is_it_pdf(upload: UploadFile) -> Optional[ErrorResponse]:
    """단일 업로드가 PDF인지 검사합니다."""
    if not _is_pdf(upload):
        return error_response(
            f"{upload.filename or '파일'}은(는) PDF 파일이 아닙니다.", 400
        )
    return None


async def reading_error_check(
    upload: UploadFile,
) -> Tuple[Optional[bytes], Optional[ErrorResponse]]:
    """업로드 내용을 읽고, 오류 시 ErrorResponse를 반환합니다."""
    try:
        content = await upload.read()
    except Exception as exc:  # pragma: no cover - I/O 안전장치
        return None, error_response(
            f"{upload.filename or '파일'}을 읽는 중 오류가 발생했습니다: {exc}", 500
        )

    if not content:
        return None, error_response(
            f"{upload.filename or '파일'}의 내용이 비어 있습니다.", 400
        )

    return content, None


def _is_pdf(upload: UploadFile) -> bool:
    """업로드 파일이 PDF인지 확장자/콘텐츠 타입으로 판별합니다."""
    filename = (upload.filename or "").lower()
    content_type = (upload.content_type or "").lower()
    return filename.endswith(".pdf") or PDF_MIME_KEYWORD in content_type
