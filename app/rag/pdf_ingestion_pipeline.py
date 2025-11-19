from elasticsearch import Elasticsearch
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, VectorParams, Distance
from sentence_transformers import SentenceTransformer
from neo4j import GraphDatabase
from pymongo import MongoClient

import os
from dotenv import load_dotenv
import asyncio

from app.rag.markdown_chunker import MarkdownChunker
from app.rag.embedding import chunk_embedding_and_upsert
from app.rag.elasticsearch_indexer import ElasticsearchIndexer
from app.rag.neo4j_knowledge_graph import Neo4jKnowledgeGraph


class PdfIngestionPipeline:
    load_dotenv()

    def __init__(self):
        # --- Markdown Folder Path ---
        self.markdown_path = "markdown_sample_data"

        # --- Markdown Chunker ---
        self.markdown_chunker = MarkdownChunker()

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
        

        # --- MongoDB Client (collection name 동기화) ---
        mongo_url = (
            f"mongodb://{os.getenv('MONGO_INITDB_ROOT_USERNAME')}:{os.getenv('MONGO_INITDB_ROOT_PASSWORD')}"
            f"@{os.getenv('MONGO_HOST')}:{os.getenv('MONGO_PORT')}"
        )
        self.mongo_client = MongoClient(mongo_url)
        self.mongo_db = self.mongo_client["promtree"]
        self.collections_collection = self.mongo_db["collections"]
        collections = self._fetch_collection_names()

        for collection in collections:
            if not self.vector_db_client.collection_exists(collection):
                self.vector_db_client.create_collection(
                    collection_name=collection,
                    vectors_config=VectorParams(
                        size=1024,
                        distance=Distance.COSINE
                    )
                )
                print(f"컬렉션 '{collection}' 생성 완료.")
            else:
                print(f"컬렉션 '{collection}'이 이미 존재합니다. 기존 컬렉션을 사용합니다.")

        # --- Knowledge Graph Client ---
        NEO4J_URI = os.getenv("NEO4J_URI")
        NEO4J_AUTH = ("neo4j", os.getenv("NEO4J_PASSWORD"))

        self.neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

    def _fetch_collection_names(self) -> list[str]:
        """
        MongoDB에서 KnowledgeCollection 이름 목록을 가져옵니다.
        """
        try:
            cursor = self.collections_collection.find({}, {"name": 1, "_id": 0})
            names = sorted({doc["name"] for doc in cursor if doc.get("name")})
            if not names:
                print("⚠️ MongoDB에 등록된 collection이 없습니다. Qdrant 컬렉션 생성 단계는 건너뜁니다.")
                return []
            print(f"📁 MongoDB에서 {len(names)}개 collection 이름을 로드했습니다: {names}")
            return names
        except Exception as e:
            print(f"⚠️ MongoDB collection 이름을 불러오지 못했습니다: {e}")
            return []

    def _chunking(self, md: str, file_uuid: str, file_name: str, collections: list[str]) -> dict[str, list[str]]:
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

                if len(collections_to_save) > 0: # 만약 새로 저장해야 할 collection이 있다면...
                    chunks = self.markdown_chunker.chunk_markdown_file(md, file_uuid, file_name, collections_to_save)

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


    def run_pdf_ingestion_pipeline(self, md: str, file_uuid: str, file_name: str, collections: list[str]):
        """
        pdf를 가져와서 청킹, 인덱싱, 임베딩까지 한 함수에서 하는 함수
        """

        try:
            chunks_and_collections = self._chunking(md, file_uuid, file_name, collections)

            if not chunks_and_collections:
                return

            self._indexing(chunks_and_collections["chunks"], chunks_and_collections["collections_to_save"])
            self._embedding(chunks_and_collections["chunks"], chunks_and_collections["collections_to_save"])
            self._knowledge_graph(chunks_and_collections["chunks"])
        except RuntimeError as e:
            print(e)
            return


if __name__ == "__main__":
    import glob
    from pathlib import Path

    pdf_ingestion_pipeline = PdfIngestionPipeline()

    # markdown_sample_data 폴더의 모든 .md 파일 찾기
    markdown_folder = "markdown_sample_data"
    md_files = glob.glob(f"{markdown_folder}/*.md")

    if not md_files:
        print(f"⚠️ '{markdown_folder}' 폴더에 .md 파일이 없습니다.")
    else:
        print(f"✅ 총 {len(md_files)}개의 .md 파일을 찾았습니다.\n")

        for i, markdown_file_path in enumerate(md_files, 1):
            print(f"{'='*80}")
            print(f"[{i}/{len(md_files)}] 처리 중: {markdown_file_path}")
            print(f"{'='*80}\n")

            # 파일 이름에서 UUID 추출 (예: "Copy of 5bc0c676-018f-46de-bb0d-0103ff9c388c.md")
            file_name = Path(markdown_file_path).stem  # 확장자 제외한 파일명

            # "Copy of " 제거 및 UUID 추출 로직
            if "Copy of " in file_name:
                file_uuid = file_name.replace("Copy of ", "").strip()
            else:
                file_uuid = file_name

            # 파일 읽기
            try:
                with open(markdown_file_path, "r", encoding="utf-8") as f:
                    md = f.read()

                # 파이프라인 실행
                pdf_ingestion_pipeline.run_pdf_ingestion_pipeline(
                    md,
                    file_uuid,
                    file_name,
                    ["msds"],  # 필요에 따라 ["msds", "tds"] 등으로 변경 가능
                )

                print(f"\n✅ [{i}/{len(md_files)}] 완료: {file_name}\n")

            except Exception as e:
                print(f"\n❌ [{i}/{len(md_files)}] 실패: {file_name}")
                print(f"   오류: {e}\n")
                continue

        print(f"\n{'='*80}")
        print(f"🎉 전체 처리 완료! (총 {len(md_files)}개 파일)")
        print(f"{'='*80}")