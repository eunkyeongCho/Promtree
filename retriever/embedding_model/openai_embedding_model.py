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

    def embed_query(self, information_need: str):

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
