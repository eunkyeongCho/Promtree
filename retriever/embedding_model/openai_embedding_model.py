import traceback
from langchain_openai import OpenAIEmbeddings
from embedding_model.base_embedding_model import BaseEmbeddingModel


class OpenAIEmbeddingModel(BaseEmbeddingModel):

    def __init__(self, model: str, api_key: str) -> None:
        """
            OpenAI 임베딩 모델 초기화.

            Args:
                model (str): 사용할 임베딩 모델 이름 (예: "text-embedding-3-large")
                api_key (str): env 파일에서 OPENAI_API_KEY 로드
        """
        self.embedding_model = OpenAIEmbeddings(
            model=model,
            dimensions=1024
        )

    def embed_documents(self, documents: list[str]) -> list[list[float]]:
        """
            여러 문서 문자열을 임베딩하여 벡터 리스트로 반환합니다.

            Args:
                documents (list[str]): 임베딩할 텍스트 리스트

            Returns:
                list[list[float]]: 텍스트별 임베딩 벡터 리스트
        """

        if not documents:
            return []

        try:
            document_vectors = self.embedding_model.embed_documents(documents)
        except Exception as e:
            error_details = traceback.format_exc()
            raise RuntimeError(
                f"❌ Embedding failed for documents batch:\n{error_details}"
            ) from e

        return document_vectors

    def embed_query(self, information_need: str):
        """
            단일 질의문(query)를 임베딩하여 벡터로 반환합니다.

            Args:
                information_need (str): 검색용 질의 문장

            Returns:
                list[float]: 질의문 임베딩 벡터
        """

        if not information_need:
            return []

        try:
            information_need_vector = self.embedding_model.embeddings.embed_query(information_need)
        except Exception as e:
            error_details = traceback.format_exc()
            raise RuntimeError(
                f"❌ Failed to embed query text:\n"
                f"Query: {information_need!r}\n"
                f"Error Details:\n{error_details}"
            ) from e

        return information_need_vector
