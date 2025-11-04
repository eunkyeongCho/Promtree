"""
최종 완성판: HTML 테이블 → 행별 딕셔너리 변환기
모든 예외 상황 고려 (rowspan, colspan, 이중헤더, 빈 셀, 중첩, 등)
"""

from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Tuple
import json
import re


class FinalTableParser:
    """
    HTML 테이블을 행별 딕셔너리로 변환 (모든 예외 처리)
    """
    
    def __init__(self, html_table: str):
        """
        Args:
            html_table: <table>로 시작하는 HTML 문자열
        """
        self.html = html_table.strip()
        self.soup = BeautifulSoup(self.html, 'html.parser')
        self.table = self.soup.find('table')
        
        if not self.table:
            raise ValueError("유효한 <table> 태그를 찾을 수 없습니다")
    
    def parse(self) -> List[Dict[str, str]]:
        """
        테이블을 행별 딕셔너리 리스트로 변환

        Returns:
            List[Dict]: [{"컬럼1": "값1", ...}, {...}, ...]
        """
        try:
            # 1. 행 헤더 테이블인지 확인 (첫 열이 th인 경우)
            if self._is_row_header_table():
                return self._extract_row_header_data()

            # 2. 헤더 추출
            headers = self._extract_headers()

            if not headers:
                # 특수 케이스: thead/th가 없고 모든 행이 2열(td)인 경우 → key-value로 처리
                if self._is_two_col_no_header():
                    return self._extract_key_value_rows()
                # 그 외: 첫 번째 행을 기준으로 자동 헤더 생성
                headers = self._fallback_headers()

            # 3. 데이터 행 추출
            data_rows = self._extract_data_rows(headers)

            return data_rows

        except Exception as e:
            # 모든 예외를 잡아서 빈 리스트 반환
            print(f"⚠️ 파싱 실패: {e}")
            return []
    
    def _extract_headers(self) -> List[str]:
        """
        헤더 추출 (thead 또는 첫 번째 tr에서)
        """
        thead = self.table.find('thead')
        
        if thead:
            # thead가 있는 경우
            header_rows = thead.find_all('tr')
            
            if len(header_rows) == 1:
                # 단일 헤더
                return self._parse_single_header(header_rows[0])
            elif len(header_rows) > 1:
                # 다중 헤더 (이중, 삼중 등)
                return self._parse_multi_headers(header_rows)
        else:
            # thead 없으면 테이블 상단의 연속된 th-only 행들을 헤더로 간주
            all_trs = self.table.find_all('tr')
            header_rows = []
            for tr in all_trs:
                cells = tr.find_all(['th', 'td'])
                if cells and all(cell.name == 'th' for cell in cells):
                    header_rows.append(tr)
                else:
                    break

            if len(header_rows) == 1:
                return self._parse_single_header(header_rows[0])
            elif len(header_rows) > 1:
                return self._parse_multi_headers(header_rows)
        
        return []
    
    def _parse_single_header(self, tr) -> List[str]:
        """단일 헤더 행 파싱"""
        headers = []
        
        for cell in tr.find_all(['th', 'td']):
            text = self._clean_text(cell.get_text())
            colspan = int(cell.get('colspan', 1))
            
            # colspan만큼 헤더 복제
            for _ in range(colspan):
                headers.append(text)
        
        return headers
    
    def _parse_multi_headers(self, header_rows: List) -> List[str]:
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
                
                text = self._clean_text(cell.get_text())
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
    
    def _fallback_headers(self) -> List[str]:
        """
        헤더를 찾을 수 없을 때 자동 생성
        """
        first_tr = self.table.find('tr')
        
        if first_tr:
            # 첫 번째 행의 셀 개수만큼 "col_0", "col_1", ... 생성
            cell_count = len(first_tr.find_all(['td', 'th']))
            return [f"col_{i}" for i in range(cell_count)]
        
        return []

    def _is_row_header_table(self) -> bool:
        """
        각 행의 첫 열이 th이고 나머지가 td인 테이블인지 판별
        (행 헤더 테이블)
        """
        tbody = self.table.find('tbody')
        trs = tbody.find_all('tr') if tbody else self.table.find_all('tr')

        if not trs:
            return False

        # thead가 있는 경우 제외
        thead = self.table.find('thead')
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

    def _extract_row_header_data(self) -> List[Dict[str, str]]:
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
        tbody = self.table.find('tbody')
        trs = tbody.find_all('tr') if tbody else self.table.find_all('tr')

        # thead 행 제외
        thead = self.table.find('thead')
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

            row_header = self._clean_text(cells[0].get_text())
            values = []

            for cell in cells[1:]:
                if cell.name == 'td':
                    value = self._clean_text(cell.get_text())
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

    def _is_two_col_no_header(self) -> bool:
        """
        thead도 없고 th도 없으며, 모든 데이터 행이 2개의 td로만 구성된 경우인지 판별
        """
        if self.table.find('thead') is not None:
            return False
        if self.table.find('th') is not None:
            return False

        # tbody 우선
        tbody = self.table.find('tbody')
        trs = tbody.find_all('tr') if tbody else self.table.find_all('tr')
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

    def _extract_key_value_rows(self) -> List[Dict[str, str]]:
        """
        2열 key-value 테이블을 {첫번째셀: 두번째셀} 형태로 추출
        """
        tbody = self.table.find('tbody')
        trs = tbody.find_all('tr') if tbody else self.table.find_all('tr')
        results: List[Dict[str, str]] = []
        for tr in trs:
            tds = tr.find_all('td')
            if len(tds) >= 2:
                key = self._clean_text(tds[0].get_text())
                value = self._clean_text(tds[1].get_text())
                if key or value:
                    results.append({key: value})
        return results
    
    def _extract_data_rows(self, headers: List[str]) -> List[Dict[str, str]]:
        """
        데이터 행 추출 (rowspan 처리 포함)
        """
        # tbody가 있으면 tbody에서, 없으면 table에서 직접
        tbody = self.table.find('tbody')
        
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
            thead = self.table.find('thead')
            all_trs = self.table.find_all('tr')
            
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
                    value = self._clean_text(cell.get_text())
                    
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
    
    def _clean_text(self, text: str) -> str:
        """
        텍스트 정리 (공백, 줄바꿈 제거)
        """
        # 여러 공백을 하나로
        text = re.sub(r'\s+', ' ', text)
        # 앞뒤 공백 제거
        text = text.strip()
        return text


def parse_table(html_table: str) -> List[Dict[str, str]]:
    """
    편의 함수: HTML 테이블 문자열을 행별 딕셔너리로 변환
    
    Args:
        html_table: <table>로 시작하는 HTML 문자열
        
    Returns:
        List[Dict]: [{"컬럼": "값", ...}, ...]
    
    Example:
        >>> html = '<table><tr><th>A</th></tr><tr><td>1</td></tr></table>'
        >>> result = parse_table(html)
        >>> print(result)
        [{'A': '1'}]
    """
    try:
        parser = FinalTableParser(html_table)
        return parser.parse()
    except Exception as e:
        print(f"❌ 파싱 실패: {e}")
        return []


def parse_and_print(html_table: str) -> None:
    """
    테이블 파싱 후 결과를 보기 좋게 출력
    """
    rows = parse_table(html_table)

    if rows:
        print(f"✅ {len(rows)}개 행 추출:")
        for i, row in enumerate(rows, 1):
            row_str = json.dumps(row, ensure_ascii=False)
            if i == len(rows):  # 마지막 행
                print(row_str)
            else:
                print(f"{row_str},")
    else:
        print("❌ 추출 실패 또는 빈 테이블")


def process_md_file(filepath: str, content: str) -> None:
    """
    MD 파일의 <table> 태그를 찾아서 파싱된 row로 교체
    """
    import re

    # <table>...</table> 패턴 찾기
    table_pattern = r'(<table>.*?</table>)'
    matches = list(re.finditer(table_pattern, content, re.DOTALL))

    if not matches:
        print("❌ MD 파일에서 <table> 태그를 찾을 수 없습니다.")
        return

    print(f"✅ {len(matches)}개의 테이블 발견")

    # 뒤에서부터 교체 (인덱스 변화 방지)
    new_content = content
    for i, match in enumerate(reversed(matches), 1):
        table_num = len(matches) - i + 1
        table_html = match.group(0)

        print(f"\n[테이블 {table_num}] 파싱 중...")

        # 테이블 파싱
        rows = parse_table(table_html)

        if rows:
            # row 데이터를 문자열로 변환 (마지막 행은 쉼표 없음)
            rows_str_list = []
            for idx, row in enumerate(rows):
                if idx == len(rows) - 1:  # 마지막 행
                    rows_str_list.append(json.dumps(row, ensure_ascii=False))
                else:
                    rows_str_list.append(f"{json.dumps(row, ensure_ascii=False)},")
            rows_str = "\n".join(rows_str_list)

            # <table> 안에 삽입
            replacement = f"<table>\n{rows_str}\n</table>"

            # 교체
            new_content = new_content[:match.start()] + replacement + new_content[match.end():]

            print(f"✅ {len(rows)}개 행으로 변환 완료")
        else:
            print(f"❌ 파싱 실패")

    # 파일 저장 (새 파일 생성)
    output_file = filepath.replace('.md', '_processed.md')
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"\n✅ 처리 완료: {output_file}")
    except Exception as e:
        print(f"\n❌ 파일 저장 실패: {e}")


# =====================================================================
# 테스트 케이스
# =====================================================================

if __name__ == "__main__":
    import sys

    def print_usage() -> None:
        print("사용법:")
        print("  python html2row.py -ex               # 내장 예제 파싱 실행")
        print("  python html2row.py <html_파일경로>   # 파일의 모든 테이블 파싱 후 출력")
        print("  python html2row.py -h | --help       # 도움말 표시")
        print("")

    if len(sys.argv) == 1:
        print_usage()
    else:
        cmd = sys.argv[1]
        if cmd in ("-h", "--help"):
            print_usage()
        elif cmd in ("-ex", "--ex"):
            print("=" * 80)
            print("최종 완성판 HTML 테이블 파서 - Examples")
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
                # MD 파일인 경우 특별 처리
                if cmd.endswith('.md'):
                    process_md_file(cmd, content)
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