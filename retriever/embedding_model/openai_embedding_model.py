import traceback
from langchain_openai import OpenAIEmbeddings
from embedding_model.base_embedding_model import BaseEmbeddingModel


class OpenAIEmbeddingModel(BaseEmbeddingModel):

    def __init__(self, model: str, api_key: str) -> None:
        self.embedding_model = OpenAIEmbeddings(
            model="text-embedding-3-large",
            dimensions=1024
        )

    def embed_documents(self, documents: list[str]) -> list[list[float]]:

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

    # def embed_query(self, information_need: str, *args):
