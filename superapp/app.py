from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import List
from urllib.parse import quote
from zipfile import ZipFile

from fastapi import File, Form, FastAPI, HTTPException, UploadFile, status
from fastapi.responses import Response, StreamingResponse

from app.models.schemas import (
    ErrorResponse,
    ParsedFileResult,
    error_responses,
)
from app.services.pipeline import parse_pipeline


app = FastAPI(title="PDF Practice", description="A simple PDF practice API")
app.tags = ["Parser"]

SUCCESS_RESPONSES = {
    200: {
        "description": "단일 PDF는 Markdown 첨부로, 여러 PDF는 ZIP 아카이브로 반환됩니다.",
        "content": {
            "text/markdown": {
                "schema": {"type": "string"},
                "example": "# Page 1\n\n문서 본문...",
            },
            "application/zip": {
                "schema": {"type": "string", "format": "binary"},
                "example": "PK...",
            },
        },
    }
}


@app.get("/", tags=["Health"])
def read_root() -> dict[str, str]:
    return {"message": "Hello World"}


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"message": "OK"}


@app.post(
    "/parser/pymupdf",
    tags=["Parser"],
    summary="PyMuPDF 파서 실행",
    description="텍스트와 이미지(옵션)를 추출해 Markdown으로 반환합니다.",
    responses={**SUCCESS_RESPONSES, **error_responses},
    response_model=None,
)
async def parser_pymupdf(
    files: List[UploadFile] = File(..., description="변환할 PDF 파일 목록"),
    image: bool = Form(
        True,
        description="이미지를 base64로 포함할지 여부",
        example=True,
    ),
) -> StreamingResponse | Response:
    parser_options = {"extract_images": image}
    result = await parse_pipeline(files, pn="pymupdf", parser_options=parser_options)
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=result.status_code, detail=result.message)
    return _as_download_response(result.results, archive_label="pymupdf_results")


@app.post(
    "/parser/pdfplumber",
    tags=["Parser"],
    summary="pdfplumber 파서 실행",
    description="텍스트 + 표 + (선택) 이미지까지 Markdown으로 변환합니다.",
    responses={**SUCCESS_RESPONSES, **error_responses},
    response_model=None,
)
async def parser_pdfplumber(
    files: List[UploadFile] = File(..., description="변환할 PDF 파일 목록"),
    image: bool = Form(
        True,
        description="페이지 내 이미지를 base64로 포함할지 여부",
        example=True,
    ),
) -> StreamingResponse | Response:
    parser_options = {"extract_images": image}
    result = await parse_pipeline(
        files, pn="pdfplumber", parser_options=parser_options
    )
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=result.status_code, detail=result.message)
    return _as_download_response(result.results, archive_label="pdfplumber_results")


@app.post(
    "/parser/docling",
    tags=["Parser"],
    summary="Docling 파서 실행",
    description="Docling 엔진으로 PDF를 Markdown 또는 HTML로 변환합니다.",
    responses={**SUCCESS_RESPONSES, **error_responses},
    response_model=None,
)
async def parser_docling(
    files: List[UploadFile] = File(..., description="변환할 PDF 파일 목록"),
    image: bool = Form(
        True,
        description="이미지를 포함할지 여부",
        example=True,
    ),
    output_format: str = Form(
        "md",
        description="출력 형식 (md|html)",
        example="md",
    ),
) -> StreamingResponse | Response:
    parser_options = {
        "include_images": image,
        "output_format": output_format,
    }
    result = await parse_pipeline(files, pn="docling", parser_options=parser_options)
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=result.status_code, detail=result.message)
    return _as_download_response(result.results, archive_label="docling_results")


@app.post(
    "/parser/promtree",
    tags=["Parser"],
    summary="PromTree 파서 실행",
    description="구조 분석 + unpivot 옵션을 지원하는 커스텀 파서입니다.",
    responses={**SUCCESS_RESPONSES, **error_responses},
    response_model=None,
)
async def upload_and_parse_pdfs(
    files: List[UploadFile] = File(..., description="변환할 PDF 파일 목록"),
    image: bool = Form(
        True,
        description="이미지 플레이스홀더를 포함할지 여부",
        example=True,
    ),
    unpivot: bool = Form(
        True,
        description="표를 unpivot 형식(JSON 문자열)으로 반환할지 여부",
        example=True,
    ),
) -> StreamingResponse | Response:
    parser_options = {
        "extract_images": image,
        "unpivot_tables": unpivot,
    }
    result = await parse_pipeline(files, pn="promtree", parser_options=parser_options)
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=result.status_code, detail=result.message)
    return _as_download_response(result.results, archive_label="promtree_results")


def _as_download_response(
    results: List[ParsedFileResult], archive_label: str
) -> StreamingResponse | Response:
    """Single file → markdown attachment, multiple → zip archive."""
    payloads = _build_file_payloads(results)
    if not payloads:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="생성된 파일이 없습니다.",
        )
    if len(payloads) == 1:
        filename, content = payloads[0]
        headers = {"Content-Disposition": _build_disposition_header(filename)}
        return Response(content=content, media_type="text/markdown", headers=headers)

    buffer = BytesIO()
    with ZipFile(buffer, "w") as zipf:
        for filename, content in payloads:
            zipf.writestr(filename, content)
    buffer.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="{archive_label}.zip"'}
    return StreamingResponse(buffer, media_type="application/zip", headers=headers)


def _build_file_payloads(results: List[ParsedFileResult]) -> List[tuple[str, str]]:
    payloads: List[tuple[str, str]] = []
    for item in results:
        safe_name = _to_md_filename(item.filename)
        payloads.append((safe_name, item.content or ""))
    return payloads


def _to_md_filename(filename: str | None) -> str:
    stem = Path(filename or "output").stem or "output"
    return f"{stem}.md"


def _build_disposition_header(filename: str) -> str:
    """
    Build an RFC 5987 compatible Content-Disposition header value that supports UTF-8 filenames.
    """
    fallback = filename.encode("ascii", errors="ignore").decode("ascii") or "output.md"
    quoted = quote(filename)
    return f'attachment; filename="{fallback}"; filename*=UTF-8\'\'{quoted}'


