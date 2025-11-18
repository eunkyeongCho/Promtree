from elasticsearch import Elasticsearch
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from qdrant_client.models import VectorParams, Distance
from neo4j import GraphDatabase

import os
from dotenv import load_dotenv
import json
import requests
import asyncio

from app.rag.elasticsearch_indexer import ElasticsearchIndexer
from app.rag.retriever import query_embedding, search_similar_chunks
from app.rag.neo4j_knowledge_graph import Neo4jKnowledgeGraph


class Search:
    load_dotenv()

    def __init__(self):

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

        # collections = ["msds", "tds"]
        # for collection in collections:
        #     self.vector_db_client.recreate_collection(
        #         collection_name=collection,
        #         vectors_config=VectorParams(
        #             size=1024,
        #             distance=Distance.COSINE
        #         )
        #     )
        #     print(f"컬렉션 '{collection}' 생성 완료.")

        # --- Knowledge Graph Client ---
        NEO4J_URI = os.getenv("NEO4J_URI")
        NEO4J_AUTH = ("neo4j", os.getenv("NEO4J_PASSWORD"))

        self.neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)


    def _keyword_search(self, query: str, collections: list[str]):
        """
        키워드 검색 수행
        """
        elasticsearch_indexer = ElasticsearchIndexer()
        elasticsearch_indexer.ensure_index(collections)
        return elasticsearch_indexer.keyword_search(query, collections)

    def _vector_search(self, query: str, collections: list[str]):
        """
        벡터 검색 수행
        """
        qv = query_embedding(self.embedding_model, query)
        print("쿼리 임베딩 완료")
        results = search_similar_chunks(self.vector_db_client, qv, collections, 5)
        print("벡터 검색 완료")
        return results

    async def _async_graph_search(self, query: str):
        """
        그래프 검색 수행
        """
        neo4j_knowledge_graph = Neo4jKnowledgeGraph()
        return await neo4j_knowledge_graph.async_search_graph(query)

    async def async_generate_rag_answer(self, query: str, collections: list[str]):
        """
        답변 생성 수행
        """
        keyword_results = json.dumps(self._keyword_search(query, collections), ensure_ascii=False, indent=2)
        vector_results = json.dumps(self._vector_search(query, collections), ensure_ascii=False, indent=2)
        graph_results = json.dumps(await self._async_graph_search(query), ensure_ascii=False, indent=2)

        prompt = f"""
        당신은 삼성전자 생산기술연구소의 소재 물성 문서 기반으로 근거 중심의 정확한 답변을 생성하는 전문 어시스턴트입니다.
        당신의 모든 답변은 아래 제공된 문서(JSON 형태)의 내용만을 기반으로 해야 합니다. 
        추론을 할 때도 반드시 문서의 내용을 근거로 해야 하며, 문서에 없는 내용은 절대 추측하지 말고 모르면 모른다고 하세요.

        -----------------------------
        [사용자 질문]
        {query}
        -----------------------------

        [검색된 문서(JSON)]
        아래 JSON 배열의 각 요소는 검색된 문서 조각(chunk)입니다.
        각 chunk는 다음 값을 포함합니다:
        - type: text/table/image/link 등 문서 유형
        - content: imgae의 경로 | link의 원본링크 | List[dict[str, str]] 형태로 언피봇된 html table의 내용 | text의 내용
        - metadata: image의 메타데이터 | link의 메타데이터 | None
        - file_info: {{
            "file_uuid" : "백엔드에서 넘어오는 Doc ID",
            "file_name" : "파일 이름",
            "collections" : ["collection 이름1", "collection 이름2", ...],
            "page_num" : 페이지 번호 정수 배열
        }}

        검색된 문서(JSON):
        [키워드 검색 결과]
        {keyword_results}

        [벡터 검색 결과]
        {vector_results}

        [그래프 검색 결과]
        {graph_results}

        -----------------------------
        [지침]

        1. 반드시 문서(JSON) 속 text 내용을 기반으로만 답변하세요.
        2. 답변에는 다음 두 가지를 반드시 포함해야 합니다:
        (A) 질문에 대한 명확한 답변
        (B) 답변에 사용된 근거의 출처 (file_uuid(파일 고유 UUID), file_name(파일명), page_num(페이지 번호))
        3. 여러 문서를 참조했다면 출처를 모두 표기하세요.
        4. 문서에 없는 정보는 "문서에 해당 정보가 없습니다."라고 답하세요. 이때에는 file_info에 대한 내용을 비워두세요.
        5. JSON 안의 구조(key 이름)는 절대 변경하지 말고 그대로 사용하세요.
        6. image / link 타입 chunk는 metadata를 요약해 텍스트처럼 다뤄도 됩니다.

        -----------------------------
        [출력 형식]
        다음 형식으로만 답변하세요:

        {{
            "answer" : "답변",
            "file_info" : {{
                "file_uuid" : "백엔드에서 넘어오는 Doc ID",
                "file_name" : "파일 이름",
                "page_num" : 페이지 번호 정수 배열
            }}
        }}
        """

        RUNPOD_URI = os.getenv("RUNPOD_URI")
        RUNPOD_LLM_MODEL = os.getenv("RUNPOD_LLM_MODEL")
        TIMEOUT = os.getenv("TIMEOUT")

        # 답변 요청
        url = f"{RUNPOD_URI}/api/generate"
        payload = {"model": RUNPOD_LLM_MODEL, "prompt": prompt, "stream": False}
        timeout = float(TIMEOUT) if TIMEOUT else None
        response = requests.post(url, json=payload, timeout=timeout)

        print(prompt)

        try:
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"❌ HTTP request failed: {e}")

        print(f"🔍 LLM response: {response.json()['response']}")

        return response.json()['response']


if __name__ == "__main__":
    search = Search()

    questions = [
        "톨루엔의 끓는점 범위는?",
        "아세틸렌의 CAS 번호는 무엇인가?",
        "수소충전소용 수소의 권고용도는?"
    ]

    for question in questions:
        print(f"\n{'='*80}")
        print(f"질문: {question}")
        print(f"{'='*80}\n")
        asyncio.run(search.async_generate_rag_answer(question, ["msds"]))