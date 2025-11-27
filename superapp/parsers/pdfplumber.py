"""pdfplumber 기반 파싱 로직"""
from __future__ import annotations

from io import BytesIO
from typing import Optional
import base64

import pdfplumber


def parsing(
    content: bytes,
    filename: Optional[str] = None,
    *,
    extract_images: bool = True,
    **_: object,
) -> str:
    """
    pdfplumber를 사용해 텍스트, 표, 이미지까지 Markdown으로 변환합니다.
    """
    markdown_parts: list[str] = []

    with pdfplumber.open(BytesIO(content)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            markdown_parts.append(f"# Page {page_num}\n")

            text = page.extract_text()
            if text and text.strip():
                markdown_parts.append(text.strip())
                markdown_parts.append("")

            try:
                tables = page.extract_tables()
                if tables:
                    for table_index, table in enumerate(tables, start=1):
                        markdown_parts.append(f"**Table {table_index}:**")
                        markdown_parts.append("")
                        if table and len(table) > 0:
                            header = table[0]
                            markdown_parts.append(
                                "| " + " | ".join(str(cell) if cell else "" for cell in header) + " |"
                            )
                            markdown_parts.append(
                                "|" + "|".join("---" for _ in header) + "|"
                            )
                            for row in table[1:]:
                                markdown_parts.append(
                                    "| " + " | ".join(str(cell) if cell else "" for cell in row) + " |"
                                )
                            markdown_parts.append("")
            except Exception:
                pass

            if extract_images:
                try:
                    images = page.images
                    for img_index, img in enumerate(images):
                        try:
                            x0, y0, x1, y1 = (
                                img["x0"],
                                img["top"],
                                img["x1"],
                                img["bottom"],
                            )
                            page_img = page.to_image(resolution=150)
                            cropped = page_img.original.crop((x0, y0, x1, y1))

                            img_buffer = BytesIO()
                            cropped.save(img_buffer, format="PNG")
                            img_bytes = img_buffer.getvalue()

                            image_base64 = base64.b64encode(img_bytes).decode("utf-8")
                            markdown_parts.append(
                                f"![image_{page_num}_{img_index}](data:image/png;base64,{image_base64})"
                            )
                            markdown_parts.append("")
                        except Exception as exc:
                            markdown_parts.append(f"[이미지 추출 실패: {exc}]")
                            markdown_parts.append("")
                except Exception:
                    pass

            markdown_parts.append("---")
            markdown_parts.append("")

    if not markdown_parts:
        return f"# {filename or 'document'}\n\n(본문을 추출하지 못했습니다.)"

    return "\n".join(markdown_parts).strip()