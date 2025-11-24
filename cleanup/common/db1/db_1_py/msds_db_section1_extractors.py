from __future__ import annotations
import re
from typing import List, Optional
from msds_db_regex import (
    PRODUCT_LABELS, SAFE_NAME_LABEL,
    ADDR_PAT, PHONE_PAT, EMAIL_PAT, WEB_PAT,
    COMPANY_LABELS, COMPANY_CAND_PAT, SAFE_COMPANY_LABEL,
    MD_HEADER_RE, HEADER_BAD_FOR_COMPANY, CONTACT_LABEL_RE
)
from msds_db_text_norm import norm, safe_value_after_label, is_noise_line, norm_company

"""
[products table 관련]
MSDS 문서의 섹션 1에서 제품명 및 회사명 정보를 추출하는 모듈.

이 모듈은 MSDS(물질안전보건자료) 문서의 텍스트로부터 제품명과 회사명을
찾아내는 함수들을 제공합니다. 다양한 형식의 문서에 대응하기 위해
라벨 기반 탐색, 패턴 매칭, 근접도 점수화 등 여러 휴리스틱 기법을 사용합니다.

주요 기능:
- `collect_product_candidates`: 'Product Name', '제품명' 등의 라벨을
  단서로 문서에서 제품명 후보들을 수집합니다.
- `collect_company_candidates`: 'Company', '제조사' 등의 라벨과
  '(주)', 'Ltd.' 같은 법인 형태 패턴을 이용해 회사명 후보들을 수집합니다.
- `pick_company_weighted_with_label_proximity`: 수집된 회사명 후보들 중,
  라벨과의 근접도 등 여러 요소를 점수화하여 가장 가능성 높은 회사명을 선택합니다.
- `_contains_only_contact_info`: 특정 라인이 주소나 전화번호 같은 연락처
  정보인지를 판별하여 제품명/회사명 후보에서 제외하는 헬퍼 함수입니다.
"""


def _contains_only_contact_info(text: str) -> bool:
    # 0) 라벨 키워드만으로도 즉시 연락처로 판정
    if CONTACT_LABEL_RE.search(text):
        return True

    has_contact = any(p.search(text) for p in (ADDR_PAT, PHONE_PAT, EMAIL_PAT, WEB_PAT))
    if not has_contact:
        return False

    # 의미 있는 단어 수가 매우 적으면 연락처/주소 전용으로 판단
    meaningful_words = re.findall(r'[A-Za-z가-힣]{2,}', text)
    if len(meaningful_words) <= 2:
        return True

    # 숫자 비중이 과한 경우도 연락처로 판단
    digits = sum(ch.isdigit() for ch in text)
    if digits >= max(6, len(text) // 3):
        return True

    # 주소가 길게 포함된 라인
    if len(text) > 40 and ADDR_PAT.search(text):
        return True

    return False


def collect_product_candidates(lines: List[str]) -> List[str]:
    """제품명 후보 수집"""
    out: List[str] = []

    for i, ln in enumerate(lines[:300]):
        if not any(re.search(lbl, ln, flags=re.I) for lbl in PRODUCT_LABELS):
            continue

        # 1) 라벨+값 한 줄 처리
        v = safe_value_after_label(ln, SAFE_NAME_LABEL)
        if v:
            v2 = norm(v)
            if v2 and not any(p.search(v2) for p in [ADDR_PAT, PHONE_PAT, EMAIL_PAT, WEB_PAT]):
                if not _contains_only_contact_info(v2):
                    out.append(v2)
                    continue

        # 2) 같은 줄 콜론/탭/공백 분리
        same = (re.search(r"[:\-–]\s*(.+)$", ln) or
                re.search(r"\t+(.+)$", ln) or
                re.search(r"\s{3,}(.+)$", ln))
        if same:
            v2 = norm(same.group(1))
            if v2 and not any(p.search(v2) for p in [ADDR_PAT, PHONE_PAT, EMAIL_PAT, WEB_PAT]):
                if not _contains_only_contact_info(v2):
                    out.append(v2)

        # 3) 다음 줄 hop 탐색
        for hop in range(1, 8):
            if i + hop >= len(lines):
                break
            raw = lines[i + hop]

            if MD_HEADER_RE.match(raw):
                continue

            cand = norm(raw)
            if not cand or is_noise_line(raw):
                continue
            if any(re.search(lbl, cand, flags=re.I) for lbl in PRODUCT_LABELS):
                continue
            if any(p.search(cand) for p in [ADDR_PAT, PHONE_PAT, EMAIL_PAT, WEB_PAT]):
                continue
            if _contains_only_contact_info(cand):
                continue
            out.append(cand)
            break

    # 중복 제거 및 상위 5개
    uniq, seen = [], set()
    for c in out:
        cc = c.strip()
        if cc and cc.lower() not in seen:
            seen.add(cc.lower())
            uniq.append(cc)
    return uniq[:5]


def collect_company_candidates(lines: List[str]) -> List[str]:
    """회사명 후보 수집"""
    out: List[str] = []

    # 1단계: 라벨 기반 수집
    for i, ln in enumerate(lines[:300]):
        if not any(re.search(lbl, ln, flags=re.I) for lbl in COMPANY_LABELS):
            continue

        # 1) 라벨+값 한 줄 처리 (라벨 접두 제거)
        v = safe_value_after_label(ln, SAFE_COMPANY_LABEL)
        if v:
            vv = norm_company(v)
            vv = re.sub(r'^\s*(?:' + '|'.join(COMPANY_LABELS) + r')\s*[:\-–]?\s*', '', vv, flags=re.I)
            if vv and not any(p.search(vv) for p in [ADDR_PAT, PHONE_PAT, EMAIL_PAT, WEB_PAT]):
                if not _contains_only_contact_info(vv):
                    out.append(vv)
                    continue

        # 2) 같은 줄 콜론/탭/공백 분리
        same = (re.search(r"[:\-–]\s*(.+)$", ln) or
                re.search(r"\t+(.+)$", ln) or
                re.search(r"\s{3,}(.+)$", ln))
        if same:
            vv = norm_company(same.group(1))
            if vv and not any(p.search(vv) for p in [ADDR_PAT, PHONE_PAT, EMAIL_PAT, WEB_PAT]):
                if not _contains_only_contact_info(vv):
                    out.append(vv)

        # 3) 다음 줄 hop 탐색
        for hop in range(1, 8):
            if i + hop >= len(lines):
                break
            raw = lines[i + hop]

            if MD_HEADER_RE.match(raw):
                continue

            cand = norm_company(raw)
            if not cand or is_noise_line(raw):
                continue
            if any(re.search(lbl, cand, flags=re.I) for lbl in COMPANY_LABELS):
                continue
            if any(p.search(cand) for p in [ADDR_PAT, PHONE_PAT, EMAIL_PAT, WEB_PAT]):
                continue
            if _contains_only_contact_info(cand):
                continue
            out.append(cand)
            break

    # 2단계: 회사명 패턴(법인 접미사) 기반 추가 수집
    for i, ln in enumerate(lines[:120]):
        if MD_HEADER_RE.match(ln):
            continue
        t = norm_company(ln)
        if not t or is_noise_line(ln):
            continue
        if _contains_only_contact_info(t):
            continue
        m = COMPANY_CAND_PAT.search(t)
        if m:
            out.append(m.group(0).strip())

    # 3단계: 헤더성 문구 + 연락처 라인 제거
    out = [c for c in out if not HEADER_BAD_FOR_COMPANY.search(c)]
    out = [c for c in out if not any(p.search(c) for p in (ADDR_PAT, PHONE_PAT, EMAIL_PAT, WEB_PAT))]
    out = [c for c in out if not _contains_only_contact_info(c)]

    # 중복 제거 및 상위 5개
    uniq, seen = [], set()
    for c in out:
        cc = c.strip()
        if cc and cc.lower() not in seen:
            seen.add(cc.lower())
            uniq.append(cc)
    return uniq[:5]


def pick_company_weighted_with_label_proximity(lines: List[str], candidates: List[str]) -> Optional[str]:
    """회사명 후보 중 최종 선택 (라벨 근접도 가중)"""
    if not candidates:
        return None

    nlines = [norm_company(x) for x in lines]

    # 라벨 위치 인덱스 수집
    label_idx = [
        i for i, ln in enumerate(nlines)
        if SAFE_COMPANY_LABEL.match(ln) or any(re.search(lbl, ln, re.I) for lbl in COMPANY_LABELS)
    ]

    def score_of(cand: str) -> float:
        s = 0.0

        # 1) 라벨 바로 아래 줄 강가중
        for li in label_idx:
            for off, w in [(1, 2.8), (2, 1.4), (3, 0.7)]:
                idx = li + off
                if 0 <= idx < len(nlines) and cand == nlines[idx]:
                    s += w

        # 2) 헤더성 문구 감점
        if HEADER_BAD_FOR_COMPANY.search(cand):
            s -= 1.5

        # 3) 주소/연락처 강한 감점
        if any(p.search(cand) for p in (ADDR_PAT, PHONE_PAT, EMAIL_PAT, WEB_PAT)):
            s -= 1.5

        # 4) 연락처만 있는 줄 강한 감점 (추가 안전장치)
        if _contains_only_contact_info(cand):
            s -= 2.0

        # 5) 회사명 형태 소폭 가점
        if COMPANY_CAND_PAT.search(cand):
            s += 0.8

        return s

    return max(candidates, key=score_of) or None
