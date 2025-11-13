from __future__ import annotations
from typing import Dict
from msds_db_regex import PAGE_NAV_PAT, PAGE_MARK_PAT, HTML_TAG_LINE_PAT, WEB_PAT
from msds_db_ingredients_locator import collect_root_index_strict, collect_root_index_relaxed, select_start_for_composition, find_next_root_after, fallback_find_next_by_title

"""
[ingredients table 관련]
MSDS 텍스트에서 구성성분 섹션을 슬라이싱(Slicing)하는 모듈.

이 모듈은 MSDS(물질안전보건자료)의 전체 텍스트로부터 구성성분 정보가
포함된 섹션(주로 2장 또는 3장)을 정확히 잘라내는 기능을 제공합니다.

주요 기능:
- `slice_section_2_or_3`: `msds_db_ingredients_locator` 모듈의 여러
  탐지 함수들을 조합하여, 구성성분 섹션의 시작과 끝을 결정하고 해당
  부분의 텍스트를 추출합니다. 또한, 페이지 번호, HTML 태그 등 불필요한
  노이즈를 제거하는 정제 작업도 수행합니다.
"""


# 성분 섹션을 검출, 원문과 정제 형태로 반환
def slice_section_2_or_3(text: str,
                         prefer_numbers=(3,2),
                         max_span_lines=12000,
                         debug=False) -> Dict[str,str]:
    # 전체 텍스트를 줄 단위로 분리(개행 미포함) → 라인 리스트 생성
    lines = text.splitlines(keepends=False)

    # 루트 헤더 인덱스: 엄격 탐색 우선, 실패 시 완화 탐색 사용
    roots = collect_root_index_strict(lines) or collect_root_index_relaxed(lines)
    if not roots:
        if debug: print("[DBG] no root headers found")
        return {"raw":"", "clean":""}

    # 성분/조성 시작점 선정: 루트 후보 + 힌트 조합
    start_i = select_start_for_composition(lines, roots, prefer_numbers)
    if start_i is None:
        if debug: print("[DBG] no composition header found")
        return {"raw":"", "clean":""}

    # 다음 루트 경계: 상위 번호 증가 지점(3→4 등)
    end_i = find_next_root_after(lines, roots, start_i, min_span_lines=8)
    # 숫자 없는 제목형 등에서 실패 시, 제목 힌트 폴백
    if end_i is None:
        end_i = fallback_find_next_by_title(lines, start_i, scan_ahead=4000)
    # 그래도 실패하면 최대 슬라이스 길이 제한으로 강제 종료
    if end_i is None:
        end_i = min(len(lines), start_i + max_span_lines)

    # 원문 블록 추출: 시작~종료 범위 슬라이스
    raw_block = "\n".join(lines[start_i:end_i])

    # 정제: 페이지/마커/HTML 제거 + 연속 빈 줄 축약
    block, prev_blank = [], False
    for ln in raw_block.splitlines():
        # 1) 페이지 네비/마커/HTML/URL 제거 조건에 WEB_PAT 추가
        if (
            PAGE_NAV_PAT.search(ln)
            or PAGE_MARK_PAT.search(ln)
            or HTML_TAG_LINE_PAT.search(ln)
            or WEB_PAT.search(ln)
        ):
            continue
        t = ln.rstrip()
        if not t:
            if prev_blank:
                continue
            prev_blank = True
            block.append("")
        else:
            prev_blank = False
            block.append(ln)
    clean_block = "\n".join(block).strip()

    # 디버그 출력: 루트 수, 시작/종료 인덱스, 시작/종료 헤더 미리보기
    if debug:
        print(f"[DBG] roots_count={len(roots)} start_i={start_i} end_i={end_i}")
        print("[DBG] start header:", lines[start_i])
        if end_i < len(lines):
            print("[DBG] end header:", lines[end_i])

    # 원문과 정제 결과를 함께 반환
    return {"raw": raw_block, "clean": clean_block}