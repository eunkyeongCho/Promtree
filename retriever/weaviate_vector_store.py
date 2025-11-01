import weaviate
from base_vector_store import BaseVectorStore

class WeaviateVectorStore(BaseVectorStore):

    def __init__(
        self,
        cluster_url: str,
        api_key: str,
    ):

        self.client = weaviate.connect_to_weaviate_cloud(
            cluster_url=cluster_url,
            auth_credentials=weaviate.classes.init.Auth.api_key(api_key),
        )
        
        is_weaviate_client_connected = self.client.is_ready()

        if is_weaviate_client_connected:
            print("✅ Successfully connected to Weaviate Cloud.")
        else:
            print("❌ Failed to connect to Weaviate Cloud.")