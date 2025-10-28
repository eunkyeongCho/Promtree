import fitz  # PyMuPDF
import os
from pathlib import Path
import re

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    print("Warning: pdfplumber not installed. Table extraction will be limited.")
    print("Install with: pip install pdfplumber")


def pdf_to_markdown_advanced(pdf_path, output_path, extract_tables=True):
    """
    PDF 파일을 Markdown으로 변환합니다 (고급 버전).
    
    Args:
        pdf_path (str): 입력 PDF 파일 경로
        output_path (str): 출력 Markdown 파일 경로
        extract_tables (bool): 표 추출 여부 (pdfplumber 필요)
    """
    # 출력 디렉토리 생성
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 이미지 저장 디렉토리 생성
    images_dir = output_dir / f"{Path(output_path).stem}_images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    # PDF 열기
    doc = fitz.open(pdf_path)
    markdown_content = []
    
    # pdfplumber로 표 추출 (가능한 경우)
    tables_by_page = {}
    if extract_tables and PDFPLUMBER_AVAILABLE:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    tables = page.extract_tables()
                    if tables:
                        tables_by_page[page_num] = tables
                        print(f"Found {len(tables)} table(s) on page {page_num + 1}")
        except Exception as e:
            print(f"Warning: Table extraction failed: {e}")
    
    print(f"Processing {len(doc)} pages...")
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        print(f"Processing page {page_num + 1}/{len(doc)}...")
        
        # 페이지 번호 추가
        if page_num > 0:
            markdown_content.append(f"\n---\n\n# Page {page_num + 1}\n")
        
        # 1. 이미지 추출 및 저장
        image_list = page.get_images(full=True)
        page_images = []
        
        for img_index, img in enumerate(image_list):
            xref = img[0]
            
            try:
                # 이미지 추출
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # 이미지 파일명 생성
                image_filename = f"page{page_num + 1}_img{img_index + 1}.{image_ext}"
                image_path = images_dir / image_filename
                
                # 이미지 저장
                with open(image_path, "wb") as img_file:
                    img_file.write(image_bytes)
                
                # 상대 경로
                relative_path = f"{images_dir.name}/{image_filename}"
                page_images.append(relative_path)
                
                print(f"  Extracted image: {image_filename}")
                
            except Exception as e:
                print(f"  Warning: Could not extract image {img_index + 1}: {e}")
        
        # 2. 텍스트 추출 (구조화)
        text_content = extract_structured_text(page)
        markdown_content.append(text_content)
        
        # 3. 표 추가
        if page_num in tables_by_page:
            for table_data in tables_by_page[page_num]:
                if table_data:  # 빈 표가 아닌 경우
                    table_md = convert_table_to_markdown(table_data)
                    markdown_content.append(table_md)
        
        # 4. 이미지 추가
        for img_path in page_images:
            markdown_content.append(f"\n![Image]({img_path})\n")
    
    doc.close()
    
    # Markdown 파일 저장
    final_markdown = "\n".join(markdown_content)
    
    # 후처리
    final_markdown = clean_markdown(final_markdown)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_markdown)
    
    print(f"\n✅ Conversion complete!")
    print(f"📄 Markdown saved to: {output_path}")
    print(f"🖼️  Images saved to: {images_dir}")
    
    return output_path


def extract_structured_text(page):
    """
    페이지에서 구조화된 텍스트를 추출합니다.
    폰트 크기와 스타일을 기반으로 제목, 본문을 구분합니다.
    """
    blocks = page.get_text("dict")["blocks"]
    structured_text = []
    
    for block in blocks:
        if block["type"] == 0:  # 텍스트 블록
            for line in block.get("lines", []):
                line_parts = []
                max_font_size = 0
                
                for span in line.get("spans", []):
                    text = span["text"].strip()
                    if not text:
                        continue
                    
                    font_size = span["size"]
                    font_flags = span["flags"]
                    
                    max_font_size = max(max_font_size, font_size)
                    
                    # 스타일 적용
                    is_bold = font_flags & 2**4
                    is_italic = font_flags & 2**1
                    
                    if is_bold and is_italic:
                        text = f"***{text}***"
                    elif is_bold:
                        text = f"**{text}**"
                    elif is_italic:
                        text = f"*{text}*"
                    
                    line_parts.append(text)
                
                if line_parts:
                    line_text = " ".join(line_parts)
                    
                    # 폰트 크기로 제목 판단
                    if max_font_size > 18:
                        line_text = f"# {line_text}"
                    elif max_font_size > 16:
                        line_text = f"## {line_text}"
                    elif max_font_size > 14:
                        line_text = f"### {line_text}"
                    elif max_font_size > 12:
                        line_text = f"#### {line_text}"
                    
                    structured_text.append(line_text)
            
            # 블록 끝에 빈 줄 추가
            if structured_text and structured_text[-1]:
                structured_text.append("")
    
    return "\n".join(structured_text)


def convert_table_to_markdown(table_data):
    """
    표 데이터를 Markdown 형식으로 변환합니다.
    """
    if not table_data or len(table_data) == 0:
        return ""
    
    # 빈 행 제거
    table_data = [row for row in table_data if any(cell for cell in row if cell)]
    
    if len(table_data) == 0:
        return ""
    
    markdown_lines = ["\n"]
    
    # 헤더 행
    header = table_data[0]
    header_cells = [str(cell if cell else "") for cell in header]
    markdown_lines.append("| " + " | ".join(header_cells) + " |")
    
    # 구분선
    markdown_lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    
    # 데이터 행
    for row in table_data[1:]:
        cells = [str(cell if cell else "") for cell in row]
        # 열 개수 맞추기
        while len(cells) < len(header):
            cells.append("")
        markdown_lines.append("| " + " | ".join(cells[:len(header)]) + " |")
    
    markdown_lines.append("\n")
    
    return "\n".join(markdown_lines)


def clean_markdown(markdown_text):
    """
    Markdown 텍스트를 정리합니다.
    """
    # 연속된 빈 줄을 2개로 제한
    markdown_text = re.sub(r'\n{4,}', '\n\n\n', markdown_text)
    
    # 줄 끝 공백 제거
    lines = markdown_text.split('\n')
    lines = [line.rstrip() for line in lines]
    markdown_text = '\n'.join(lines)
    
    # 시작과 끝 공백 제거
    markdown_text = markdown_text.strip()
    
    return markdown_text


# 사용 예시
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) >= 3:
        pdf_path = sys.argv[1]
        output_path = sys.argv[2]
        
        if os.path.exists(pdf_path):
            pdf_to_markdown_advanced(pdf_path, output_path)
        else:
            print(f"❌ PDF 파일을 찾을 수 없습니다: {pdf_path}")
    else:
        print("사용 방법:")
        print("  python pdf_to_markdown_advanced.py input.pdf output.md")
        print("\n또는 코드에서 직접 호출:")
        print("  from pdf_to_markdown_advanced import pdf_to_markdown_advanced")
        print("  pdf_to_markdown_advanced('input.pdf', 'output.md')")



