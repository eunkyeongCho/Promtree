from __future__ import annotations
import re
from typing import Optional, List
from msds_db_regex import CONTROL_WS, DOT_LIKE, PAGE_NAV_PAT, PAGE_MARK_PAT, HTML_TAG_LINE_PAT, COPYRIGHT_STOPWORDS, DOC_TITLE_STOP, CODE_LABEL_RX

"""
[products table 관련]
MSDS 텍스트 분석을 위한 텍스트 정규화 및 정제 유틸리티 모듈.

이 모듈은 MSDS(물질안전보건자료) 문서의 텍스트를 분석하기 전에,
다양한 형태의 '노이즈'를 제거하고 문자열을 일관된 표준 형식으로
변환하는 헬퍼 함수들을 제공합니다.

주요 기능:
- `norm`: 제어 문자, 특수 공백, 서식 문자 등을 제거하고 소문자로 변환하는
  범용 정규화 함수입니다.
- `norm_company`: `norm`에 더해, 회사명 추출에 특화된 정제 로직(괄호 제거,
  연락처 정보 분리 등)을 수행합니다.
- `is_noise_line`: 특정 라인이 페이지 번호나 HTML 태그와 같은 무시해도
  되는 노이즈인지를 판별합니다.
- `safe_value_after_label`: "라벨: 값" 형식의 라인에서 안전하게 값을
  추출합니다.
- `clean_section1_lines`: 섹션 1 텍스트 블록에서 저작권 문구나 문서 제목 등
  불필요한 라인들을 제거합니다.
"""



# 문자열을 표준 형태로 정규화 함수
def norm(s: str) -> str:
    t = CONTROL_WS.sub(" ", s)
    t = t.translate(DOT_LIKE)
    t = re.sub(r"[*_`]+", "", t)
    t = t.replace("\t", " ")
    t = t.replace("：", ":").replace("－", "-").replace("—", "-").replace("–", "-")
    t = t.strip(" \t:;,-|")
    t = re.sub(r"\s+", " ", t)
    return t

# 회사명 문자열 정규화 전용 함수
def norm_company(s: str) -> str:
    t = norm(s)
    t = re.sub(r"\([^)]*\)", "", t).strip()
    t = re.split(r"(?:Tel\.?|Phone|Fax|E-?mail|Email|www\.|https?://|주소|전화|팩스)\b", t, maxsplit=1)[0].strip()
    t = re.sub(r"[|•]+", " ", t)
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t

# 입력된 한 줄이 '잡음라인'인지 판단하는 함수
def is_noise_line(s: str) -> bool:
    t = s.strip()
    if not t: return True
    if PAGE_NAV_PAT.match(t) or PAGE_MARK_PAT.match(t): return True
    if HTML_TAG_LINE_PAT.match(t): return True
    return False

# 라벨 뒤의 값을 안전하게 추출하기 위한 헬퍼 함수
def safe_value_after_label(line: str, safe_label_re: re.Pattern) -> Optional[str]:
    m = re.split(r"[:\-–]\s*", line, maxsplit=1)
    if len(m) == 2:
        left, right = norm(m[0]), norm(m[1])
        if safe_label_re.match(left) and right:
            return right
    return None

# Section 1 (제품 및 회사에 관한 정보) 블록에서 불필요한 라인을 걸러내는 후처리 함수
def clean_section1_lines(lines: List[str]) -> List[str]:
    out = []
    for ln in lines:
        t = ln.strip()
        if not t: continue
        if COPYRIGHT_STOPWORDS.search(t): continue
        if DOC_TITLE_STOP.search(t): continue
        if t.startswith("| ---"): continue
        if re.match(r"^\|\s*[^|]+\s*\|$", t): continue
        if CODE_LABEL_RX.search(t): continue
        out.append(ln)
    return out