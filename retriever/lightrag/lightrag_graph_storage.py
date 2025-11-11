"""
LightRAG Graph Storage - ApeRAG 방식 구현
MongoDB + NetworkX 기반 그래프 스토리지
"""

from dotenv import load_dotenv
import os
from pymongo import MongoClient
import networkx as nx
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json

load_dotenv()

# MongoDB 연결 설정
USERNAME = os.getenv("MONGO_INITDB_ROOT_USERNAME", "admin")
PASSWORD = os.getenv("MONGO_INITDB_ROOT_PASSWORD", "password")
HOST = os.getenv("MONGO_HOST", "localhost")
PORT = int(os.getenv("MONGO_PORT", "27017"))

url = f"mongodb://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/"
client = MongoClient(url)
db = client['s307_db']

# 그래프 데이터용 컬렉션
entities_collection = db['graph_entities']  # 엔티티 노드
relationships_collection = db['graph_relationships']  # 관계 엣지

# ApeRAG 스타일 구분자
GRAPH_FIELD_SEP = "§"


class GraphStorage:
    """
    ApeRAG 방식의 그래프 스토리지 클래스
    - MongoDB: 영구 저장
    - NetworkX: 메모리 내 그래프 연산
    """

    def __init__(self):
        """그래프 스토리지 초기화"""
        self.graph = nx.Graph()  # NetworkX 그래프
        self._load_graph_from_db()

    def _load_graph_from_db(self):
        """MongoDB에서 그래프 로드"""
        print("[GraphStorage] MongoDB에서 그래프 로드 중...")

        # 엔티티 로드
        entities = list(entities_collection.find({}))
        for entity in entities:
            self.graph.add_node(
                entity['entity_name'],
                entity_type=entity.get('entity_type', ''),
                description=entity.get('description', ''),
                source_chunks=entity.get('source_chunks', []),
                mention_count=entity.get('mention_count', 0)
            )

        # 관계 로드
        relationships = list(relationships_collection.find({}))
        for rel in relationships:
            self.graph.add_edge(
                rel['src_id'],
                rel['tgt_id'],
                weight=rel.get('weight', 1.0),
                description=rel.get('description', ''),
                keywords=rel.get('keywords', ''),
                source_chunks=rel.get('source_chunks', [])
            )

        print(f"[GraphStorage] 로드 완료: {self.graph.number_of_nodes()}개 노드, {self.graph.number_of_edges()}개 엣지")

    def upsert_node(self, entity_name: str, entity_data: Dict[str, Any]) -> bool:
        """
        엔티티 노드 추가/업데이트 (ApeRAG 방식)

        Args:
            entity_name: 엔티티 이름
            entity_data: 엔티티 데이터
                - entity_type: 엔티티 타입
                - description: 설명 (§로 구분된 여러 설명)
                - source_chunks: 출처 청크 리스트
                - mention_count: 언급 횟수

        Returns:
            bool: 성공 여부
        """
        try:
            # NetworkX 그래프 업데이트
            if self.graph.has_node(entity_name):
                # 기존 노드 업데이트
                self.graph.nodes[entity_name].update(entity_data)
            else:
                # 새 노드 추가
                self.graph.add_node(entity_name, **entity_data)

            # MongoDB 업데이트
            entity_doc = {
                'entity_name': entity_name,
                'entity_type': entity_data.get('entity_type', ''),
                'description': entity_data.get('description', ''),
                'source_chunks': entity_data.get('source_chunks', []),
                'file_paths': entity_data.get('file_paths', []),
                'mention_count': entity_data.get('mention_count', 0),
                'updated_at': datetime.now()
            }

            entities_collection.update_one(
                {'entity_name': entity_name},
                {'$set': entity_doc, '$setOnInsert': {'created_at': datetime.now()}},
                upsert=True
            )

            return True

        except Exception as e:
            print(f"[GraphStorage] 노드 업데이트 실패: {e}")
            return False

    def upsert_edge(self, src_id: str, tgt_id: str, edge_data: Dict[str, Any]) -> bool:
        """
        관계 엣지 추가/업데이트 (ApeRAG 방식)

        Args:
            src_id: 소스 엔티티
            tgt_id: 타겟 엔티티
            edge_data: 엣지 데이터
                - weight: 가중치 (누적)
                - description: 설명 (§로 구분)
                - keywords: 키워드
                - source_chunks: 출처 청크 리스트

        Returns:
            bool: 성공 여부
        """
        try:
            # 양방향 정규화: 알파벳 순서로 정렬
            sorted_ids = tuple(sorted([src_id, tgt_id]))

            # NetworkX 그래프 업데이트
            if self.graph.has_edge(src_id, tgt_id):
                # 기존 엣지 업데이트
                self.graph.edges[src_id, tgt_id].update(edge_data)
            else:
                # 새 엣지 추가
                self.graph.add_edge(src_id, tgt_id, **edge_data)

            # MongoDB 업데이트
            edge_doc = {
                'src_id': sorted_ids[0],
                'tgt_id': sorted_ids[1],
                'weight': edge_data.get('weight', 1.0),
                'description': edge_data.get('description', ''),
                'keywords': edge_data.get('keywords', ''),
                'source_chunks': edge_data.get('source_chunks', []),
                'file_paths': edge_data.get('file_paths', []),
                'mention_count': edge_data.get('mention_count', 0),
                'updated_at': datetime.now()
            }

            relationships_collection.update_one(
                {'src_id': sorted_ids[0], 'tgt_id': sorted_ids[1]},
                {'$set': edge_doc, '$setOnInsert': {'created_at': datetime.now()}},
                upsert=True
            )

            return True

        except Exception as e:
            print(f"[GraphStorage] 엣지 업데이트 실패: {e}")
            return False

    def get_node(self, entity_name: str) -> Optional[Dict[str, Any]]:
        """
        엔티티 노드 조회

        Args:
            entity_name: 엔티티 이름

        Returns:
            Optional[Dict]: 엔티티 데이터 (없으면 None)
        """
        if self.graph.has_node(entity_name):
            return dict(self.graph.nodes[entity_name])
        return None

    def get_edge(self, src_id: str, tgt_id: str) -> Optional[Dict[str, Any]]:
        """
        관계 엣지 조회

        Args:
            src_id: 소스 엔티티
            tgt_id: 타겟 엔티티

        Returns:
            Optional[Dict]: 엣지 데이터 (없으면 None)
        """
        if self.graph.has_edge(src_id, tgt_id):
            return dict(self.graph.edges[src_id, tgt_id])
        return None

    def get_neighbors(self, entity_name: str, max_hops: int = 1) -> List[str]:
        """
        이웃 노드 조회 (N-hop neighbors)

        Args:
            entity_name: 엔티티 이름
            max_hops: 최대 hop 수

        Returns:
            List[str]: 이웃 엔티티 이름 리스트
        """
        if not self.graph.has_node(entity_name):
            return []

        neighbors = set()
        current_level = {entity_name}

        for _ in range(max_hops):
            next_level = set()
            for node in current_level:
                next_level.update(self.graph.neighbors(node))
            neighbors.update(next_level)
            current_level = next_level

        neighbors.discard(entity_name)  # 자기 자신 제외
        return list(neighbors)

    def get_subgraph(self, entity_names: List[str], max_hops: int = 2) -> nx.Graph:
        """
        서브그래프 추출

        Args:
            entity_names: 중심 엔티티 리스트
            max_hops: 최대 hop 수

        Returns:
            nx.Graph: 서브그래프
        """
        nodes = set(entity_names)

        for entity in entity_names:
            neighbors = self.get_neighbors(entity, max_hops)
            nodes.update(neighbors)

        return self.graph.subgraph(nodes).copy()

    def find_shortest_path(self, src: str, tgt: str) -> Optional[List[str]]:
        """
        최단 경로 찾기

        Args:
            src: 시작 엔티티
            tgt: 종료 엔티티

        Returns:
            Optional[List[str]]: 경로 (없으면 None)
        """
        try:
            return nx.shortest_path(self.graph, src, tgt)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def get_connected_components(self) -> List[List[str]]:
        """
        Connected Components 추출 (ApeRAG 병렬 처리 최적화용)

        Returns:
            List[List[str]]: 각 컴포넌트의 노드 리스트
        """
        return [list(component) for component in nx.connected_components(self.graph)]

    def clear_graph(self):
        """그래프 초기화 (테스트용)"""
        self.graph.clear()
        entities_collection.delete_many({})
        relationships_collection.delete_many({})
        print("[GraphStorage] 그래프 초기화 완료")

    def get_stats(self) -> Dict[str, Any]:
        """
        그래프 통계 정보

        Returns:
            Dict: 통계 정보
        """
        return {
            'num_nodes': self.graph.number_of_nodes(),
            'num_edges': self.graph.number_of_edges(),
            'num_components': nx.number_connected_components(self.graph),
            'avg_degree': sum(dict(self.graph.degree()).values()) / max(self.graph.number_of_nodes(), 1)
        }


if __name__ == "__main__":
    # 테스트 코드
    print("=== GraphStorage 테스트 ===\n")

    storage = GraphStorage()

    # 1. 노드 추가
    print("1. 노드 추가 테스트")
    storage.upsert_node("John", {
        'entity_type': 'Person',
        'description': 'CTO§Product Manager',
        'source_chunks': ['chunk_001', 'chunk_002'],
        'mention_count': 2
    })

    storage.upsert_node("ABC Corp", {
        'entity_type': 'Organization',
        'description': 'Technology company',
        'source_chunks': ['chunk_001'],
        'mention_count': 1
    })

    # 2. 엣지 추가
    print("2. 엣지 추가 테스트")
    storage.upsert_edge("John", "ABC Corp", {
        'weight': 2.0,
        'description': 'Employment§Management',
        'keywords': 'employee, company',
        'source_chunks': ['chunk_001', 'chunk_002']
    })

    # 3. 조회 테스트
    print("\n3. 조회 테스트")
    john = storage.get_node("John")
    print(f"John 노드: {john}")

    edge = storage.get_edge("John", "ABC Corp")
    print(f"John-ABC Corp 엣지: {edge}")

    # 4. 통계
    print("\n4. 그래프 통계")
    stats = storage.get_stats()
    print(f"통계: {stats}")

    print("\n=== 테스트 완료 ===")
