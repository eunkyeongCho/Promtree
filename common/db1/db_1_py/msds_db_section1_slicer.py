from __future__ import annotations
from typing import List, Optional
from msds_db_text_norm import norm, is_noise_line, clean_section1_lines
from msds_db_regex import SEC23_RE_STRICT, SEC23_RE_LOOSE, SEC1_RE

"""
[products table 관련]
MSDS 텍스트에서 섹션 1(제품 및 회사 정보)을 슬라이싱하는 모듈.

이 모듈은 MSDS(물질안전보건자료)의 전체 텍스트로부터 섹션 1에 해당하는
부분을 정확히 잘라내는 함수를 제공합니다.

주요 기능:
- `slice_section1`: 'Section 1' 헤더를 탐지하여 시작점을 찾고,
  'Section 2' 또는 'Section 3' 헤더가 나타나는 지점을 종료 지점으로 삼아
  텍스트를 슬라이싱합니다. 또한, 추출된 텍스트에서 불필요한 노이즈를
  제거하는 정제 작업도 수행합니다.
- `slice_section1_debug`: `slice_section1`과 동일한 작업을 수행하면서,
  슬라이싱 과정에서 사용된 인덱스 등 디버깅 정보를 함께 반환합니다.
"""

# 다음 주요 섹션의 시작 라인을 탐색하기 위한 함수
def find_next_section2_or_3(lines: List[str], start_idx: int) -> Optional[int]:
    for k in range(start_idx + 1, min(len(lines), start_idx + 4000)):
        row = norm(lines[k])
        if SEC23_RE_STRICT.search(row):
            return k
    for k in range(start_idx + 1, min(len(lines), start_idx + 4000)):
        row = norm(lines[k])
        if SEC23_RE_LOOSE.search(row):
            return k
    return None


# Section 1 본문만 추출하는 메인 함수.
def slice_section1(text: str, max_lookahead_lines: int = 1200, body_limit: int = 1200) -> str:
    lines = text.splitlines()
    # 1. Section 1 헤더 탐색
    start_idx = None
    for i, ln in enumerate(lines[:max_lookahead_lines]):
        if SEC1_RE.search(norm(ln)):
            start_idx = i
            break
    if start_idx is None:
        start_idx = 0

    # 2. 실질적인 본문 시작라인 찾기 (공백/잡음 라인 통과)
    j = start_idx + 1
    while j < len(lines):
        if norm(lines[j]) and not is_noise_line(lines[j]):
            break
        j += 1
    start_idx = min(j, len(lines)-1)

    # 3. 다음 섹션 2 또는 3의 시작 인덱스 탐색
    next_idx = find_next_section2_or_3(lines, start_idx)
    end_idx = next_idx if next_idx is not None else min(len(lines), start_idx + body_limit)

    # 4. 라인 슬라이스 및 정제
    raw = lines[start_idx:end_idx]
    body = [ln for ln in raw if not is_noise_line(ln)]
    body = clean_section1_lines(body)
    return "\n".join(body)


# slice_section1()의 디버그 버전.
def slice_section1_debug(text: str, max_lookahead_lines: int = 1200, body_limit: int = 1200):
    lines = text.splitlines()

    # Section 1 헤더 탐색
    start_idx = None
    for i, ln in enumerate(lines[:max_lookahead_lines]):
        if SEC1_RE.search(norm(ln)):
            start_idx = i
            break
    if start_idx is None:
        start_idx = 0

    # 실질적인 본문 시작라인 보정
    j = start_idx + 1
    while j < len(lines):
        if norm(lines[j]) and not is_noise_line(lines[j]):
            break
        j += 1
    start_idx = min(j, len(lines)-1)

    # 다음 섹션 탐색
    next_idx = find_next_section2_or_3(lines, start_idx)
    end_idx = next_idx if next_idx is not None else min(len(lines), start_idx + body_limit)

    # Section 1 본문 추출 및 정제
    raw = lines[start_idx:end_idx]
    body = [ln for ln in raw if not is_noise_line(ln)]
    body = clean_section1_lines(body)
    section_text = "\n".join(body)

    # 디버그 정보 구성
    debug = {"start_idx": start_idx, "end_idx": end_idx, "found_next": next_idx}
    return section_text, debug