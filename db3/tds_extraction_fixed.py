"""
TDS 물성 추출 (Fixed - LangChain 최신 버전)
"""
import os
import re
from typing import List, Dict
from datetime import datetime
from dotenv import load_dotenv
import pymongo

# LangChain imports (최신 버전)
try:
    from langchain_ollama import ChatOllama  # 최신 버전
except ImportError:
    from langchain_community.chat_models import ChatOllama  # 구버전 fallback

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

load_dotenv()

MONGO_URI = f"mongodb://{os.getenv('MONGO_INITDB_ROOT_USERNAME')}:{os.getenv('MONGO_INITDB_ROOT_PASSWORD')}@{os.getenv('MONGO_HOST')}:{os.getenv('MONGO_PORT')}/"
RUNPOD_URI = os.getenv('RUNPOD_URI', 'https://bcb7tjvf0wm6jb-11434.proxy.runpod.net/')

# Regex 패턴 (간소화)
PATTERNS = {
    'Tg': [(r'Tg.*?(\d+\.?\d*)\s*°?\s*([CF])', 1, 2)],
    'Tm': [(r'Tm.*?(\d+\.?\d*)\s*°?\s*([CF])', 1, 2)],
    'YS': [(r'YS.*?(\d+\.?\d*)\s*(MPa|GPa)', 1, 2)],
    'Density': [(r'Density.*?(\d+\.?\d*)\s*(g/cm³|kg/m³)', 1, 2)],
}

def extract_regex(text: str) -> List[Dict]:
    """Regex 추출"""
    results = []
    for prop, patterns in PATTERNS.items():
        for pattern, val_idx, unit_idx in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    results.append({
                        'property': prop,
                        'value': float(match.group(val_idx)),
                        'unit': match.group(unit_idx),
                        'method': 'regex'
                    })
                except:
                    pass
    return results

def extract_llm(text: str) -> List[Dict]:
    """LLM 추출 (간소화)"""
    try:
        llm = ChatOllama(base_url=RUNPOD_URI, model="qwen2.5:7b", temperature=0)

        prompt = ChatPromptTemplate.from_messages([
            ("system", "Extract material properties as JSON array: [{\"property\": \"Tg\", \"value\": 150, \"unit\": \"°C\"}]. Return [] if none."),
            ("human", "{text}")
        ])

        chain = prompt | llm | JsonOutputParser()
        result = chain.invoke({"text": text[:2000]})

        if isinstance(result, list):
            for r in result:
                r['method'] = 'llm'
            return result
    except Exception as e:
        print(f"LLM 오류: {e}")
    return []

def main():
    print("TDS 물성 추출 시작...")

    client = pymongo.MongoClient(MONGO_URI)
    db = client['s307_db']

    docs = list(db['markdown_collection'].find({'document_id': {'$regex': '^MOCK_'}}).limit(2))
    print(f"처리 대상: {len(docs)}개")

    for doc in docs:
        doc_id = doc['document_id']
        content = doc.get('content', '')

        print(f"\n처리 중: {doc_id}")

        # Regex only (LLM 없이 테스트)
        props = extract_regex(content)
        print(f"추출: {len(props)}개 물성")

        for p in props:
            print(f"  - {p['property']}: {p['value']} {p['unit']}")

        # MongoDB 저장
        db['tds_summary'].update_one(
            {'document_id': doc_id},
            {'$set': {'properties': props, 'updated_at': datetime.utcnow()}},
            upsert=True
        )

    print("\n완료!")
    client.close()

if __name__ == "__main__":
    main()
