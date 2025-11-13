import json
import re
from typing import List, Dict, Optional

def _normalize_quotes(s: str) -> str:
    # 스마트 따옴표/전각 따옴표를 ASCII로 교정
    return (
        s.replace("“", '"').replace("”", '"')
         .replace("‘", "'").replace("’", "'")
         .replace("＂", '"').replace("＇", "'")
    )

def normalize_korean_keys(obj: Dict) -> Dict:
    key_map = {
        "화학물질명": "name",
        "관용명": "common_name",
        "카스 번호": "cas",
        "카스번호": "cas",
        "CAS": "cas",
        "CAS No": "cas",
        "함유량 (%)": "concentration",
        "함유량(%)": "concentration",
        "함유량": "concentration",
        "농도": "concentration",
    }
    out = {}
    for k, v in obj.items():
        std_k = key_map.get(str(k).strip(), str(k).strip())
        out[std_k] = v
    return out

# 하이픈/틸드/대시 폭 다양성, 전각 퍼센트 지원
_range_pat = re.compile(r"\s*(\d+(?:\.\d+)?)\s*[-~–—−]\s*(\d+(?:\.\d+)?)\s*[%％]?\s*$")
_num_pat = re.compile(r"\s*(\d+(?:\.\d+)?)\s*[%％]?\s*$")

def normalize_concentration(value: Optional[str]) -> Dict:
    if value is None:
        return {"value": None, "unit": "%"}
    s = str(value).strip()
    m = _range_pat.match(s)
    if m:
        return {"min": float(m.group(1)), "max": float(m.group(2)), "unit": "%"}
    m = _num_pat.match(s)
    if m:
        return {"value": float(m.group(1)), "unit": "%"}
    return {"raw": s}

def _clean_minor_syntax(inner: str) -> str:
    # 말미에 남은 쉼표 제거, 불필요 공백 정리
    t = inner.strip()
    t = _normalize_quotes(t)
    # 흔한 오류: "},{," 같은 패턴 정리
    t = re.sub(r"}\s*,\s*,\s*{", "},{", t)
    # 끝 쉼표 제거
    t = t.rstrip(", \n\t")
    return t

def _post_standardize(items: List[Dict]) -> List[Dict]:
    standardized = []
    for it in items:
        if not isinstance(it, dict):
            continue
        it2 = normalize_korean_keys(it)
        for k, v in list(it2.items()):
            if isinstance(v, str) and v.strip() in ("자료 없음 .", "자료없음", "-", ""):
                it2[k] = None
        if "cas" in it2 and isinstance(it2["cas"], str):
            it2["cas"] = it2["cas"].replace(" ", "").strip()
        if "concentration" in it2:
            it2["concentration"] = normalize_concentration(it2["concentration"])
        # 필드 기본값 보강
        it2.setdefault("name", None)
        it2.setdefault("common_name", None)
        it2.setdefault("cas", None)
        it2.setdefault("concentration", {"value": None, "unit": "%"})
        standardized.append(it2)
    return standardized

def wrap_table_json_array(table_inner_text: str) -> List[Dict]:
    """
    <table> 내부에 JSON 객체들이 쉼표로 나열된 경우 이를 [ {...}, {...} ]로 래핑해 파싱.
    - 정상: List[Dict] 반환
    - 비적합/실패: [] 반환 (None은 오류 상황에서만 사용하지 않음)
    """
    if not table_inner_text or not table_inner_text.strip():
        return []

    inner = _clean_minor_syntax(table_inner_text)

    # 이미 배열인 경우
    if inner.startswith("[") and inner.endswith("]"):
        try:
            items = json.loads(inner)
            return _post_standardize(items) if isinstance(items, list) else []
        except Exception:
            return []

    # 단일 객체 혹은 여러 객체 나열 감지
    if inner.startswith("{") and inner.endswith("}"):
        # 객체 나열 패턴 (최상위 '} , {' 존재)
        if re.search(r"}\s*,\s*{", inner):
            try:
                items = json.loads(f"[{inner}]")
                return _post_standardize(items) if isinstance(items, list) else []
            except Exception:
                # 경미한 구문 오류 교정 후 재시도
                cleaned = _clean_minor_syntax(inner)
                try:
                    items = json.loads(f"[{cleaned}]")
                    return _post_standardize(items) if isinstance(items, list) else []
                except Exception:
                    return []
        else:
            # 단일 객체만 있는 경우
            try:
                obj = json.loads(inner)
                return _post_standardize([obj]) if isinstance(obj, dict) else []
            except Exception:
                # 경미 오류 교정 후 재시도
                cleaned = _clean_minor_syntax(inner)
                try:
                    obj = json.loads(cleaned)
                    return _post_standardize([obj]) if isinstance(obj, dict) else []
                except Exception:
                    return []

    # 기타 포맷(예: CSV/HTML-셀 기반)은 이 전처리에서 처리하지 않음
    return []
