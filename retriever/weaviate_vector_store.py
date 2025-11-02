# Weaviate
import weaviate
from weaviate.classes.config import (
    Configure,
    Property,
    DataType,
    VectorDistances,
    VectorFilterStrategy,
)
from weaviate.classes.init import Auth

# LangChain
from langchain_core.documents import Document

# Base
from base_vector_store import BaseVectorStore


class WeaviateVectorStore(BaseVectorStore):

    # Weaviate에서 DB Table에 해당하는 개념이 Collection
    # 이름을 지정해줘야 하는데, 일단은 MaterialPropertyKnowledge으로 하드코딩하고 추후에 확장이 필요하다면 Initializer에서 받도록 수정할 예정
    collection_name = "MaterialPropertyKnowledge"

    def __init__(self, cluster_url: str, api_key: str) -> None:

        # client 생성
        self.client = weaviate.connect_to_weaviate_cloud(
            cluster_url = cluster_url,
            auth_credentials = Auth.api_key(api_key),
        )
        
        is_client_connected = self.client.is_ready()

        if is_client_connected:
            print("✅ Successfully connected to Weaviate Cloud.")
        else:
            print("❌ Failed to connect to Weaviate Cloud.")

        # Collection 생성
        if not self.client.collections.exists(self.collection_name):
            self.client.collections.create(
                name=self.collection_name,
                properties=[ # Property 정의 (Column과 같은 개념)
                    Property(name="chunk", data_type=DataType.TEXT, description="원본 Chunk 내용"),
                    Property(name="metadata", data_type=DataType.JSON, description="원본 Chunk 메타데이터(file_name, page_num, etc.)")
                ],
                vector_config=Configure.Vectorizer.none(), # 외부 임베딩 모델 사용해서 임베딩을 하지 않음
                vector_index_config=Configure.VectorIndex.hnsw( # HNSW 인덱스 사용
                    ef_construction=300, # 인덱스를 만들 때 사용하는 탐색 너비(값이 클수록 검색 정확도 증가 및 검색 시간 증가, 100-300이 기본값)
                    distance_metric=VectorDistances.COSINE, # 벡터간 유사도 계산 방식 (텍스트 기반 RAG는 COSINE 권장)
                    filter_strategy=VectorFilterStrategy.ACORN, # 검색 시 필터와 벡터 인덱스를 어떻게 결합해서 검색할지 결정. (ACORN은 필터와 벡터 인덱스를 결합해서 속도가 개선된 최신 기법)
                ),
                inverted_index_config=Configure.inverted_index( # 키워드 검색 시 속도 및 정밀도 향상을 위해 해놓는 역색인을 위한 설정들 (현재는 전부 공식문서 기본값으로 설정)
                    bm25_b=0.7, # 문장길이가 길수록 단어 등장 빈도수가 증가하므로 문장길이에 따른 영향도를 조절하기 위한 파라미터 (높을수록 짧은 문장에 대해 가중치를 줌)
                    bm25_k1=1.25, # 단어 등장 빈도수가 높을수록 가중치를 줄지에 대한 파라미터 (높을수록 빈도수가 높은 것에 대해 가중치를 줌)
                    index_null_state=True, # NULL 값을 인덱싱하여 필터링에 활용할지 여부 (True: 포함, False: 제외)
                    index_property_length=True, # 속성 길이를 인덱싱하여 필터링에 활용할지 여부 (True: 포함, False: 제외)
                    index_timestamps=True, # 생성/업데이트 타임스탬프 정보를 인덱싱할지 여부 (True: 최신순 정렬/기간 검색 가능, False: 불가능)
                )
            )

    def add_documents(self, documents: list[Document], embedding_model) -> bool:
        """
        여러 청크를 임베딩해서 저장
        """

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