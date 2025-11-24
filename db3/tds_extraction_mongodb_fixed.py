"""
TDS 물성 추출 MongoDB 버전 (수정완료)

문제 해결:
1. LangChain import 오류 수정
2. ChatPromptTemplate 변수 매칭 오류 수정
3. RunnablePassthrough 제거

사용법:
    source venv/bin/activate
    python tds_extraction_mongodb_fixed.py
"""

import os
import re
from typing import List, Dict
from datetime import datetime
from dotenv import load_dotenv
import pymongo
from langchain_ollama import ChatOllama  # 수정: langchain_community 대신 langchain_ollama 사용
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

# ============================================
# 환경 변수
# ============================================
load_dotenv()

MONGO_URI = f"mongodb://{os.getenv('MONGO_INITDB_ROOT_USERNAME')}:{os.getenv('MONGO_INITDB_ROOT_PASSWORD')}@{os.getenv('MONGO_HOST')}:{os.getenv('MONGO_PORT')}/"
RUNPOD_URI = os.getenv('RUNPOD_URI', 'https://bcb7tjvf0wm6jb-11434.proxy.runpod.net/')

# ============================================
# 물성 타입 정의
# ============================================
PROPERTY_NAMES = {
    'Tg': 'Glass Transition Temperature',
    'Tm': 'Melting Temperature',
    'Td': 'Decomposition Temperature',
    'DC': 'Degree of Crystallinity',
    'Eg': 'Band Gap Energy',
    'YS': 'Yield Strength',
    'YM': "Young's Modulus",
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
    'CH4_permeability': 'Methane Permeability',
}

# ============================================
# Regex 패턴
# ============================================
PATTERNS = {
    'Tg': [(r'(?:Glass Transition|Tg)[\s:]+(-?\d+\.?\d*)\s*°?\s*([CF℃])', 1, 2)],
    'Tm': [(r'(?:Melting|Tm)[\s:]+(\d+\.?\d*)\s*°?\s*([CF℃])', 1, 2)],
    'Td': [(r'(?:Decomposition|Td)[\s:]+(\d+\.?\d*)\s*°?\s*([CF℃])', 1, 2)],
    'DC': [(r'(?:Crystallinity|DC)[\s:]+(\d+\.?\d*)\s*%', 1, '%')],
    'YS': [(r'(?:Yield Strength|YS)[\s:]+(\d+\.?\d*)\s*(MPa|GPa|psi)', 1, 2)],
    'YM': [(r"(?:Young's Modulus|YM)[\s:]+(\d+\.?\d*)\s*(MPa|GPa|psi)', 1, 2)],
    'Tensile_Strength': [(r'(?:Tensile Strength)[\s:]+(\d+\.?\d*)\s*(MPa|GPa|psi)', 1, 2)],
    'Elongation_Rate': [(r'(?:Elongation)[\s:]+(\d+\.?\d*)\s*%', 1, '%')],
    'Density': [(r'(?:Density)[\s:]+(\d+\.?\d*)\s*(g/cm³|kg/m³)', 1, 2)],
    'Thermal_Conductivity': [(r'(?:Thermal Conductivity)[\s:]+(\d+\.?\d*)\s*(W/m·K|W/mK)', 1, 2)],
}

# ============================================
# Regex 추출
# ============================================
def detect_all_properties(text: str) -> List[Dict]:
    """Regex로 물성 추출"""
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
                            'extraction_method': 'regex',
                        })
                        seen.add(key)
                except (ValueError, IndexError):
                    continue

    return properties

# ============================================
# LLM 추출 (수정됨)
# ============================================
class PropertyExtractionAgent:
    def __init__(self):
        self.llm = ChatOllama(
            base_url=RUNPOD_URI,
            model="qwen2.5:7b",
            temperature=0.0,
        )

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """Extract material properties from TDS markdown.
Output JSON array: [{"property": "Tg", "value": 120.5, "unit": "°C", "matched_name": "Glass Transition Temperature"}]
Property types: Tg, Tm, Td, DC, Eg, YS, YM, BS, Tensile_Strength, Elongation_Rate, Hardness, HDT, Thermal_Conductivity, Density, Viscosity
Return [] if none found."""),
            ("human", "{text}"),
        ])

        # 수정: RunnablePassthrough 제거, 직접 연결
        self.chain = self.prompt | self.llm | JsonOutputParser()

    def extract_properties(self, text: str) -> List[Dict]:
        """LLM으로 물성 추출"""
        try:
            # 수정: invoke에 딕셔너리 직접 전달
            result = self.chain.invoke({"text": text[:8000]})

            if isinstance(result, list):
                for prop in result:
                    prop['extraction_method'] = 'llm'
                return result
            return []
        except Exception as e:
            print(f"LLM 추출 오류: {e}")
            return []

# ============================================
# 하이브리드 병합
# ============================================
def merge_properties(llm_props: List[Dict], regex_props: List[Dict]) -> List[Dict]:
    """LLM 우선, Regex 보완"""
    merged = {}

    for prop in llm_props:
        merged[prop['property']] = prop

    for prop in regex_props:
        if prop['property'] not in merged:
            merged[prop['property']] = prop

    return list(merged.values())

# ============================================
# 메인 파이프라인
# ============================================
def process_document(doc_id: str, doc: Dict, mongodb, use_llm: bool = True) -> Dict:
    """단일 문서 처리"""
    print(f"\n{'='*70}")
    print(f"📄 문서: {doc_id}")
    print(f"{'='*70}")

    content = doc.get('content', '')
    file_name = doc.get('file_name', None)

    # 1) LLM 추출
    llm_properties: List[Dict] = []
    if use_llm:
        try:
            print("🤖 LLM 추출 시작...")
            llm_agent = PropertyExtractionAgent()
            llm_properties = llm_agent.extract_properties(content)
            print(f"✅ LLM 추출: {len(llm_properties)}개")
        except Exception as e:
            print(f"❌ LLM 오류: {e}")

    # 2) Regex 추출
    regex_properties = detect_all_properties(content)
    print(f"✅ Regex 추출: {len(regex_properties)}개")

    # 3) 병합
    if llm_properties:
        properties = merge_properties(llm_properties, regex_properties)
        print(f"📊 병합: 총 {len(properties)}개")
    else:
        properties = regex_properties
        print(f"⚠️  LLM 실패 - Regex만 사용: {len(properties)}개")

    # 4) MongoDB 저장
    temp_collection = mongodb['temp_extraction']
    for prop in properties:
        temp_collection.insert_one({
            'document_id': doc_id,
            'property_field': prop['property'],
            'property_value': prop['value'],
            'property_unit': prop['unit'],
            'matched_name': prop.get('matched_name', ''),
            'extraction_method': prop.get('extraction_method', 'regex'),
        })

    # 5) 요약 저장
    summary_collection = mongodb['tds_summary']
    now = datetime.utcnow()

    summary_collection.update_one(
        {'document_id': doc_id},
        {
            '$set': {
                'document_id': doc_id,
                'file_name': file_name,
                'properties': properties,
                'updated_at': now,
            },
            '$setOnInsert': {'created_at': now},
        },
        upsert=True,
    )

    print(f"\n📋 최종 결과: {len(properties)}개")
    for prop in properties:
        print(f"  - {prop['property']}: {prop['value']} {prop['unit']} [{prop.get('extraction_method', 'unknown')}]")

    return {
        'document_id': doc_id,
        'property_count': len(properties),
        'properties': properties,
    }


def main():
    """메인 실행"""
    print("=" * 70)
    print("TDS 물성 추출 파이프라인 (MongoDB Only - 수정버전)")
    print("=" * 70)

    # MongoDB 연결
    mongo_client = pymongo.MongoClient(MONGO_URI)
    mongodb = mongo_client['s307_db']
    print(f"✅ MongoDB 연결: {MONGO_URI}")

    # 처리 대상 문서
    markdown_collection = mongodb['markdown_collection']
    documents = list(markdown_collection.find({'document_id': {'$regex': '^MOCK_'}}))

    print(f"\n📚 처리 대상: {len(documents)}개 문서\n")

    results = []
    for doc in documents:
        result = process_document(doc['document_id'], doc, mongodb, use_llm=True)
        results.append(result)

    # 요약
    print(f"\n{'='*70}")
    print("✅ 파이프라인 완료!")
    print(f"{'='*70}")
    print(f"총 {len(results)}개 문서 처리")
    total_props = sum(r['property_count'] for r in results)
    avg_props = total_props / len(results) if results else 0
    print(f"총 {total_props}개 물성 추출")
    print(f"평균 {avg_props:.1f}개 물성/문서")

    mongo_client.close()


if __name__ == "__main__":
    main()
