# pymupdf 파서 구현
from __future__ import annotations

import base64
from typing import Optional

import fitz


def parsing(
    content: bytes,
    filename: Optional[str] = None,
    *,
    extract_images: bool = True,
    **_: object,
) -> str:
    """
    PyMuPDF를 사용해 PDF 내용을 Markdown으로 변환합니다.

    Args:
        content: 업로드된 PDF의 raw bytes.
        filename: 원본 파일명 (미제공 시 fallback).
    """
    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        return f"# {filename or 'document'}\n\nPDF를 여는 중 오류가 발생했습니다: {exc}"

    sections: list[str] = []
    with doc:
        for page_num, page in enumerate(doc, start=1):
            lines: list[str] = [f"# Page {page_num}", ""]

            text = (page.get_text("text") or "").strip()
            if text:
                lines.append(text)
                lines.append("")

            if extract_images:
                images = page.get_images(full=True)
                for img_idx, img in enumerate(images):
                    xref = img[0]
                    try:
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image.get("ext", "png")
                        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
                        lines.append(
                            f"![image_{page_num}_{img_idx}]"
                            f"(data:image/{image_ext};base64,{image_b64})"
                        )
                        lines.append("")
                    except Exception as exc:
                        lines.append(f"[이미지 추출 실패: {exc}]")
                        lines.append("")

            lines.append("---")
            sections.append("\n".join(lines).strip())

    markdown = "\n\n".join(section for section in sections if section).strip()
    if markdown:
        return markdown
    return f"# {filename or 'document'}\n\n(본문을 추출하지 못했습니다.)"