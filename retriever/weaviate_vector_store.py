import weaviate
from base_vector_store import BaseVectorStore
from langchain_core.documents import Document

class WeaviateVectorStore(BaseVectorStore):

    # Weaviate에서 DB Table에 해당하는 개념이 Collection
    # 이름을 지정해줘야 하는데, 일단은 MaterialPropertyKnowledge으로 하드코딩하고 추후에 확장이 필요하다면 Initializer에서 받도록 수정할 예정
    collection_name = "MaterialPropertyKnowledge"

    def __init__(self, cluster_url: str, api_key: str) -> None:

        # client 생성
        self.client = weaviate.connect_to_weaviate_cloud(
            cluster_url=cluster_url,
            auth_credentials=weaviate.classes.init.Auth.api_key(api_key),
        )
        
        is_client_connected = self.client.is_ready()

        if is_client_connected:
            print("✅ Successfully connected to Weaviate Cloud.")
        else:
            print("❌ Failed to connect to Weaviate Cloud.")

        # collection 생성
        existing_collections = [c.name for c in self.client.collections.list_all()]

        if self.collection_name not in existing_collections:
            self.client.collections.create(
                name=self.collection_name,
                properties=[
                    {"name": "chunk", "dataType": "text"},
                    {"name": "metadata", "dataType": "json"},
                ],
                vectorizer_config={"vectorizer": "none"}, # 외부 임베딩 모델 사용해서 임베딩
            )

    def add_documents(self, documents: list[Document], embedding_model) -> bool:

        collection = self.client.collections.get(self.collection_name)

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