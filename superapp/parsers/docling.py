# docling 파서 구현
from __future__ import annotations

import re
from io import BytesIO
from typing import Optional

from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import DocumentStream
from docling.datamodel.document import ConversionStatus
from docling_core.types.doc.document import ImageRefMode

_converter = DocumentConverter()


def parsing(
    content: bytes,
    filename: Optional[str] = None,
    *,
    output_format: str = "md",
    include_images: bool = True,
    **_: object,
) -> str:
    """
    Docling 파서를 사용해 PDF 파일을 파싱하고 Markdown 형식으로 반환합니다.
    """
    stream = DocumentStream(
        name=filename or "uploaded.pdf", stream=BytesIO(content)
    )
    try:
        conv_result = _converter.convert(stream, raises_on_error=False)
    except Exception as exc:
        return f"# {filename or 'document'}\n\nDocling 변환 실패: {exc}"

    if conv_result.status not in (ConversionStatus.SUCCESS, ConversionStatus.PARTIAL_SUCCESS):
        details = "; ".join(err.error_message for err in (conv_result.errors or []))
        return (
            f"# {filename or 'document'}\n\n"
            f"Docling 변환이 완료되지 않았습니다. 상태: {conv_result.status}. {details}"
        )

    if not conv_result.document:
        return f"# {filename or 'document'}\n\nDocling에서 문서를 생성하지 못했습니다."

    doc = conv_result.document
    fmt = (output_format or "md").lower()
    if fmt not in {"md", "markdown", "html"}:
        fmt = "md"
    image_mode = ImageRefMode.EMBEDDED if include_images else ImageRefMode.DISCARD

    if fmt == "html":
        try:
            return doc.export_to_html(image_mode=image_mode)
        except TypeError:
            html = doc.export_to_html()
            if not include_images:
                return _strip_img_tags(html)
            return html

    return doc.export_to_markdown(
        image_mode=image_mode,
        page_break_placeholder="<!-- page break -->",
    )


def _strip_img_tags(html: str) -> str:
    """Fallback: remove img tags when exporter can't skip images."""
    return re.sub(r"<img\b[^>]*>", "", html, flags=re.IGNORECASE)