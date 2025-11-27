"""공통 파이프라인 서비스"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from fastapi import UploadFile

from app.models.schemas import ErrorResponse, ParsedFileResult, ParsedFilesResponse, error_response
from app.parsers import docling, pdfplumber, promtree, pymupdf
from app.services.base import (
    files_exist,
    is_it_pdf,
    reading_error_check,
)


PARSERS = {
    "pdfplumber": pdfplumber,
    "pymupdf": pymupdf,
    "docling": docling,
    "promtree": promtree,
}


async def parse_pipeline(
    files: List[UploadFile],
    pn: str,
    parser_options: Optional[Dict[str, Any]] = None,
) -> Union[ParsedFilesResponse, ErrorResponse]:
    """
    받은 파일들을 유효성 검사 후, 지정된 파서로 파싱하고 결과를 반환합니다.
    
    Args:
        files: 업로드된 파일 리스트
        pn: 파서 이름 (예: "pdfplumber", "pymupdf", "docling", "promtree")
    
    Returns:
        ParsedFilesResponse 또는 ErrorResponse
    """
    error = files_exist(files)
    if error:
        return error

    results = []
    
    for upload in files:
        error = is_it_pdf(upload)
        if error:
            return error

        content, read_error = await reading_error_check(upload)
        if read_error:
            return read_error

        result = parsing_w_parser(pn, content, upload.filename, parser_options)
        if isinstance(result, ErrorResponse):
            return result
        
        results.append(result)

    return ParsedFilesResponse(
        success=True,
        message=f"{pn} 파서로 {len(results)}개 파일을 처리했습니다.",
        results=results,
    )


def parsing_w_parser(
    pn: str,
    content: bytes,
    filename: Optional[str] = None,
    parser_options: Optional[Dict[str, Any]] = None,
) -> Union[ParsedFileResult, ErrorResponse]:
    """
    파서 이름에 따라 해당 파서 모듈의 parsing 함수를 호출합니다.
    
    Args:
        pn: 파서 이름 (예: "pdfplumber", "pymupdf", "docling", "promtree")
        content: PDF 파일의 바이트 내용
        filename: 원본 파일명 (선택사항)
    
    Returns:
        ParsedFileResult 또는 ErrorResponse
    """
    try:
        # 딕셔너리 lookup으로 파서 모듈 가져오기 (O(1) 성능)
        parser_module = PARSERS.get(pn)
        if parser_module is None:
            supported = ", ".join(PARSERS.keys())
            return error_response(
                f"지원하지 않는 파서입니다: '{pn}'. 지원 파서: {supported}",
                400,
            )
        
        # 파서의 parsing 함수 호출
        options = parser_options or {}
        md_content = parser_module.parsing(content, filename, **options)
        
        return ParsedFileResult(
            filename=filename or "uploaded.pdf",
            saved_path=None,
            content=md_content,
        )
        
    except Exception as e:
        return error_response(
            f"파싱 중 오류가 발생했습니다: {e}",
            500,
        )