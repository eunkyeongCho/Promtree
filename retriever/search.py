# _pdf 불러와서 청킹 (프로젝트 경로에 있는 pdf 중 아직 청킹되지 않은 것 (uuid 기준)-> 청킹해서 mongodb에 저장)
# _청킹 결과를 벡터 데이터베이스에 저장 (mongodb에서 불러온 청크 -> 벡터 데이터베이스에 저장)

# _키워드 검색 (쿼리 -> 키워드 검색 결과)
# _벡터 데이터베이스에서 검색 (쿼리 -> 벡터 검색 결과)
# _그래프 검색 (쿼리 -> 그래프 검색 결과)

# 답변생성 (쿼리 -> 생성된 답변)
from pymongo import MongoClient
from elasticsearch import Elasticsearch
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from neo4j import GraphDatabase

import os
from pathlib import Path
from dotenv import load_dotenv


class Search:
    BASE_DIR = Path(__file__).resolve().parents[1]  # root 경로
    load_dotenv(BASE_DIR / "common" / ".env")

    def __init__(self):
        # --- PDF Folder Path ---
        self.pdf_path = self.BASE_DIR / "pdf"

        # --- Chunking Database Client ---
        MONGO_USERNAME = os.getenv("MONGO_INITDB_ROOT_USERNAME", "root")
        MONGO_PASSWORD = os.getenv("MONGO_INITDB_ROOT_PASSWORD", "example")
        MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
        MONGO_PORT = int(os.getenv("MONGO_PORT", 27017))

        self.chunking_db_client = MongoClient(f"mongodb://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/")

        # --- Indexing Database Client ---
        ELASTIC_PASSWORD = os.getenv("ELASTIC_PASSWORD")

        self.indexing_db_client = Elasticsearch(
            "http://localhost:9200",
            basic_auth=("elastic", ELASTIC_PASSWORD)
        )

        # --- Embedding Model Client ---
        self.embedding_model = SentenceTransformer('Qwen/Qwen3-Embedding-0.6B', trust_remote_code=True)

        # --- Vector Database Client ---
        self.vector_db_client = QdrantClient(url="http://localhost:6333")

        # --- Knowledge Graph Client ---
        NEO4J_URI = os.getenv("NEO4J_URI")
        NEO4J_AUTH = ("neo4j", os.getenv("NEO4J_PASSWORD"))

        self.neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)


    def chunking(self):