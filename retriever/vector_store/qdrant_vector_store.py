from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

from typing import List
import numpy as np
import json

def init():
    """
    모델과 client 연결 초기화
    """
    # Qwen 임베딩 모델 로드
    model = SentenceTransformer('Qwen/Qwen3-Embedding-0.6B', trust_remote_code=True)

    # Qdrant 클라이언트 초기화
    client = QdrantClient(url="http://localhost:6333")

    return model, client

def query_embedding(model: SentenceTransformer, text: str) -> List[float]:
    """
    쿼리 텍스트를 임베딩 벡터로 변환

    Args:
        model: SentenceTransformer 모델
        text: 쿼리 텍스트
    Returns:
        임베딩 벡터 리스트
    """
    embedding = model.encode([text], normalize_embeddings=True)
    return embedding[0]


def search_similar_chunks(client: QdrantClient, qv, collections: list[str], top_k=5) -> list[dict]:
    """
    여러 Qdrant 컬렉션을 대상으로 쿼리 벡터와 유사한 청크를 검색합니다.

    이 함수는 주어진 컬렉션 리스트를 순회하며 각 컬렉션에 대해 벡터 검색을 수행하고,
    검색된 모든 결과를 하나의 리스트로 모읍니다. 이후 유사도(score) 기준으로
    전체 결과를 정렬하여 상위 top_k 개만 반환합니다.

    Args:
        client (QdrantClient):
            Qdrant 벡터 데이터베이스에 연결된 클라이언트 인스턴스.
        qv (list[float] 또는 np.ndarray):
            검색 기준이 되는 쿼리 벡터.
        collections (list[str]):
            검색을 수행할 컬렉션 이름 리스트.
        top_k (int, optional):
            최종적으로 반환할 상위 결과 개수. 기본값은 5.

    Returns:
        list[dict]:
            각 결과를 나타내는 딕셔너리 리스트.
            각 딕셔너리는 다음 필드를 포함합니다:
                - "score": 쿼리 벡터와의 유사도 점수
                - "chunk": 해당 청크의 payload(내용/메타데이터)
            결과는 score 기준으로 내림차순 정렬되며, 상위 top_k개만 반환됩니다.
    """
    if isinstance(qv, np.ndarray):
        qv = qv.tolist() # qdrant는 내부적으로 list 형태의 벡터를 기대하기 때문에, list로 변환

    combined_results = []
    
    for collection in collections:
        result = client.query_points(
            collection_name=collection,
            query=qv,
            limit=top_k,
        )

        for r in result.points:
            combined_results.append({
                "score": r.score,
                "chunk": r.payload
            })

    if not combined_results:
        print(f"No results found.")
        return

    combined_results = sorted(combined_results, key=lambda x: x["score"], reverse=True)

    for idx, item in enumerate(combined_results, start=1):
        score = item["score"]
        chunk = item["chunk"]

        try:
            chunk_str = json.dumps(chunk, ensure_ascii=False, indent=2)
        except:
            chunk_str = str(chunk)

        print(f"--- Result {idx} ---")
        print(f"Score: {score:.4f}")
        print(f"Chunk:\n{(chunk_str, '  ')}\n")

    return combined_results[:top_k]

if __name__ == "__main__":
    model, client = init()
    example_query = "Product Number 1509의 실험결과를 요약하시오"

    qv = query_embedding(model, example_query)
    results = search_similar_chunks(client, qv, collection_name="demo", top_k=2)

    print(f"Query: {example_query}")
    print(f"\n=== 검색 결과 (상위 {2}개) ===")

    for idx, point in enumerate(results.points, 1):
        print(f"\n--- 결과 {idx} ---")
        print(f"Score: {point.score:.4f}")
        print(f"Text: {point.payload.get('text', 'N/A')[:200]}...")
        print(f"Chunk Index: {point.payload.get('chunk_index', 'N/A')}")
