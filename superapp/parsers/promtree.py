# promtree 파서 구현
from __future__ import annotations

from io import BytesIO
from typing import Optional

from docling_core.types.doc import TextItem, TableItem, PictureItem, SectionHeaderItem
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat, DocumentStream
from docling.datamodel.document import ConversionStatus

from app.utils import unpivot
import base64


def converter_init() -> DocumentConverter:
    """
    DocumentConverter 초기화 함수
    
    PDF 파이프라인의 input format을 PDF로 설정하고,
    이미지 생성을 비활성화하며, 이미지 스케일을 2.0으로 설정합니다.

    Args:
        None
    Returns:
        DocumentConverter: 초기화된 DocumentConverter 객체
    """
    pipeline_options = PdfPipelineOptions()
    pipeline_options.generate_picture_images = False
    pipeline_options.images_scale = 2.0
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    return converter


_converter = converter_init()


def parsing(
    content: bytes,
    filename: Optional[str] = None,
    *,
    extract_images: bool = True,
    unpivot_tables: bool = True,
    **_: object,
) -> str:
    """
    PDF 파일을 파싱하여 마크다운 문자열을 반환하는 함수

    Args:
        content: 업로드된 PDF의 raw bytes
        filename: 원본 파일명 (선택사항)
    Returns:
        str: 파싱된 마크다운 문자열
    """
    stream = DocumentStream(
        name=filename or "uploaded.pdf", stream=BytesIO(content)
    )
    
    try:
        result = _converter.convert(stream, raises_on_error=False)
    except Exception as exc:
        return f"# {filename or 'document'}\n\nPromTree 변환 실패: {exc}"

    if result.status not in (ConversionStatus.SUCCESS, ConversionStatus.PARTIAL_SUCCESS):
        details = "; ".join(err.error_message for err in (result.errors or []))
        return (
            f"# {filename or 'document'}\n\n"
            f"PromTree 변환이 완료되지 않았습니다. 상태: {result.status}. {details}"
        )

    if not result.document:
        return f"# {filename or 'document'}\n\nPromTree에서 문서를 생성하지 못했습니다."

    doc = result.document
    contents = []
    # current_page = None

    for item, _ in doc.iterate_items():
        # if hasattr(item, 'prov') and item.prov:
        #     page_number = item.prov[0].page_no
            # if page_number != current_page:
            #     current_page = page_number
            #     contents.append(f">>> page_{page_number}")
        
        if isinstance(item, SectionHeaderItem):
            # 섹션 아이템은 제목으로 추가
            contents.append(f"## {item.text}")

        elif isinstance(item, TextItem):
            # 텍스트 아이템은 markdown 형식으로
            contents.append(item.text)
        

        elif isinstance(item, TableItem):
            # 표 아이템은 HTML로 변환해서 추가
            html = item.export_to_html(doc)
            if unpivot_tables:
                unpivot_table = unpivot.parse_html_table(html)
                contents.extend(unpivot_table)
            else:
                contents.append(html)

        elif isinstance(item, PictureItem) and extract_images:
            # 이미지 처리 - base64로 인코딩
            try:
                if item.image and item.image.pil_image:
                    # # PIL Image를 바이트로 변환
                    img_buffer = BytesIO()
                    item.image.pil_image.save(img_buffer, format="PNG")
                    img_bytes = img_buffer.getvalue()

                    # base64 인코딩
                    base64_image = base64.b64encode(img_bytes).decode('utf-8')

                    # markdown 이미지 문법
                    image_markdown = f"![image](data:image/png;base64,{base64_image})"
                    contents.append(image_markdown)
            except Exception as e:
                print(f"Warning: Could not process image in {filename or 'document'}: {e}")

    if not contents:
        return f"# {filename or 'document'}\n\n(본문을 추출하지 못했습니다.)"
    
    return "\n\n".join(contents)
