# pdf 경로, 페이지, 좌표 입력하면 html 테이블 -> dict 형 row 추출
import tabula.io as tabula_io
import pandas as pd
from typing import Tuple, List

def _extract_cell_bboxes(tables_json: list) -> list:
    """
    JSON 형식의 테이블을 파싱하여 각 셀의 박스 좌표를 추출합니다.
    Arg:    
        tables_json: tabula JSON 출력 리스트
    Returns:
        cell_bboxes: 셀 박스 좌표 리스트의 2차원 배열. 없으면 [] 반환
    """

    if not tables_json or len(tables_json) == 0:
        return []

    
    # 첫 번째 테이블의 data 필드 가져오기
    cell_data = tables_json[0]['data']
    cell_bboxes = []
    for table_row in cell_data:
        row_collections = []
        for cell in table_row:
            bbox = []
            top, left = cell['top'], cell['left']
            height, width = cell['height'], cell['width']
            if width <= 0 or height <= 0:
                bbox = None
            else:
                bottom, right = top + height, left + width
                bbox = [left, top, right, bottom]

            row_collections.append(bbox)

        cell_bboxes.append(row_collections)


    return cell_bboxes

def _json_to_dataframe(tables_json: list) -> pd.DataFrame:
    """
    JSON 형식의 테이블을 pandas DataFrame으로 변환합니다.
    
    Args:
        tables_json: tabula JSON 출력 리스트
    
    Returns:
        df: pandas DataFrame. 없으면 빈 DataFrame 반환
    """
    if not tables_json or len(tables_json) == 0:
        return pd.DataFrame()
    
    # 첫 번째 테이블의 data 필드 가져오기
    table_data = tables_json[0]['data']
    
    # 각 행의 각 셀에서 text만 추출
    rows = []
    for row in table_data:
        row_texts = []
        for cell in row:
            text = cell.get('text', '')
            row_texts.append(text)
        rows.append(row_texts)
    
    # DataFrame 생성
    if rows:
        df = pd.DataFrame(rows[:])
    else:
        df = pd.DataFrame()
    
    return df

def _extract_json_formatted_table(pdf_path: str, tabula_bbox: Tuple[float, float, float, float], page: int, stream: bool = True) -> Tuple[pd.DataFrame, list]:
    """
    tabula-py를 사용하여 PDF에서 지정한 bbox 영역의 테이블을 JSON 형식으로 추출합니다.
    
    Args:
        pdf_path: PDF 파일 경로
        tabula_bbox: 테이블의 bounding box 좌표 [top, left, bottom, right] (포인트 단위)
        page: 추출할 페이지 번호 (1부터 시작, 기본값: 1)
        stream: True면 stream 모드 사용 (기본값: True)
    
    Returns:
        Tuple[df: pd.DataFrame, bboxes: dict]: pandas DataFrame와 셀 박스 좌표 리스트의 2차원 배열
    """
    tables_json = tabula_io.read_pdf(
        pdf_path,
        pages=page,
        area=tabula_bbox,
        stream=stream,
        output_format="json"
    )

    df = _json_to_dataframe(tables_json)
    cell_bboxes = _extract_cell_bboxes(tables_json)

    return df, cell_bboxes


def CAS_in_table(table: pd.DataFrame) -> int:
    """
    테이블에 "CAS"가 포함되어 있는지 확인하고 해당 열 인덱스를 반환
    각 열을 확인하면서 'CAS'가 포함된 열 찾기. 없으면 0 반환
    
    Args:
        table: DataFrame 형식의 테이블.
    
    Returns:
        col_idx: CAS가 포함된 열 인덱스. 없으면 0 반환
    """
    
    for col_idx in range(table.shape[1]):
        column_values = table.iloc[:, col_idx].astype(str)
        if any('CAS' in str(val) for val in column_values):
            return col_idx  # CAS가 포함된 열 인덱스 반환
    
    return 0  # CAS가 포함된 열이 없으면 0 반환

def preprocess_table(table: pd.DataFrame, cell_bboxes: list) -> Tuple[pd.DataFrame, list]:
    """
    pandas DataFrame을 전처리합니다.
    각 행에 "CAS"라는 단어가 포함되어 있는지 확인합니다.
    
    Args:
        table: DataFrame 형태의 테이블
        cell_bboxes: 셀 박스 좌표 리스트의 2차원 배열
    Returns:
        Tuple[table: DataFrame, cell_bboxes: list]: 전처리된 테이블과 셀 박스 좌표 리스트
    """
    
    def _is_it_mergeable(row: pd.Series, col_idx: int) -> bool:
        """
        해당 행의 특정 열(col_idx)이 비어있거나 NaN인지 확인 (병합 가능한지 확인)
        해당 열의 값이 NaN이거나 빈 문자열이면 True (병합 가능)

        Args:
            row: Series 형식의 행
            col_idx: 열 인덱스
        
        Returns:
            bool: 병합 가능한지 여부
        """
        value = row.iloc[col_idx]
        return pd.isna(value) or str(value).strip() == '' or str(value).strip().lower() == 'nan'
    
    def _is_row_mostly_empty(row: pd.Series) -> bool:
        """한 행에서 한 셀을 제외한 다른 열이 다 비어있거나 NaN인지 확인"""
        non_empty_count = 0
        for col_idx in range(len(row)):
            value = row.iloc[col_idx]
            if pd.notna(value) and str(value).strip() != '' and str(value).strip().lower() != 'nan':
                non_empty_count += 1
        
        # 비어있지 않은 셀이 1개 이하면 병합 가능
        return non_empty_count <= 1
    
    def _is_valid_bbox(bbox: list) -> bool:
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            return False
        try:
            l, t, r, btm = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
        except Exception:
            return False
        return (r > l) and (btm > t)
    
    def _merge_bboxes(bbox1: list, bbox2: list) -> list:
        """두 개의 bbox(l, t, r, b)를 하나로 병합합니다.
        
        Args:
            bbox1: [l1, t1, r1, b1]
            bbox2: [l2, t2, r2, b2]
        
        Returns:
            [l, t, r, b] 또는 None - 병합된 bbox
        """
        has1 = _is_valid_bbox(bbox1)
        has2 = _is_valid_bbox(bbox2)
        if not has1 and not has2:
            return None
        if not has1 and has2:
            return list(map(float, bbox2))
        if has1 and not has2:
            return list(map(float, bbox1))
        l1, t1, r1, b1 = map(float, bbox1)
        l2, t2, r2, b2 = map(float, bbox2)
        return [min(l1, l2), min(t1, t2), max(r1, r2), max(b1, b2)]
    

    def _merge_rows(table: pd.DataFrame, cell_bboxes: list, is_mergeable_func: callable) -> Tuple[pd.DataFrame, list]:
        """
        병합 가능한 행을 윗 행과 병합하는 공통 함수 (DataFrame과 bbox 모두 병합)
        
        Args:
            table: DataFrame 형식의 테이블
            cell_bboxes: 셀 박스 좌표 리스트의 2차원 배열
            is_mergeable_func: 병합 가능한지 확인하는 함수
        
        Returns:
            Tuple[merged_df: DataFrame, merged_bboxes: list]: 병합된 테이블과 셀 박스 좌표 리스트
        """
        # 결과를 저장할 리스트              
        merged_rows = []
        merged_bboxes = []
        
        # bbox 복사 (원본 보존)
        current_bboxes = [row.copy() for row in cell_bboxes] if cell_bboxes else []
        
        # 첫 번째 행은 무조건 추가
        current_row = table.iloc[0].copy()
        merged_rows.append(current_row.copy())
        if current_bboxes and len(current_bboxes) > 0:
            merged_bboxes.append(current_bboxes[0].copy())
        
        # 두 번째 행부터 순회
        for row_idx in range(1, len(table)):
            row = table.iloc[row_idx]
            
            # 병합 가능한지 확인
            if is_mergeable_func(row):
                # 병합 가능한 행이면 윗 행과 병합
                for col_idx, (current_val, new_val) in enumerate(zip(current_row, row)):
                    # DataFrame 값 병합
                    current_val_str = str(current_val) if pd.notna(current_val) else ''
                    new_val_str = str(new_val) if pd.notna(new_val) else ''
                    
                    # 두 값을 공백으로 연결 (둘 다 있을 경우만)
                    if current_val_str and new_val_str:
                        merged_val = f"{current_val_str} {new_val_str}".strip()
                    elif new_val_str:
                        merged_val = new_val_str
                    else:
                        merged_val = current_val_str
                    
                    # 윗 행의 값 업데이트
                    current_row.iloc[col_idx] = merged_val if merged_val else None
                    
                    # bbox 병합 (각 열별로) - _merge_bboxes 헬퍼 함수 사용
                    if current_bboxes and row_idx < len(current_bboxes) and len(merged_bboxes) > 0:
                        # 병합된 행의 현재 bbox
                        current_bbox = merged_bboxes[-1][col_idx] if col_idx < len(merged_bboxes[-1]) else None
                        # 병합할 행의 bbox
                        new_bbox = current_bboxes[row_idx][col_idx] if col_idx < len(current_bboxes[row_idx]) else None
                        
                        merged_bbox = _merge_bboxes(current_bbox, new_bbox)
                        if merged_bbox is not None:
                            merged_bboxes[-1][col_idx] = merged_bbox
                
                # 윗 행 업데이트
                merged_rows[-1] = current_row.copy()
            else:
                # 병합 불가능한 행이면 그대로 추가
                merged_rows.append(row.copy())
                current_row = row.copy()
                if current_bboxes and row_idx < len(current_bboxes):
                    merged_bboxes.append(current_bboxes[row_idx].copy())
        
        # 병합된 DataFrame 생성
        merged_df = pd.DataFrame(merged_rows)
        merged_df.reset_index(drop=True, inplace=True)
        
        return merged_df, merged_bboxes


    cas_col_idx = CAS_in_table(table)
    if cas_col_idx != 0:
        
        # CAS가 없는 행을 윗 행과 병합 (CAS 열을 기준으로 병합 가능 여부 판단)
        is_mergeable = lambda row: _is_it_mergeable(row, cas_col_idx)
        table, cell_bboxes = _merge_rows(table, cell_bboxes, is_mergeable)
        
    else:   

        # CAS가 없는 경우: 한 셀을 제외한 나머지가 다 비어있거나 NaN인 행을 윗 행과 병합
        table, cell_bboxes = _merge_rows(table, cell_bboxes, _is_row_mostly_empty)
        

    return table, cell_bboxes

def extract_tubla_table_with_bbox(pdf_path: str, bbox: Tuple[float, float, float, float], page: int, stream: bool = True) -> Tuple[pd.DataFrame, list]:
    """
    tabula-py를 사용하여 PDF에서 지정한 bbox 영역의 테이블을 추출합니다.

    Args:
        pdf_path: PDF 파일 경로
        bbox: bounding box 좌표 [top, left, bottom, right] (포인트 단위)
              또는 [y1, x1, y2, x2] 형식
        page: 추출할 페이지 번호 (1부터 시작, 기본값: 1)
        stream: True면 stream 모드 사용 (기본값: True)

    Returns:
        Tuple[df: DataFrame, cell_bboxes: list]: pandas DataFrame와 셀 박스 좌표 리스트의 2차원 배열
    """

    # tabula에 맞는 bbox 형식으로 변환
    left, top, right, bottom = bbox
    tabula_bbox = [top, left, bottom, right]


    df, cell_bboxes = _extract_json_formatted_table(pdf_path, tabula_bbox, page, stream)

    return df, cell_bboxes


def extract_multiple_tables_batch(
    pdf_path: str,
    page: int,
    bboxes: List[Tuple[float, float, float, float]],
    stream: bool = True
) -> List[Tuple[pd.DataFrame, list]]:
    """
    같은 페이지의 여러 테이블을 한 번에 추출 (PDF를 한 번만 로드)

    Args:
        pdf_path: PDF 파일 경로
        page: 페이지 번호 (1부터 시작)
        bboxes: 여러 bbox 리스트 [(l,t,r,b), (l,t,r,b), ...]
        stream: True면 stream 모드 사용

    Returns:
        [(DataFrame, cell_bboxes), (DataFrame, cell_bboxes), ...]
    """
    # bbox를 tabula 형식으로 변환: (l,t,r,b) -> [t,l,b,r]
    tabula_bboxes = []
    for left, top, right, bottom in bboxes:
        tabula_bboxes.append([top, left, bottom, right])

    # 한 번에 여러 영역 추출
    tables_json_list = tabula_io.read_pdf(
        pdf_path,
        pages=page,
        area=tabula_bboxes,  # 리스트로 전달하면 여러 영역을 한 번에 처리
        stream=stream,
        output_format="json"
    )

    # 결과 파싱
    # tabula가 여러 area를 처리하면 각 area마다 하나의 dict를 리스트로 반환
    results = []

    if not tables_json_list:
        # 빈 결과: 모든 bbox에 대해 빈 DataFrame 반환
        for _ in bboxes:
            results.append((pd.DataFrame(), []))
    else:
        # tables_json_list가 리스트인 경우, 각 항목이 dict
        for tables_json in tables_json_list:
            # tables_json은 단일 dict 형태
            if isinstance(tables_json, dict):
                # dict를 리스트로 감싸서 _json_to_dataframe에 전달
                df = _json_to_dataframe([tables_json])
                cell_bboxes = _extract_cell_bboxes([tables_json])
            else:
                df = pd.DataFrame()
                cell_bboxes = []
            results.append((df, cell_bboxes))

    return results



def convert_to_html(table: pd.DataFrame) -> str:
    """
    pandas DataFrame을 HTML로 변환합니다.
    extract_to_html 함수 사용 전 시험용으로 사용해 본 함수입니다.
    Args:
        table: pandas DataFrame
    
    Returns:
        HTML 문자열
    """
    # pandas DataFrame의 to_html() 메서드 사용
    html = table.to_html(index=False, escape=False)
    return html

# 사용 예제
if __name__ == "__main__":
    # PDF 파일 경로 설정
    pdf_file = "noline.pdf"  # 실제 PDF 파일 경로로 변경하세요
    

    print("\n" + "="*60 + "\n")
    
    # # promtree에서 추출한 좌표s
    # bbox = (53.3, 581.4, 415.9, 732.5)
    bbox = (56.00, 207.61000061035156, 515.00, 418.1012878417969)
    
    table, cell_bboxes = extract_tubla_table_with_bbox(pdf_path=pdf_file, bbox=bbox, page=7, stream=True)

    print("\n" + "="*60 + "\n")

    p_table, merged_bboxes = preprocess_table(table, cell_bboxes)

    print("\n" + "="*60 + "\n")

    # html = convert_to_html(p_table)
    # pprint.pprint(html)
    # parse_and_print(html)

