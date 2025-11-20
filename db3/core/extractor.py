"""
[핵심] 물성 추출기 (Extractor)

역할:
- 정규식 기반 패턴 매칭으로 TDS 마크다운에서 물성 추출
- properties_dict.py 정의된 23개 물성 자동 추출
- 값(숫자)과 단위 분리 추출

주요 함수:
    extract_property_from_text(text, property_key)  → 특정 물성 1개 추출
    detect_all_properties(markdown_text)            → 모든 물성 추출

추출 패턴:
    - "Tg: 150 ℃"           (콜론 형식)
    - "Tg 150 ℃"            (공백 형식)
    - "Tg (유리전이온도): 150℃"  (설명 포함)

특징:
    - 한글/영문 이름 모두 인식
    - 단위 자동 파싱 (%, ℃, MPa, GPa 등)
    - 중복 제거 (같은 물성 여러 번 나와도 첫 번째만)
"""

import re
from typing import List, Dict, Optional
from properties_dict import PROPERTY_PATTERNS, add_dynamic_property
from html.parser import HTMLParser


class TableParser(HTMLParser):
    """HTML 테이블 파싱 클래스"""
    def __init__(self):
        super().__init__()
        self.tables = []
        self.current_table = []
        self.current_row = []
        self.current_cell = []
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.cell_attrs = {}

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == 'table':
            self.in_table = True
            self.current_table = []
        elif tag == 'tr' and self.in_table:
            self.in_row = True
            self.current_row = []
        elif tag in ['td', 'th'] and self.in_row:
            self.in_cell = True
            self.current_cell = []
            self.cell_attrs = attrs_dict

    def handle_endtag(self, tag):
        if tag == 'table':
            self.tables.append(self.current_table)
            self.in_table = False
        elif tag == 'tr':
            if self.current_row:
                self.current_table.append(self.current_row)
            self.in_row = False
        elif tag in ['td', 'th']:
            cell_text = ''.join(self.current_cell).strip()
            colspan = int(self.cell_attrs.get('colspan', 1))
            self.current_row.append({
                'text': cell_text,
                'colspan': colspan,
                'tag': tag
            })
            self.in_cell = False

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell.append(data)


def extract_from_table(table_html: str) -> List[Dict]:
    """
    HTML 테이블에서 물성 추출 (colspan 처리 개선)

    Args:
        table_html: HTML 테이블 문자열

    Returns:
        추출된 물성 정보 리스트
    """
    parser = TableParser()
    parser.feed(table_html)

    extracted = []

    for table in parser.tables:
        if len(table) < 2:
            continue

        # colspan을 고려해서 행을 확장
        def expand_row(row):
            """colspan을 고려해서 셀을 복제"""
            expanded = []
            for cell in row:
                expanded.append(cell)
                # colspan > 1이면 빈 셀 추가
                for _ in range(cell['colspan'] - 1):
                    expanded.append({'text': '', 'colspan': 1, 'tag': cell['tag'], 'merged': True})
            return expanded

        # 모든 행 확장
        expanded_table = [expand_row(row) for row in table]

        # 헤더 행과 데이터 행 분리
        header_rows = []
        data_rows = []

        for row in expanded_table:
            th_count = sum(1 for cell in row if cell['tag'] == 'th' and cell['text'])
            if th_count > 0:  # th가 하나라도 있으면 헤더
                header_rows.append(row)
            else:
                data_rows.append(row)

        if not header_rows or not data_rows:
            continue

        # 최대 컬럼 수 계산
        max_cols = max(len(row) for row in expanded_table)

        # 각 컬럼의 정보 수집 (이름 + 단위)
        column_info = []
        for col_idx in range(max_cols):
            col_names = []
            col_units = []

            for header_row in header_rows:
                if col_idx < len(header_row):
                    cell = header_row[col_idx]
                    text = cell['text'].strip()

                    if not text or cell.get('merged'):
                        continue

                    # 단위 패턴 확인
                    unit_patterns = ['℃', '°C', 'mm', 'μm', '㎜', 'Kg/25mm', 'kg/25mm', 'N/25mm', 'MPa', 'GPa']
                    is_unit = any(unit in text for unit in unit_patterns)

                    if is_unit:
                        col_units.append(text)
                    else:
                        col_names.append(text)

            column_info.append({
                'names': col_names,
                'units': col_units
            })

        # 데이터 행에서 물성 추출
        for data_row in data_rows:
            for col_idx, cell in enumerate(data_row):
                if col_idx >= len(column_info):
                    continue

                col = column_info[col_idx]
                value_text = cell['text'].strip()

                # 숫자 값 파싱
                value_match = re.search(r'(\d+\.?\d*)', value_text)
                if not value_match:
                    continue

                value = float(value_match.group(1))

                # 물성명 매칭
                for property_key, prop_info in PROPERTY_PATTERNS.items():
                    for prop_name in prop_info['names']:
                        # 컬럼명과 물성명 매칭
                        if any(prop_name in col_name for col_name in col['names']):
                            # 단위 확인
                            unit = col['units'][0] if col['units'] else ''

                            extracted.append({
                                'property': property_key,
                                'value': value,
                                'unit': unit,
                                'matched_name': prop_name,
                                'pattern': 'table'
                            })
                            break

    return extracted


def extract_property_from_text(text: str, property_key: str) -> Optional[Dict]:
    """
    텍스트에서 특정 물성 추출

    Args:
        text: Markdown 텍스트
        property_key: 물성 키 (예: 'Tg', 'Tm')

    Returns:
        추출된 물성 정보 dict 또는 None
    """
    if property_key not in PROPERTY_PATTERNS:
        return None

    prop = PROPERTY_PATTERNS[property_key]

    # 모든 가능한 이름으로 검색
    for name in prop['names']:
        # 다양한 패턴 시도
        patterns = [
            # "Tg: 150 ℃" 또는 "Tg : 150℃"
            rf'{re.escape(name)}\s*[:：=]\s*([0-9.]+)\s*([^\s\n,;]+)?',
            # "Tg 150 ℃" (콜론 없음)
            rf'{re.escape(name)}\s+([0-9.]+)\s*([^\s\n,;]+)?',
            # "Tg(℃): 150" 또는 "Tg (유리전이온도): 150℃"
            rf'{re.escape(name)}\s*\([^)]*\)\s*[:：=]?\s*([0-9.]+)\s*([^\s\n,;]+)?',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            if matches:
                # 첫 번째 매치 사용
                match = matches[0]

                # 값과 단위 파싱
                if len(match) >= 1:
                    value_str = match[0]
                    unit = match[1] if len(match) > 1 else ''

                    # 단위 정리 (앞뒤 공백, 특수문자 제거)
                    unit = unit.strip()
                    if unit and not any(c.isalnum() or c in ['/', '·', '²', '³', '°', '℃', '%'] for c in unit):
                        unit = ''

                    try:
                        value = float(value_str)

                        return {
                            'property': property_key,
                            'value': value,
                            'unit': unit,
                            'matched_name': name,
                            'pattern': pattern
                        }
                    except ValueError:
                        continue

    return None


def detect_all_properties(markdown_text: str) -> List[Dict]:
    """
    Markdown에서 모든 물성 정보 추출

    Args:
        markdown_text: Markdown 문서 내용

    Returns:
        추출된 물성 정보 리스트
    """
    detected_properties = []

    # 1. HTML 테이블에서 추출
    table_pattern = r'<table>.*?</table>'
    table_matches = re.findall(table_pattern, markdown_text, re.DOTALL | re.IGNORECASE)

    for table_html in table_matches:
        table_props = extract_from_table(table_html)
        detected_properties.extend(table_props)

    # 2. 일반 텍스트에서 추출 (테이블에서 이미 추출된 물성 제외)
    extracted_keys = set(p['property'] for p in detected_properties)

    for property_key in PROPERTY_PATTERNS.keys():
        if property_key not in extracted_keys:
            result = extract_property_from_text(markdown_text, property_key)
            if result:
                detected_properties.append(result)

    return detected_properties


def detect_unknown_properties(markdown_text: str, detected_properties: List[Dict]) -> List[Dict]:
    """
    미등록 물성 자동 감지
    "항목명: 숫자 단위" 패턴 중 아직 매칭 안 된 것 찾기

    Args:
        markdown_text: Markdown 문서 내용
        detected_properties: 이미 감지된 물성 리스트

    Returns:
        새로 발견된 물성 리스트
    """
    # 이미 매칭된 항목명
    matched_names = set()
    for prop in detected_properties:
        matched_names.add(prop['matched_name'])

    # 일반적인 패턴으로 전체 스캔
    generic_pattern = r'([A-Za-z가-힣][A-Za-z가-힣\s]+?)\s*[:：=]\s*([0-9.]+)\s*([A-Za-z/²³·℃°%]+)?'
    matches = re.findall(generic_pattern, markdown_text, re.MULTILINE)

    unknown_props = []
    for name, value, unit in matches:
        name = name.strip()

        # 이미 매칭됐으면 skip
        if name in matched_names:
            continue

        # 너무 긴 이름 제외 (문장일 가능성)
        if len(name) > 50:
            continue

        try:
            unknown_props.append({
                'property': f'Unknown_{name.replace(" ", "_")}',
                'value': float(value),
                'unit': unit.strip() if unit else '',
                'matched_name': name,
                'pattern': 'generic'
            })
        except ValueError:
            continue

    return unknown_props


def extract_with_context(markdown_text: str, include_unknown: bool = False) -> Dict:
    """
    문맥 정보 포함한 전체 추출

    Args:
        markdown_text: Markdown 문서 내용
        include_unknown: 미등록 물성도 포함할지 여부

    Returns:
        추출 결과 dict
    """
    # 정의된 물성 추출
    detected = detect_all_properties(markdown_text)

    # 미등록 물성 추출 (옵션)
    unknown = []
    if include_unknown:
        unknown = detect_unknown_properties(markdown_text, detected)

    return {
        'detected_properties': detected,
        'unknown_properties': unknown,
        'total_count': len(detected) + len(unknown)
    }


if __name__ == "__main__":
    # 테스트
    sample_text = """
    # 소재 물성 정보

    Tg: 150 ℃
    Tm (용융온도): 180°C
    항복강도(YS): 500 MPa
    DC (유전상수) = 3.5
    영률: 2.5 GPa
    He투과율: 15.2 cm³/m²

    새로운속성: 123 units
    """

    print("=" * 50)
    print("물성 추출 테스트")
    print("=" * 50)

    result = extract_with_context(sample_text, include_unknown=True)

    print(f"\n✅ 정의된 물성: {len(result['detected_properties'])}개")
    for prop in result['detected_properties']:
        print(f"  - {prop['property']}: {prop['value']} {prop['unit']} (매칭: {prop['matched_name']})")

    print(f"\n❓ 미등록 물성: {len(result['unknown_properties'])}개")
    for prop in result['unknown_properties']:
        print(f"  - {prop['property']}: {prop['value']} {prop['unit']}")
