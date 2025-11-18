"""
TDS 물성 추출 올인원 스크립트 🚀

사용법:
    1. MongoDB에 TDS 마크다운 문서 저장
    2. .env 파일 설정 (MongoDB, PostgreSQL 연결 정보)
    3. python tds_extraction_standalone.py 실행

요구사항:
    - MongoDB에 markdown_collection (document_id, content 필드)
    - PostgreSQL DB (tds_properties 테이블 자동 생성)
    - RunPod Ollama URL (RUNPOD_OLLAMA_URI 환경변수)

출력:
    - MongoDB temp_extraction: 임시 추출 결과
    - PostgreSQL tds_properties: 최종 물성 데이터

추출 전략:
    1. LLM 추출 (RunPod Ollama qwen2.5:7b) - 컨텍스트 이해
    2. Regex 추출 - LLM 누락 물성 보완
    3. 하이브리드 병합 - 최종 결과 최적화
"""

import os
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv
import pymongo
import psycopg2
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnablePassthrough

# ============================================
# 1. 환경 변수 로드
# ============================================

load_dotenv()

MONGO_URI = f"mongodb://{os.getenv('MONGO_INITDB_ROOT_USERNAME')}:{os.getenv('MONGO_INITDB_ROOT_PASSWORD')}@{os.getenv('MONGO_HOST')}:{os.getenv('MONGO_PORT')}/"
POSTGRES_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5432'),
    'database': os.getenv('POSTGRES_DB', 'CoreDB'),
    'user': os.getenv('POSTGRES_USER', 'promtree'),
    'password': os.getenv('POSTGRES_PASSWORD', 'ssafy13s307')
}
RUNPOD_OLLAMA_URI = os.getenv('RUNPOD_OLLAMA_URI', 'https://bcb7tjvf0wm6jb-11434.proxy.runpod.net/')

# ============================================
# 2. 물성 타입 정의 (23개)
# ============================================

PROPERTY_NAMES = {
    'Tg': 'Glass Transition Temperature',
    'Tm': 'Melting Temperature',
    'Td': 'Decomposition Temperature',
    'DC': 'Degree of Crystallinity',
    'Eg': 'Band Gap Energy',
    'YS': 'Yield Strength',
    'YM': 'Young\'s Modulus',
    'BS': 'Bending Strength',
    'Tensile_Strength': 'Tensile Strength',
    'Elongation_Rate': 'Elongation at Break',
    'Hardness': 'Hardness',
    'HDT': 'Heat Deflection Temperature',
    'Thermal_Conductivity': 'Thermal Conductivity',
    'Density': 'Density',
    'Viscosity': 'Viscosity',
    'Thixotropic_index': 'Thixotropic Index',
    'He_permeability': 'Helium Permeability',
    'H2_permeability': 'Hydrogen Permeability',
    'O2_permeability': 'Oxygen Permeability',
    'N2_permeability': 'Nitrogen Permeability',
    'CO2_permeability': 'Carbon Dioxide Permeability',
    'CH4_permeability': 'Methane Permeability'
}

# ============================================
# 3. Regex 패턴 (23개 물성)
# ============================================

PATTERNS = {
    'Tg': [
        (r'(?:Glass Transition|Tg)[\s:]+(-?\d+\.?\d*)\s*°?\s*([CF])', 1, 2),
        (r'Tg\s*[=:~]\s*(-?\d+\.?\d*)\s*°?\s*([CF])', 1, 2),
    ],
    'Tm': [
        (r'(?:Melting Point|Melting Temperature|Tm)[\s:]+(\d+\.?\d*)\s*°?\s*([CF])', 1, 2),
        (r'Tm\s*[=:~]\s*(\d+\.?\d*)\s*°?\s*([CF])', 1, 2),
    ],
    'Td': [
        (r'(?:Decomposition Temperature|Td)[\s:]+(\d+\.?\d*)\s*°?\s*([CF])', 1, 2),
    ],
    'DC': [
        (r'(?:Degree of Crystallinity|Crystallinity)[\s:]+(\d+\.?\d*)\s*%', 1, '%'),
    ],
    'Eg': [
        (r'(?:Band Gap|Eg)[\s:]+(\d+\.?\d*)\s*(eV)', 1, 2),
    ],
    'YS': [
        (r'(?:Yield Strength|YS)[\s:]+(\d+\.?\d*)\s*(MPa|GPa|psi)', 1, 2),
    ],
    'YM': [
        (r'(?:Young\'s Modulus|Elastic Modulus|YM)[\s:]+(\d+\.?\d*)\s*(MPa|GPa|psi)', 1, 2),
    ],
    'BS': [
        (r'(?:Bending Strength|Flexural Strength|BS)[\s:]+(\d+\.?\d*)\s*(MPa|GPa|psi)', 1, 2),
    ],
    'Tensile_Strength': [
        (r'(?:Tensile Strength|TS)[\s:]+(\d+\.?\d*)\s*(MPa|GPa|psi)', 1, 2),
    ],
    'Elongation_Rate': [
        (r'(?:Elongation at Break|Elongation)[\s:]+(\d+\.?\d*)\s*%', 1, '%'),
    ],
    'Hardness': [
        (r'(?:Hardness|Shore)[\s:]+(\d+\.?\d*)\s*(Shore [AD]|HRC|HRB)', 1, 2),
    ],
    'HDT': [
        (r'(?:Heat Deflection Temperature|HDT)[\s:]+(\d+\.?\d*)\s*°?\s*([CF])', 1, 2),
    ],
    'Thermal_Conductivity': [
        (r'(?:Thermal Conductivity)[\s:]+(\d+\.?\d*)\s*(W/m·K|W/mK)', 1, 2),
    ],
    'Density': [
        (r'(?:Density)[\s:]+(\d+\.?\d*)\s*(g/cm³|kg/m³)', 1, 2),
    ],
    'Viscosity': [
        (r'(?:Viscosity)[\s:]+(\d+\.?\d*)\s*(Pa·s|cP|mPa·s)', 1, 2),
    ],
    'Thixotropic_index': [
        (r'(?:Thixotropic Index|TI)[\s:]+(\d+\.?\d*)', 1, ''),
    ],
    'He_permeability': [
        (r'(?:He Permeability|Helium Permeability)[\s:]+(\d+\.?\d*(?:e[+-]?\d+)?)\s*(barrer|cm³·mm/m²·day·atm)', 1, 2),
    ],
    'H2_permeability': [
        (r'(?:H2 Permeability|Hydrogen Permeability)[\s:]+(\d+\.?\d*(?:e[+-]?\d+)?)\s*(barrer|cm³·mm/m²·day·atm)', 1, 2),
    ],
    'O2_permeability': [
        (r'(?:O2 Permeability|Oxygen Permeability)[\s:]+(\d+\.?\d*(?:e[+-]?\d+)?)\s*(barrer|cm³·mm/m²·day·atm)', 1, 2),
    ],
    'N2_permeability': [
        (r'(?:N2 Permeability|Nitrogen Permeability)[\s:]+(\d+\.?\d*(?:e[+-]?\d+)?)\s*(barrer|cm³·mm/m²·day·atm)', 1, 2),
    ],
    'CO2_permeability': [
        (r'(?:CO2 Permeability|Carbon Dioxide Permeability)[\s:]+(\d+\.?\d*(?:e[+-]?\d+)?)\s*(barrer|cm³·mm/m²·day·atm)', 1, 2),
    ],
    'CH4_permeability': [
        (r'(?:CH4 Permeability|Methane Permeability)[\s:]+(\d+\.?\d*(?:e[+-]?\d+)?)\s*(barrer|cm³·mm/m²·day·atm)', 1, 2),
    ],
}

# ============================================
# 4. Regex 추출 함수
# ============================================

def detect_all_properties(text: str) -> List[Dict]:
    """Regex로 모든 물성 추출"""
    properties = []
    seen = set()

    for prop_name, patterns in PATTERNS.items():
        for pattern, value_group, unit_group in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    value = float(match.group(value_group))
                    unit = match.group(unit_group) if isinstance(unit_group, int) else unit_group

                    key = (prop_name, value, unit)
                    if key not in seen:
                        properties.append({
                            'property': prop_name,
                            'value': value,
                            'unit': unit,
                            'matched_name': PROPERTY_NAMES.get(prop_name, prop_name),
                            'extraction_method': 'regex'
                        })
                        seen.add(key)
                except (ValueError, IndexError):
                    continue

    return properties

# ============================================
# 5. LLM 추출 (LangChain + RunPod Ollama)
# ============================================

class PropertyExtractionAgent:
    def __init__(self):
        self.llm = ChatOllama(
            base_url=RUNPOD_OLLAMA_URI,
            model="qwen2.5:7b",
            temperature=0.0
        )

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a TDS (Technical Data Sheet) property extraction expert.
Extract material properties from the given markdown text.

Output format (JSON array):
[
    {{"property": "Tg", "value": 120.5, "unit": "°C", "matched_name": "Glass Transition Temperature"}},
    {{"property": "Tm", "value": 250.0, "unit": "°C", "matched_name": "Melting Temperature"}}
]

Property types to extract (23 types):
Tg, Tm, Td, DC, Eg, YS, YM, BS, Tensile_Strength, Elongation_Rate, Hardness, HDT,
Thermal_Conductivity, Density, Viscosity, Thixotropic_index,
He_permeability, H2_permeability, O2_permeability, N2_permeability, CO2_permeability, CH4_permeability

If no properties found, return empty array []."""),
            ("human", "{text}")
        ])

        self.chain = (
            {"text": RunnablePassthrough()}
            | self.prompt
            | self.llm
            | JsonOutputParser()
        )

    def extract_properties(self, text: str) -> List[Dict]:
        """LLM으로 물성 추출"""
        try:
            result = self.chain.invoke(text[:8000])  # 토큰 제한
            if isinstance(result, list):
                for prop in result:
                    prop['extraction_method'] = 'llm'
                return result
            return []
        except Exception as e:
            print(f"LLM 추출 오류: {e}")
            return []

# ============================================
# 6. 하이브리드 병합
# ============================================

def merge_properties(llm_props: List[Dict], regex_props: List[Dict]) -> List[Dict]:
    """LLM 우선, Regex로 보완"""
    merged = {}

    # LLM 결과 먼저
    for prop in llm_props:
        key = prop['property']
        merged[key] = prop

    # Regex로 누락 추가
    for prop in regex_props:
        key = prop['property']
        if key not in merged:
            merged[key] = prop

    return list(merged.values())

# ============================================
# 7. PostgreSQL 테이블 관리
# ============================================

def ensure_column_exists(cursor, property_name: str):
    """동적으로 컬럼 생성"""
    value_col = f"{property_name.lower()}_value"
    unit_col = f"{property_name.lower()}_unit"

    cursor.execute(f"""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'tds_properties' AND column_name = '{value_col}'
    """)

    if not cursor.fetchone():
        cursor.execute(f"ALTER TABLE tds_properties ADD COLUMN {value_col} FLOAT")
        cursor.execute(f"ALTER TABLE tds_properties ADD COLUMN {unit_col} VARCHAR(50)")

def create_tables(postgres_conn):
    """초기 테이블 생성"""
    cursor = postgres_conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tds_properties (
            id SERIAL PRIMARY KEY,
            document_id VARCHAR(100) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    postgres_conn.commit()
    cursor.close()

# ============================================
# 8. 메인 파이프라인
# ============================================

def process_document(doc_id: str, doc: Dict, mongodb, postgres_conn, use_llm: bool = True) -> Dict:
    """단일 문서 처리"""
    print(f"\n{'='*70}")
    print(f"📄 문서: {doc_id}")
    print(f"{'='*70}")

    # LLM 추출
    llm_properties = []
    if use_llm:
        try:
            print(f"🤖 LLM 추출 시작...")
            llm_agent = PropertyExtractionAgent()
            llm_properties = llm_agent.extract_properties(doc['content'])
            print(f"✅ LLM 추출: {len(llm_properties)}개")
        except Exception as e:
            print(f"❌ LLM 오류: {e}")

    # Regex 추출
    regex_properties = detect_all_properties(doc['content'])
    print(f"✅ Regex 추출: {len(regex_properties)}개")

    # 병합
    if llm_properties:
        properties = merge_properties(llm_properties, regex_properties)
        print(f"📊 병합: LLM {len(llm_properties)}개 + Regex 추가 {len(properties)-len(llm_properties)}개 = 총 {len(properties)}개")
    else:
        properties = regex_properties
        print(f"⚠️  LLM 실패 - Regex만 사용: {len(properties)}개")

    # MongoDB temp 저장
    temp_collection = mongodb['temp_extraction']
    for prop in properties:
        temp_collection.insert_one({
            'document_id': doc_id,
            'property_field': prop['property'],
            'property_value': prop['value'],
            'property_unit': prop['unit'],
            'matched_name': prop.get('matched_name', ''),
            'extraction_method': prop.get('extraction_method', 'regex')
        })

    # PostgreSQL 저장
    if postgres_conn:
        cursor = postgres_conn.cursor()
        cursor.execute("INSERT INTO tds_properties (document_id) VALUES (%s) ON CONFLICT (document_id) DO NOTHING", (doc_id,))

        for prop in properties:
            ensure_column_exists(cursor, prop['property'])
            value_col = f"{prop['property'].lower()}_value"
            unit_col = f"{prop['property'].lower()}_unit"
            cursor.execute(f"UPDATE tds_properties SET {value_col} = %s, {unit_col} = %s WHERE document_id = %s",
                         (prop['value'], prop['unit'], doc_id))

        postgres_conn.commit()
        cursor.close()

    print(f"\n📋 최종 추출 결과: {len(properties)}개")
    for prop in properties:
        print(f"  - {prop['property']}: {prop['value']} {prop['unit']} [{prop.get('extraction_method', 'unknown')}]")

    return {'document_id': doc_id, 'property_count': len(properties), 'properties': properties}

def main():
    """메인 실행"""
    print("="*70)
    print("TDS 물성 추출 파이프라인 (올인원)")
    print("LLM 우선 + Regex 보완 하이브리드 전략")
    print("="*70)

    # MongoDB 연결
    mongo_client = pymongo.MongoClient(MONGO_URI)
    mongodb = mongo_client['s307_db']
    print(f"✅ MongoDB 연결: {MONGO_URI}")

    # PostgreSQL 연결
    try:
        postgres_conn = psycopg2.connect(**POSTGRES_CONFIG)
        create_tables(postgres_conn)
        print(f"✅ PostgreSQL 연결: {POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}")
    except Exception as e:
        print(f"⚠️  PostgreSQL 연결 실패: {e}")
        postgres_conn = None

    # 문서 처리
    markdown_collection = mongodb['markdown_collection']
    documents = list(markdown_collection.find({'document_id': {'$regex': '^MOCK_'}}))  # Mock 데이터 필터

    print(f"\n📚 처리 대상: {len(documents)}개 문서\n")

    results = []
    for doc in documents:
        result = process_document(doc['document_id'], doc, mongodb, postgres_conn, use_llm=True)
        results.append(result)

    # 요약
    print(f"\n{'='*70}")
    print(f"✅ 파이프라인 완료!")
    print(f"{'='*70}")
    print(f"총 {len(results)}개 문서 처리")
    total_props = sum(r['property_count'] for r in results)
    print(f"총 {total_props}개 물성 추출")
    print(f"평균 {total_props/len(results):.1f}개 물성/문서")

    if postgres_conn:
        postgres_conn.close()
    mongo_client.close()

if __name__ == "__main__":
    main()
