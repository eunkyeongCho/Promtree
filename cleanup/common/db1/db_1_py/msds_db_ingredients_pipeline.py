from __future__ import annotations
from typing import Dict, List
from msds_db_ingredients_slicer import slice_section_2_or_3
from msds_db_ingredients_LLM import extract_ingredients_with_ollama
from msds_db_ingredients_postprocess import (
    postprocess_synonyms,
    normalize_unit_basis,
    enrich_cas_and_conc,
    parse_conc_raw,
    normalize_concentration_to_100,
    apply_confidential_flags,
)

"""
[ingredients table 관련]
MSDS 구성성분 추출을 위한 모듈.

이 모듈은 MSDS(물질안전보건자료)의 전체 텍스트로부터 구성성분 정보를 추출하는 함수를 제공합니다.

주요 기능:
- `extract_section23_and_ingredients`: 전체 텍스트를 입력받아,
  내부적으로 슬라이싱, LLM을 이용한 정보 추출, 후처리 단계를 모두
  수행하여 최종적으로 정제된 성분 데이터 리스트를 반환하는 핵심 함수입니다.

데이터 처리 흐름:
1.  **섹션 슬라이싱**: `msds_db_ingredients_slicer` 모듈을 사용하여
    텍스트에서 구성성분 정보가 담긴 부분(주로 섹션 2 또는 3)을 잘라냅니다.
2.  **LLM 정보 추출**: `msds_db_ingredients_LLM` 모듈을 통해 잘라낸 텍스트를
    Ollama LLM에 전달하고, 구조화된 JSON 형식의 성분 데이터를 추출합니다.
3.  **데이터 후처리**: `msds_db_ingredients_postprocess` 모듈의 함수들을
    사용하여 LLM이 추출한 데이터의 정확도를 높이고, 형식을 표준화하며,
    누락된 정보를 보강합니다.

이 모듈은 다른 여러 모듈의 기능을 오케스트레이션하여, 복잡한 텍스트 처리
과정을 단일 함수 호출로 단순화하는 역할을 합니다.
"""


def extract_section23_and_ingredients(text: str, debug: bool = True) -> Dict:
    """ Section 2/3 추출 및 성분 분석 파이프라인 """
    if debug:
        print("\n[INFO] Section 2/3 슬라이싱 시작...")
    
    sec = slice_section_2_or_3(text, prefer_numbers=(3, 2), debug=debug)
    section2_3_text = sec["clean"]
    
    if debug:
        print("\n[INFO] LLM 호출 시작...")
    
    ingredients = extract_ingredients_with_ollama(section2_3_text)
    
    if debug:
        print("[INFO] LLM 호출 완료")
        print("[INFO] 후처리 시작...")
    
    ingredients = postprocess_synonyms(ingredients)
    ingredients = [normalize_unit_basis(it, section2_3_text) for it in ingredients]
    ingredients = enrich_cas_and_conc(ingredients)
    ingredients = apply_confidential_flags(ingredients)

        
    for it in ingredients:
        if "is_conc_confidential" in it and "is_conc_secret" not in it:
            it["is_conc_secret"] = bool(it["is_conc_confidential"])
        it["concentration"] = parse_conc_raw(it.get("concentration", {}))
    
    ingredients = normalize_concentration_to_100(
        ingredients,
        treat_secret_range_as_variable=True
    )

    
    if debug:
        print("[INFO] 후처리 완료")
    
    return {
        "ingredients": ingredients,
        "section2_3_text": section2_3_text,
        "section_info": {
            "start_idx": sec.get("start_idx"),
            "end_idx": sec.get("end_idx"),
            "found_section": sec.get("found_section", "unknown")
        }
    }