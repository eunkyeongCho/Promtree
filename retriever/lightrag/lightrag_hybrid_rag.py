"""
LightRAG Hybrid RAG System - ApeRAG 방식 완전 구현
벡터 검색 + 그래프 검색 통합
"""

from dotenv import load_dotenv
import os
from typing import Dict, List, Any

from .lightrag_graph_storage import GraphStorage
from .lightrag_entity_extractor import EntityExtractor
from .lightrag_entity_merger import EntityMerger
from .lightrag_graph_search import GraphSearcher
from .lightrag_query_processor import QueryProcessor

# 기존 RAG 시스템
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from rag_system import RAGSystem

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()


class HybridRAG:
    """
    하이브리드 RAG 시스템
    - 벡터 검색 (기존 FAISS)
    - 그래프 검색 (ApeRAG 방식)
    - 결과 병합 및 LLM 응답 생성
    """

    def __init__(
        self,
        vector_rag: RAGSystem = None,
        graph_storage: GraphStorage = None,
        llm_model: str = "gemini-2.5-flash"
    ):
        """
        하이브리드 RAG 초기화

        Args:
            vector_rag: 벡터 기반 RAG (기존)
            graph_storage: 그래프 스토리지
            llm_model: LLM 모델
        """
        # 벡터 검색
        self.vector_rag = vector_rag if vector_rag else RAGSystem()

        # 그래프 검색
        self.graph_storage = graph_storage if graph_storage else GraphStorage()
        self.graph_searcher = GraphSearcher(
            self.graph_storage,
            embedding_model=self.vector_rag.model if hasattr(self.vector_rag, 'model') else None,
            use_embedding=True
        )

        # 쿼리 전처리 (엔티티 추출)
        self.query_processor = QueryProcessor()

        # 엔티티 추출 및 병합 (인덱싱용)
        self.entity_extractor = EntityExtractor()
        self.entity_merger = EntityMerger(self.graph_storage)

        # LLM
        self.llm = ChatGoogleGenerativeAI(
            model=llm_model,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.1,
        )

        # 하이브리드 프롬프트
        self.hybrid_prompt = ChatPromptTemplate.from_messages([
            ("system",
             "당신은 질문에 답변하는 AI 어시스턴트입니다. "
             "벡터 검색 결과와 그래프 검색 결과를 모두 참고하여 정확하고 포괄적인 답변을 제공하세요."),
            ("human",
             "# 벡터 검색 결과 (유사 문서):\n{vector_context}\n\n"
             "# 그래프 검색 결과 (관련 엔티티 및 관계):\n{graph_context}\n\n"
             "# 질문:\n{question}\n\n"
             "# 답변:")
        ])

        self.chain = self.hybrid_prompt | self.llm | StrOutputParser()

    async def index_chunks(self, chunks: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        청크들을 인덱싱 (그래프 구축)

        Args:
            chunks: 청크 리스트
                [{"content": "...", "chunk_id": "...", "file_path": "..."}, ...]

        Returns:
            Dict: 인덱싱 통계
        """
        print(f"[HybridRAG] {len(chunks)}개 청크 인덱싱 시작...")

        # 1. 엔티티 추출
        print("[HybridRAG] 엔티티 추출 중...")
        chunk_results = await self.entity_extractor.extract_entities(chunks, max_concurrent=3)

        # 2. 엔티티 병합 및 그래프 업데이트
        print("[HybridRAG] 엔티티 병합 중...")
        num_entities, num_relationships = self.entity_merger.merge_nodes_and_edges(chunk_results)

        print(f"[HybridRAG] 인덱싱 완료: {num_entities}개 엔티티, {num_relationships}개 관계")

        return {
            'num_entities': num_entities,
            'num_relationships': num_relationships
        }

    async def search_hybrid(
        self,
        question: str,
        vector_top_k: int = 5,
        graph_top_k: int = 5,
        graph_max_hops: int = 2
    ) -> Dict[str, Any]:
        """
        하이브리드 검색 (벡터 + 그래프)

        Args:
            question: 질문
            vector_top_k: 벡터 검색 상위 K
            graph_top_k: 그래프 검색 상위 K
            graph_max_hops: 그래프 탐색 깊이

        Returns:
            Dict: 검색 결과
        """
        # 0. 질문에서 엔티티 추출 (LLM)
        query_info = await self.query_processor.extract_entities_from_query(question)
        extracted_entities = query_info.get('entities', [])

        print(f"[HybridRAG] 추출된 엔티티: {extracted_entities}")

        # 1. 벡터 검색
        vector_results = self.vector_rag.search_similar_chunks(question, vector_top_k)

        # 2. 그래프 검색 (추출된 엔티티 활용)
        graph_results = self.graph_searcher.search(
            question,
            top_k=graph_top_k,
            max_hops=graph_max_hops,
            extracted_entities=extracted_entities
        )

        return {
            'vector_results': vector_results,
            'graph_results': graph_results,
            'query_info': query_info
        }

    async def ask_question(
        self,
        question: str,
        vector_top_k: int = 5,
        graph_top_k: int = 5,
        graph_max_hops: int = 2
    ) -> Dict[str, Any]:
        """
        하이브리드 RAG 질의응답

        Args:
            question: 질문
            vector_top_k: 벡터 검색 상위 K
            graph_top_k: 그래프 검색 상위 K
            graph_max_hops: 그래프 탐색 깊이

        Returns:
            Dict: 응답 결과
        """
        # 1. 하이브리드 검색
        search_results = await self.search_hybrid(
            question,
            vector_top_k=vector_top_k,
            graph_top_k=graph_top_k,
            graph_max_hops=graph_max_hops
        )

        # 2. 컨텍스트 생성
        vector_context = self._build_vector_context(search_results['vector_results'])
        graph_context = search_results['graph_results'].get('context', '')

        # 3. LLM 응답 생성
        answer = await self.chain.ainvoke({
            'vector_context': vector_context,
            'graph_context': graph_context,
            'question': question
        })

        return {
            'answer': answer,
            'vector_context': vector_context,
            'graph_context': graph_context,
            'vector_results': search_results['vector_results'],
            'graph_results': search_results['graph_results']
        }

    def _build_vector_context(self, vector_results: List[Dict]) -> str:
        """
        벡터 검색 결과로부터 컨텍스트 생성

        Args:
            vector_results: 벡터 검색 결과

        Returns:
            str: 컨텍스트 텍스트
        """
        context_parts = []
        for i, result in enumerate(vector_results):
            chunk = result['chunk']
            similarity = result['similarity']
            content = chunk.get('content', '')
            source = chunk.get('source_file_name', 'Unknown')
            page = chunk.get('page_num', 'Unknown')

            context_parts.append(
                f"[문서 {i+1}] (유사도: {similarity:.3f}, 출처: {source}, 페이지: {page})\n{content}"
            )

        return '\n\n'.join(context_parts)

    def get_statistics(self) -> Dict[str, Any]:
        """
        시스템 통계

        Returns:
            Dict: 통계 정보
        """
        graph_stats = self.graph_storage.get_stats()

        return {
            'graph': graph_stats,
            'vector': {
                'index_size': self.vector_rag.index.ntotal if self.vector_rag.index else 0
            }
        }
