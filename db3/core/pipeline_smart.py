"""
[핵심] 스마트 파이프라인 ⭐ 메인 실행 파일

역할:
- TDS 물성 추출 메인 파이프라인
- MongoDB 마크다운 → 물성 추출 → PostgreSQL 저장
- LLM 우선 + Regex 보완 하이브리드 전략

추출 전략:
    1. LLM 추출 (RunPod Ollama qwen2.5:7b) - 컨텍스트 이해, 높은 정확도
    2. Regex 추출 - LLM 누락 물성 보완 및 검증
    3. 하이브리드 병합 - LLM 우선, Regex로 추가 물성 보완

실행:
    python pipeline_smart.py

옵션:
    use_llm_fallback=True   → LLM 우선 + Regex 보완 (정확, 느림)
    use_llm_fallback=False  → Regex만 (빠름, Mock 데이터 충분)

출력:
    - MongoDB temp_extraction 컬렉션에 임시 저장
    - PostgreSQL tds_properties 테이블에 최종 저장
    - 문서별 추출 결과 요약 (LLM vs Regex 기여도 포함)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db_connection import get_mongodb, get_postgresql
from extractor import detect_all_properties
from create_pg_tables import ensure_column_exists
from llm_agent_langchain import PropertyExtractionAgent  # LangChain LCEL 버전으로 변경
from typing import List, Dict


def should_use_llm(properties: List[Dict], doc_text: str) -> tuple[bool, str]:
    """
    업계 표준 기반 실패 감지

    Args:
        properties: 정규식으로 추출된 물성 리스트
        doc_text: 원본 마크다운 텍스트

    Returns:
        (LLM 사용 여부, 실패 이유)

    기준:
    - MUC-5 Partial Match 비율 < 0.3
    - Azure 신뢰도 기준 < 0.7
    - Entity-Level Completeness (필수 물성)
    """
    # 1. 완전 실패 (Strict Match 0%)
    if len(properties) == 0:
        return True, "완전 실패 (STRICT_FAIL)"

    # 2. Partial Match 비율 계산
    doc_lines = len(doc_text.split('\n'))
    expected_min_properties = max(3, doc_lines // 20)  # 문서 20줄당 1개 물성 기대
    partial_ratio = len(properties) / expected_min_properties

    if partial_ratio < 0.3:  # MUC-5 기준
        return True, f"추출 부족 (PARTIAL_RATIO={partial_ratio:.2f})"

    # 3. Entity-Level Completeness (필수 물성)
    extracted_keys = {p['property'] for p in properties}
    REQUIRED = {'Tg', 'Tm', 'YS'}  # 도메인 필수 물성

    if not (REQUIRED & extracted_keys) and len(properties) < 5:
        return True, f"필수 물성 누락 (ENTITY_INCOMPLETE): {REQUIRED - extracted_keys}"

    # 4. Confidence Score (extractor에서 제공하는 경우)
    if all('confidence' in p for p in properties):
        avg_confidence = sum(p['confidence'] for p in properties) / len(properties)
        if avg_confidence < 0.7:  # Azure 표준
            return True, f"신뢰도 낮음 (CONFIDENCE={avg_confidence:.2f})"

    return False, "OK (REGEX_SUFFICIENT)"


def normalize_property_name(name: str) -> str:
    """
    물성 이름 정규화 (중복 비교용)

    "Tensile_Strength" → "tensilestrength"
    "Tensile Strength" → "tensilestrength"
    "tensile strength" → "tensilestrength"
    """
    return name.lower().replace('_', '').replace(' ', '').replace('-', '')


def merge_properties(regex_props: List[Dict], llm_props: List[Dict]) -> List[Dict]:
    """
    정규식 결과와 LLM 결과 병합 (중복 제거)

    Args:
        regex_props: 정규식 추출 결과
        llm_props: LLM 추출 결과

    Returns:
        병합된 물성 리스트 (정규식 우선, LLM은 추가분만)
    """
    merged = list(regex_props)  # 정규식 결과 복사

    # 정규식 결과를 정규화된 이름으로 매핑
    regex_normalized = {normalize_property_name(p['property']): p['property']
                        for p in regex_props}

    # LLM 결과 중 새로운 물성만 추가
    for llm_prop in llm_props:
        normalized_llm = normalize_property_name(llm_prop['property'])

        # 정규화된 이름으로 비교
        if normalized_llm not in regex_normalized:
            merged.append(llm_prop)
        # else: 중복이므로 제외 (정규식 우선)

    return merged


def process_document_smart(doc_id: str, mongodb, postgres_conn, use_llm_fallback: bool = True):
    """
    하이브리드 추출 (정규식 + LLM Fallback)

    Args:
        doc_id: 문서 ID
        mongodb: MongoDB database
        postgres_conn: PostgreSQL connection
        use_llm_fallback: LLM fallback 사용 여부 (기본 True)
    """
    print(f"\n{'='*70}")
    print(f"📄 문서 처리: {doc_id}")
    print(f"{'='*70}")

    # 1. Markdown 가져오기
    collection = mongodb['markdown_collection']
    doc = collection.find_one({'document_id': doc_id})

    if not doc:
        print(f"❌ 문서를 찾을 수 없습니다: {doc_id}")
        return None

    print(f"파일명: {doc.get('file_name', 'N/A')}")

    # 2. LLM 추출 먼저 실행 (RunPod Ollama)
    if use_llm_fallback:
        print(f"🤖 LLM 추출 시작... (RunPod Ollama 우선)")

        try:
            llm_agent = PropertyExtractionAgent()  # RunPod 기본값
            llm_properties = llm_agent.extract_properties(doc['content'])

            if llm_properties:
                print(f"✅ LLM 추출: {len(llm_properties)}개")
            else:
                print(f"⚠️  LLM 추출 결과 없음")
                llm_properties = []

        except Exception as e:
            print(f"❌ LLM 오류: {e}")
            llm_properties = []

    else:
        print(f"⚠️  LLM 비활성화")
        llm_properties = []

    # 3. 정규식 추출 (검증 및 보완)
    regex_properties = detect_all_properties(doc['content'])
    print(f"\n✅ 정규식 추출: {len(regex_properties)}개 (검증/보완)")

    # 4. 병합 (LLM 우선, Regex로 보완)
    if llm_properties:
        # LLM 결과를 기반으로 하되, Regex로 추가 물성 보완
        properties = merge_properties(llm_properties, regex_properties)

        llm_only = len(llm_properties)
        regex_added = len(properties) - llm_only

        print(f"📊 병합 결과:")
        print(f"   - LLM: {llm_only}개")
        print(f"   - Regex 추가: {regex_added}개")
        print(f"   - 최종: {len(properties)}개")
    else:
        # LLM 실패 시 Regex만 사용
        print(f"⚠️  LLM 실패 - 정규식 결과만 사용")
        properties = regex_properties

    # 추출된 물성 출력
    print(f"\n📋 최종 추출 결과: {len(properties)}개")
    for prop in properties:
        print(f"  - {prop['property']}: {prop['value']} {prop['unit']}")

    # 4. Temp DB에 저장 (MongoDB)
    temp_collection = mongodb['temp_extraction']

    for prop in properties:
        temp_collection.insert_one({
            'document_id': doc_id,
            'property_field': prop['property'],
            'property_value': prop['value'],
            'property_unit': prop['unit'],
            'matched_name': prop.get('matched_name', ''),
            'extraction_method': prop.get('extraction_method', 'regex')  # 추출 방식 기록
        })

    # 5. PostgreSQL에 저장
    if postgres_conn is not None:
        cursor = postgres_conn.cursor()

        # 문서 레코드 생성
        cursor.execute("""
            INSERT INTO tds_properties (document_id)
            VALUES (%s)
            ON CONFLICT (document_id) DO NOTHING
        """, (doc_id,))
        postgres_conn.commit()

        # 각 물성 컬럼 추가 및 값 업데이트
        for prop in properties:
            ensure_column_exists(prop['property'], postgres_conn)

            col_name = prop['property'].replace(' ', '_').replace('(', '').replace(')', '').lower()

            cursor.execute(f"""
                UPDATE tds_properties
                SET {col_name}_value = %s,
                    {col_name}_unit = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE document_id = %s
            """, (prop['value'], prop['unit'], doc_id))

        postgres_conn.commit()
        print(f"\n✅ PostgreSQL 저장 완료")
    else:
        print(f"\n⚠️  PostgreSQL 건너뜀")

    return properties


def process_all_documents(mongodb, postgres_conn, doc_filter=None, use_llm_fallback=True):
    """
    모든 문서 처리

    Args:
        mongodb: MongoDB database
        postgres_conn: PostgreSQL connection
        doc_filter: 문서 필터 (None이면 전체)
        use_llm_fallback: LLM fallback 사용 여부
    """
    collection = mongodb['markdown_collection']

    if doc_filter:
        docs = collection.find(doc_filter)
    else:
        docs = collection.find()

    doc_list = list(docs)
    print(f"\n{'='*70}")
    print(f"병렬 추출 파이프라인 시작: {len(doc_list)}개 문서")
    print(f"전략: 정규식 + LLM 항상 병렬 실행 {'(활성화)' if use_llm_fallback else '(LLM 비활성화)'}")
    print(f"{'='*70}")

    results = []

    for doc in doc_list:
        doc_id = doc['document_id']
        properties = process_document_smart(doc_id, mongodb, postgres_conn, use_llm_fallback)

        if properties:
            results.append({
                'document_id': doc_id,
                'property_count': len(properties),
                'properties': properties
            })

    # 결과 요약
    print(f"\n{'='*70}")
    print(f"처리 완료 요약")
    print(f"{'='*70}")
    print(f"총 문서 수: {len(results)}")
    print(f"총 물성 수: {sum(r['property_count'] for r in results)}")

    # 경고 문서 표시
    low_extraction = [r for r in results if r['property_count'] < 3]
    if low_extraction:
        print(f"\n⚠️  추출 부족 문서: {len(low_extraction)}개")
        for r in low_extraction:
            print(f"   - {r['document_id']}: {r['property_count']}개만 추출")

    return results


if __name__ == "__main__":
    print("=" * 70)
    print("TDS 병렬 추출 파이프라인")
    print("정규식 + Ollama LLM (Qwen2.5:7b) 항상 병렬 실행")
    print("=" * 70)

    # DB 연결
    mongodb = get_mongodb()

    if mongodb is None:
        print("❌ MongoDB 연결 필수")
        exit(1)

    postgres = get_postgresql()

    if postgres is None:
        print("⚠️  PostgreSQL 없음 - MongoDB 전용 모드로 실행\n")

    # 전체 문서 처리 (Mock 데이터)
    # use_llm_fallback=True: LLM 사용
    # use_llm_fallback=False: 정규식만 (LLM 비활성화)
    results = process_all_documents(
        mongodb,
        postgres,
        doc_filter={'document_id': {'$regex': '^MOCK_'}},
        use_llm_fallback=True  # ← 정규식 + RunPod LLM (정확도 향상)
    )

    if postgres is not None:
        postgres.close()

    print("\n✅ 하이브리드 파이프라인 완료!")
