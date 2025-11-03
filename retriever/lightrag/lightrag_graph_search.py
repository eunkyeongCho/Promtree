"""
LightRAG Graph Search - 그래프 기반 검색
엔티티 기반 컨텍스트 확장 및 관계 추적
임베딩 기반 유사도 매칭 지원
"""

from typing import List, Dict, Any, Set, Optional
from .lightrag_graph_storage import GraphStorage
import re
import numpy as np
from sentence_transformers import SentenceTransformer


class GraphSearcher:
    """
    그래프 기반 검색기
    - 엔티티 매칭 (문자열 + 임베딩)
    - 이웃 탐색 (N-hop)
    - 서브그래프 추출
    - 컨텍스트 생성
    """

    def __init__(
        self,
        graph_storage: GraphStorage,
        embedding_model: Optional[SentenceTransformer] = None,
        use_embedding: bool = True
    ):
        """
        그래프 검색기 초기화

        Args:
            graph_storage: 그래프 스토리지 인스턴스
            embedding_model: 임베딩 모델 (옵션)
            use_embedding: 임베딩 기반 매칭 사용 여부
        """
        self.storage = graph_storage
        self.use_embedding = use_embedding
        self.embedding_model = embedding_model

        # 엔티티 임베딩 캐시
        self.entity_embeddings = None
        self.entity_names_list = None

        if self.use_embedding and self.embedding_model is not None:
            self._build_entity_embeddings()

    def search(
        self,
        query: str,
        top_k: int = 5,
        max_hops: int = 2,
        extracted_entities: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        쿼리를 통해 그래프 검색

        Args:
            query: 검색 쿼리
            top_k: 최대 엔티티 수
            max_hops: 이웃 탐색 깊이
            extracted_entities: LLM이 추출한 엔티티 리스트 (옵션)

        Returns:
            Dict: 검색 결과
                - entities: 매칭된 엔티티 리스트
                - subgraph_entities: 서브그래프 엔티티 리스트
                - relationships: 관련 관계 리스트
                - context: 텍스트 컨텍스트
        """
        # 1. 쿼리에서 엔티티 추출 (문자열 + LLM + 임베딩)
        matched_entities = self._match_entities(query, top_k, extracted_entities)

        if not matched_entities:
            return {
                'entities': [],
                'subgraph_entities': [],
                'relationships': [],
                'context': ''
            }

        # 2. 서브그래프 추출
        entity_names = [e['entity_name'] for e in matched_entities]
        subgraph = self.storage.get_subgraph(entity_names, max_hops)

        # 3. 서브그래프 엔티티 및 관계 수집
        subgraph_entities = []
        for node in subgraph.nodes():
            node_data = subgraph.nodes[node]
            subgraph_entities.append({
                'entity_name': node,
                'entity_type': node_data.get('entity_type', ''),
                'description': node_data.get('description', ''),
                'mention_count': node_data.get('mention_count', 0)
            })

        relationships = []
        for src, tgt in subgraph.edges():
            edge_data = subgraph.edges[src, tgt]
            relationships.append({
                'src_id': src,
                'tgt_id': tgt,
                'weight': edge_data.get('weight', 1.0),
                'description': edge_data.get('description', ''),
                'keywords': edge_data.get('keywords', '')
            })

        # 4. 컨텍스트 생성
        context = self._generate_context(matched_entities, relationships)

        return {
            'entities': matched_entities,
            'subgraph_entities': subgraph_entities,
            'relationships': relationships,
            'context': context
        }

    def _build_entity_embeddings(self):
        """
        모든 엔티티의 임베딩을 미리 생성 (캐싱)
        """
        if self.embedding_model is None:
            return

        self.entity_names_list = list(self.storage.graph.nodes())
        if not self.entity_names_list:
            return

        print(f"[GraphSearcher] {len(self.entity_names_list)}개 엔티티 임베딩 생성 중...")
        self.entity_embeddings = self.embedding_model.encode(
            self.entity_names_list,
            batch_size=32,
            show_progress_bar=False
        )
        print(f"[GraphSearcher] 엔티티 임베딩 생성 완료")

    def _match_entities(
        self,
        query: str,
        top_k: int,
        extracted_entities: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        쿼리에서 엔티티 매칭 (문자열 + 임베딩)

        Args:
            query: 검색 쿼리
            top_k: 최대 엔티티 수
            extracted_entities: LLM이 추출한 엔티티 리스트 (옵션)

        Returns:
            List[Dict]: 매칭된 엔티티 리스트
        """
        matched = []
        query_lower = query.lower()

        # 1. 문자열 기반 매칭 (정확한 매칭)
        for node in self.storage.graph.nodes():
            node_data = self.storage.graph.nodes[node]
            node_lower = node.lower()

            # 엔티티 이름 매칭
            if node_lower in query_lower or query_lower in node_lower:
                matched.append({
                    'entity_name': node,
                    'entity_type': node_data.get('entity_type', ''),
                    'description': node_data.get('description', ''),
                    'mention_count': node_data.get('mention_count', 0),
                    'match_score': 1.0  # 정확한 매칭
                })

        # 2. LLM 추출 엔티티 매칭 (부분 매칭)
        if extracted_entities:
            for extracted_entity in extracted_entities:
                extracted_lower = extracted_entity.lower()
                for node in self.storage.graph.nodes():
                    node_data = self.storage.graph.nodes[node]
                    node_lower = node.lower()

                    # 이미 매칭된 엔티티는 제외
                    if any(m['entity_name'] == node for m in matched):
                        continue

                    # 부분 매칭
                    if extracted_lower in node_lower or node_lower in extracted_lower:
                        matched.append({
                            'entity_name': node,
                            'entity_type': node_data.get('entity_type', ''),
                            'description': node_data.get('description', ''),
                            'mention_count': node_data.get('mention_count', 0),
                            'match_score': 0.8  # LLM 추출 매칭
                        })

        # 3. 임베딩 기반 유사도 매칭 (문자열 매칭 실패 시)
        if not matched and self.use_embedding and self.entity_embeddings is not None:
            # 쿼리 임베딩
            query_embedding = self.embedding_model.encode([query])[0]

            # 코사인 유사도 계산
            similarities = np.dot(self.entity_embeddings, query_embedding) / (
                np.linalg.norm(self.entity_embeddings, axis=1) * np.linalg.norm(query_embedding)
            )

            # 유사도 상위 top_k * 2개 추출
            top_indices = np.argsort(similarities)[::-1][:top_k * 2]

            for idx in top_indices:
                similarity = similarities[idx]
                if similarity > 0.5:  # 임계값
                    node = self.entity_names_list[idx]
                    node_data = self.storage.graph.nodes[node]
                    matched.append({
                        'entity_name': node,
                        'entity_type': node_data.get('entity_type', ''),
                        'description': node_data.get('description', ''),
                        'mention_count': node_data.get('mention_count', 0),
                        'match_score': float(similarity)
                    })

        # mention_count와 match_score 기준 정렬
        matched.sort(key=lambda x: (x['match_score'], x['mention_count']), reverse=True)

        return matched[:top_k]

    def _generate_context(
        self,
        entities: List[Dict],
        relationships: List[Dict]
    ) -> str:
        """
        엔티티와 관계로부터 텍스트 컨텍스트 생성

        Args:
            entities: 엔티티 리스트
            relationships: 관계 리스트

        Returns:
            str: 텍스트 컨텍스트
        """
        context_parts = []

        # 엔티티 정보
        for entity in entities:
            entity_name = entity['entity_name']
            entity_type = entity['entity_type']
            description = entity.get('description', '')

            # § 구분자로 분리된 설명을 합치기
            if '§' in description:
                descriptions = description.split('§')
                desc_text = ', '.join(descriptions)
            else:
                desc_text = description

            context_parts.append(
                f"{entity_name} ({entity_type}): {desc_text}"
            )

        # 관계 정보
        for rel in relationships:
            src = rel['src_id']
            tgt = rel['tgt_id']
            description = rel.get('description', '')

            # § 구분자로 분리된 설명을 합치기
            if '§' in description:
                descriptions = description.split('§')
                desc_text = ', '.join(descriptions)
            else:
                desc_text = description

            context_parts.append(
                f"{src} - {tgt}: {desc_text}"
            )

        return '\n'.join(context_parts)
