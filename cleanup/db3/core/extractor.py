"""
[핵심] 물성 추출기 (Extractor)

역할:
- 정규식 기반 패턴 매칭으로 TDS 마크다운에서 물성 추출
- properties_dict.py 정의된 23개 물성 자동 추출
- 값(숫자)과 단위 분리 추출

주요 함수:
    extract_property_from_text(text, property_key)  → 특정 물성 1개 추출
    detect_all_properties(markdown_text)            → 모든 물성 추출

추출 패턴:
    - "Tg: 150 ℃"           (콜론 형식)
    - "Tg 150 ℃"            (공백 형식)
    - "Tg (유리전이온도): 150℃"  (설명 포함)

특징:
    - 한글/영문 이름 모두 인식
    - 단위 자동 파싱 (%, ℃, MPa, GPa 등)
    - 중복 제거 (같은 물성 여러 번 나와도 첫 번째만)
"""

import re
from typing import List, Dict, Optional
from properties_dict import PROPERTY_PATTERNS, add_dynamic_property


def extract_property_from_text(text: str, property_key: str) -> Optional[Dict]:
    """
    텍스트에서 특정 물성 추출

    Args:
        text: Markdown 텍스트
        property_key: 물성 키 (예: 'Tg', 'Tm')

    Returns:
        추출된 물성 정보 dict 또는 None
    """
    if property_key not in PROPERTY_PATTERNS:
        return None

    prop = PROPERTY_PATTERNS[property_key]

    # 모든 가능한 이름으로 검색
    for name in prop['names']:
        # 다양한 패턴 시도
        patterns = [
            # "Tg: 150 ℃" 또는 "Tg : 150℃"
            rf'{re.escape(name)}\s*[:：=]\s*([0-9.]+)\s*([^\s\n,;]+)?',
            # "Tg 150 ℃" (콜론 없음)
            rf'{re.escape(name)}\s+([0-9.]+)\s*([^\s\n,;]+)?',
            # "Tg(℃): 150" 또는 "Tg (유리전이온도): 150℃"
            rf'{re.escape(name)}\s*\([^)]*\)\s*[:：=]?\s*([0-9.]+)\s*([^\s\n,;]+)?',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            if matches:
                # 첫 번째 매치 사용
                match = matches[0]

                # 값과 단위 파싱
                if len(match) >= 1:
                    value_str = match[0]
                    unit = match[1] if len(match) > 1 else ''

                    # 단위 정리 (앞뒤 공백, 특수문자 제거)
                    unit = unit.strip()
                    if unit and not any(c.isalnum() or c in ['/', '·', '²', '³', '°', '℃', '%'] for c in unit):
                        unit = ''

                    try:
                        value = float(value_str)

                        return {
                            'property': property_key,
                            'value': value,
                            'unit': unit,
                            'matched_name': name,
                            'pattern': pattern
                        }
                    except ValueError:
                        continue

    return None


def detect_all_properties(markdown_text: str) -> List[Dict]:
    """
    Markdown에서 모든 물성 정보 추출

    Args:
        markdown_text: Markdown 문서 내용

    Returns:
        추출된 물성 정보 리스트
    """
    detected_properties = []

    # 사전에 등록된 모든 물성 검색
    for property_key in PROPERTY_PATTERNS.keys():
        result = extract_property_from_text(markdown_text, property_key)
        if result:
            detected_properties.append(result)

    return detected_properties


def detect_unknown_properties(markdown_text: str, detected_properties: List[Dict]) -> List[Dict]:
    """
    미등록 물성 자동 감지
    "항목명: 숫자 단위" 패턴 중 아직 매칭 안 된 것 찾기

    Args:
        markdown_text: Markdown 문서 내용
        detected_properties: 이미 감지된 물성 리스트

    Returns:
        새로 발견된 물성 리스트
    """
    # 이미 매칭된 항목명
    matched_names = set()
    for prop in detected_properties:
        matched_names.add(prop['matched_name'])

    # 일반적인 패턴으로 전체 스캔
    generic_pattern = r'([A-Za-z가-힣][A-Za-z가-힣\s]+?)\s*[:：=]\s*([0-9.]+)\s*([A-Za-z/²³·℃°%]+)?'
    matches = re.findall(generic_pattern, markdown_text, re.MULTILINE)

    unknown_props = []
    for name, value, unit in matches:
        name = name.strip()

        # 이미 매칭됐으면 skip
        if name in matched_names:
            continue

        # 너무 긴 이름 제외 (문장일 가능성)
        if len(name) > 50:
            continue

        try:
            unknown_props.append({
                'property': f'Unknown_{name.replace(" ", "_")}',
                'value': float(value),
                'unit': unit.strip() if unit else '',
                'matched_name': name,
                'pattern': 'generic'
            })
        except ValueError:
            continue

    return unknown_props


def extract_with_context(markdown_text: str, include_unknown: bool = False) -> Dict:
    """
    문맥 정보 포함한 전체 추출

    Args:
        markdown_text: Markdown 문서 내용
        include_unknown: 미등록 물성도 포함할지 여부

    Returns:
        추출 결과 dict
    """
    # 정의된 물성 추출
    detected = detect_all_properties(markdown_text)

    # 미등록 물성 추출 (옵션)
    unknown = []
    if include_unknown:
        unknown = detect_unknown_properties(markdown_text, detected)

    return {
        'detected_properties': detected,
        'unknown_properties': unknown,
        'total_count': len(detected) + len(unknown)
    }


if __name__ == "__main__":
    # 테스트
    sample_text = """
    # 소재 물성 정보

    Tg: 150 ℃
    Tm (용융온도): 180°C
    항복강도(YS): 500 MPa
    DC (유전상수) = 3.5
    영률: 2.5 GPa
    He투과율: 15.2 cm³/m²

    새로운속성: 123 units
    """

    print("=" * 50)
    print("물성 추출 테스트")
    print("=" * 50)

    result = extract_with_context(sample_text, include_unknown=True)

    print(f"\n✅ 정의된 물성: {len(result['detected_properties'])}개")
    for prop in result['detected_properties']:
        print(f"  - {prop['property']}: {prop['value']} {prop['unit']} (매칭: {prop['matched_name']})")

    print(f"\n❓ 미등록 물성: {len(result['unknown_properties'])}개")
    for prop in result['unknown_properties']:
        print(f"  - {prop['property']}: {prop['value']} {prop['unit']}")
