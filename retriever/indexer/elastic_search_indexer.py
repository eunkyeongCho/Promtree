from typing import List, Dict, Any
from elasticsearch import helpers

from db.mongodb import get_mongodb_client
from db.elasticsearch.elasticsearch import get_elasticsearch_client


class ElasticSearchIndexer:
    def __init__(self):
        self.mongodb_client = get_mongodb_client()
        self.elasticsearch_client = get_elasticsearch_client()
        self.chunk_collection = self.mongo_client["chunk_db"]["chunk_collection"]


    def index_file(self, file_name: str, index_name: str) -> bool:
        """
        MongoDB에 저장된 청킹(chunk) 데이터를 Elasticsearch에 색인하는 함수.

        주어진 `file_name` 을 기준으로 MongoDB의 chunk_collection 에서 문서 조각들을
        조회한 뒤, Elasticsearch의 `index_name` 인덱스로 bulk API를 이용해 일괄 색인한다.
        이 때 MongoDB의 `_id` 값을 그대로 Elasticsearch 문서 `_id` 로 사용하여
        중복 색인을 방지하고, 동일 문서가 재색인될 경우 덮어쓰기(upsert)되도록 한다.

        Args:
            file_name (str): 색인할 원본 문서의 파일 이름.
            index_name (str): 색인이 저장될 Elasticsearch 인덱스 이름. (화면에서부터 사용자가 MSDS/TDS 선택하기로 했으므로 index_name을 넘겨줄 수 있을 것으로 판단함. index_name은 소문자로 msds or tds)

        Returns:
            bool: 색인 작업이 성공적으로 완료되면 True, 
                청킹 데이터가 없거나 색인 과정에서 오류가 발생하면 False.

        Notes:
            - generator 방식으로 bulk 요청을 처리하여 대량 데이터에도 메모리 안전함.
            - 색인 개수와 에러 개수는 함수 내부에서 로그로 출력됨.
        """

        # MongoDB에서 청크들 가져오기
        chunks = self.chunk_collection.find({"file_info.file_name": file_name})

        # 청크 데이터를 모두 메모리에 올리면 비효율적이므로, 첫번째 청크 데이터를 기준으로 청크 존재여부 확인
        first_chunk = next(chunks, None)

        if first_chunk is None:
            print(f"⚠️ No chunk data found for file: {file_name}")
            return False

        # 청크가 존재한다면 인덱싱 진행
        # action은 공식문서의 표현이어서 따름
        # 인덱싱할 데이터를 모두 메모리에 올리지 않고, generator를 통해 데이터를 하나씩 흘려보내는 것이 Elasticsearch 공식문서에서 권장하는 방식이므로 따름
        def generate_actions():
            # 첫 문서부터 처리
            yield {
                "_op_type": "index",
                "_index": index_name,
                "_id": str(first_chunk["_id"]), # MongoDB의 _id 값을 그대로 Elasticsearch의 _id 값으로 사용
                "_source": {
                    "type": first_chunk.get("type", ""),
                    "content": first_chunk.get("content", ""),
                    "metadata": first_chunk.get("metadata", ""),
                    "file_info": first_chunk.get("file_info", {})
                }
            }

            # 나머지 문서 처리
            for chunk in chunks:
                yield {
                    "_op_type": "index",
                    "_index": index_name,
                    "_id": str(chunk["_id"]),
                    "_source": {
                        "type": chunk.get("type", ""),
                        "content": chunk.get("content", ""),
                        "metadata": chunk.get("metadata", ""),
                        "file_info": chunk.get("file_info", {})
                    }
                }

        try:
            (success_count, errors) = helpers.bulk(self.elasticsearch_client, generate_actions())

        except Exception as e:
            print(f"❌ Error indexing chunks: {e}")
            return False

        error_count = len(errors) if errors else 0

        print(f"✅ Indexed {success_count} chunks into `{index_name}` with {error_count} errors.")
        
        if errors and error_count > 0:
            print("\n⚠️ Detailed errors:")
            for i, err in enumerate(errors, start=1):
                print(f"  {i}. {err}\n")
        else:
            print("🎉 No errors during indexing!")

        return True


    def build_query(query: str, chunk_type: str) -> dict:

        if(chunk_type == "text" or chunk_type == "table"):
            search_field = "content"
        elif(chunk_type == "image"):
            search_field = "metadata"

        return {
            "bool": {
                "must": [
                    {"match": {search_field: query}}
                ],
                "filter": [
                    {"term": {"type": chunk_type}}
                ]
            }
        }


    def search(self, query: str, index_name: list[str], size: int = 10) -> List[Dict[str, Any]]:
        """
        Elasticsearch에서 query로 검색
        """
        elasticsearch_query = {
            "bool": {
                "should": [
                    {
                        "bool": {
                            "must": [
                                {"match": {"content": query}}
                            ],
                            "filter": [
                                {"terms": {"type": ["text", "table"]}}
                            ]
                        }
                    },
                    {
                        "bool": {
                            "must": [
                                {"match": {"metadata": query}}
                            ],
                            "filter": [
                                {"term": {"type": "image"}}
                            ]
                        }
                    }
                ],
                "minimum_should_match": 1
            }
        }

        response  = self.elasticsearch_client.search(
            index=index_name,
            size=size,
            query=elasticsearch_query
        )

        hits = response["hits"]["hits"]

        scored_results = sorted(
            [
                {
                    "score": hit["_score"],
                    "type": hit["_source"].get("type"),
                    "content": hit["_source"].get("content"),
                    "metadata": hit["_source"].get("metadata"),
                    "file_info": hit["_source"].get("file_info")
                }
                for hit in hits
            ],
            key=lambda result: result["score"],
            reverse=True
        )

        results = [
            {
                "type": scored_result["type"],
                "content": scored_result["content"],
                "metadata": scored_result["metadata"],
                "file_info": scored_result["file_info"]
            }
            for scored_result in scored_results
        ]

        print(f"✅ Found {len(results)} results")
        return results