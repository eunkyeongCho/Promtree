"""
[보조] 추출 결과 검증 도구

역할:
- 원본 Markdown과 PostgreSQL 추출 결과를 나란히 출력
- 사람이 눈으로 검증하기 쉽게 포맷팅
- 누락/오탐 발견 및 Ground Truth 작성 보조

사용법:
    # 특정 문서 1개 검증
    python verify_results.py MOCK_TDS_001

    # 전체 문서 순차 검증
    python verify_results.py
    (Enter 눌러서 다음 문서로 이동)

출력 내용:
    1. 원본 Markdown 전체 내용
    2. PostgreSQL에 저장된 추출 결과
    3. 검증 가이드 (비교 방법)

활용:
    - 정규식 추출 정확도 검증
    - LLM 추출 결과 비교
    - 파서팀에게 전달할 Ground Truth 작성
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))

from db_connection import get_mongodb, get_postgresql


def verify_document(doc_id: str):
    """
    문서 검증: 원본과 추출 결과 비교
    """
    mongodb = get_mongodb()
    postgres = get_postgresql()

    if mongodb is None:
        print("❌ MongoDB 연결 실패")
        return

    # 1. 원본 Markdown 가져오기
    collection = mongodb['markdown_collection']
    doc = collection.find_one({'document_id': doc_id})

    if not doc:
        print(f"❌ 문서를 찾을 수 없습니다: {doc_id}")
        return

    print("=" * 80)
    print(f"📄 문서: {doc_id}")
    print(f"파일명: {doc.get('file_name', 'N/A')}")
    print("=" * 80)

    # 2. 원본 내용 출력
    print("\n" + "="*80)
    print("📝 원본 Markdown 내용:")
    print("="*80)
    print(doc['content'])

    # 3. 추출된 결과 (PostgreSQL)
    if postgres:
        cursor = postgres.cursor()

        # 컬럼 목록 가져오기
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'tds_properties'
            AND column_name LIKE '%_value'
            ORDER BY ordinal_position
        """)

        value_columns = [row[0] for row in cursor.fetchall()]

        # 데이터 조회
        cursor.execute("""
            SELECT * FROM tds_properties
            WHERE document_id = %s
        """, (doc_id,))

        row = cursor.fetchone()

        if row:
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'tds_properties'
                ORDER BY ordinal_position
            """)
            all_columns = [col[0] for col in cursor.fetchall()]

            print("\n" + "="*80)
            print("✅ 추출된 물성 (PostgreSQL):")
            print("="*80)

            count = 0
            for col in all_columns:
                if col.endswith('_value'):
                    idx = all_columns.index(col)
                    value = row[idx]

                    if value is not None:
                        # 단위 컬럼 찾기
                        unit_col = col.replace('_value', '_unit')
                        unit_idx = all_columns.index(unit_col) if unit_col in all_columns else None
                        unit = row[unit_idx] if unit_idx else ''

                        prop_name = col.replace('_value', '').upper()
                        count += 1
                        print(f"{count:2d}. {prop_name:25s} = {value:10} {unit}")

            print(f"\n총 {count}개 물성 추출")

        else:
            print("\n⚠️  PostgreSQL에 데이터 없음")

        postgres.close()

    # 4. 검증 가이드
    print("\n" + "="*80)
    print("🔍 검증 방법:")
    print("="*80)
    print("1. 위 '원본 Markdown'을 읽으면서 물성을 찾아보세요")
    print("2. '추출된 물성' 리스트와 비교하세요")
    print("3. 누락된 것이 있나요? 추가로 추출된 것이 있나요?")
    print("4. 값과 단위가 정확한가요?")
    print()


def verify_all_documents():
    """
    모든 Mock 문서 검증
    """
    mongodb = get_mongodb()
    collection = mongodb['markdown_collection']

    docs = list(collection.find({'document_id': {'$regex': '^MOCK_'}}))

    print(f"총 {len(docs)}개 문서 검증\n")

    for i, doc in enumerate(docs, 1):
        print(f"\n\n{'#'*80}")
        print(f"문서 {i}/{len(docs)}")
        print(f"{'#'*80}")

        verify_document(doc['document_id'])

        if i < len(docs):
            input("\n[Enter]를 눌러 다음 문서로... ")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # 특정 문서만 검증
        doc_id = sys.argv[1]
        verify_document(doc_id)
    else:
        # 전체 문서 검증
        verify_all_documents()
