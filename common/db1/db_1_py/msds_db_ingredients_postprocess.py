from __future__ import annotations
import re
from typing import List, Optional, Dict
from msds_db_regex import BASIS_PATTERNS, UNIT_WHITELIST, DELIMS_RX, EN_MIX_RX, KO_MIX_RX

"""
[ingredients table 관련]
LLM이 추출한 MSDS 성분 데이터 후처리(Post-processing) 모듈.

이 모듈은 대규모 언어 모델(LLM)이 추출한 초기 JSON 형식의 성분 데이터에 대해
정확성을 높이고 데이터 형식을 표준화하며, 누락된 정보를 보강하는 다양한
함수들을 제공합니다.

주요 기능:
- `normalize_unit_basis`: 농도의 단위와 기준('w/w', 'v/v')을 표준화합니다.
- `postprocess_synonyms`: 쉼표, 세미콜론 등으로 연결된 동의어 문자열을
  개별 토큰으로 분리하고 중복을 제거합니다.
- `enrich_cas_and_conc`: 구조화된 농도 값(min, max, value)을 기반으로
  원본 텍스트(`raw`) 필드를 재생성하는 등 데이터를 보강합니다.
- `fix_name_mixture`: '혼합물' 또는 'Mixture'와 같은 이름과 동의어를
  일관된 형식으로 표준화합니다.
"""



# 원문 텍스트(raw_text)에서 혼합 기준(basis: 'w/w' 또는 'v/v') 단서를 탐지
def infer_basis_from_text(raw_text: str) -> Optional[str]:
    t = raw_text or ""
    for rx, basis in BASIS_PATTERNS:
        if rx.search(t):
            return basis
    return None

# item['concentration']의 단위/기준을 표준화하고 누락 시 텍스트에서 basis를 추론
def normalize_unit_basis(item: Dict, raw_text: str) -> Dict:
    conc = item.get("concentration") or {}
    unit = (conc.get("unit") or "")
    basis = conc.get("basis")

    # 1) unit에 포함된 키워드로 basis/단위 보정
    u = unit.strip().lower()
    detected_basis = None
    if "w/w" in u or "wt%" in u or "중량" in u:
        detected_basis = "w/w"
        unit = "%"
    elif "v/v" in u or "부피" in u:
        detected_basis = "v/v"
        unit = "%"

    # 2) 화이트리스트 외 단위 표현을 흔한 변형 규칙으로 정규화
    if unit not in UNIT_WHITELIST and unit != "":
        if u in {"% w/w", "%(w/w)", "wt%", "중량 %"}:
            unit = "%"
            detected_basis = detected_basis or "w/w"
        elif u in {"% v/v", "%(v/v)", "부피 %"}:
            unit = "%"
            detected_basis = detected_basis or "v/v"
    
    # 3) basis 누락 시 원문에서 추론
    if not basis:
        basis_text = infer_basis_from_text(raw_text)
        if basis_text:
            basis = basis_text

    # 4) unit에서 감지된 basis가 우선
    if detected_basis:
        basis = detected_basis

    # 5) None 정규화 후 반영
    conc["unit"]  = unit if unit else None
    conc["basis"] = basis if basis else None
    item["concentration"] = conc
    return item

# 동의어 문자열 하나를 구분자(DELIMS_RX) 기준으로 토큰 분할
def split_synonyms_token(s: str) -> List[str]:
    s = (s or "").strip()
    if not s:
        return []
    parts = [p.strip() for p in re.split(DELIMS_RX, s) if p.strip()]
    return parts

# 각 항목의 synonym 필드를 구분자 분할 → 전개 → 중복 제거(순서 보존)로 정제
def postprocess_synonyms(items: List[Dict]) -> List[Dict]:
    out=[]
    for it in items:
        syns = it.get("synonym") or []
        new=[]
        for s in syns:
            new.extend(split_synonyms_token(s))
        seen=set(); syn_norm=[]
        for x in new:
            if x not in seen:
                seen.add(x); syn_norm.append(x)
        it["synonym"] = syn_norm
        out.append(it)
    return out

# 항목 리스트에 대해 cas/concentration 후처리를 보강
def enrich_cas_and_conc(items: List[Dict]) -> List[Dict]:
    out=[]
    for it in items:
        # raw가 비었지만 구조화 값이 있으면 raw 문자열을 조립
        conc = it.get("concentration") or {}
        if conc.get("raw") is None:
            parts=[]
            if conc.get("op_min") and conc.get("min") is not None:
                parts.append(f"{conc['op_min']}{conc['min']}")
            elif conc.get("min") is not None and conc.get("max") is not None:
                parts.append(f"{conc['min']}-{conc['max']}")
            elif conc.get("value") is not None:
                parts.append(str(conc["value"]))
            if conc.get("unit"): parts.append(conc["unit"])
            if conc.get("basis"): parts.append(f"({conc['basis']})")
            conc["raw"] = " ".join(parts) if parts else None
            it["concentration"] = conc

        out.append(it)
    return out

# '혼합물/Mixture' 이름/동의어 표기를 일관화
def fix_name_mixture(items: List[Dict]) -> List[Dict]:
    out=[]
    for it in items:
        name = (it.get("name") or "").strip()
        syns = [s.strip() for s in (it.get("synonym") or []) if s and s.strip()]
        
        # case 1: 이름이 영어 'mixture' → 한국어 '혼합물'로 표준화하고 동의어에 'Mixture' 선두 보장
        if EN_MIX_RX.match(name):
            syns = [s for s in syns if not EN_MIX_RX.match(s)]
            syns.insert(0, "Mixture")
            it["name"] = "혼합물"
            it["synonym"] = syns
        # case 2: 이름이 한국어 '혼합물' → 동의어에 영어 'Mixture' 보장
        elif KO_MIX_RX.match(name):
            if not any(EN_MIX_RX.match(s) for s in syns):
                syns.insert(0, "Mixture")
                it["synonym"] = syns
        # case 3: 이름이 둘 다 아니나 동의어에 '혼합물'이 포함 → 이름을 '혼합물'로 변경
        else:
            has_ko = any(KO_MIX_RX.match(s) for s in syns)
            if has_ko:
                it["name"] = "혼합물"
                syns = [s for s in syns if not KO_MIX_RX.match(s)]
                if not any(EN_MIX_RX.match(s) for s in syns):
                    syns.insert(0, "Mixture")
                it["synonym"] = syns
        out.append(it)
    return out

