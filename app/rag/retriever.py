from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from typing import List
from pathlib import Path
import requests
from dotenv import load_dotenv
import os
import numpy as np

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


def search_similar_chunks(client: QdrantClient, qv, collections: list[str], top_k=5):
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

    raw_results = []
    for collection in collections: # 각 컬렉션에 대해 검색
        raw_result = client.query_points(
            collection_name=collection,
            query=qv.tolist() if hasattr(qv, 'tolist') else qv,
            limit=top_k
        )
        raw_results.extend(raw_result.points)

    # 전체 결과 score 기준 정렬 (내림차순)
    raw_results.sort(key=lambda x: x.score, reverse=True)

    search_result = []
    search_result = [
        {
            "score": r.score,
            "chunk": r.payload
        }
        for r in raw_results
    ]

    return search_result

if __name__ == "__main__":
    model, client = init()
    example_query = "Product Number 1509의 실험결과를 요약하시오"

    qv = query_embedding(model, example_query)
    results = search_similar_chunks(client, qv, ["msds", "tds"], top_k=2)

    prompt = f"""
    당신은 질문에 답변하는 AI 어시스턴트입니다.
    벡터 검색 결과를 참고하여 정확하고 포괄적인 답변을 제공하세요.
    
    질문: {example_query}
    Qdrant 벡터 검색 결과: {results}
    """

    BASE_DIR = Path(__file__).resolve().parents[1]  # root 경로
    load_dotenv(BASE_DIR / "common" / ".env")

    RUNPOD_URI = os.getenv("RUNPOD_URI")
    RUNPOD_LLM_MODEL = os.getenv("RUNPOD_LLM_MODEL")
    TIMEOUT = os.getenv("TIMEOUT")

    # 답변 요청
    url = f"{RUNPOD_URI}/api/generate"
    payload = {"model": RUNPOD_LLM_MODEL, "prompt": prompt, "stream": False}
    timeout = float(TIMEOUT) if TIMEOUT else None
    response = requests.post(url, json=payload, timeout=timeout)

    try:
        response.raise_for_status() # 에러나면 예외 발생시킴
    except requests.RequestException as e:
        print(f"HTTP request failed: {e}")

    print(f"🔍 LLM response: {response.json()['response']}")