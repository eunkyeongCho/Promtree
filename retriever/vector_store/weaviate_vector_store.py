import weaviate
from weaviate.classes.config import (
    Configure,
    Property,
    DataType,
    Tokenization,
    VectorDistances,
    VectorFilterStrategy,
)
from weaviate.classes.query import (
    HybridFusion,
    BM25Operator,
    MetadataQuery
)
from weaviate.classes.init import Auth

from langchain_core.documents import Document

from base_vector_store import BaseVectorStore
from embedding_model.base_embedding_model import BaseEmbeddingModel


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
            raise ConnectionError(
                "❌ Failed to connect to Weaviate Cloud. "
                "Please check your cluster URL, API key, and network configuration."
            )

        # Collection 생성
        if not self.client.collections.exists(self.collection_name):
            self.client.collections.create(
                name=self.collection_name,
                properties=[ # Property 정의 (Column과 같은 개념)
                    Property(
                        name="content",
                        data_type=DataType.TEXT,
                        tokenization=Tokenization.LOWERCASE, # 키워드 검색 시 영어는 모두 소문자로 바꿔서 공백 기준 나눠서 키워드 매칭에 사용
                        description="원본 Chunk 내용"
                    ),
                    Property(
                        name="metadata",
                        data_type=DataType.JSON,
                        description="원본 Chunk 메타데이터(file_name, page_num, etc.)"
                    )
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

    def add_documents(self, documents: list[Document], embedding_model: BaseEmbeddingModel) -> bool:
        """
            Document 리스트를 임베딩하여 Weaviate 컬렉션에 일괄 저장합니다.

            주어진 Document에서 텍스트와 메타데이터를 추출하고, 매개값으로 받은 임베딩 모델로 벡터를 생성한 뒤 batch 모드를 사용하여 저장합니다.
            batch 저장은 개별 업로드보다 훨씬 빠르게 동작합니다.

            Args:
                documents (list[Document]): 저장할 Document 목록. (LangChain Core Document타입의 배열)
                embedding_model (BaseEmbeddingModel): 사용할 임베딩 모델

            Returns:
                bool: 저장 완료 시 True.
        """

        contents = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]

        vectors = embedding_model.embed_documents(contents)

        with self.client.batch.dynamic() as batch: # fixed_size(), rate_limit()도 사용가능
            for content, metadata, vector in zip(contents, metadatas, vectors):
                batch.add_object(
                    class_name=self.collection_name,
                    properties={
                        "content": content,
                        "metadata": metadata,
                    },
                    vector=vector,
                )

        print(f"✅ Successfully stored vectorized documents into the '{self.collection_name}' collection.")
        print("ℹ️  When you have finished all Weaviate-related operations, call `close()` to safely close the client connection.")

        return True

    def similarity_search(self, information_need: str, embedding_model: BaseEmbeddingModel) -> list[Document]:
        """
            비교해서 검색할 문자열에 대해 임베딩을 생성한 후, Weaviate에서 유사 문서를 벡터 기반으로 검색합니다.

            Args:
                information_need (str): 검색 질의 문자열
                embedding_model (BaseEmbeddingModel): 사용할 임베딩 모델

            Returns:
                list[Document]: 유사도가 높은 순으로 정렬된 Document 리스트
        """

        # information_need 벡터화
        information_need_vector = embedding_model.embed_query(information_need)

        # Collection 객체 가져오기
        if self.client.collections.exists(self.collection_name):
            collection = self.client.collections.use(self.collection_name)
        else:
            raise ValueError(
                f"❌ Collection '{self.collection_name}' does not exist. "
                f"Please ensure that the WeaviateVectorStore is properly initialized and that the collection has been created."
            )

        # 검색 수행
        search_result = collection.query.hybrid( # 하이브리드 검색기법 사용
            query=information_need,
            vector=information_need_vector,
            fusion_type=HybridFusion.RANKED, # 키워드 검색 점수와 벡터 검색 점수를 정규화하지 않고 순위에만 기반해서 검색. (RELATIVE_SCORE도 선택 가능한데 소재 물성 쪽은 RANKED가 더 안정적인 결과를 가져온다고 함) 
            bm25_operator=BM25Operator.or_(minimum_match=2), # 쿼리의 키워드 최소 2개 이상 포함되어 있어야 함 (기본 추천값)
            alpha=0.5, # 물성 소재를 다루므로 다른 도메인보다키워드가 좀 더 중요한 경향이 있어서 기본 추천값인 0.75보다 좀 더 키워드 검색에 비중을 두는 0.5 정도로 설정
            limit=50, # 후에 mmr, reranking 단계에서 후처리를 하므로 hybrid search 단계에서는 넉넉하게 50개 가져오기
            # max_vector_distance은 일반적으로 기술적인 문서는 유의미한 결과값도 벡터 공간 상에서는 멀게 표현되는 경우가 있어서 잘 사용하지 않는 파라미터라고 해서 일단 제외
            return_metadata=MetadataQuery(score=True, explain_score=True) # score와 그에 대한 설명 받기
        )

        # 검색 결과를 LangChain Document 타입 배열로 변환
        documents = []
        for obj in search_result.objects:

            metadata = obj.properties.get('metadata', {}).copy() # 커서에서 copy() 메서드 deprecated 되었다고 에러 뜨는데, 이 부분 dict 타입인 것 보장되므로 그냥 사용해도 무방함. BaseModel 쪽에만 deprecated 된 것이기 때문에.

            metadata['score'] = obj.metadata.score
            metadata['explain_score'] = obj.metadata.explain_score

            documents.append(Document(obj.properties['content'], metadata=metadata))

        return documents

    def close(self):
        self.client.close()