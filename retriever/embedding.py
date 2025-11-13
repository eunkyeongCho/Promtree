from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from qdrant_client.models import VectorParams, Distance

from typing import List
import uuid
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

def chunk_embedding_and_upsert(chunks: List[dict], model: SentenceTransformer, client: QdrantClient, collections: list[str]) -> None:
    """
    청크를 임베딩하고 Qdrant에 업로드

    Args:
        chunk: 청크 리스트
        model: SentenceTransformer 모델
        client: QdrantClient 인스턴스
        collections: 사용자가 선택한 컬렉션 리스트
    """

    points = []
    for idx, chunk in enumerate(chunks, 1):
        if chunk['type'] == "text" or chunk['type'] == "table":
            embeddings = model.encode(chunk['content'], normalize_embeddings=True, show_progress_bar=True)
        else:
            embeddings = model.encode(chunk['metadata'], normalize_embeddings=True, show_progress_bar=True)

        print(f"✅ Embedding chunk {idx}/{len(chunks)}\n")

        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=embeddings,
            payload=chunk
        )

        print(json.dumps({
            "id": point.id,
            "vector_dim": len(point.vector),
            "payload": point.payload
        }, ensure_ascii=False, indent=2))

        points.append(point)

    print("✅ Embedding completed.\n")

    for collection in collections:
        print(f"📌 Uploading to {collection} collection in Qdrant...\n")
        client.upsert(collection_name=collection, points=points)
    
    print("🎉 All embeddings successfully uploaded to Qdrant!\n")

if __name__ == "__main__":
    import retriever.chunker.chunking as chunking
    from retriever.chunker.markdown_chunker import MarkdownChunker
    import retriever.parsing as parsing
    from pathlib import Path
    from qdrant_client.models import Distance, VectorParams

    model, client = init()

    # 컬렉션이 이미 존재하면 삭제 후 재생성
    collections = ["msds", "tds"]
    for collection in collections:
        try:
            if client.collection_exists(collection):
                print(f"컬렉션 '{collection}'이 이미 존재합니다. 삭제 후 재생성합니다.")
                client.delete_collection(collection)
        except Exception as e:
            print(f"컬렉션 확인 중 오류: {e}")

        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(
                size=1024,
                distance=Distance.COSINE
            )
        )
        print(f"컬렉션 '{collection}' 생성 완료.")

    retriever_dir = Path(__file__).resolve().parent
    pdf_path = retriever_dir / "3M-1509-DC-Polyethylene-Tape-TIS-Jun13.pdf"
    markdown_sample_data_folder_path = retriever_dir / "markdown_sample_data"

    # converter = parsing.converter_init()
    # contents = parsing.parse_pdf(pdf_path, converter)

    markdown_chunker = MarkdownChunker()

    for md_file_path in markdown_sample_data_folder_path.rglob("*.md"): # md 파일만 순회돌기

        chunks = markdown_chunker.chunk_markdown_file(md_file_path)

    chunk_embedding_and_upsert(chunks, model, client, ["msds", "tds"])

    # 저장된 벡터 개수 확인
    for collection in collections:
        count_result = client.count(collection_name=collection)
        print(f"\n=== 저장 완료 ===")
        print(f"총 벡터 개수: {count_result.count}")

    # 저장된 데이터 샘플 확인 (처음 3개)
    for collection in collections:
        print(f"\n=== 저장된 데이터 샘플 (처음 3개) ===")
        scroll_result = client.scroll(
            collection_name=collection,
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
