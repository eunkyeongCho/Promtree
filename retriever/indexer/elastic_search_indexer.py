from typing import List, Dict, Any
from elasticsearch import helpers

from db.mongodb import get_mongodb_client
from db.elasticsearch.elasticsearch import get_elasticsearch_client


class ElasticSearchIndexer:
    """
    MongoDB에서 생성된 청킹(chunk) 데이터를 Elasticsearch에 색인(indexing)하고, 저장된 데이터를 검색(query)할 수 있는 클래스입니다.
    """
    def __init__(self):
        """
        MongoDB 및 Elasticsearch 클라이언트의 싱글톤 객체를 얻고, 청킹 데이터가 저장된 MongoDB 컬렉션을 변수에 할당합니다.
        """
        self.mongodb_client = get_mongodb_client()
        self.elasticsearch_client = get_elasticsearch_client()
        self.chunk_collection = self.mongodb_client["chunk_db"]["chunk_collection"]


    def index_file(self, file_name: str, index_name: str) -> bool:
        """
        MongoDB에 저장된 특정 파일의 청킹(chunk) 데이터를 Elasticsearch 인덱스에 일괄 색인합니다.

        Args:
            file_name (str):
                색인 대상 원본 파일 이름
            index_name (str):
                색인이 저장될 Elasticsearch 인덱스 이름(msds, tds 둘 중 하나)
                화면에서부터 사용자가 PDF를 업로드할 MSDS/TDS 선택하기로 했으므로 index_name을 넘겨줄 수 있을 것으로 판단함.

        Returns:
            bool:
                - 색인이 정상적으로 수행되면 True
                - 파일에 대응하는 청킹 데이터가 없거나 색인 중 오류가 발생하면 False
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


    def keyword_search(self, query: str, index_name: list[str]) -> List[Dict[str, Any]]:
        """
        Elasticsearch에서 검색어(query)에 따라 청크를 검색합니다.

        문서의 type 값에 따라 검색 기준 필드를 자동으로 구분:
            - type = text or table → content 필드에서 검색
            - type = image → metadata 필드에서 검색

        Args:
            query (str): 사용자의 query
            index_name (list[str]): 검색을 수행할 Elasticsearch 인덱스 목록

        Returns:
            List[Dict[str, Any]]:
                검색된 문서 목록. 각 문서는 다음 구조를 가진다:
                {
                    "type": str,
                    "content": str | None,
                    "metadata": str | None,
                    "file_info": {
                        "file_name": str,
                        "page_num": list[int]
                    }
                }
        """

        RETURN_SIZE = 10 # 반환할 청크 수

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
            size=RETURN_SIZE,
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