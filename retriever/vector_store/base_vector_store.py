from abc import ABC, abstractmethod
from langchain_core.documents import Document
from retriever.embedding_model.base_embedding_model import BaseEmbeddingModel


class BaseVectorStore(ABC):
    @abstractmethod
    def add_documents(self, documents: list[Document], embedding_model: BaseEmbeddingModel, *args):
        pass

    @abstractmethod
    def similarity_search(self, information_need: str, embedding_model: BaseEmbeddingModel, *args):
        pass
