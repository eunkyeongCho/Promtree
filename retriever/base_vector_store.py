from abc import ABC, abstractmethod
from typing import List
from langchain_core.documents import Document

class BaseVectorStore(ABC):

    @abstractmethod
    def add_documents(self, documents: List[Document], embedding_model, *args):
        pass

    @abstractmethod
    def similarity_search(self, query_text: str, top_k: int = 5, *args):
        pass
