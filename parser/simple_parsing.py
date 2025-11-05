from pathlib import Path
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import TextItem, TableItem, PictureItem
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
import base64
from io import BytesIO

# 파일 존재 확인
pdf_file = Path("msds/001001.pdf")
if not pdf_file.exists():
    raise FileNotFoundError(f"PDF file not found: {pdf_file}")

# 이미지를 포함하도록 변환 세팅
pipeline_options = PdfPipelineOptions()
pipeline_options.generate_picture_images = True  # 이미지 생성 활성화
pipeline_options.images_scale = 2.0  # 이미지 해상도

# ✅ PdfFormatOption 객체 사용
converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)
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
    
    if isinstance(item, TextItem):
        # 텍스트 아이템은 markdown 형식으로
        combined_content.append(item.text)
    
    elif isinstance(item, TableItem):
        # 표 아이템은 HTML로 변환해서 추가
        # table_df = item.export_to_dataframe(doc)
        # html = table_df.to_html(border=1)
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
            print(f"Warning: Could not process image - {e}")

# 하나의 markdown 파일로 저장
output_file = pdf_file.stem + ".md"
Path(output_file).write_text("\n\n".join(combined_content), encoding="utf-8")
print(f"✅ Saved to {output_file}")