"""
TDS 물성 추출 테스트 (MongoDB 전용)
"""
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = f"mongodb://{os.getenv('MONGO_INITDB_ROOT_USERNAME')}:{os.getenv('MONGO_INITDB_ROOT_PASSWORD')}@{os.getenv('MONGO_HOST')}:{os.getenv('MONGO_PORT')}/"

# MongoDB 연결 테스트
client = MongoClient(MONGO_URI)
db = client['s307_db']

# 문서 확인
docs = list(db['markdown_collection'].find({'document_id': {'$regex': '^MOCK_'}}))
print(f"총 {len(docs)}개 문서 발견")

for doc in docs[:2]:
    print(f"\n문서: {doc['document_id']}")
    print(f"파일명: {doc.get('file_name', 'N/A')}")
    print(f"내용 길이: {len(doc.get('content', ''))} chars")
