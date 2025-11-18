from __future__ import annotations
import re
from typing import List, Optional, Dict
from msds_db_regex import BASIS_PATTERNS, UNIT_WHITELIST, DELIMS_RX, RANGE_RX, LT_RX, EQ_RX, CONF_TOKENS

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

def parse_conc_raw(conc: dict) -> dict:
    """
    concentration.raw 문자열을 value/min/max/op_min로 구조화.
    - 'a-b%': min=a, max=b
    - '<x%':  min=0, max=x, op_min='<'
    - 'x%':   value=x
    unit 비어 있으면 '%' 기본값.
    """
    c = dict(conc or {})
    raw = (c.get("raw") or "").strip()
    if not raw:
        return c
    m = RANGE_RX.match(raw)
    if m:
        c["min"] = float(m.group(1)); c["max"] = float(m.group(2))
        c["value"] = None; c["op_min"] = None
        c.setdefault("unit", "%")
        return c
    m = LT_RX.match(raw)
    if m:
        c["min"] = 0.0; c["max"] = float(m.group(1))
        c["value"] = None; c["op_min"] = "<"
        c.setdefault("unit", "%")
        return c
    m = EQ_RX.match(raw)
    if m:
        c["value"] = float(m.group(1))
        c["min"] = None; c["max"] = None; c["op_min"] = None
        c.setdefault("unit", "%")
        return c
    return c


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

# 100% 보정
def normalize_concentration_to_100(
    ingredients: List[Dict],
    treat_secret_range_as_variable: bool = True,
    enable_lower_only_cap_scale: bool = True,
    enable_upper_only_cap_scale: bool = True,
) -> List[Dict]:
    fixed, variable, lower_only, upper_only = [], [], [], []

    """
    성분 목록의 농도를 100에 맞추도록 정규화하여 각 항목에 'conc_adjusted' 값을 부여한다.

    개요
    - 농도 형태에 따라 항목을 분류하고, 고정값의 합(fixed_sum)을 우선 확보한 뒤 나머지 예산(100 - fixed_sum)을
      범위형(min–max)의 평균값 비율로 배분한다. 필요 시 하한만 있는 항목(>=, >)과 상한만 있는 항목(<=, <)에도
      잔여 예산을 간단한 프록시로 비례 배분한다. 안전하게 계산할 수 없는 항목은 'conc_adjusted'를 None으로 둔다.

    처리 단계
    1) 분류
       - fixed: concentration.value가 있는 항목(최종에 그대로 복사).
       - variable: concentration.min과 concentration.max가 모두 있는 항목(중앙값으로 비례 배분).
       - lower_only: min만 있고 op_min이 '>' 또는 '>='인 항목(옵션에 따라 잔여 예산 배분).
       - upper_only: max만 있고 op_max가 '<' 또는 '<='인 항목(옵션에 따라 최종 잔여 예산 배분).
       - 비공개(기밀) 처리: ing['is_conc_secret']가 True이면,
         treat_secret_range_as_variable가 True이고 유효한 min–max가 있을 때만 variable로 취급하고,
         그렇지 않으면 conc_adjusted=None 처리한다.

    2) 합계 계산 및 배분
       - fixed 합(fixed_sum)을 계산한다.
       - variable은 (min+max)/2의 합을 기준으로, 남은 목표치(100 - fixed_sum)를 비례 배분한다.
       - lower_only는 잔여 예산이 남고 enable_lower_only_cap_scale이 True일 때,
         간단한 프록시((min + 100)/2) 비율로 배분한다.
       - upper_only는 그 이후 잔여 예산이 남고 enable_upper_only_cap_scale이 True일 때,
         프록시(max/2) 비율로 배분한다.
       - fixed 항목의 conc_adjusted는 마지막에 value를 그대로 설정한다.

    파라미터
    - ingredients (List[Dict]): 각 항목은 'concentration' 키를 갖는 딕셔너리이며,
      concentration에는 value, min, max, op_min, op_max 등의 키가 선택적으로 존재한다.
      또한 'is_conc_secret'(bool)이 있을 수 있다.
    - treat_secret_range_as_variable (bool): 기밀 표기 항목이라도 min–max 범위가 있으면
      variable로 포함해 배분할지 여부. 기본 True.
    - enable_lower_only_cap_scale (bool): 하한만 있는 항목에 잔여 예산을 프록시로 배분할지 여부. 기본 True.
    - enable_upper_only_cap_scale (bool): 상한만 있는 항목에 잔여 예산을 프록시로 배분할지 여부. 기본 True.

    반환
    - List[Dict]: 입력 ingredients를 그대로 반환하되, 각 항목에 'conc_adjusted'(float 또는 None)를 추가한다.

    주의사항
    - 이 함수는 단위/기준(ww/vv) 통일이나 원시 파싱을 수행하지 않는다. value/min/max/op_* 등이
      사전에 신뢰성 있게 파싱·정규화되어 있어야 한다.
    - 합계가 정확히 100이 되도록 보정하기보다, 논리적으로 가능한 범위 내에서 비례 배분을 수행한다.
      입력 값에 따라 미세한 잔차가 남을 수 있다.
    - 기밀 항목 처리 정책(treat_secret_range_as_variable)과 하한/상한 전용 배분 옵션은
      도메인 정책에 맞게 설정해야 한다.

    예시
    - fixed 2개와 variable 1개가 있을 때: fixed 합을 우선 확보하고, 나머지를 variable 평균값 비율로 배분.
    - lower_only만 여러 개 있고 fixed/variable이 적을 때: 잔여 예산을 (min+100)/2 비율로 분할.
    - upper_only만 여러 개이고 잔여가 남을 때: 잔여 예산을 (max/2) 비율로 분할.
    """

    # 1) 분류
    for ing in ingredients:
        c = ing.get("concentration") or {}
        if ing.get("is_conc_secret", False):
            has_range = c.get("min") is not None and c.get("max") is not None
            if not (treat_secret_range_as_variable and has_range):
                ing["conc_adjusted"] = None
                continue
        val = c.get("value")
        mn, mx = c.get("min"), c.get("max")
        op_min, op_max = c.get("op_min"), c.get("op_max")

        if val is not None:
            fixed.append(ing)
        elif mn is not None and mx is not None:
            variable.append(ing)
        elif mn is not None and mx is None and op_min in (">", ">="):
            lower_only.append(ing)
        elif mx is not None and mn is None and op_max in ("<", "<="):
            upper_only.append(ing)
        else:
            ing["conc_adjusted"] = None

    # 2) fixed 합
    fixed_sum = sum(float(x["concentration"]["value"]) for x in fixed)

    # 3) 범위 스케일
    var_avgs = []
    for x in variable:
        c = x["concentration"]
        var_avgs.append((float(c["min"]) + float(c["max"])) / 2.0)
    var_sum = sum(var_avgs)
    target_for_var = max(0.0, 100.0 - fixed_sum)
    var_ratio = (target_for_var / var_sum) if var_sum > 0 else 1.0

    var_adjusted_sum = 0.0
    for i, x in enumerate(variable):
        adj = round(var_avgs[i] * var_ratio, 4)
        x["conc_adjusted"] = adj
        var_adjusted_sum += adj

    # 4) 하한-only 배분
    residual = max(0.0, 100.0 - fixed_sum - var_adjusted_sum)
    lower_only_adjusted_sum = 0.0
    if enable_lower_only_cap_scale and residual > 0 and lower_only:
        proxies = [ (float(x["concentration"]["min"]) + 100.0) / 2.0 for x in lower_only ]
        sum_proxy = sum(proxies)
        if sum_proxy > 0:
            for i, x in enumerate(lower_only):
                share = round(proxies[i] / sum_proxy * residual, 4)
                x["conc_adjusted"] = share
                lower_only_adjusted_sum += share

        else:
            for x in lower_only:
                x["conc_adjusted"] = None


    # 5) 상한-only 배분(옵션, 0~상한 중앙값 사용)
    residual2 = max(0.0, 100.0 - fixed_sum - var_adjusted_sum - lower_only_adjusted_sum)
    if enable_upper_only_cap_scale and residual2 > 0 and upper_only:
        proxies = [ float(x["concentration"]["max"]) / 2.0 for x in upper_only ]
        sum_proxy = sum(proxies)
        if sum_proxy > 0:
            for i, x in enumerate(upper_only):
                share = round(proxies[i] / sum_proxy * residual2, 4)
                x["conc_adjusted"] = share
        else:
            for x in upper_only:
                x["conc_adjusted"] = None

    # 6) fixed
    for x in fixed:
        x["conc_adjusted"] = float(x["concentration"]["value"])

    return ingredients



def apply_confidential_flags(items: List[Dict]) -> List[Dict]:
    """
    성분 항목 리스트에서 CAS/농도 값이 '기밀(영업 비밀 등)'로 표기된 경우를 감지해
    표준 플래그를 설정하고, 농도 필드를 안전한 값으로 초기화한다.

    개요
    - 미리 정의된 기밀 토큰 집합(CONF_TOKENS)과 대조하여 CAS 또는 농도 원시 텍스트가
      기밀로 표기된 항목을 탐지한다.
    - CAS가 기밀이면 is_cas_secret=True로 설정한다.
    - 농도가 기밀이면 concentration.raw를 '영업 비밀'로 표준화하고,
      value/min/max/unit/basis/op_min/op_max를 모두 None으로 설정한 뒤
      is_conc_secret=True로 설정한다.

    파라미터
    - items (List[Dict]): 각 항목은 다음과 같은 키를 가질 수 있다.
      * cas: CAS 원본 문자열
      * concentration: dict(raw, value, min, max, unit, basis, op_min, op_max)
      * concentration_raw: 과거 스키마 호환을 위한 농도 원시 문자열(선택)
      * is_cas_secret, is_conc_secret: 기존 플래그(없으면 False로 간주)

    반환
    - List[Dict]: 입력 리스트를 제자리 수정하여 반환하며,
      각 항목에는 기밀 여부 플래그와 정규화된 concentration가 반영된다.

    처리 흐름
    1) 기본 플래그 초기화: is_cas_secret, is_conc_secret를 bool(...)로 정규화.
    2) CAS 기밀 판정: cas를 소문자 비교해 기밀 토큰과 일치하면 is_cas_secret=True.
    3) 농도 기밀 판정:
       - concentration.raw 우선, 없으면 concentration_raw를 사용해 원시 문자열을 확보.
       - 기밀 토큰과 일치하면 concentration를 다음과 같이 갱신:
         raw='영업 비밀', value=None, min=None, max=None,
         unit=None, basis=None, op_min=None, op_max=None,
         그리고 is_conc_secret=True 설정.
    4) 갱신된 concentration를 항목에 재할당.

    주의사항
    - 이 함수는 '기밀 표기'만 처리한다. CAS 형식/체크섬 검증이나 농도 수치 파싱 및 단위/기준 정규화는
      별도의 전처리 단계에서 수행해야 한다.
    - concentration_raw는 과거 스키마 호환용이며, 최종적으로는 concentration 사전을
      단일 진실 소스로 유지하는 것이 권장된다.
    - CONF_TOKENS는 도메인에 맞게 확장 가능하며, 비교는 소문자 기준으로 수행한다.

    예시
    - cas='Trade Secret', concentration.raw='CONFIDENTIAL'인 경우:
      is_cas_secret=True, is_conc_secret=True,
      concentration.raw='영업 비밀', 수치/단위/연산자 필드는 모두 None으로 초기화.
    """
    lowered = {s.lower() for s in CONF_TOKENS}
    for it in items:
        # 0) 기본값 False로 초기화
        it["is_cas_secret"]  = bool(it.get("is_cas_secret",  False))
        it["is_conc_secret"] = bool(it.get("is_conc_secret", False))

        # 1) CAS 기밀
        cas_raw = (it.get("cas") or "").strip()
        if cas_raw and cas_raw.lower() in lowered:
            it["is_cas_secret"] = True

        # 2) 농도 기밀
        conc = dict(it.get("concentration") or {})
        raw = (conc.get("raw") or it.get("concentration_raw") or "").strip()
        if raw and raw.lower() in lowered:
            conc.update({
                "raw":"영업 비밀",
                "value":None,"min":None,"max":None,
                "unit":None,"basis":None,"op_min":None,"op_max":None
            })
            it["is_conc_secret"] = True
        it["concentration"] = conc
    return items

