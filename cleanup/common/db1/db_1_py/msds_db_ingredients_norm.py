from __future__ import annotations
import re
from msds_db_regex import CONTROL_WS, DOT_LIKE, FULLWIDTH

"""
[ingredients table 관련]
텍스트 분석을 위한 문자열 정규화(Normalization) 모듈.

이 모듈은 텍스트 비교 및 검색의 정확도를 높이기 위해 문자열을 표준 형식으로
변환하는 함수들을 제공합니다. 또한, 텍스트의 구조적 특징(예: 마크다운 테이블)을
판별하는 헬퍼 함수도 포함합니다.

주요 기능:
- `norm_lower`: 제어 문자, 특수 공백, 마크다운 서식 등을 제거하고
  모든 문자를 소문자로 변환하여 '검색 친화적인' 표준 형식으로 만듭니다.
- `is_table_line_raw`: 주어진 라인이 마크다운 테이블의 행 형식인지 판별합니다.
"""


# 문자열을 '검색/비교 친화적 소문자 표준형'으로 정규화
def norm_lower(s: str) -> str:
    """
    문자열을 '검색 및 비교 친화적인' 소문자 표준 형식으로 정규화합니다.

    이 함수는 다음과 같은 정규화 단계를 순차적으로 수행합니다:
    1. 제어 문자(`CONTROL_WS`)를 공백으로 변환합니다.
    2. 점과 유사한 유니코드 문자(`DOT_LIKE`)를 표준 온점('.')으로 통일합니다.
    3. 전각 문자(`FULLWIDTH`)를 해당하는 반각 문자로 변환합니다.
    4. 다양한 유니코드 공백 문자를 표준 공백(' ')으로 바꿉니다.
    5. 마크다운 서식 문자('*', '_', '`')를 제거합니다.
    6. 탭 문자를 공백으로 변환합니다.
    7. 문자열 양 끝의 공백, 탭, 및 특정 구분자들을 제거합니다.
    8. 연속된 여러 공백을 단일 공백으로 축약합니다.
    9. 최종적으로 모든 문자를 소문자로 변환합니다.

    Args:
        s (str): 정규화할 원본 문자열.

    Returns:
        str: 정규화된 소문자 문자열.
    
    Example:
        >>> norm_lower("  *Hello*　World！  ")
        'hello world!'
    """
    t = CONTROL_WS.sub(" ", s)
    t = s.translate(DOT_LIKE).translate(FULLWIDTH)
    t = re.sub(r"[\u2000-\u200B\u2060\u00A0\u00AD]", " ", t)
    t = re.sub(r"[*_`]+", "", t)
    t = t.replace("\t", " ")
    t = t.strip(" \t:;,-|")
    t = re.sub(r"\s+", " ", t)
    return t.lower()

# Markdown 표 형태의 라인 여부를 판별
def is_table_line_raw(ln: str) -> bool:
    """
    주어진 라인이 마크다운(Markdown) 테이블의 행 형식인지 판별합니다.

    판별 기준은 다음과 같습니다:
    - 라인의 양 끝 공백을 제거했을 때, '|'로 시작하고 '|'로 끝나야 합니다.
    - 라인에 포함된 '|' 문자가 2개 이상이어야 합니다 (최소 1개 열).

    Args:
        ln (str): 검사할 한 줄의 문자열.

    Returns:
        bool: 마크다운 테이블 행 형식이면 True, 아니면 False.

    Example:
        >>> is_table_line_raw("| Column 1 | Column 2 |")
        True
        >>> is_table_line_raw("  | A | B |  ")
        True
        >>> is_table_line_raw("This is not a table line.")
        False
        >>> is_table_line_raw("| Incomplete ")
        False
    """
    s = ln.strip()
    return s.startswith("|") and s.endswith("|") and s.count("|") >= 2