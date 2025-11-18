"""
LightRAG Entity Merger - ApeRAG 핵심 기능 구현
Cross-chunk 엔티티 및 관계 병합 (ApeRAG 방식)
"""

from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Any
from .lightrag_graph_storage import GraphStorage, GRAPH_FIELD_SEP


class EntityMerger:
    """
    ApeRAG 방식 엔티티 병합기
    - Cross-chunk 데이터 수집
    - 타입 선택 (빈도 기반)
    - 설명 병합 (§ 구분자)
    - 가중치 누적
    - 지능형 요약 (선택)
    """

    def __init__(self, graph_storage: GraphStorage):
        """
        엔티티 병합기 초기화

        Args:
            graph_storage: 그래프 스토리지 인스턴스
        """
        self.storage = graph_storage

    def merge_nodes_and_edges(
        self,
        chunk_results: List[Tuple[Dict, Dict]],
        force_llm_summary_threshold: int = 5
    ) -> Tuple[int, int]:
        """
        여러 청크의 추출 결과를 병합하여 그래프 업데이트 (ApeRAG 방식)

        Args:
            chunk_results: [(maybe_nodes, maybe_edges), ...]
            force_llm_summary_threshold: LLM 요약 시작 임계값 (현재는 미구현)

        Returns:
            Tuple[num_entities, num_relationships]: 업데이트된 엔티티/관계 수
        """
        print("[EntityMerger] Cross-chunk 데이터 수집 중...")

        # 1. Cross-chunk 데이터 수집
        all_nodes = defaultdict(list)  # {entity_name: [entity1, entity2, ...]}
        all_edges = defaultdict(list)  # {(src, tgt): [edge1, edge2, ...]}

        for maybe_nodes, maybe_edges in chunk_results:
            # 엔티티 수집
            for entity_name, entities in maybe_nodes.items():
                all_nodes[entity_name].extend(entities)

            # 관계 수집 (양방향 정규화)
            for edge_key, edges in maybe_edges.items():
                sorted_key = tuple(sorted(edge_key))
                all_edges[sorted_key].extend(edges)

        print(f"[EntityMerger] 수집 완료: {len(all_nodes)}개 엔티티, {len(all_edges)}개 관계")

        # 2. 엔티티 병합 및 저장
        num_entities = 0
        for entity_name, entities in all_nodes.items():
            merged_entity = self._merge_entity(entity_name, entities)
            if self.storage.upsert_node(entity_name, merged_entity):
                num_entities += 1

        # 3. 관계 병합 및 저장
        num_relationships = 0
        for edge_key, edges in all_edges.items():
            src, tgt = edge_key
            merged_edge = self._merge_edge(edges)

            # 엔티티 존재 확인 (자동 생성)
            if not self.storage.get_node(src):
                self._create_missing_entity(src)
            if not self.storage.get_node(tgt):
                self._create_missing_entity(tgt)

            if self.storage.upsert_edge(src, tgt, merged_edge):
                num_relationships += 1

        print(f"[EntityMerger] 병합 완료: {num_entities}개 엔티티, {num_relationships}개 관계 업데이트")

        return num_entities, num_relationships

    def _merge_entity(self, entity_name: str, entities: List[Dict]) -> Dict[str, Any]:
        """
        같은 이름의 엔티티들을 병합 (ApeRAG 방식)

        Args:
            entity_name: 엔티티 이름
            entities: 엔티티 리스트

        Returns:
            Dict: 병합된 엔티티 데이터
        """
        # 1. 타입 선택: 가장 빈도가 높은 타입
        entity_types = [e.get("entity_type", "Unknown") for e in entities]
        entity_type = Counter(entity_types).most_common(1)[0][0]

        # 2. 설명 병합: § 구분자로 연결, 중복 제거 및 정렬
        descriptions = []
        for entity in entities:
            desc = entity.get("description", "").strip()
            if desc:
                descriptions.append(desc)

        # 기존 엔티티가 있으면 기존 설명도 포함
        existing_entity = self.storage.get_node(entity_name)
        if existing_entity and existing_entity.get("description"):
            existing_descs = existing_entity["description"].split(GRAPH_FIELD_SEP)
            descriptions.extend(existing_descs)

        # 중복 제거 및 정렬
        unique_descriptions = sorted(set(desc.strip() for desc in descriptions if desc.strip()))
        merged_description = GRAPH_FIELD_SEP.join(unique_descriptions)

        # 3. 출처 정보 수집
        source_chunks = []
        file_paths = []
        for entity in entities:
            source_id = entity.get("source_id")
            if source_id:
                source_chunks.append(source_id)

            file_path = entity.get("file_path")
            if file_path:
                file_paths.append(file_path)

        # 기존 출처도 포함
        if existing_entity:
            source_chunks.extend(existing_entity.get("source_chunks", []))
            file_paths.extend(existing_entity.get("file_paths", []))

        # 중복 제거
        source_chunks = sorted(set(source_chunks))
        file_paths = sorted(set(file_paths))

        # 4. 언급 횟수
        mention_count = len(source_chunks)

        # TODO: 지능형 요약 (description이 너무 길면 LLM으로 요약)
        # fragment_count = merged_description.count(GRAPH_FIELD_SEP) + 1
        # if fragment_count >= force_llm_summary_threshold:
        #     merged_description = await llm_summarize(entity_name, merged_description)

        return {
            "entity_type": entity_type,
            "description": merged_description,
            "source_chunks": source_chunks,
            "file_paths": file_paths,
            "mention_count": mention_count
        }

    def _merge_edge(self, edges: List[Dict]) -> Dict[str, Any]:
        """
        같은 관계의 엣지들을 병합 (ApeRAG 방식)

        Args:
            edges: 엣지 리스트

        Returns:
            Dict: 병합된 엣지 데이터
        """
        # 1. 가중치 누적
        total_weight = sum(edge.get("weight", 1.0) for edge in edges)

        # 기존 엣지가 있으면 기존 가중치도 누적
        src, tgt = edges[0].get("src_id"), edges[0].get("tgt_id")
        existing_edge = self.storage.get_edge(src, tgt)
        if existing_edge:
            total_weight += existing_edge.get("weight", 0.0)

        # 2. 설명 병합: § 구분자로 연결
        descriptions = []
        for edge in edges:
            desc = edge.get("description", "").strip()
            if desc:
                descriptions.append(desc)

        # 기존 설명도 포함
        if existing_edge and existing_edge.get("description"):
            existing_descs = existing_edge["description"].split(GRAPH_FIELD_SEP)
            descriptions.extend(existing_descs)

        # 중복 제거 및 정렬
        unique_descriptions = sorted(set(desc.strip() for desc in descriptions if desc.strip()))
        merged_description = GRAPH_FIELD_SEP.join(unique_descriptions)

        # 3. 키워드 병합
        all_keywords = []
        for edge in edges:
            keywords = edge.get("keywords", "")
            if keywords:
                all_keywords.extend([k.strip() for k in keywords.split(",")])

        # 기존 키워드도 포함
        if existing_edge and existing_edge.get("keywords"):
            existing_keywords = existing_edge["keywords"].split(",")
            all_keywords.extend([k.strip() for k in existing_keywords])

        # 중복 제거 및 정렬
        unique_keywords = sorted(set(k for k in all_keywords if k))
        merged_keywords = ", ".join(unique_keywords)

        # 4. 출처 정보
        source_chunks = []
        file_paths = []
        for edge in edges:
            source_id = edge.get("source_id")
            if source_id:
                source_chunks.append(source_id)

            file_path = edge.get("file_path")
            if file_path:
                file_paths.append(file_path)

        # 기존 출처도 포함
        if existing_edge:
            source_chunks.extend(existing_edge.get("source_chunks", []))
            file_paths.extend(existing_edge.get("file_paths", []))

        # 중복 제거
        source_chunks = sorted(set(source_chunks))
        file_paths = sorted(set(file_paths))

        # 5. 언급 횟수
        mention_count = len(source_chunks)

        return {
            "weight": total_weight,
            "description": merged_description,
            "keywords": merged_keywords,
            "source_chunks": source_chunks,
            "file_paths": file_paths,
            "mention_count": mention_count
        }

    def _create_missing_entity(self, entity_name: str):
        """
        누락된 엔티티 자동 생성 (Fault Tolerance)

        Args:
            entity_name: 엔티티 이름
        """
        print(f"[EntityMerger] 누락된 엔티티 자동 생성: {entity_name}")
        self.storage.upsert_node(entity_name, {
            "entity_type": "Unknown",
            "description": "자동 생성된 엔티티",
            "source_chunks": [],
            "file_paths": [],
            "mention_count": 0
        })


if __name__ == "__main__":
    # 테스트 코드
    print("=== EntityMerger 테스트 ===\n")

    from .lightrag_graph_storage import GraphStorage

    storage = GraphStorage()
    storage.clear_graph()  # 초기화

    merger = EntityMerger(storage)

    # 테스트 데이터: 2개 청크에서 추출된 결과
    chunk_results = [
        # Chunk 1
        (
            {
                "John": [{
                    "entity_name": "John",
                    "entity_type": "Person",
                    "description": "CTO",
                    "source_id": "chunk_001",
                    "file_path": "test.txt"
                }],
                "ABC Corp": [{
                    "entity_name": "ABC Corp",
                    "entity_type": "Organization",
                    "description": "Technology company",
                    "source_id": "chunk_001",
                    "file_path": "test.txt"
                }]
            },
            {
                ("ABC Corp", "John"): [{
                    "src_id": "John",
                    "tgt_id": "ABC Corp",
                    "weight": 1.0,
                    "description": "Employment",
                    "keywords": "employee, company",
                    "source_id": "chunk_001",
                    "file_path": "test.txt"
                }]
            }
        ),
        # Chunk 2 (같은 엔티티 반복)
        (
            {
                "John": [{
                    "entity_name": "John",
                    "entity_type": "Person",
                    "description": "Product Manager",
                    "source_id": "chunk_002",
                    "file_path": "test.txt"
                }],
                "ABC Corp": [{
                    "entity_name": "ABC Corp",
                    "entity_type": "Company",  # 다른 타입
                    "description": "Technology company",  # 중복 설명
                    "source_id": "chunk_002",
                    "file_path": "test.txt"
                }]
            },
            {
                ("ABC Corp", "John"): [{
                    "src_id": "John",
                    "tgt_id": "ABC Corp",
                    "weight": 1.0,
                    "description": "Management",  # 다른 설명
                    "keywords": "management, responsible",  # 다른 키워드
                    "source_id": "chunk_002",
                    "file_path": "test.txt"
                }]
            }
        )
    ]

    # 병합 실행
    print("엔티티 및 관계 병합 중...")
    num_entities, num_relationships = merger.merge_nodes_and_edges(chunk_results)

    print(f"\n병합 결과: {num_entities}개 엔티티, {num_relationships}개 관계\n")

    # 결과 확인
    print("=== 병합된 엔티티 ===")
    john = storage.get_node("John")
    print(f"\nJohn:")
    print(f"  타입: {john['entity_type']}")
    print(f"  설명: {john['description']}")
    print(f"  언급횟수: {john['mention_count']}")
    print(f"  출처: {john['source_chunks']}")

    abc = storage.get_node("ABC Corp")
    print(f"\nABC Corp:")
    print(f"  타입: {abc['entity_type']}")
    print(f"  설명: {abc['description']}")
    print(f"  언급횟수: {abc['mention_count']}")

    print("\n=== 병합된 관계 ===")
    edge = storage.get_edge("John", "ABC Corp")
    print(f"\nJohn <-> ABC Corp:")
    print(f"  가중치: {edge['weight']}")
    print(f"  설명: {edge['description']}")
    print(f"  키워드: {edge['keywords']}")
    print(f"  언급횟수: {edge['mention_count']}")

    print("\n그래프 통계:")
    stats = storage.get_stats()
    print(f"  노드: {stats['num_nodes']}개")
    print(f"  엣지: {stats['num_edges']}개")

    print("\n=== 테스트 완료 ===")
