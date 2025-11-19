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
import httpx
from openai import OpenAI

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

    def postprecessing(self, chunks: list[dict], type: str) -> list[dict]:
        """
        청크 후처리
        """
        if type == "keyword":
            normalized = []
            for es_result in chunks:
                chunk_type = es_result.get("type", "")
                file_info = es_result.get("file_info", {})
                
                # image 타입인 경우 metadata를, 그 외에는 content를 사용
                if chunk_type == "image":
                    content = es_result.get("metadata", "")
                else:
                    content = es_result.get("content", "")
                
                normalized.append({
                    "content": content,
                    "documentId": file_info.get("file_uuid", ""),
                    "file_name": file_info.get("file_name", ""),
                    "page_nums": file_info.get("page_num", []),
                    "snippet": content[:200] + "...",
                })
            return normalized
        elif type == "vector":
            normalized = []
            for qdrant_result in chunks:
                chunk = qdrant_result.get("chunk", {})
                chunk_type = chunk.get("type", "")
                file_info = chunk.get("file_info", {})
                
                # image 타입인 경우 metadata를, 그 외에는 content를 사용
                if chunk_type == "image":
                    content = chunk.get("metadata", "")
                else:
                    content = chunk.get("content", "")
                
                normalized.append({
                    "content": content,
                    "documentId": file_info.get("file_uuid", ""),
                    "file_name": file_info.get("file_name", ""),
                    "page_nums": file_info.get("page_num", []),
                    "snippet": content[:200] + "...",
                })
            return normalized
        elif type == "graph":
            normalized = []
            for graph_result in chunks:
                graph_content = graph_result.get("graph", "")
                file_info = graph_result.get("file_info", {})
                
                normalized.append({
                    "content": graph_content,
                    "documentId": file_info.get("file_uuid", ""),
                    "file_name": file_info.get("file_name", ""),
                    "page_nums": file_info.get("page_num", []),
                    "snippet": graph_content[:200] + "...",
                })
            return normalized
    
    
    def extract_sources(self, chunks: list[dict]) -> list[dict]:
       """
       후처리된 청크 리스트를 문서별로 그룹핑하여 sources 구조로 변환
       """
       grouped = {}
       for entry in chunks:
           doc_id = entry.get("documentId", "")
           file_name = entry.get("file_name", "")
           page_nums = entry.get("page_nums") or [0]
           
           if not doc_id:
               # documentId가 없으면 viewer URL을 만들 수 없어 건너뜁니다.
               # (이 경우에도 snippet/text는 ranking에는 사용됩니다.)
               url = None
           else:
               url = f"/{doc_id}/view"

           group = grouped.setdefault(doc_id, {
               "title": file_name,
               "documentId": doc_id,
               "url": url,
               "chunks": []
           })
           
           group["chunks"].append({
               "pageRange": {"start": page_nums[0], "end": page_nums[-1]},
               "snippet": entry.get("snippet", ""),
               "text": entry.get("content", ""),
           })
       return list(grouped.values())


    async def _async_graph_search(self, query: str):
        """
        그래프 검색 수행
        """
        neo4j_knowledge_graph = Neo4jKnowledgeGraph()
        return await neo4j_knowledge_graph.async_search_graph(query)

    async def async_generate_rag_answer(self, query: str, collections: list[str], history: list[dict] | None = None):
        """
        답변 생성 수행
        """
        print(f"\n{'='*80}")
        print(f"🔍 [RAG] async_generate_rag_answer 시작")
        print(f"   Query: {query}")
        print(f"   Collections: {collections}")
        print(f"   History length: {len(history) if history else 0}")
        print(f"{'='*80}\n")
        
        try:
            print(f"📊 [RAG] 키워드 검색 시작...")
            keyword_raw = self._keyword_search(query, collections)
            print(f"   ✅ 키워드 검색 완료: {len(keyword_raw)}개 결과")
            keyword_chunks = self.postprecessing(keyword_raw, "keyword")
            print(f"   ✅ 키워드 후처리 완료: {len(keyword_chunks)}개 청크\n")
        except Exception as e:
            print(f"   ❌ 키워드 검색 실패: {e}")
            raise
        
        try:
            print(f"🔢 [RAG] 벡터 검색 시작...")
            vector_raw = self._vector_search(query, collections)
            print(f"   ✅ 벡터 검색 완료: {len(vector_raw)}개 결과")
            vector_chunks = self.postprecessing(vector_raw, "vector")
            print(f"   ✅ 벡터 후처리 완료: {len(vector_chunks)}개 청크\n")
        except Exception as e:
            print(f"   ❌ 벡터 검색 실패: {e}")
            raise
        
        try:
            print(f"🕸️  [RAG] 그래프 검색 시작...")
            graph_raw = await self._async_graph_search(query)
            print(f"   ✅ 그래프 검색 완료: {len(graph_raw)}개 결과")
            graph_chunks = self.postprecessing(graph_raw, "graph")
            print(f"   ✅ 그래프 후처리 완료: {len(graph_chunks)}개 청크\n")
        except Exception as e:
            print(f"   ❌ 그래프 검색 실패: {e}")
            raise

        keyword_results = json.dumps(keyword_chunks, ensure_ascii=False, indent=2)
        vector_results = json.dumps(vector_chunks, ensure_ascii=False, indent=2)
        graph_results = json.dumps(graph_chunks, ensure_ascii=False, indent=2)

        ranked_chunks = keyword_chunks + vector_chunks + graph_chunks
        print(f"📦 [RAG] 전체 청크 통합: {len(ranked_chunks)}개 (키워드: {len(keyword_chunks)}, 벡터: {len(vector_chunks)}, 그래프: {len(graph_chunks)})")
        
        sources = self.extract_sources(ranked_chunks)
        print(f"📚 [RAG] Sources 추출 완료: {len(sources)}개 문서\n")

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
        2. 질문에 대한 명확하고 정확한 답변을 제공하세요.
        3. 여러 문서를 참조했다면 답변에 그 내용을 모두 반영하세요.
        4. 문서에 없는 정보는 "문서에 해당 정보가 없습니다."라고 답하세요.
        5. JSON 안의 구조(key 이름)는 절대 변경하지 말고 그대로 사용하세요.
        6. image / link 타입 chunk는 metadata를 요약해 텍스트처럼 다뤄도 됩니다.

        -----------------------------
        [출력 형식]
        다음 형식으로만 답변하세요:

        {{
            "answer" : "답변 내용"
        }}
        """

        # Upstage API 클라이언트 초기화
        upstage_key = os.getenv("UPSTAGE_API_KEY")
        print(f"🔑 [RAG] Upstage API Key 확인: {'✅ 설정됨' if upstage_key else '❌ 없음'}")
        
        if not upstage_key:
            raise ValueError("UPSTAGE_API_KEY가 설정되지 않았습니다.")
        
        client = OpenAI(
            api_key=upstage_key,
            base_url="https://api.upstage.ai/v1",
            http_client=httpx.Client()
        )
        print(f"🤖 [RAG] Upstage API 클라이언트 초기화 완료\n")

        # 이전 대화 맥락을 messages 형식으로 변환
        messages = []
        if history:
            for msg in history:
                role = msg.get("role", "user")
                contents = msg.get("contents", "")
                # role이 "chatbot"이면 "assistant"로 변환
                if role == "chatbot":
                    role = "assistant"
                elif role not in ["user", "assistant", "system"]:
                    role = "user"
                messages.append({
                    "role": role,
                    "content": contents
                })
        
        # 현재 질문과 프롬프트 추가
        messages.append({
            "role": "user",
            "content": prompt
        })

        # 답변 요청
        print(f"🚀 [RAG] Upstage API 호출 시작...")
        print(f"   Model: solar-pro")
        print(f"   Messages count: {len(messages)}")
        print(f"   Prompt length: {len(prompt)} characters\n")
        
        try:
            response = client.chat.completions.create(
                model="solar-pro",
                messages=messages,
                temperature=0.7,
                stream=False
            )
            
            print(f"✅ [RAG] Upstage API 응답 수신 완료")
            llm_answer_raw = response.choices[0].message.content
            print(f"   응답 길이: {len(llm_answer_raw)} characters")
            print(f"🔍 LLM response: {llm_answer_raw[:200]}..." if len(llm_answer_raw) > 200 else f"🔍 LLM response: {llm_answer_raw}\n")
            
            try:
                answer_payload = json.loads(llm_answer_raw)
                answer = answer_payload.get("answer", "")
                print(f"✅ [RAG] JSON 파싱 성공: answer 길이 {len(answer)} characters\n")
            except json.JSONDecodeError as e:
                print(f"⚠️  [RAG] JSON 파싱 실패, 원본 텍스트 사용: {e}")
                answer = llm_answer_raw
                
        except Exception as e:
            print(f"\n❌ [RAG] Upstage API request failed:")
            print(f"   Error type: {type(e).__name__}")
            print(f"   Error message: {str(e)}")
            if hasattr(e, 'response'):
                print(f"   Response status: {e.response.status_code if hasattr(e.response, 'status_code') else 'N/A'}")
            print(f"{'='*80}\n")
            raise

        print(f"✅ [RAG] async_generate_rag_answer 완료")
        print(f"   Answer: {answer[:100]}..." if len(answer) > 100 else f"   Answer: {answer}")
        print(f"   Sources: {len(sources)}개\n")
        print(f"{'='*80}\n")
        
        return (answer, sources)


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