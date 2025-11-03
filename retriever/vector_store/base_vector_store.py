from abc import ABC, abstractmethod
from langchain_core.documents import Document
from retriever.embedding_model.base_embedding_model import BaseEmbeddingModel


class BaseVectorStore(ABC):
    @abstractmethod
    def add_documents(self, documents: list[Document], embedding_model: BaseEmbeddingModel, *args):
        """
            Document 리스트를 임베딩하여 벡터 스토어에 일괄 저장합니다.

            Args:
                documents (list[Document]): 저장할 Document 목록. (LangChain Core Document타입의 배열)
                embedding_model (BaseEmbeddingModel): 사용할 임베딩 모델

            Returns:
                bool: 저장 완료 시 True.

            Notes:
                추상 클래스이므로 함수 본문은 없습니다. 구체적인 동작방식은 구현체에서 구현합니다.
        """
        pass

    @abstractmethod
    def similarity_search(self, information_need: str, embedding_model: BaseEmbeddingModel, *args):
        """
            비교해서 검색할 문자열에 대해 임베딩을 생성한 후, 유사 문서를 벡터 스토어에서 검색합니다.

            Args:
                information_need (str): 검색 질의 문자열
                embedding_model (BaseEmbeddingModel): 사용할 임베딩 모델

            Returns:
                list[Document]: 유사도가 높은 순으로 정렬된 Document 리스트
            
            Notes:
                추상 클래스이므로 함수 본문은 없습니다. 구체적인 동작방식은 구현체에서 구현합니다.
        """
        pass
