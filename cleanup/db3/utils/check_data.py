"""
[보조] 파서팀 데이터 확인 도구

역할:
- MongoDB에 실제 데이터가 들어왔는지 확인
- Mock 데이터 vs 실제 데이터 구분 표시
- 파서팀 연동 상태 모니터링

실행:
    python check_data.py

출력:
    - 총 문서 수
    - Mock 데이터 개수
    - 실제 데이터 개수
    - 전체 문서 목록 (document_id, file_name, 길이)

활용:
    - 파서팀이 데이터를 넣었는지 주기적 확인
    - MOCK_으로 시작하는 문서는 테스트용
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))

from db_connection import get_mongodb

mongodb = get_mongodb()
collection = mongodb['markdown_collection']

# 전체 문서 수
total = collection.count_documents({})
print(f"📊 총 문서 수: {total}개\n")

# Mock vs 실제 데이터 구분
mock_count = collection.count_documents({'document_id': {'$regex': '^MOCK_'}})
real_count = total - mock_count

print(f"🧪 Mock 데이터: {mock_count}개")
print(f"📄 실제 데이터: {real_count}개\n")

# 문서 목록 출력
print("=" * 60)
print("문서 목록:")
print("=" * 60)

for doc in collection.find().sort('document_id', 1):
    doc_id = doc['document_id']
    file_name = doc.get('file_name', 'N/A')
    content_len = len(doc.get('content', ''))

    # Mock 데이터 표시
    if doc_id.startswith('MOCK_'):
        label = "🧪 [Mock]"
    else:
        label = "📄 [실제]"

    print(f"{label} {doc_id:20s} | {file_name:30s} | {content_len:5d}자")

print("\n" + "=" * 60)
if real_count > 0:
    print("✅ 파서팀 데이터 발견!")
else:
    print("⏳ 파서팀 데이터 아직 없음 (Mock 데이터만 존재)")
