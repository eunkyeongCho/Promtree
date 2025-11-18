"""
html2row.py와 유사한 기능을 수행하는 모듈입니다.
단, MD가 아닌 str로 구성된 html을 직접 입력받습니다.
또한 output이 dict가 아닌 List[str] 형태로 반환됩니다.
"""

from bs4 import BeautifulSoup
from typing import List, Dict
import json
import re


def parse_html_table(html_table: str) -> List[str]:
    """
    HTML 테이블 문자열을 행별 JSON 문자열 리스트로 변환

    Args:
        html_table: <table>로 시작하는 HTML 문자열

    Returns:
        List[str]: 각 행이 JSON 문자열인 리스트

    Example:
        >>> html = '<table><tr><th>이름</th><th>나이</th></tr><tr><td>홍길동</td><td>30</td></tr></table>'
        >>> result = parse_html_table(html)
        >>> print(result)
        ['{"이름": "홍길동", "나이": "30"}']
    """
    try:
        soup = BeautifulSoup(html_table.strip(), 'html.parser')
        table = soup.find('table')

        if not table:
            return []

        # 1. 행 헤더 테이블인지 확인 (첫 열이 th인 경우)
        if _is_row_header_table(table):
            rows = _extract_row_header_data(table)
        else:
            # 2. 헤더 추출
            headers = _extract_headers(table)

            if not headers:
                # 특수 케이스: thead/th가 없고 모든 행이 2열(td)인 경우 → key-value로 처리
                if _is_two_col_no_header(table):
                    rows = _extract_key_value_rows(table)
                else:
                    # 그 외: 첫 번째 행을 기준으로 자동 헤더 생성
                    headers = _fallback_headers(table)
                    rows = _extract_data_rows(table, headers)
            else:
                # 3. 데이터 행 추출
                rows = _extract_data_rows(table, headers)

        # 각 행을 JSON 문자열로 변환
        result = []
        for row in rows:
            result.append(json.dumps(row, ensure_ascii=False))

        return result

    except Exception as e:
        print(f"⚠️ 파싱 실패: {e}")
        return []


def _extract_headers(table) -> List[str]:
    """헤더 추출 (thead 또는 첫 번째 tr에서)"""
    thead = table.find('thead')

    if thead:
        # thead가 있는 경우
        header_rows = thead.find_all('tr')

        if len(header_rows) == 1:
            # 단일 헤더
            return _parse_single_header(header_rows[0])
        elif len(header_rows) > 1:
            # 다중 헤더 (이중, 삼중 등)
            return _parse_multi_headers(header_rows)
    else:
        # thead 없으면 테이블 상단의 연속된 th-only 행들을 헤더로 간주
        all_trs = table.find_all('tr')
        header_rows = []
        for tr in all_trs:
            cells = tr.find_all(['th', 'td'])
            if cells and all(cell.name == 'th' for cell in cells):
                header_rows.append(tr)
            else:
                break

        if len(header_rows) == 1:
            return _parse_single_header(header_rows[0])
        elif len(header_rows) > 1:
            return _parse_multi_headers(header_rows)

    return []


def _parse_single_header(tr) -> List[str]:
    """단일 헤더 행 파싱"""
    headers = []

    for cell in tr.find_all(['th', 'td']):
        text = _clean_text(cell.get_text())
        colspan = int(cell.get('colspan', 1))

        # colspan만큼 헤더 복제
        for _ in range(colspan):
            headers.append(text)

    return headers


def _parse_multi_headers(header_rows: List) -> List[str]:
    """
    다중 헤더 파싱 (이중, 삼중 등)
    복잡한 rowspan/colspan 조합 처리
    """
    # 헤더를 2D 그리드로 구성
    max_cols = 0
    for tr in header_rows:
        cols = sum(int(cell.get('colspan', 1)) for cell in tr.find_all(['th', 'td']))
        max_cols = max(max_cols, cols)

    # 그리드 초기화
    grid = [[None for _ in range(max_cols)] for _ in range(len(header_rows))]

    # 각 행을 순회하며 그리드 채우기
    for row_idx, tr in enumerate(header_rows):
        col_idx = 0

        for cell in tr.find_all(['th', 'td']):
            # 이미 채워진 셀 건너뛰기 (rowspan에 의해)
            while col_idx < max_cols and grid[row_idx][col_idx] is not None:
                col_idx += 1

            if col_idx >= max_cols:
                break

            text = _clean_text(cell.get_text())
            rowspan = int(cell.get('rowspan', 1))
            colspan = int(cell.get('colspan', 1))

            # 그리드에 값 채우기 (rowspan, colspan 고려)
            for r in range(rowspan):
                for c in range(colspan):
                    if row_idx + r < len(grid) and col_idx + c < max_cols:
                        grid[row_idx + r][col_idx + c] = text

            col_idx += colspan

    # 그리드를 헤더 리스트로 변환 (계층 구조 유지)
    headers = []
    for col_idx in range(max_cols):
        header_parts = []
        last_non_empty = None
        for row_idx in range(len(grid)):
            value = grid[row_idx][col_idx]
            if value is None or value == "":
                header_parts.append("")
            elif last_non_empty is not None and value == last_non_empty:
                # 헤더의 rowspan에 의해 반복된 텍스트는 비워서 중복을 줄임
                header_parts.append("")
            else:
                header_parts.append(value)
                last_non_empty = value

        # 모든 비어있지 않은 값이 동일한 하나의 토큰인 경우, 우측 정렬([,,항목])로 표기
        non_empty_tokens = [p for p in header_parts if p]
        if non_empty_tokens:
            unique_tokens = set(non_empty_tokens)
            if len(unique_tokens) == 1 and len(header_parts) > 1:
                token = non_empty_tokens[-1]
                header_parts = [""] * len(header_parts)
                header_parts[-1] = token

        # 계층 헤더를 [상위, 하위] 형식으로 (빈 값은 공란으로 유지)
        if len(header_parts) > 1:
            headers.append(f"[{', '.join(header_parts)}]")
        else:
            headers.append(header_parts[0] if header_parts else "")

    return headers


def _fallback_headers(table) -> List[str]:
    """헤더를 찾을 수 없을 때 자동 생성"""
    first_tr = table.find('tr')

    if first_tr:
        # 첫 번째 행의 셀 개수만큼 "col_0", "col_1", ... 생성
        cell_count = len(first_tr.find_all(['td', 'th']))
        return [f"col_{i}" for i in range(cell_count)]

    return []


def _is_row_header_table(table) -> bool:
    """
    각 행의 첫 열이 th이고 나머지가 td인 테이블인지 판별
    (행 헤더 테이블)
    """
    tbody = table.find('tbody')
    trs = tbody.find_all('tr') if tbody else table.find_all('tr')

    if not trs:
        return False

    # thead가 있는 경우 제외
    thead = table.find('thead')
    if thead:
        thead_trs = thead.find_all('tr')
        trs = [tr for tr in trs if tr not in thead_trs]

    # 적어도 2개 이상의 행이 있어야 함
    if len(trs) < 2:
        return False

    # 각 행의 첫 셀이 th이고 나머지가 td인지 확인
    row_header_count = 0
    for tr in trs:
        cells = tr.find_all(['th', 'td'])
        if not cells:
            continue

        # 첫 셀이 th이고, 나머지에 td가 있는 경우
        if cells[0].name == 'th' and len(cells) > 1:
            has_td = any(cell.name == 'td' for cell in cells[1:])
            if has_td:
                row_header_count += 1

    # 전체 행의 절반 이상이 이 패턴이면 행 헤더 테이블로 판단
    return row_header_count >= len(trs) // 2


def _extract_row_header_data(table) -> List[Dict[str, str]]:
    """
    행 헤더 테이블 추출: wide format을 long format으로 변환

    예:
    <tr><th>이름</th><td>홍길동</td><td>김철수</td></tr>
    <tr><th>나이</th><td>30</td><td>25</td></tr>
    →
    [
      {"이름": "홍길동", "나이": "30"},
      {"이름": "김철수", "나이": "25"}
    ]
    """
    # 데이터 행 추출
    tbody = table.find('tbody')
    trs = tbody.find_all('tr') if tbody else table.find_all('tr')

    # thead 행 제외
    thead = table.find('thead')
    if thead:
        thead_trs = thead.find_all('tr')
        trs = [tr for tr in trs if tr not in thead_trs]

    if not trs:
        return []

    # 각 행의 데이터를 수집 (행 헤더 : [값1, 값2, ...])
    row_data = {}  # {row_header: [values]}
    max_cols = 0

    for tr in trs:
        cells = tr.find_all(['th', 'td'])
        if not cells or cells[0].name != 'th':
            continue

        row_header = _clean_text(cells[0].get_text())
        values = []

        for cell in cells[1:]:
            if cell.name == 'td':
                value = _clean_text(cell.get_text())
                values.append(value)

        if values:
            row_data[row_header] = values
            max_cols = max(max_cols, len(values))

    # wide format → long format 변환
    # 각 열(column)을 하나의 행(row)으로
    results = []
    for col_idx in range(max_cols):
        row_dict = {}
        for row_header, values in row_data.items():
            if col_idx < len(values):
                value = values[col_idx]
                if value.strip():
                    row_dict[row_header] = value
                else:
                    row_dict[row_header] = ""
            else:
                row_dict[row_header] = ""

        # 빈 행이 아니면 추가
        if any(v.strip() for v in row_dict.values()):
            results.append(row_dict)

    return results


def _is_two_col_no_header(table) -> bool:
    """
    thead도 없고 th도 없으며, 모든 데이터 행이 2개의 td로만 구성된 경우인지 판별
    """
    if table.find('thead') is not None:
        return False
    if table.find('th') is not None:
        return False

    # tbody 우선
    tbody = table.find('tbody')
    trs = tbody.find_all('tr') if tbody else table.find_all('tr')
    if not trs:
        return False

    # 적어도 한 행은 2열이어야 하고, 2열이 아닌 행이 있으면 특수 케이스 아님
    saw_two = False
    for tr in trs:
        tds = tr.find_all('td')
        ths = tr.find_all('th')
        if ths:
            return False
        if not tds:
            continue
        if len(tds) != 2:
            return False
        saw_two = True
    return saw_two


def _extract_key_value_rows(table) -> List[Dict[str, str]]:
    """
    2열 key-value 테이블을 {첫번째셀: 두번째셀} 형태로 추출
    """
    tbody = table.find('tbody')
    trs = tbody.find_all('tr') if tbody else table.find_all('tr')
    results: List[Dict[str, str]] = []
    for tr in trs:
        tds = tr.find_all('td')
        if len(tds) >= 2:
            key = _clean_text(tds[0].get_text())
            value = _clean_text(tds[1].get_text())
            if key or value:
                results.append({key: value})
    return results


def _extract_data_rows(table, headers: List[str]) -> List[Dict[str, str]]:
    """
    데이터 행 추출 (rowspan 처리 포함)
    """
    # tbody가 있으면 tbody에서, 없으면 table에서 직접
    tbody = table.find('tbody')

    if tbody:
        # tbody 내에서도 선두의 th-only 행들은 헤더로 간주하여 스킵
        tbody_trs = tbody.find_all('tr')
        header_count = 0
        for tr in tbody_trs:
            cells = tr.find_all(['th', 'td'])
            if cells and all(cell.name == 'th' for cell in cells):
                header_count += 1
            else:
                break
        data_trs = tbody_trs[header_count:]
    else:
        # thead가 있으면 제외
        thead = table.find('thead')
        all_trs = table.find_all('tr')

        if thead:
            thead_trs = thead.find_all('tr')
            data_trs = [tr for tr in all_trs if tr not in thead_trs]
        else:
            # 상단의 연속된 th-only 헤더 행들 모두 제외
            header_count = 0
            for tr in all_trs:
                cells = tr.find_all(['th', 'td'])
                if cells and all(cell.name == 'th' for cell in cells):
                    header_count += 1
                else:
                    break
            data_trs = all_trs[header_count:] if header_count > 0 else all_trs

    # rowspan 추적을 위한 딕셔너리
    pending_rowspans = {}  # {col_idx: (value, remaining_rows)}

    results = []

    for tr in data_trs:
        cells = tr.find_all(['td', 'th'])
        row_dict = {}

        col_idx = 0
        cell_idx = 0

        while col_idx < len(headers):
            # rowspan으로 이전 행에서 이어지는 값 확인
            if col_idx in pending_rowspans:
                value, remaining = pending_rowspans[col_idx]
                row_dict[headers[col_idx]] = value

                if remaining > 1:
                    pending_rowspans[col_idx] = (value, remaining - 1)
                else:
                    del pending_rowspans[col_idx]

                col_idx += 1
                continue

            # 현재 셀 처리
            if cell_idx < len(cells):
                cell = cells[cell_idx]
                value = _clean_text(cell.get_text())

                # rowspan 처리
                rowspan = int(cell.get('rowspan', 1))
                if rowspan > 1:
                    pending_rowspans[col_idx] = (value, rowspan - 1)

                # colspan 처리
                colspan = int(cell.get('colspan', 1))
                for i in range(colspan):
                    if col_idx + i < len(headers):
                        row_dict[headers[col_idx + i]] = value

                col_idx += colspan
                cell_idx += 1
            else:
                # 셀이 부족하면 빈 문자열
                if col_idx < len(headers):
                    row_dict[headers[col_idx]] = ""
                col_idx += 1

        # 빈 행은 제외
        if any(v.strip() for v in row_dict.values()):
            results.append(row_dict)

    return results


def _clean_text(text: str) -> str:
    """
    텍스트 정리 (공백, 줄바꿈 제거)
    """
    # 여러 공백을 하나로
    text = re.sub(r'\s+', ' ', text)
    # 앞뒤 공백 제거
    text = text.strip()
    return text


# =====================================================================
# 테스트 케이스
# =====================================================================

if __name__ == "__main__":
    import sys

    def print_usage() -> None:
        print("사용법:")
        print("  python unpivot.py -ex               # 내장 예제 파싱 실행")
        print("  python unpivot.py <html_파일경로>   # 파일의 모든 테이블 파싱 후 출력")
        print("  python unpivot.py -h | --help       # 도움말 표시")
        print("")

    def parse_and_print(html_table: str) -> None:
        """테이블 파싱 후 결과를 보기 좋게 출력"""
        rows = parse_html_table(html_table)

        if rows:
            print(f"✅ {len(rows)}개 행 추출:")
            for i, row_str in enumerate(rows, 1):
                if i == len(rows):  # 마지막 행
                    print(row_str)
                else:
                    print(f"{row_str},")
        else:
            print("❌ 추출 실패 또는 빈 테이블")

    if len(sys.argv) == 1:
        print_usage()
    else:
        cmd = sys.argv[1]
        if cmd in ("-h", "--help"):
            print_usage()
        elif cmd in ("-ex", "--ex"):
            print("=" * 80)
            print("HTML 테이블 Unpivot 파서 - Examples")
            print("=" * 80)

            test_cases = [
                ("1. 기본 테이블", """
                <table>
                  <thead>
                    <tr><th>이름</th><th>나이</th></tr>
                  </thead>
                  <tbody>
                    <tr><td>홍길동</td><td>30</td></tr>
                    <tr><td>김철수</td><td>25</td></tr>
                  </tbody>
                </table>
                """),
                ("2. rowspan 테이블", """
                <table>
                  <tr><th>구분</th><th>항목</th><th>값</th></tr>
                  <tr><td rowspan="2">그룹A</td><td>항목1</td><td>100</td></tr>
                  <tr><td>항목2</td><td>200</td></tr>
                </table>
                """),
                ("3. colspan 테이블", """
                <table>
                  <tr><th>항목</th><th colspan="2">측정값</th></tr>
                  <tr><th>온도</th><th>최소</th><th>최대</th></tr>
                  <tr><td>실내</td><td>18</td><td>26</td></tr>
                </table>
                """),
                ("4. 이중 헤더", """
                <table>
                  <thead>
                    <tr>
                      <th rowspan="2">구분</th>
                      <th colspan="2">값</th>
                    </tr>
                    <tr>
                      <th>최소</th>
                      <th>최대</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr><td>온도</td><td>0</td><td>100</td></tr>
                  </tbody>
                </table>
                """),
                ("5. thead 없는 테이블", """
                <table>
                  <tr><th>A</th><th>B</th></tr>
                  <tr><td>1</td><td>2</td></tr>
                </table>
                """),
                ("6. 완전히 빈 헤더 (자동 생성)", """
                <table>
                  <tr><td>값1</td><td>값2</td></tr>
                  <tr><td>값3</td><td>값4</td></tr>
                </table>
                """),
                ("7. 복잡한 rowspan + colspan", """
                <table>
                  <thead>
                    <tr>
                      <th rowspan="3">항목</th>
                      <th colspan="4">측정값</th>
                    </tr>
                    <tr>
                      <th colspan="2">실내</th>
                      <th colspan="2">실외</th>
                    </tr>
                    <tr>
                      <th>최소</th><th>최대</th>
                      <th>최소</th><th>최대</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr><td>온도</td><td>18</td><td>26</td><td>-10</td><td>35</td></tr>
                    <tr><td>습도</td><td>30</td><td>70</td><td>0</td><td>100</td></tr>
                  </tbody>
                </table>
                """),
                ("8. 빈 셀 포함", """
                <table>
                  <tr><th>A</th><th>B</th><th>C</th></tr>
                  <tr><td>1</td><td></td><td>3</td></tr>
                  <tr><td></td><td>2</td><td></td></tr>
                </table>
                """),
                ("9. 행 헤더 테이블 (첫 열이 th)", """
                <table>
                  <tr><th>이름</th><td>홍길동</td><td>김철수</td></tr>
                  <tr><th>나이</th><td>30</td><td>25</td></tr>
                  <tr><th>직업</th><td>개발자</td><td>디자이너</td></tr>
                </table>
                """),
            ]

            for title, html in test_cases:
                print(f"\n{title}")
                print("-" * 80)
                parse_and_print(html)

            print("\n" + "=" * 80)
            print("모든 테스트 완료!")
            print("=" * 80)
        else:
            # 파일 처리
            try:
                with open(cmd, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                print(f"파일을 열 수 없습니다: {e}")
            else:
                soup = BeautifulSoup(content, "html.parser")
                tables = soup.find_all("table")
                if not tables:
                    print("[1] 테이블 (직접 파싱 시도)")
                    print("-" * 80)
                    parse_and_print(content)
                else:
                    for i, tbl in enumerate(tables, 1):
                        print(f"\n[{i}] 테이블")
                        print("-" * 80)
                        parse_and_print(str(tbl))
