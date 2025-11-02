from abc import ABC, abstractmethod


class BaseEmbeddingModel(ABC):
    @abstractmethod
    def embed_documents(self, documents: list[str], *args) -> list[list[float]]:
        pass

    @abstractmethod
    def embed_query(self, information_need: str, *args) -> list[float]:
        pass