from elasticsearch import Elasticsearch
import os
from dotenv import load_dotenv

load_dotenv()

print("="*80)
print("Elasticsearch 확인")
print("="*80)

ELASTIC_PASSWORD = os.getenv("ELASTIC_PASSWORD")
es_client = Elasticsearch(
    "http://localhost:9200",
    basic_auth=("elastic", ELASTIC_PASSWORD)
)

try:
    # 모든 인덱스 확인
    indices = es_client.indices.get_alias(index="*")
    print(f"\n총 {len(indices)}개의 인덱스 발견:")

    for index_name in indices.keys():
        if not index_name.startswith('.'):  # 시스템 인덱스 제외
            count = es_client.count(index=index_name)
            print(f"  - {index_name}: {count['count']} documents")

    # msds, tds 인덱스 구체적으로 확인
    for collection in ["msds", "tds"]:
        if es_client.indices.exists(index=collection):
            count = es_client.count(index=collection)
            print(f"\n[{collection}] 인덱스: {count['count']} documents")
        else:
            print(f"\n[{collection}] 인덱스: 존재하지 않음")

except Exception as e:
    print(f"❌ Elasticsearch 연결 실패: {e}")

print("\n" + "="*80)