import os
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

load_dotenv()

# --- 싱글톤 Elasticsearch Client 인스턴스 생성 ---
ELASTIC_PASSWORD = os.getenv("ELASTIC_PASSWORD")

_ELASTICSEARCH_CLIENT = Elasticsearch(
    "http://localhost:9200",
    basic_auth=("elastic", ELASTIC_PASSWORD)
)

def get_elasticsearch_client():
    return _ELASTICSEARCH_CLIENT