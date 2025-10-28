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


def pdf_to_markdown_advanced(pdf_path, output_path, extract_tables=True, table_settings=None):
    """
    PDF 파일을 Markdown으로 변환합니다 (좌표 기반 레이아웃 보존).

    Args:
        pdf_path (str): 입력 PDF 파일 경로
        output_path (str): 출력 Markdown 파일 경로
        extract_tables (bool): 표 추출 여부 (pdfplumber 필요)
        table_settings (dict): pdfplumber 테이블 추출 설정
            예: {
                "vertical_strategy": "lines",  # or "text"
                "horizontal_strategy": "lines",  # or "text"
                "snap_tolerance": 3,
                "join_tolerance": 3,
                "edge_min_length": 3,
                "min_words_vertical": 3,
                "min_words_horizontal": 1
            }

    Features:
        - 텍스트와 이미지의 원본 순서 유지 (좌표 기반)
        - &nbsp;로 공백 표현
        - 폰트 크기로 제목 레벨 자동 감지 (##, ###)
        - pdfplumber 고급 테이블 추출 (find_tables, extract)
    """
    # 기본 테이블 설정
    if table_settings is None:
        table_settings = {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "snap_tolerance": 3,
            "join_tolerance": 3,
            "edge_min_length": 3
        }
    # 출력 디렉토리 생성
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # 이미지 저장 디렉토리 생성
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # PDF 열기
    doc = fitz.open(pdf_path)
    markdown_content = []

    # pdfplumber로 표 추출 (가능한 경우) - 강화된 버전
    tables_by_page = {}
    if extract_tables and PDFPLUMBER_AVAILABLE:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # find_tables()로 테이블 객체 감지 (설정 적용)
                    table_finder = page.find_tables(table_settings=table_settings)

                    if table_finder:
                        tables_with_bbox = []

                        for table_obj in table_finder:
                            # extract() 메서드로 테이블 데이터 추출
                            table_data = table_obj.extract()

                            if table_data and len(table_data) > 0:
                                bbox = table_obj.bbox  # (x0, y0, x1, y1)

                                # 디버그 정보 수집
                                debug_info = {
                                    'rows': len(table_data),
                                    'cols': len(table_data[0]) if table_data else 0,
                                    'bbox': bbox,
                                    'cells': sum(1 for row in table_data for cell in row if cell)
                                }

                                tables_with_bbox.append({
                                    'data': table_data,
                                    'bbox': bbox,
                                    'y0': bbox[1],  # 정렬용
                                    'debug': debug_info
                                })

                                print(f"  Found table: {debug_info['rows']}x{debug_info['cols']} ({debug_info['cells']} cells) at y={bbox[1]:.1f}")

                        if tables_with_bbox:
                            tables_by_page[page_num] = tables_with_bbox
                            print(f"Found {len(tables_with_bbox)} table(s) on page {page_num + 1}")

        except Exception as e:
            print(f"Warning: Table extraction failed: {e}")
            import traceback
            traceback.print_exc()

    print(f"Processing {len(doc)} pages...")

    # 1단계: 전체 문서의 폰트 크기 분석 (빈도 기반)
    print("Analyzing font sizes across document...")
    font_size_counts = {}
    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block["type"] == 0:  # 텍스트 블록
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        if span["text"].strip():
                            size = round(span["size"], 1)  # 소수점 1자리로 반올림
                            font_size_counts[size] = font_size_counts.get(size, 0) + 1

    # 폰트 크기 통계 계산 (빈도 기반)
    if font_size_counts:
        # 가장 많이 사용된 폰트 크기 찾기 (기본 사이즈)
        base_size = max(font_size_counts.items(), key=lambda x: x[1])[0]

        # 모든 고유한 폰트 크기를 정렬 (큰 것부터)
        unique_sizes = sorted(font_size_counts.keys(), reverse=True)

        # 가장 큰 폰트 크기
        max_size = unique_sizes[0]

        # 기본 사이즈보다 큰 사이즈들만 추출
        larger_sizes = [s for s in unique_sizes if s > base_size]

        # 제목 레벨 임계값 설정
        if len(larger_sizes) > 0:
            # 가장 큰 크기 = H1
            h1_threshold = max_size

            # 기본과 최대 사이의 범위를 3등분
            size_range = max_size - base_size

            if len(larger_sizes) >= 2:
                # H2: 기본에서 66% 지점
                h2_threshold = base_size + (size_range * 2 / 3)
                # H3: 기본에서 33% 지점
                h3_threshold = base_size + (size_range * 1 / 3)
            else:
                # 큰 사이즈가 1개뿐: H1만 사용
                h2_threshold = max_size
                h3_threshold = max_size
        else:
            # 기본 사이즈만 있음: 제목 없음
            h1_threshold = base_size
            h2_threshold = base_size
            h3_threshold = base_size

        print(f"Font size analysis:")
        print(f"  Most common (base): {base_size:.1f}pt (used {font_size_counts[base_size]} times)")
        print(f"  Largest size: {max_size:.1f}pt")
        print(f"  All unique sizes: {', '.join([f'{s:.1f}pt' for s in unique_sizes])}")
        if larger_sizes:
            print(f"  Size range: {base_size:.1f}pt (base) ~ {max_size:.1f}pt (max)")
            print(f"  H3 threshold (33%): ≥ {h3_threshold:.1f}pt")
            print(f"  H2 threshold (66%): ≥ {h2_threshold:.1f}pt")
            print(f"  H1 threshold (max): ≥ {h1_threshold:.1f}pt")
        else:
            print(f"  No sizes larger than base - no headers detected")
    else:
        # 기본값
        base_size = 11
        h1_threshold = 18
        h2_threshold = 16
        h3_threshold = 14

    # 2단계: 페이지별 처리
    for page_num in range(len(doc)):
        page = doc[page_num]
        print(f"Processing page {page_num + 1}/{len(doc)}...")

        # 페이지 시작 마커
        markdown_content.append(f"\n>>> page {page_num + 1}\n")

        # 모든 요소(텍스트, 이미지, 테이블)를 좌표 기반으로 수집
        page_elements = []

        # 1. 텍스트 블록 수집
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block["type"] == 0:  # 텍스트 블록
                bbox = block["bbox"]  # (x0, y0, x1, y1)
                text_content = extract_text_from_block(block, base_size, h1_threshold, h2_threshold, h3_threshold)
                if text_content.strip():
                    page_elements.append({
                        'type': 'text',
                        'content': text_content,
                        'y0': bbox[1],
                        'x0': bbox[0],
                        'bbox': bbox
                    })

        # 2. 이미지 수집 및 추출
        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list):
            xref = img[0]

            try:
                # 이미지 위치 정보 가져오기
                img_rects = page.get_image_rects(xref)
                if not img_rects:
                    continue

                # 첫 번째 사각형 사용 (대부분의 경우 하나만 있음)
                img_rect = img_rects[0]

                # 이미지 추출
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]

                # 이미지 크기 정보
                width = img_rect.width
                height = img_rect.height

                # 이미지 파일명 생성
                image_filename = f"page_{page_num + 1}_img_{img_index + 1}.{image_ext}"
                image_path = images_dir / image_filename

                # 이미지 저장
                with open(image_path, "wb") as img_file:
                    img_file.write(image_bytes)

                # 상대 경로
                relative_path = f"images/{image_filename}"

                # 이미지 HTML 태그
                img_tag = f'<img src="{relative_path}" alt="image" width="{int(width)}" height="{int(height)}" />'

                page_elements.append({
                    'type': 'image',
                    'content': img_tag,
                    'y0': img_rect.y0,
                    'x0': img_rect.x0,
                    'bbox': (img_rect.x0, img_rect.y0, img_rect.x1, img_rect.y1)
                })

                print(f"  Extracted image: {image_filename} ({width:.1f}x{height:.1f}pt)")

            except Exception as e:
                print(f"  Warning: Could not extract image {img_index + 1}: {e}")

        # 3. 테이블 수집
        if page_num in tables_by_page:
            for table_info in tables_by_page[page_num]:
                table_md = convert_table_to_markdown(table_info['data'])
                bbox = table_info['bbox']
                page_elements.append({
                    'type': 'table',
                    'content': table_md,
                    'y0': bbox[1],
                    'x0': bbox[0],
                    'bbox': bbox
                })

        # 4. 좌표 기준으로 정렬 (위→아래, 왼쪽→오른쪽)
        page_elements.sort(key=lambda e: (e['y0'], e['x0']))

        # 5. 정렬된 요소들을 마크다운으로 변환
        for element in page_elements:
            if element['type'] == 'text':
                markdown_content.append(element['content'])
            elif element['type'] == 'image':
                markdown_content.append(element['content'])
            elif element['type'] == 'table':
                markdown_content.append(element['content'])

        # 페이지 끝 마커
        markdown_content.append("\n>>> pend\n")

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


def extract_text_from_block(block, base_size, h1_threshold, h2_threshold, h3_threshold):
    """
    텍스트 블록에서 라인별로 텍스트를 추출하고 간격 기반으로 &nbsp; 처리.
    빈도 기반 상대적 폰트 크기로 제목 레벨 자동 감지.

    Args:
        block: PyMuPDF 텍스트 블록
        base_size: 가장 많이 사용된 기본 폰트 크기
        h1_threshold: H1(#) 제목으로 판단할 폰트 크기 임계값 (= 최대 크기)
        h2_threshold: H2(##) 제목으로 판단할 폰트 크기 임계값 (= 66% 지점)
        h3_threshold: H3(###) 제목으로 판단할 폰트 크기 임계값 (= 33% 지점)

    로직:
        - 가장 많이 나오는 크기 = 기본 (일반 텍스트)
        - 가장 큰 크기 = # (H1)
        - 기본 ~ 최대 범위를 3등분:
            * 기본 + 33% ~ 66% = ### (H3)
            * 기본 + 66% ~ 100% = ## (H2)
            * 최대 = # (H1)
    """
    lines = []

    for line in block.get("lines", []):
        spans = line.get("spans", [])
        if not spans:
            continue

        # 라인 내 span들을 x 좌표 순으로 정렬
        sorted_spans = sorted(spans, key=lambda s: s["bbox"][0])

        line_parts = []
        prev_x1 = None
        avg_char_width = 5  # 평균 문자 너비 추정값
        max_font_size = 0  # 라인의 최대 폰트 크기

        for span in sorted_spans:
            text = span["text"]
            if not text.strip():
                continue

            # 공백 제거하여 ** 처리 오류 방지
            text = text.strip()

            bbox = span["bbox"]
            x0 = bbox[0]
            font_size = round(span["size"], 1)  # 소수점 1자리로 반올림
            font_flags = span["flags"]

            # 라인의 최대 폰트 크기 추적
            max_font_size = max(max_font_size, font_size)

            # 이전 span과의 간격 계산
            if prev_x1 is not None:
                gap = x0 - prev_x1
                # 간격이 평균 문자 너비의 2배 이상이면 &nbsp; 추가
                if gap > avg_char_width * 2:
                    num_spaces = int(gap / avg_char_width)
                    line_parts.append("&nbsp;" * num_spaces)

            # 스타일 적용 (이미 strip된 텍스트 사용)
            is_bold = font_flags & 2**4
            is_italic = font_flags & 2**1

            styled_text = text
            if is_bold and is_italic:
                styled_text = f"***{text}***"
            elif is_bold:
                styled_text = f"**{text}**"
            elif is_italic:
                styled_text = f"*{text}*"

            line_parts.append(styled_text)
            prev_x1 = bbox[2]  # 현재 span의 x1 위치 저장

        if line_parts:
            line_text = "".join(line_parts)

            # 빈도 기반 상대적 폰트 크기로 제목 레벨 판단
            # 기본 사이즈보다 큰 것만 제목으로 처리
            if max_font_size > base_size:
                if max_font_size >= h1_threshold:
                    # 가장 큰 사이즈 (base + 3단계 이상)
                    line_text = f"# {line_text}"
                elif max_font_size >= h2_threshold:
                    # 두 번째로 큰 사이즈 (base + 2단계)
                    line_text = f"## {line_text}"
                elif max_font_size >= h3_threshold:
                    # 세 번째로 큰 사이즈 (base + 1단계)
                    line_text = f"### {line_text}"
                else:
                    # 기본 사이즈
                    line_text = line_text
            else:
                # 기본 사이즈 이하 = 일반 텍스트
                line_text = line_text

            lines.append(line_text)

    return "\n".join(lines)


def convert_table_to_markdown(table_data):
    """
    표 데이터를 Markdown 형식으로 변환합니다 (개선된 버전).

    Features:
        - 빈 셀 정리
        - 개행 문자 처리
        - 열 정렬 보정
        - 셀 내용 정리
    """
    if not table_data or len(table_data) == 0:
        return ""

    # 빈 행 제거 (모든 셀이 None이거나 빈 문자열인 행)
    table_data = [row for row in table_data if any(cell for cell in row if cell and str(cell).strip())]

    if len(table_data) == 0:
        return ""

    # 셀 내용 정리 함수
    def clean_cell(cell):
        if cell is None:
            return ""
        cell_str = str(cell).strip()
        # 개행 문자를 공백으로 변환
        cell_str = cell_str.replace('\n', ' ')
        # 연속된 공백을 하나로
        cell_str = re.sub(r'\s+', ' ', cell_str)
        return cell_str

    markdown_lines = ["\n"]

    # 열 개수 결정 (가장 긴 행 기준)
    max_cols = max(len(row) for row in table_data)

    # 헤더 행
    header = table_data[0]
    header_cells = [clean_cell(cell) for cell in header]
    # 열 개수 맞추기
    while len(header_cells) < max_cols:
        header_cells.append("")

    markdown_lines.append("| " + " | ".join(header_cells) + " |")

    # 구분선
    markdown_lines.append("| " + " | ".join(["---"] * max_cols) + " |")

    # 데이터 행
    for row in table_data[1:]:
        cells = [clean_cell(cell) for cell in row]
        # 열 개수 맞추기
        while len(cells) < max_cols:
            cells.append("")
        markdown_lines.append("| " + " | ".join(cells) + " |")

    markdown_lines.append("\n")

    return "\n".join(markdown_lines)


def clean_markdown(markdown_text):
    """
    Markdown 텍스트를 정리합니다.
    """
    # 연속된 빈 줄을 2개로 제한
    markdown_text = re.sub(r'\n{4,}', '\n\n\n', markdown_text)

    # 줄 끝 공백 제거 (단, &nbsp;는 유지)
    lines = markdown_text.split('\n')
    cleaned_lines = []
    for line in lines:
        # &nbsp;가 아닌 일반 공백만 제거
        if not line.endswith('&nbsp;'):
            line = line.rstrip()
        cleaned_lines.append(line)

    markdown_text = '\n'.join(cleaned_lines)

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
            # 기본 설정으로 변환
            pdf_to_markdown_advanced(pdf_path, output_path)

            # 또는 테이블 추출 설정 커스터마이징
            # custom_table_settings = {
            #     "vertical_strategy": "text",     # 텍스트 기반 세로 경계 감지
            #     "horizontal_strategy": "text",   # 텍스트 기반 가로 경계 감지
            #     "snap_tolerance": 5,             # 선 감지 허용 오차
            #     "join_tolerance": 5,             # 선 결합 허용 오차
            #     "edge_min_length": 5             # 최소 선 길이
            # }
            # pdf_to_markdown_advanced(pdf_path, output_path, table_settings=custom_table_settings)
        else:
            print(f"❌ PDF 파일을 찾을 수 없습니다: {pdf_path}")
    else:
        print("=" * 70)
        print("Advanced PDF to Markdown Converter")
        print("=" * 70)
        print("\n사용 방법:")
        print("  python advanced_pdf_to_md.py input.pdf output.md")
        print("\n주요 기능:")
        print("  ✅ 좌표 기반 요소 정렬 (텍스트, 이미지, 테이블)")
        print("  ✅ 제목 레벨 자동 감지 (#, ##, ###, ####)")
        print("  ✅ 공백 표현 (&nbsp;)")
        print("  ✅ pdfplumber 고급 테이블 추출")
        print("\nPython 코드에서 사용:")
        print("  from advanced_pdf_to_md import pdf_to_markdown_advanced")
        print("  pdf_to_markdown_advanced('input.pdf', 'output.md')")
        print("\n테이블 추출 설정 커스터마이징:")
        print("  settings = {")
        print("      'vertical_strategy': 'lines',   # or 'text'")
        print("      'horizontal_strategy': 'lines', # or 'text'")
        print("      'snap_tolerance': 3")
        print("  }")
        print("  pdf_to_markdown_advanced('input.pdf', 'output.md', table_settings=settings)")
        print("=" * 70)
