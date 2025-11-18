from abc import ABC, abstractmethod


class BaseEmbeddingModel(ABC):
    @abstractmethod
    def embed_documents(self, documents: list[str], *args) -> list[list[float]]:
        """
            여러 문서 문자열을 임베딩하여 벡터 리스트로 반환합니다.

            Args:
                documents (list[str]): 임베딩할 텍스트 리스트

            Returns:
                list[list[float]]: 텍스트별 임베딩 벡터 리스트

            Notes:
                추상 클래스이므로 함수 본문은 없습니다. 구체적인 동작방식은 구현체에서 구현합니다.
        """
        pass

    @abstractmethod
    def embed_query(self, information_need: str, *args) -> list[float]:
        """
            검색용 질의 문장을 임베딩하여 벡터로 반환합니다.

            Args:
                information_need (str): 검색용 질의 문장

            Returns:
                list[float]: 질의문 임베딩 벡터

            Notes:
                추상 클래스이므로 함수 본문은 없습니다. 구체적인 동작방식은 구현체에서 구현합니다.
        """
        pass