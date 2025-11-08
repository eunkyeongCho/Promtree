# tabula 정보를 tableitem 객체로 변환
from typing import List, Tuple
import math
import importlib
import pandas as pd
from tabula_table_extractor import CAS_in_table
from tabula_table_extractor import preprocess_table
from html2row import parse_and_print
from docling_core.types.doc import DoclingDocument
import pprint


def _import_docling_types():
    """
    실행 시점에 docling 타입들을 동적으로 임포트하여 강한 의존성을 피합니다.
    
    Returns:
        dict: docling 타입들의 딕셔너리
    """
    doc_module = importlib.import_module('docling_core.types.doc')

    return {
        'TableItem': getattr(doc_module, 'TableItem'),
        'TableData': getattr(doc_module, 'TableData'),
        'TableCell': getattr(doc_module, 'TableCell'),
        'BoundingBox': getattr(doc_module, 'BoundingBox'),
        'CoordOrigin': getattr(doc_module, 'CoordOrigin'),
        'RefItem': getattr(doc_module, 'RefItem'),
        'ContentLayer': getattr(doc_module, 'ContentLayer'),
        'DocItemLabel': getattr(doc_module, 'DocItemLabel'),
        'ProvenanceItem': getattr(doc_module, 'ProvenanceItem'),
    }


def _equal_grid_boxes(
    table_bbox_top_left: Tuple[float, float, float, float],
    num_rows: int,
    num_cols: int,
) -> List[List[Tuple[float, float, float, float]]]:
    """
    테이블 바운딩 박스를 균등 분할하여 TOPLEFT 기준의 셀 박스들을 생성합니다.
    바운딩 박스 형식: (l, t, r, b)
    """
    left, top, right, bottom = table_bbox_top_left
    width = max(0.0, right - left)
    height = max(0.0, bottom - top)

    col_width = width / float(max(1, num_cols))
    row_height = height / float(max(1, num_rows))

    boxes: List[List[Tuple[float, float, float, float]]] = []
    for r in range(num_rows):
        row_boxes: List[Tuple[float, float, float, float]] = []
        for c in range(num_cols):
            l = left + c * col_width
            t = top + r * row_height
            rgt = left + (c + 1) * col_width
            btm = top + (r + 1) * row_height
            row_boxes.append((l, t, rgt, btm))
        boxes.append(row_boxes)
    return boxes


def make_table_item_from_dataframe(
    df: pd.DataFrame,
    cell_bboxes: list,
    page_no: int,
    use_df_columns_as_header: bool = True,
    table_bbox_top_left: Tuple[float, float, float, float] | None = None,
):
    """
    tabula로부터 얻은 pandas DataFrame을 docling의 TableItem으로 변환합니다.

    Args:
        df: tabula가 반환한 pandas DataFrame
        table_bbox_top_left: 테이블 전체 영역의 TOPLEFT 기준 바운딩 박스 (l, t, r, b)
        page_no: PDF 페이지 번호 (1부터 시작)
        use_df_columns_as_header: True이면 DataFrame 컬럼명을 헤더 행으로 사용

    Returns:
        docling의 TableItem 인스턴스
    """
    types = _import_docling_types()
    TableItem = types['TableItem']
    TableData = types['TableData']
    TableCell = types['TableCell']
    BoundingBox = types['BoundingBox']
    CoordOrigin = types['CoordOrigin']
    RefItem = types['RefItem']
    ContentLayer = types['ContentLayer']
    DocItemLabel = types['DocItemLabel']
    ProvenanceItem = types['ProvenanceItem']
    
    # CAS 열 탐지
    cas_col_idx = CAS_in_table(df)
    
    # 그리드 크기 준비 (df는 헤더 행을 포함하고 있다고 가정)
    num_cols = int(df.shape[1])
    num_rows_total = int(df.shape[0])
    has_header = bool(use_df_columns_as_header and num_cols > 0 and num_rows_total > 0)

    # 간단 유틸. cell들의 빈 값 탐지를 위한 함수
    def _is_empty(val) -> bool:
        return (val is None) or (isinstance(val, float) and math.isnan(val)) or str(val).strip().lower() in ("", "nan")

    # grid 초기화: 앵커만 채우고 덮이는 칸은 None 유지
    grid: List[List] = [[None for _ in range(num_cols)] for _ in range(num_rows_total)]
    table_cells: List = []

    # 헤더 행: df의 0행을 헤더 텍스트로 사용
    if has_header:
        header_values = df.iloc[0].tolist()
        for c_idx in range(num_cols):
            text = "" if _is_empty(header_values[c_idx]) else str(header_values[c_idx])
            bbox_list = cell_bboxes[0][c_idx] if (cell_bboxes and len(cell_bboxes) > 0) else None
            if bbox_list is None:
                bbox_obj = BoundingBox(l=0.0, t=0.0, r=0.0, b=0.0, coord_origin=CoordOrigin.TOPLEFT)
            else:
                l, t, r, b = bbox_list
                bbox_obj = BoundingBox(l=float(l), t=float(t), r=float(r), b=float(b), coord_origin=CoordOrigin.TOPLEFT)
            cell = TableCell(
                bbox=bbox_obj,
                row_span=1,
                col_span=1,
                start_row_offset_idx=0,
                end_row_offset_idx=1,
                start_col_offset_idx=c_idx,
                end_col_offset_idx=c_idx + 1,
                text=text,
                column_header=True,
            )
            table_cells.append(cell)
            grid[0][c_idx] = cell

    # 데이터 행: 1행부터 끝까지 순회
    anchor_first_col = None  # 현재 1열 앵커(TableCell)
    for grid_r in range(1 if has_header else 0, num_rows_total):
        data_values = df.iloc[grid_r].tolist()

        # 1열 처리 (rowspan 확장)
        first_val = data_values[0] if num_cols > 0 else None
        if _is_empty(first_val):
            # 앵커가 존재하면 end_row_offset_idx만 증가 (bbox는 그대로)
            if anchor_first_col is not None:
                anchor_first_col.row_span += 1
                anchor_first_col.end_row_offset_idx = grid_r + 1
                grid[grid_r][0] = None
            else:
                # 앵커가 아직 없다면 건너뜀 (안전)
                grid[grid_r][0] = None
        else:
            # 새 앵커 생성
            bbox_list = cell_bboxes[grid_r][0] if (cell_bboxes and grid_r < len(cell_bboxes) and 0 < len(cell_bboxes[grid_r])) else None
            if bbox_list is None:
                bbox_obj = BoundingBox(l=0.0, t=0.0, r=0.0, b=0.0, coord_origin=CoordOrigin.TOPLEFT)
            else:
                l, t, r, b = bbox_list
                bbox_obj = BoundingBox(l=float(l), t=float(t), r=float(r), b=float(b), coord_origin=CoordOrigin.TOPLEFT)
            cell = TableCell(
                bbox=bbox_obj,
                row_span=1,
                col_span=1,
                start_row_offset_idx=grid_r,
                end_row_offset_idx=grid_r + 1,
                start_col_offset_idx=0,
                end_col_offset_idx=1,
                text=str(first_val),
                column_header=False,
            )
            table_cells.append(cell)
            grid[grid_r][0] = cell
            anchor_first_col = cell

        # 나머지 열 처리
        for c_idx in range(1, num_cols):
            val = data_values[c_idx]
            text = "" if _is_empty(val) else str(val)
            bbox_list = cell_bboxes[grid_r][c_idx] if (cell_bboxes and grid_r < len(cell_bboxes) and c_idx < len(cell_bboxes[grid_r])) else None
            if bbox_list is None:
                bbox_obj = BoundingBox(l=0.0, t=0.0, r=0.0, b=0.0, coord_origin=CoordOrigin.TOPLEFT)
            else:
                l, t, r, b = bbox_list
                bbox_obj = BoundingBox(l=float(l), t=float(t), r=float(r), b=float(b), coord_origin=CoordOrigin.TOPLEFT)
            cell = TableCell(
                bbox=bbox_obj,
                row_span=1,
                col_span=1,
                start_row_offset_idx=grid_r,
                end_row_offset_idx=grid_r + 1,
                start_col_offset_idx=c_idx,
                end_col_offset_idx=c_idx + 1,
                text=text,
                column_header=False,
            )
            table_cells.append(cell)
            grid[grid_r][c_idx] = cell

    # TableData 구성
    table_data = TableData(
        table_cells=table_cells,
        num_rows=num_rows_total,
        num_cols=num_cols,
        grid=grid,
    )

    # provenance bbox: 우선 입력 table_bbox_top_left 사용, 없으면 cell_bboxes 전체에서 min/max로 계산 (TOPLEFT)
    if table_bbox_top_left is not None:
        table_bbox = tuple(map(float, table_bbox_top_left))
    else:
        all_coords = []
        for r in range(len(cell_bboxes or [])):
            for c in range(len(cell_bboxes[r] or [])):
                bb = cell_bboxes[r][c]
                if bb and len(bb) == 4:
                    all_coords.append(tuple(map(float, bb)))
        if all_coords:
            l_vals = [bb[0] for bb in all_coords]
            t_vals = [bb[1] for bb in all_coords]
            r_vals = [bb[2] for bb in all_coords]
            b_vals = [bb[3] for bb in all_coords]
            table_bbox = (min(l_vals), min(t_vals), max(r_vals), max(b_vals))
        else:
            table_bbox = (0.0, 0.0, 0.0, 0.0)

    prov = [
        ProvenanceItem(
            page_no=page_no,
            bbox=BoundingBox(
                l=table_bbox[0],
                t=table_bbox[1],
                r=table_bbox[2],
                b=table_bbox[3],
                coord_origin=CoordOrigin.TOPLEFT,
            ),
            charspan=(0, 0),
        )
    ]

    table_item = TableItem(
        self_ref='#/tables/0',
        parent=RefItem(cref='#/body'),
        children=[],
        content_layer=ContentLayer.BODY,
        meta=None,
        label=DocItemLabel.TABLE,
        prov=prov,
        captions=[],
        references=[],
        footnotes=[],
        image=None,
        data=table_data,
        annotations=[],
    )

    return table_item


if __name__ == '__main__':
    # 사용 예: tabula 추출과 연계
    from tabula_table_extractor import extract_tubla_table_with_bbox

    pdf_path = 'noline.pdf'

    table_bbox = (56.00, 207.61000061035156, 515.00, 418.1012878417969)
    page = 7

    raw_df, raw_cell_bboxes = extract_tubla_table_with_bbox(pdf_path=pdf_path, bbox=table_bbox , page=page, stream=True)
    df, cell_bboxes = preprocess_table(raw_df, raw_cell_bboxes)
    # 테이블 아이템 객체 생성
    ti = make_table_item_from_dataframe(df, cell_bboxes, page_no=page, use_df_columns_as_header=True)
    doc = DoclingDocument(name="table", tables=[ti])
    html_table = ti.export_to_html(doc=doc)
    # print("html로 변환된 table:")
    # pprint.pprint(html_table)
    parse_and_print(html_table)