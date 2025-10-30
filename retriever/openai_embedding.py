# 임베딩 모델
from langchain_openai import OpenAIEmbeddings

# 기타
from typing import TypedDict

# Chunk dict 타입 정의
class Chunk(TypedDict):
    type: str
    file_name: str
    page_num: list[int]
    content: str
    metadata: str

# 임베딩 모델 정의
openai_embedding_model = OpenAIEmbeddings(
    model="text-embedding-3-large",
    dimensions=1024
)

# 한 pdf 파일의 청크들을 임베딩
def embed_documents(chunks: list[Chunk]) -> bool:

    for chunk in chunks:
        match chunk['type']:
            case "text":
                # 텍스트 청크 처리
                vectors = openai_embedding_model.embed_documents([chunk["content"]])

    vectors = openai_embedding_model.embed_documents(["hello", "goodbye"])

# 쿼리를 임베딩해서 유사도 검색 (매개값으로 벡터 스토어에 접근할 수 있는 객체가 주어져야 할듯)

