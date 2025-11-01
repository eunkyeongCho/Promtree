import weaviate
from base_vector_store import BaseVectorStore
from langchain_core.documents import Document

class WeaviateVectorStore(BaseVectorStore):

    # Weaviate는 DB에서 Table에 해당하는 개념이 Class
    # 이름을 지정해줘야 하는데, 일단은 MaterialPropertyKnowledge으로 하드코딩하고 추후에 확장이 필요하다면 Initializer에서 받도록 수정할 예정
    class_name = "MaterialPropertyKnowledge"

    def __init__(self, cluster_url: str, api_key: str) -> None:

        # Weaviate Client 객체 생성
        self.client = weaviate.connect_to_weaviate_cloud(
            cluster_url=cluster_url,
            auth_credentials=weaviate.classes.init.Auth.api_key(api_key),
        )
        
        is_weaviate_client_connected = self.client.is_ready()

        if is_weaviate_client_connected:
            print("✅ Successfully connected to Weaviate Cloud.")
        else:
            print("❌ Failed to connect to Weaviate Cloud.")

    def add_documents(self, documents: list[Document], embedding_model) -> bool:

        collection = self.client.collections.get(self.class_name)

        contents = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]

        vectors = embedding_model.embed_documents(contents)

        with collection.batch.dynamic() as batch:
            for content, metadata, vector in zip(contents, metadatas, vectors):
                batch.add_data_object(
                    properties={
                        "text": content,
                        "metadata": metadata,
                    },
                    vector=vector,
                )

        return True

    # def similarity_search