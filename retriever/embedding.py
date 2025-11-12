from sentence_transformers import SentenceTransformer
from typing import List
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
import uuid

def init():
    """
    모델과 client 연결 초기화
    """
    # Qwen 임베딩 모델 로드
    model = SentenceTransformer('Qwen/Qwen3-Embedding-0.6B', trust_remote_code=True)

    # Qdrant 클라이언트 초기화
    client = QdrantClient(url="http://localhost:6333")

    return model, client

def chunk_embedding_and_upsert(chunk: List[str], model: SentenceTransformer, client: QdrantClient, collection_name: str = "demo") -> None:
    """
    청크를 임베딩하고 Qdrant에 업로드

    Args:
        chunk: 청크 텍스트 리스트
        model: SentenceTransformer 모델
        client: QdrantClient 인스턴스
        collection_name: 컬렉션 이름
    """
    embeddings = model.encode(chunk, normalize_embeddings=True, show_progress_bar=True)

    # Qdrant에 임베딩 업로드 (원본 텍스트도 payload에 포함)
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding.tolist(),
            payload={"text": text, "chunk_index": idx}
        )
        for idx, (embedding, text) in enumerate(zip(embeddings, chunk))
    ]
    client.upsert(collection_name=collection_name, points=points)

if __name__ == "__main__":
    import retriever.chunker.chunking as chunking
    import retriever.parsing as parsing
    from pathlib import Path
    from qdrant_client.models import Distance, VectorParams

    model, client = init()

    # 컬렉션이 이미 존재하면 삭제 후 재생성
    collection_name = "demo"
    try:
        if client.collection_exists(collection_name):
            print(f"컬렉션 '{collection_name}'이 이미 존재합니다. 삭제 후 재생성합니다.")
            client.delete_collection(collection_name)
    except Exception as e:
        print(f"컬렉션 확인 중 오류: {e}")

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=1024, distance=Distance.DOT)
    )
    print(f"컬렉션 '{collection_name}' 생성 완료.")

    retriever_dir = Path(__file__).resolve().parent
    pdf_path = retriever_dir / "3M-1509-DC-Polyethylene-Tape-TIS-Jun13.pdf"

    converter = parsing.converter_init()
    contents = parsing.parse_pdf(pdf_path, converter)
    chunks = chunking.hybrid_chunking(contents, chunk_size=1000, chunk_overlap=100)

    for i, chunk in enumerate(chunks):
        print(f"--- Chunk {i+1} ---")
        print(chunk)
        print()

    chunk_embedding_and_upsert(chunks, model, client, collection_name)

    # 저장된 벡터 개수 확인
    count_result = client.count(collection_name=collection_name)
    print(f"\n=== 저장 완료 ===")
    print(f"총 벡터 개수: {count_result.count}")

    # 저장된 데이터 샘플 확인 (처음 3개)
    print(f"\n=== 저장된 데이터 샘플 (처음 3개) ===")
    scroll_result = client.scroll(
        collection_name=collection_name,
        limit=3,
        with_payload=True,
        with_vectors=True
    )

    for idx, point in enumerate(scroll_result[0], 1):
        print(f"\n--- 샘플 {idx} ---")
        print(f"ID: {point.id}")
        print(f"청크 인덱스: {point.payload.get('chunk_index', 'N/A')}")
        print(f"벡터 차원: {len(point.vector)}")
        print(f"벡터 샘플 (처음 10개): {point.vector[:10]}")
        print(f"원본 텍스트 (처음 200자):\n{point.payload.get('text', 'N/A')[:200]}...")
