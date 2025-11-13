from __future__ import annotations
import re
from typing import List, Optional
from msds_db_regex import SUBSEC_RX, ROOT_ANY_RX, HEAD_HINTS_RE, DASH_CLASS, SEP, FALLBACK_ROOT_HINTS
from msds_db_ingredients_norm import norm_lower, is_table_line_raw

"""
[ingredients table 관련]
MSDS 텍스트에서 구성성분 섹션의 경계를 탐지하는 로케이터 모듈.

이 모듈은 MSDS(물질안전보건자료) 문서의 전체 텍스트(줄 단위 리스트)를
입력받아, 구성성분 정보가 포함된 섹션(주로 2장 또는 3장)의 시작과 끝
인덱스를 찾는 함수들을 제공합니다.

다양한 형식의 문서를 처리하기 위해 여러 단계의 탐지 전략(엄격, 완화, 폴백)과
휴리스틱을 사용합니다.

주요 기능:
- `collect_root_index_*`: 'Section 1', '2.' 등 주요 섹션 헤더의 위치를 탐지.
- `select_start_for_composition`: 여러 단서를 조합하여 구성성분 섹션의
  시작점을 결정.
- `find_next_root_after`: 현재 섹션 번호보다 큰 번호의 섹션이 나타나는
  지점을 찾아 섹션의 끝으로 간주.
- `fallback_find_next_by_title`: 숫자 번호가 없는 경우, 제목 키워드를
  기반으로 다음 섹션의 시작점을 추정.
"""

# 가까운 인덱스 묶음을 간소화하여 대표 인덱스만 유지
def _dedup_close(idxs: List[int], gap: int = 3) -> List[int]:
    out=[]
    for x in sorted(idxs):
        if not out or x - out[-1] > gap:
            out.append(x)
    return out

# 루트 헤더(숫자/로마/Section) 엄격 탐지
def collect_root_index_strict(lines: List[str]) -> List[int]:
    idxs=[]
    for i, ln in enumerate(lines):
        if is_table_line_raw(ln): continue
        t = norm_lower(ln)
        if SUBSEC_RX.search(t): continue  # 선제 배제
        if ROOT_ANY_RX.search(t):
            idxs.append(i)
    return _dedup_close(idxs)

# 숫자 기반 완화 탐지(섹션 키워드 optional)
def collect_root_index_relaxed(lines: List[str]) -> List[int]:
    idxs=[]
    for i, ln in enumerate(lines):
        t = norm_lower(ln)
        if SUBSEC_RX.search(t): continue
        if re.search(r"(?:^|[\s])(section\s*)?(?:[1-9]|1[0-6])\s*[:\.\)\-\u2013\u2014]", t, re.I):
            idxs.append(i)
    return _dedup_close(idxs)

# 성분/조성 헤더 힌트(EN/KO) 탐지
def find_composition_headers(lines: List[str]) -> List[int]:
    idxs=[]
    for i, ln in enumerate(lines):
        if HEAD_HINTS_RE.search(norm_lower(ln)):
            idxs.append(i)
    return _dedup_close(idxs, gap=2)

# 조합 규칙으로 ‘성분/조성’ 시작 인덱스 선택
def select_start_for_composition(lines: List[str], roots: List[int], prefer_numbers=(3,2)) -> Optional[int]:
    comp_idxs = find_composition_headers(lines)
    # 1) '3' + 힌트 최우선
    for i in comp_idxs:
        if re.match(r"^\s*(?:##+\s*)?(?:section\s*)?3\s*[:\.\)\-\u2013\u2014]\b", norm_lower(lines[i])):
            return i
    # 2) 힌트만 만족
    if comp_idxs:
        return comp_idxs[0]
    # 3) roots와 힌트가 동시에 일치
    for pn in prefer_numbers:
        num_pat = re.compile(rf"^\s*(?:##+\s*)?(?:section\s*)?{pn}\s*{DASH_CLASS}\b", re.I)
        for i in roots:
            hdr = norm_lower(lines[i])
            if num_pat.search(hdr) and HEAD_HINTS_RE.search(hdr):
                return i
    # 4) roots 중 힌트만 일치
    for i in roots:
        if HEAD_HINTS_RE.search(norm_lower(lines[i])):
            return i

    # 5) roots 첫 번째 또는 None 최종 폴백
    return roots[0] if roots else None


# 루트 헤더 라인에서 '장 번호(1~2자리 정수)'를 추출하기 위한 보조 파서.
def parse_root_number(t: str) -> Optional[int]:
    # 1) Markdown/리스트 프리픽스 제거
    t2 = re.sub(r"^[#>*\s]+", "", t)
    # 2) "Section <num> <sep>" 또는 "<num> <sep>" 매칭
    m = re.search(rf"^\s*(?:section\s*)?(\d{{1,2}})\s*{SEP}\b", t2, re.I) or \
        re.search(rf"(?:^|[\s])(\d{{1,2}})\s*{SEP}\b", t2)
    # 3) 성공 시 정수 변환
    return int(m.group(1)) if m else None

# 현재 장 번호(n_curr)의 하위 소절인지 여부를 판정
def is_subsection_of(n_curr: int, line_norm: str) -> bool:
    # 같은 섹션의 소절(예: "3.2", "3 . 2", "3.2.1")
    # line_norm 사전 정규화(norm_lower)된 문자열을 가정.
    return bool(re.match(rf"^\s*(?:##+\s*)?{n_curr}\s*\.\s*\d", line_norm))

# start_i 이후의 루트 후보 인덱스 중 '상위 번호 증가'가 발생하는 첫 지점을 반환
def find_next_root_after(lines: List[str], roots: List[int], start_i: int, min_span_lines: int = 8) -> Optional[int]:
    # 시작 인덱스 라인의 정규화 텍스트에서 현재 루트 장 번호를 파싱
    curr_n = parse_root_number(norm_lower(lines[start_i]))
    # 미리 수집된 루트 후보 인덱스들을 순회
    for i in roots:
        # 시작 인덱스 이전 또는 같은 위치는 건너뜀
        if i <= start_i: 
            continue
        # 시작점으로부터 너무 가까운 후보는 노이즈 가능성이 있어 건너뜀
        if i - start_i < min_span_lines:
            continue
        # 후보 라인을 정규화하여 다음 루트 번호 파싱 준비
        tline = norm_lower(lines[i])
        # 후보 라인에서 다음 루트 장 번호를 파싱
        nxt_n = parse_root_number(tline)
        if curr_n is not None and nxt_n is not None:
            # 같은 장의 소절은 내부 포함
            if nxt_n == curr_n and (SUBSEC_RX.search(tline) or is_subsection_of(curr_n, tline)):
                continue
            # 번호 감소/동일 루트는 컷 아님
            if nxt_n <= curr_n:
                continue
            # 번호 증가 → 다음 루트 경계
            return i
        # 숫자 파싱 실패 케이스는 폴백 로직에서 처리
    return None

# 폴백: 제목 힌트를 활용해 다음 루트 경계를 추정.
def fallback_find_next_by_title(lines: List[str], start_i: int, scan_ahead: int = 4000) -> Optional[int]:
    best=None
    for k in range(start_i + 8, min(len(lines), start_i + scan_ahead)):
        raw = lines[k]; t = norm_lower(raw)
        # 서브섹션(3.2, 3.2.1 등)으로 보이는 라인은 건너뜀
        if SUBSEC_RX.search(t): 
            continue
        
        if FALLBACK_ROOT_HINTS.search(t):
            score = 0
            # +4: 마크다운 헤딩(##) 외양
            if re.match(r"^\s*##+\s*\S", raw): score += 4
            # +1: 짧은 제목 길이(<80자)
            if len(raw) < 80: score += 1
            # -3: 문장부호(마침표/느낌표/물음표)로 끝남 → 문장일 가능성
            if re.search(r"[.!?]\s*$", raw): score -= 3
            # -1: 콤마 2개 초과 → 열거형 문장일 가능성
            if raw.count(",") > 2: score -= 1
            # -1: 너무 긴 라인(>140자) → 본문일 가능성
            if len(raw) > 140: score -= 1

            if best is None or score > best[0]:
                best = (score, k)
    return best[1] if best else None

