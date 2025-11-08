# tabula_table_extractor.py, make_table_item.py, html2row.py 을 사용한 파이프 라인 구현
from typing import Tuple
from tabula_table_extractor import extract_tubla_table_with_bbox, preprocess_table
from make_table_item import make_table_item_from_dataframe
from docling_core.types.doc import DoclingDocument
from html2row import parse_and_print


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





def main() -> None:
    # 여기에 값만 수정하면 됩니다
    pdf_path = "noline.pdf"
    
    
    # cas 있는 테이블.
    page = 2
    table_bbox = (35.00, 194.5336456298828, 520.6958923339844, 323.229248046875)

    # cas 없는 테이블.
    # page = 7
    # table_bbox = (56.00, 207.61000061035156, 515.00, 418.1012878417969)


    stream_mode = True  # True면 stream 모드, False면 lattice 모드

    parse_with_tabula(pdf_path, page, table_bbox, stream_mode)


if __name__ == "__main__":
    main()
