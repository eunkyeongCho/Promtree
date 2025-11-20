from docling_core.types.doc import TextItem, TableItem, PictureItem, SectionHeaderItem
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
from typing import List
from pathlib import Path
from io import BytesIO
import base64
from app.promtree import unpivot
from app.promtree import metadata


def converter_init() -> DocumentConverter:
    """
    DocumentConverter 초기화 함수
    
    PDF 파이프라인의 input format을 PDF로 설정하고,
    이미지 생성을 활성화하며, 이미지 스케일을 2.0으로 설정합니다.

    Args:
        None
    Returns:
        DocumentConverter: 초기화된 DocumentConverter 객체
    """
    pipeline_options = PdfPipelineOptions()
    pipeline_options.generate_picture_images = True
    pipeline_options.images_scale = 2.0
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    return converter


def image_processor_init() -> metadata.VLLMMetadataExtractor:
    return metadata.VLLMMetadataExtractor()

    

def parse_pdf(pdf_file: Path, converter: DocumentConverter, image_processor: metadata.VLLMMetadataExtractor) -> List[str]:
    """
    PDF 파일을 파싱하여 콘텐츠 리스트를 반환하는 함수

    Args:
        pdf_file (Path): 파싱할 PDF 파일의 경로
        converter (DocumentConverter): DocumentConverter 객체
    Returns:
        List[str]: 파싱된 콘텐츠 리스트(텍스트=마크다운, 이미지=base64 인코딩, 표=HTML)
    """
    print(f"🔄 PDF 파일 파싱 시작 (파일: {pdf_file.name})")
    result = converter.convert(pdf_file)
    doc = result.document

    contents = []
    current_page = None

    for item, _ in doc.iterate_items():
        if hasattr(item, 'prov') and item.prov:
            page_number = item.prov[0].page_no
            if page_number != current_page:
                current_page = page_number
                contents.append(f">>> page_{page_number}")
        
        if isinstance(item, SectionHeaderItem):
            # 섹션 아이템은 제목으로 추가
            contents.append(f"## {item.text}")

        elif isinstance(item, TextItem):
            # 텍스트 아이템은 markdown 형식으로
            contents.append(item.text)
        

        elif isinstance(item, TableItem):
            # 표 아이템은 HTML로 변환해서 추가
            html = item.export_to_html(doc)
            unpivot_table = unpivot.parse_html_table(html)
            contents.extend(unpivot_table)

        elif isinstance(item, PictureItem):
            # 이미지 처리 - base64로 인코딩
            try:
                if not item.image:
                    print(f"⚠️ 이미지 객체가 없습니다 (파일: {pdf_file.name}, 페이지: {current_page})")
                elif not item.image.pil_image:
                    print(f"⚠️ PIL 이미지가 없습니다 (파일: {pdf_file.name}, 페이지: {current_page})")
                    print(f"   generate_picture_images=False 설정으로 인해 이미지가 생성되지 않았을 수 있습니다.")
                else:
                    # PIL Image를 바이트로 변환
                    img_buffer = BytesIO()
                    item.image.pil_image.save(img_buffer, format="PNG")
                    img_bytes = img_buffer.getvalue()

                    # base64 인코딩
                    base64_image = base64.b64encode(img_bytes).decode('utf-8')

                    # VLLM으로부터 이미지 메타데이터 추출
                    print(f"🔄 VLLM 이미지 메타데이터 추출 중...")
                    try:
                        image_metadata_text = image_processor.extract(base64_image)
                        print(f"✅ VLLM 메타데이터 추출 완료: {image_metadata_text[:100]}...")
                        # 마크다운 이미지 문법 형식으로 변환하여 chunking 가능하도록 함
                        image_markdown = f"![{image_metadata_text}]()"
                        contents.append(image_markdown)
                        print(f"✅ 이미지 마크다운 추가 완료")
                    except Exception as vllm_error:
                        # VLLM 에러 시 경고만 출력하고 계속 진행 (이미지 건너뜀)
                        error_msg = f"⚠️ VLLM 이미지 처리 실패 (파일: {pdf_file.name}, 페이지: {current_page}): {vllm_error}"
                        print(error_msg)
                        print("⏩ 이미지를 건너뛰고 계속 진행합니다...")
            except Exception as e:
                # 다른 예외는 로그만 출력하고 계속
                print(f"⚠️ 이미지 처리 중 예외 발생: {e}")

    return contents


if __name__ == "__main__":
    import os
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    
    pdf_path = Path("3M-1509-DC-Polyethylene-Tape-TIS-Jun13.pdf")
    converter = converter_init()
    contents = parse_pdf(pdf_path, converter)
    for content in contents:
        print(content)
