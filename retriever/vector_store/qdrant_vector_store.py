from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from typing import List

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


def search_similar_chunks(client: QdrantClient, qv, collection_name="demo", top_k=5):
    """
    쿼리 벡터와 유사한 청크 검색

    Args:
        client: QdrantClient 인스턴스
        qv: 쿼리 벡터
        collection_name: 컬렉션 이름
        top_k: 상위 k개 결과 반환
    Returns:
        유사한 청크 리스트
    """
    search_result = client.query_points(
        collection_name=collection_name,
        query=qv,
        limit=top_k,
    )
    return search_result

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
