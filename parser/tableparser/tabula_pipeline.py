# tabula_table_extractor.py, make_table_item.py, html2row.py 을 사용한 파이프 라인 구현
from tabula_table_extractor import (
    extract_tubla_table_with_bbox,
    extract_multiple_tables_batch,
    preprocess_table
)
from make_table_item import make_table_item_from_dataframe
from docling_core.types.doc import DoclingDocument
from html2row import parse_and_print
from typing import List, Tuple, Dict
import pandas as pd

def parse_with_tabula(
    pdf_path: str,
    page: int,
    table_bbox: Tuple[float, float, float, float],
    stream_mode: bool = True,
) -> None:
    """
    PDF 테이블을 파싱하여 행 dict로 출력하는 파이프라인
    
    Args:
        pdf_path: PDF 파일 경로
        page: 페이지 번호 (1부터 시작)
        table_bbox: 테이블 bbox 좌표 (l, t, r, b)
        stream_mode: True면 stream 모드, False면 lattice 모드
    """
    # 1) Tabula JSON 추출 → DataFrame, 셀 bbox
    raw_df, raw_cell_bboxes = extract_tubla_table_with_bbox(
        pdf_path=pdf_path, bbox=table_bbox, page=page, stream=stream_mode
    )

    # 2) 전처리 (행 병합 + bbox 동기 병합)
    df, cell_bboxes = preprocess_table(raw_df, raw_cell_bboxes)

    # 3) TableItem 생성
    ti = make_table_item_from_dataframe(
        df,
        cell_bboxes,
        page_no=page,
        use_df_columns_as_header=True,
        table_bbox_top_left=table_bbox,
    )

    # 4) 문서 생성 및 테이블만 HTML 변환
    doc = DoclingDocument(name="table", tables=[ti])
    html_table = ti.export_to_html(doc=doc)

    # 5) HTML 테이블 → 행 dict 출력
    parse_and_print(html_table)


def batch_extract_tables(
    pdf_path: str,
    table_regions: List[Dict[str, any]],
    stream_mode: bool = True,
    use_preprocessing: bool = True  # CAS 병합 등 전처리 사용 여부
) -> Dict[int, Tuple[pd.DataFrame, list]]:
    """
    여러 테이블 bbox를 한 번에 추출 (기존 tabula_table_extractor 함수 재사용)

    Args:
        pdf_path: PDF 파일 경로
        table_regions: [{"page": 1, "bbox": (l,t,r,b), "id": 0}, ...]
        stream_mode: stream 모드 사용 여부
        use_preprocessing: preprocess_table 적용 여부 (CAS 병합 등)

    Returns:
        {table_id: (DataFrame, cell_bboxes), ...}
    """
    results = {}

    # 페이지별로 그룹화
    pages_dict = {}
    for region in table_regions:
        page = region["page"]
        if page not in pages_dict:
            pages_dict[page] = []
        pages_dict[page].append(region)

    # 페이지별로 처리 (같은 페이지의 여러 테이블을 한 번에 추출)
    for page_num, regions in pages_dict.items():
        print(f"\n📄 Processing page {page_num} with {len(regions)} tables...")

        # 같은 페이지의 모든 bbox를 모음
        bboxes = [region["bbox"] for region in regions]
        table_ids = [region["id"] for region in regions]

        try:
            # ⚡ 최적화: 같은 페이지의 여러 테이블을 한 번에 추출 (PDF 한 번만 로드!)
            batch_results = extract_multiple_tables_batch(
                pdf_path=pdf_path,
                page=page_num,
                bboxes=bboxes,
                stream=stream_mode
            )

            # 결과 처리
            for table_id, (raw_df, raw_cell_bboxes) in zip(table_ids, batch_results):
                if not raw_df.empty:
                    # 전처리 적용 (CAS 병합 등)
                    if use_preprocessing:
                        df, cell_bboxes = preprocess_table(raw_df, raw_cell_bboxes)
                    else:
                        df, cell_bboxes = raw_df, raw_cell_bboxes

                    results[table_id] = (df, cell_bboxes)
                    print(f"  ✅ Table {table_id}: {df.shape[0]}x{df.shape[1]}")
                else:
                    results[table_id] = (pd.DataFrame(), [])
                    print(f"  ❌ Table {table_id}: No data found")

        except Exception as e:
            # 배치 처리 실패 시 개별 처리로 폴백
            print(f"  ⚠️ Batch extraction failed: {e}, falling back to individual extraction")
            for region in regions:
                table_id = region["id"]
                bbox = region["bbox"]
                try:
                    raw_df, raw_cell_bboxes = extract_tubla_table_with_bbox(
                        pdf_path=pdf_path, bbox=bbox, page=page_num, stream=stream_mode
                    )
                    if not raw_df.empty:
                        if use_preprocessing:
                            df, cell_bboxes = preprocess_table(raw_df, raw_cell_bboxes)
                        else:
                            df, cell_bboxes = raw_df, raw_cell_bboxes
                        results[table_id] = (df, cell_bboxes)
                        print(f"  ✅ Table {table_id}: {df.shape[0]}x{df.shape[1]}")
                    else:
                        results[table_id] = (pd.DataFrame(), [])
                except Exception as e2:
                    results[table_id] = (pd.DataFrame(), [])
                    print(f"  ⚠️ Table {table_id}: Error - {e2}")

    return results


def main() -> None:
    # 여기에 값만 수정하면 됩니다
    pdf_path = "./noline.pdf"
    
    # 하나의 테이블 추출 테스트=========================================
    # cas 있는 테이블.
    # page = 2
    # table_bbox = (35.00, 194.5336456298828, 520.6958923339844, 323.229248046875)

    # cas 없는 테이블.
    # page = 7
    # table_bbox = (56.00, 207.61000061035156, 515.00, 418.1012878417969)


    # stream_mode = True  # True면 stream 모드, False면 lattice 모드

    # parse_with_tabula(pdf_path, page, table_bbox, stream_mode)


    # =========================================

    test_regions = [
        {"id": 1, "page": 2, "bbox": (35.00, 194.53, 520.70, 323.23)},
        {"id": 2, "page": 2, "bbox": (35.00, 323.23, 520.70, 523.23)}, # 같은 페이지에 여러 테이블 추가 가능 확인용
        {"id": 3, "page": 7, "bbox": (56.00, 207.61, 515.00, 418.10)},
        # 같은 페이지에 여러 테이블 추가 가능
    ]

    print("="*60)
    print("🚀 Batch Table Extraction Test")
    print("="*60)

    # 배치 추출
    results = batch_extract_tables(
        pdf_path=pdf_path,
        table_regions=test_regions,
        stream_mode=True
    )


    # 결과 출력
    print("\n" + "="*60)
    print("📊 Results Summary")
    print("="*60)
    for tid, (df, bboxes) in results.items():
        print(f"\nTable {tid}: {df.shape}")
        if not df.empty:
            print(df.head(3))


if __name__ == "__main__":
    main()
