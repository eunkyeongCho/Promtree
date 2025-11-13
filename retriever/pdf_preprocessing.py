# pdf, UUID, 업로드 하고자 하는 collection 이름을 받아서 청킹, 엘라스틱 서치에 저장, 임베딩해서 벡터스토어에 저장, 그래프 추출까지 한 함수에서 하는 함수
# _pdf를 받아서 청킹
# _엘라스틱 서치에 저장
# _임베딩해서 벡터스토어에 저장
# 그래프 추출까지 한 함수에서 하는 함수

# - type: text/table/image/link 등 문서 유형
#         - content: imgae의 경로 | link의 원본링크 | List[dict[str, str]] 형태로 언피봇된 html table의 내용 | text의 내용
#         - metadata: image의 메타데이터 | link의 메타데이터 | None
#         - file_info: {
#             "collection_name" : "collection 이름",
#             "uuid" : "UUID",
#             "file_name" : "파일 이름",
#             "page_num" : 페이지 번호 정수 배열
#         }
from pymongo import MongoClient
from elasticsearch import Elasticsearch
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from neo4j import GraphDatabase

import os
from pathlib import Path
from dotenv import load_dotenv
import json
import requests


class PdfPreprocessing:
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