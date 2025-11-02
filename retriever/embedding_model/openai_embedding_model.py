from langchain_openai import OpenAIEmbeddings
from embedding_model.base_embedding_model import BaseEmbeddingModel


class OpenAIEmbeddingModel(BaseEmbeddingModel):
    embed = OpenAIEmbeddings(
        model="text-embedding-3-large"
        # With the `text-embedding-3` class
        # of models, you can specify the size
        # of the embeddings you want returned.
        # dimensions=1024
    )