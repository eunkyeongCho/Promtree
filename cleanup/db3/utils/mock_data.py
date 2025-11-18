"""
[보조] Mock 데이터 생성

역할:
- 파서팀 데이터 대기 중 테스트용 가짜 TDS 문서 생성
- MongoDB markdown_collection에 5개 샘플 문서 저장
- 파이프라인 개발 및 테스트용

Mock 문서 (5개):
    - MOCK_TDS_001: STS304 (10개 물성)
    - MOCK_TDS_002: Polymer A (13개 물성)
    - MOCK_TDS_003: Composite B (11개 물성)
    - MOCK_TDS_004: Advanced Polymer C (9개 물성)
    - MOCK_TDS_005: Special Material D (8개 물성)

실행:
    python mock_data.py  → MongoDB에 Mock 데이터 생성

주의:
    - 파서팀 실제 데이터가 오면 삭제 가능
    - document_id가 'MOCK_'로 시작 (실제 데이터와 구분)
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))

from db_connection import get_mongodb


def create_mock_markdown_db(mongodb):
    """
    파싱 팀 대기 중이니 가짜 Markdown 데이터로 테스트
    """
    collection = mongodb['markdown_collection']

    # 기존 Mock 데이터 삭제 (재실행 시)
    collection.delete_many({'document_id': {'$regex': '^MOCK_'}})

    mock_documents = [
        {
            "document_id": "MOCK_TDS_001",
            "file_name": "STS304_datasheet.pdf",
            "content": """
# STS304 소재 물성 정보

## 기본 정보
- 소재명: STS304 Stainless Steel
- 제조사: Samsung Materials

## 열적 특성
- Tg (유리전이온도): 150 ℃
- Tm (용융온도): 1450 ℃
- Td (열분해온도): 1600 ℃

## 전기적 특성
- DC (유전상수): 3.5

## 기계적 특성
- YS (항복강도): 215 MPa
- YM (영률): 193 GPa
- Tensile Strength: 505 MPa
- Elongation Rate: 40 %

## 기타
- Density: 8.0 g/cm³
- Thermal Conductivity: 16.2 W/m·K
            """
        },
        {
            "document_id": "MOCK_TDS_002",
            "file_name": "Polymer_A_spec.pdf",
            "content": """
# Polymer A 물성표

소재 코드: PA-2024-001

## Thermal Properties
Tg: 120°C
Tm: 180°C
Td: 350°C
HDT: 95°C

## Mechanical Properties
항복강도(YS): 450 MPa
영률: 2.5 GPa
굽힘강도: 80 MPa
Hardness (Shore A): 85

## Electrical
DC (유전상수): 4.2
Eg (에너지 밴드갭): 2.8 eV

## Gas Permeability
He투과율: 15.2 cm³/m²
O2투과율: 45.7 cm³/m²
N2투과율: 12.3 cm³/m²
            """
        },
        {
            "document_id": "MOCK_TDS_003",
            "file_name": "Composite_B_tds.pdf",
            "content": """
# Composite Material B - Technical Data Sheet

## Material Identification
Material Name: High-Performance Composite B
Grade: HP-B-2024

## Physical Properties
- Density: 1.42 g/cm³
- 점도: 850 cP

## Thermal Analysis
- Glass Transition Temperature (Tg): 165 K
- Melting Point: 225 ℃
- Decomposition Temperature: 400 ℃

## Mechanical Testing Results
- Yield Strength: 320 N/mm²
- Young's Modulus: 3200 MPa
- Bending Strength (BS): 115 Nm²

## Barrier Properties
- CO2 투과율: 8.5 cm³/m²
- CH4 투과율: 6.2 cm³/m²
            """
        },
        {
            "document_id": "MOCK_TDS_004",
            "file_name": "Advanced_Polymer_C.pdf",
            "content": """
Advanced Polymer C Specification

물성 데이터:

Tg = 95℃
Tm(TDS/LDS) = 175℃
Modulus = 2800 MPa
Thixotropic index = 1.85
점도 = 1200 cP
Hardness (Shore A) = 78
Tensile Strength = 480 MPa
Elongation Rate = 25%
Thermal Conductivity = 0.25 W/m·K

추가 정보:
- 측정 온도: 23℃
- 상대 습도: 50%
            """
        },
        {
            "document_id": "MOCK_TDS_005",
            "file_name": "Special_Material_D.pdf",
            "content": """
## Special Material D - 특수 소재 D

### 에너지 관련
- Eg (에너지 밴드갭): 3.2 eV
- PL: 확인 필요

### 투과율 테스트
He: 22.5 barrier cm³/m²
H2: 18.3 cm³/m²
O2: 52.1 cm³/m²

### 기계 강도
YS (항복강도): 580 ksi
BS (굽힘강도): 95 Pam3

### 기타
HDT: 110℃
Density: 2.15 g/cm³
            """
        }
    ]

    result = collection.insert_many(mock_documents)
    print(f"✅ Mock 데이터 {len(result.inserted_ids)}개 삽입 완료")

    return mock_documents


def verify_mock_data(mongodb):
    """
    Mock 데이터 확인
    """
    collection = mongodb['markdown_collection']

    print("\n📄 저장된 Mock 문서:")
    for doc in collection.find({'document_id': {'$regex': '^MOCK_'}}):
        print(f"  - {doc['document_id']}: {doc['file_name']}")
        # 첫 100자만 출력
        content_preview = doc['content'][:100].replace('\n', ' ')
        print(f"    내용: {content_preview}...")


if __name__ == "__main__":
    print("=" * 50)
    print("Mock Markdown DB 생성")
    print("=" * 50)

    mongodb = get_mongodb()

    if mongodb is not None:
        mock_docs = create_mock_markdown_db(mongodb)
        verify_mock_data(mongodb)

        print(f"\n✅ 총 {len(mock_docs)}개 Mock 문서 준비 완료")
        print("\n다음 단계: python extractor.py 실행")
