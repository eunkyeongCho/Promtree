from __future__ import annotations
from msds_db_section1_extractors import collect_product_candidates, collect_company_candidates, pick_company_weighted_with_label_proximity
from msds_db_section1_slicer import slice_section1
from typing import Dict
from msds_db_section1_extractors import (
    collect_product_candidates,
    collect_company_candidates,
    pick_company_weighted_with_label_proximity,
)
from msds_db_section1_slicer import slice_section1

"""
[products table 관련]
MSDS 섹션 1 분석 및 정보 추출을 위한 메인 파이프라인 모듈.

이 모듈은 MSDS(물질안전보건자료)의 전체 텍스트로부터 섹션 1에 해당하는
부분을 잘라내고, 그 안에서 제품명과 회사명을 추출하는 함수를 제공합니다.

주요 기능:
- `extract_section1_and_fields_from_text`: 전체 텍스트를 입력받아
  내부적으로 슬라이싱, 후보 수집, 최종 선택 단계를 모두 수행하여
  최종 제품명과 회사명, 그리고 분석 과정에서 수집된 후보 목록을 반환합니다.

의존성:
- `msds_db_section1_slicer`: 텍스트에서 섹션 1 부분을 잘라내는 역할.
- `msds_db_section1_extractors`: 잘라낸 텍스트에서 제품명 및 회사명
  후보를 수집하고, 최종 값을 선택하는 역할.
"""


def extract_section1_and_fields_from_text(text: str):
    section1 = slice_section1(text)
    lines = section1.splitlines()

    prodcands = collect_product_candidates(lines)
    compcands = collect_company_candidates(lines)

    product_name = prodcands[0] if prodcands else 'UNKNOWN'
    company_name = pick_company_weighted_with_label_proximity(lines, compcands) or 'UNKNOWN'

    return {
        'product_name': product_name,
        'company_name': company_name,
        'section1_excerpt': section1[:1500],
        'product_candidates': prodcands,
        'company_candidates': compcands,
    }
