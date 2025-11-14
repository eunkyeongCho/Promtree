from retriever.chunker.markdown_chunker import MarkdownChunker
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

from pathlib import Path
from dotenv import load_dotenv

from retriever.embedding import chunk_embedding_and_upsert


class EmbeddingTest:
    def __init__(self):
        pass

    def test_embedding(self):
        BASE_DIR = Path(__file__).resolve().parents[1]  # root 경로
        markdown_sample_data_folder_path = BASE_DIR / "retriever" / "markdown_sample_data" # markdown 샘플 데이터 경로

        for markdown_file_path in markdown_sample_data_folder_path.rglob("*.md"): # md 파일만 순회돌기
            with open(markdown_file_path, "r", encoding="utf-8") as f:  # 파일로부터 md 문자열을 읽어옵니다.
                md = f.read()

                markdown_chunker = MarkdownChunker()
                chunks = markdown_chunker.chunk_markdown_file(md, "5bc0c676-018f-46de-bb0d-0103ff9c388c", "5bc0c676-018f-46de-bb0d-0103ff9c388c_3M-1509-DC-Polyethylene-Tape-TIS-Jun13", ["msds"]) # 임의로 하드코딩 했으므로 모든 샘플 파일의 file_info의 키 중 file_uuid, file_name, collections 값이 동일하게 청크가 만들어집니다.

        # Qwen 임베딩 모델 로드
        model = SentenceTransformer('Qwen/Qwen3-Embedding-0.6B', trust_remote_code=True)

        # Qdrant 클라이언트 초기화
        client = QdrantClient(url="http://localhost:6333")

        chunk_embedding_and_upsert(chunks, model, client, ["msds"])

if __name__ == "__main__":
    embedding_test = EmbeddingTest()
    embedding_test.test_embedding()