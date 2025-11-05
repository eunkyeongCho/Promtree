from pathlib import Path
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import TextItem, TableItem, PictureItem, SectionHeaderItem
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
import base64
from io import BytesIO
from tqdm import tqdm
import sys

# 로깅 제거 - 필요시 print 사용

def create_converter():
    """
    DocumentConverter 인스턴스를 생성하고 반환
    
    Returns:
        DocumentConverter: 설정된 converter 인스턴스
    """
    # 이미지를 포함하도록 변환 세팅
    pipeline_options = PdfPipelineOptions()
    pipeline_options.generate_picture_images = True  # 이미지 생성 활성화
    pipeline_options.images_scale = 2.0  # 이미지 해상도

    # PdfFormatOption 객체 사용
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    
    print("DocumentConverter initialized")
    return converter

def process_single_pdf(pdf_file: Path, output_dir: Path, converter: DocumentConverter) -> bool:
    """
    단일 PDF 파일을 처리하여 마크다운으로 변환

    Args:
        pdf_file: 처리할 PDF 파일 경로
        output_dir: 출력 디렉토리 경로
        converter: DocumentConverter 인스턴스

    Returns:
        bool: 성공 여부
    """
    try:
        print(f"Processing: {pdf_file.name}")

        # PDF 변환
        result = converter.convert(pdf_file)
        doc = result.document

        # 텍스트, 표, 이미지를 함께 처리
        combined_content = []
        current_page = None

        for item, level in doc.iterate_items():
            # 페이지 변경 감지
            if hasattr(item, 'prov') and item.prov:
                page_no = item.prov[0].page_no
                if page_no != current_page:
                    current_page = page_no
                    combined_content.append(f">>> page_{page_no}")

            if isinstance(item, SectionHeaderItem):
                # 섹션 아이템은 제목으로 추가
                combined_content.append(f"## {item.text}")

            elif isinstance(item, TextItem):
                # 텍스트 아이템은 markdown 형식으로
                combined_content.append(item.text)
            

            elif isinstance(item, TableItem):
                # 표 아이템은 HTML로 변환해서 추가
                html = item.export_to_html(doc)
                combined_content.append(html)

            elif isinstance(item, PictureItem):
                # 이미지 처리 - base64로 인코딩
                try:
                    if item.image and item.image.pil_image:
                        # PIL Image를 바이트로 변환
                        img_buffer = BytesIO()
                        item.image.pil_image.save(img_buffer, format="PNG")
                        img_bytes = img_buffer.getvalue()

                        # base64 인코딩
                        base64_image = base64.b64encode(img_bytes).decode('utf-8')

                        # markdown 이미지 문법
                        image_markdown = f"![image](data:image/png;base64,{base64_image})"
                        combined_content.append(image_markdown)
                except Exception as e:
                    print(f"Warning: Could not process image in {pdf_file.name}: {e}")

        # 출력 파일 경로 설정
        output_file = output_dir / f"{pdf_file.stem}.md"

        # 마크다운 파일로 저장
        output_file.write_text("\n\n".join(combined_content), encoding="utf-8")
        print(f"✅ Saved: {output_file}")

        return True

    except Exception as e:
        print(f"❌ Error processing {pdf_file.name}: {str(e)}")
        return False

def process_pdf_folder(pdf_folder_path: str, output_folder_path: str = "output"):
    """
    PDF 폴더 내의 모든 PDF 파일을 처리

    Args:
        pdf_folder_path: PDF 파일들이 있는 폴더 경로
        output_folder_path: 결과를 저장할 폴더 경로 (기본값: "output")
    """
    # 경로 객체 생성
    pdf_folder = Path(pdf_folder_path)
    output_folder = Path(output_folder_path)

    # 입력 폴더 확인
    if not pdf_folder.exists():
        print(f"Error: PDF folder not found: {pdf_folder}")
        return

    if not pdf_folder.is_dir():
        print(f"Error: Path is not a directory: {pdf_folder}")
        return

    # PDF 파일 목록 가져오기
    pdf_files = list(pdf_folder.glob("*.pdf"))

    if not pdf_files:
        print(f"Warning: No PDF files found in: {pdf_folder}")
        return

    print(f"Found {len(pdf_files)} PDF file(s) to process")

    # 출력 폴더 생성
    output_folder.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_folder.absolute()}")

    # DocumentConverter를 한 번만 생성
    converter = create_converter()

    # 처리 통계
    success_count = 0
    failed_files = []

    # 프로그레스 바와 함께 각 PDF 파일 처리
    for pdf_file in tqdm(pdf_files, desc="Processing PDFs", unit="file"):
        if process_single_pdf(pdf_file, output_folder, converter):
            success_count += 1
        else:
            failed_files.append(pdf_file.name)

    # 처리 결과 출력
    print("="*50)
    print("Processing Complete!")
    print(f"✅ Successfully processed: {success_count}/{len(pdf_files)} files")

    if failed_files:
        print(f"❌ Failed files: {', '.join(failed_files)}")

    print(f"Output files saved in: {output_folder.absolute()}")

def main():
    """메인 함수"""
    import argparse

    # 커맨드라인 인자 파서 설정
    parser = argparse.ArgumentParser(
        description="Convert multiple PDF files to Markdown format with images and tables"
    )
    parser.add_argument(
        "pdf_folder",
        help="Path to folder containing PDF files"
    )
    parser.add_argument(
        "-o", "--output",
        default="output",
        help="Output folder path (default: output)"
    )

    # 인자 파싱
    args = parser.parse_args()

    # PDF 폴더 처리
    process_pdf_folder(args.pdf_folder, args.output)

if __name__ == "__main__":
    # 예제 사용법 (직접 실행 시)
    if len(sys.argv) == 1:
        # 인자가 없으면 예제 실행
        print("Usage examples:")
        print("  python multi_parsing.py msds")
        print("  python multi_parsing.py /path/to/pdfs -o /path/to/output")
        print("\nRunning with default 'msds' folder...")
        process_pdf_folder("msds")
    else:
        # 커맨드라인 인자가 있으면 main 함수 실행
        main()