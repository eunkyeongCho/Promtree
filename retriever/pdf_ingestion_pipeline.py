from pymongo import MongoClient
from elasticsearch import Elasticsearch
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, VectorParams, Distance
from sentence_transformers import SentenceTransformer
from neo4j import GraphDatabase

import os
from pathlib import Path
from dotenv import load_dotenv
import re
import asyncio

from retriever.chunker.markdown_chunker import MarkdownChunker
from retriever.embedding import chunk_embedding_and_upsert
from retriever.indexer.elasticsearch_indexer import ElasticsearchIndexer
from retriever.knowledge_graph.neo4j_knowledge_graph import Neo4jKnowledgeGraph


class PdfIngestionPipeline:
    BASE_DIR = Path(__file__).resolve().parents[1]  # root 경로
    load_dotenv(BASE_DIR / "common" / ".env")

    def __init__(self):
        # --- PDF Folder Path ---
        self.pdf_path = self.BASE_DIR / "pdf"

        # --- Markdown Folder Path ---
        self.markdown_path = self.BASE_DIR / "retriever" / "markdown_sample_data"

        # --- Markdown Chunker ---
        self.markdown_chunker = MarkdownChunker()

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

        self.elasticsearch_indexer = ElasticsearchIndexer()

        # --- Embedding Model Client ---
        self.embedding_model = SentenceTransformer('Qwen/Qwen3-Embedding-0.6B', trust_remote_code=True)

        # --- Vector Database Client ---
        self.vector_db_client = QdrantClient(url="http://localhost:6333")

        collections = ["msds", "tds"]
        for collection in collections:
            self.vector_db_client.recreate_collection(
                collection_name=collection,
                vectors_config=VectorParams(
                    size=1024,
                    distance=Distance.COSINE
                )
            )
            print(f"컬렉션 '{collection}' 생성 완료.")

        # --- Knowledge Graph Client ---
        NEO4J_URI = os.getenv("NEO4J_URI")
        NEO4J_AUTH = ("neo4j", os.getenv("NEO4J_PASSWORD"))

        self.neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

    def _chunking(self, file_uuid: str, collections: list[str]) -> dict[str, list[str]]:
        """
        제공된 collection 중 청킹이 이뤄지지 않은 collection이 존재할 때만 청킹을 하고, 청킹이 이뤄지지 않은 collection만 필터링해서 반환합니다.
        """

        is_file_exists_filter = Filter(
            must=[
                FieldCondition(
                    key="file_info.file_uuid",
                    match=MatchValue(value=file_uuid)
                )
            ]
        )

        collections_to_save = []

        for collection in collections:
            points, next_page = self.vector_db_client.scroll(
                collection_name=collection,
                scroll_filter=is_file_exists_filter,
                limit=1,
                with_payload=False,
            )

            if not points:
                collections_to_save.append(collection)

        target_file_name_pattern = re.compile(rf"^{file_uuid}_.*")

        for file_path in self.markdown_path.rglob("*.md"): # md 파일만 순회돌기
            file_name = file_path.stem

            if target_file_name_pattern.match(file_name):
                if len(collections_to_save) > 0:
                    chunks = self.markdown_chunker.chunk_markdown_file(file_path, file_uuid, collections_to_save)

                    return {
                        "chunks": chunks,
                        "collections_to_save": collections_to_save
                    }
                
                else:
                    print("☑️ 요청된 모든 collection에 이미 청킹이 이뤄져 있으므로 청킹을 수행하지 않고 메서드를 종료합니다.")
                    return None
            
        raise RuntimeError("☑️ 제공된 UUID로 시작하는 PDF파일이 프로젝트 내부 PDF 폴더에 업로드되지 않았습니다.")
                

    def _indexing(self, chunks: list[dict], collections: list[str]):
        """
        청크를 가져와서 인덱싱 후 저장
        """
        self.elasticsearch_indexer.index_chunks(chunks, collections)


    def _embedding(self, chunks: list[dict], collections: list[str]):
        """
        청킹을 가져와서 임베딩 후 벡터스토어에 저장
        """
        chunk_embedding_and_upsert(chunks, self.embedding_model, self.vector_db_client, collections)

    def _knowledge_graph(self, chunks: list[dict]):
        """
        청킹을 가져와서 지식 그래프 추출 및 저장
        """
        asyncio.run(Neo4jKnowledgeGraph().async_ingest_chunks(chunks))


    def run_pdf_ingestion_pipeline(self, file_uuid: str, collections: list[str]):
        """
        pdf를 가져와서 청킹, 인덱싱, 임베딩까지 한 함수에서 하는 함수
        """

        try:
            chunks_and_collections = self._chunking(file_uuid, collections)

            if chunks_and_collections is None:
                return

            self._indexing(chunks_and_collections["chunks"], chunks_and_collections["collections_to_save"])
            self._embedding(chunks_and_collections["chunks"], chunks_and_collections["collections_to_save"])
            self._knowledge_graph(chunks_and_collections["chunks"])
        except RuntimeError as e:
            print(e)
            return


if __name__ == "__main__":
    pdf_ingestion_pipeline = PdfIngestionPipeline()
    pdf_ingestion_pipeline.run_pdf_ingestion_pipeline("5bc0c676-018f-46de-bb0d-0103ff9c388c", ["msds"])