from typing import List, Dict, Any
from elasticsearch import helpers

from db.mongodb import get_mongodb_client
from db.elasticsearch.elasticsearch import get_elasticsearch_client


class ElasticSearchIndexer:
    def __init__(self):
        self.mongo_client = get_mongodb_client()
        self.es_client = get_elasticsearch_client()
        self.chunk_collection = self.mongo_client["chunk_db"]["chunk_collection"]


    def index_file(self, file_name: str, index_name: str) -> bool:

        # MongoDB에서 문서 가져오기
        chunks = self.chunk_collection.find({"file_info.file_name": file_name})

        # 청크 데이터를 모두 메모리에 올리면 비효율적이므로, 첫번째 청크 데이터를 기준으로 청크 존재여부 확인
        first_chunk = next(chunks, None)

        if first_chunk is None:
            print(f"⚠️ No chunk data found for file: {file_name}")
            return False

        # 청크가 존재한다면 인덱싱 진행
        # action은 공식문서의 표현이어서 따름
        # 인덱싱할 데이터를 모두 메모리에 올리지 않고, generator를 통해 데이터를 하나씩 흘려보내는 것이 공식문서에서 권장하는 방식이므로 따름
        def generate_actions():
            # 첫 문서부터 처리
            yield {
                "_op_type": "index",
                "_index": index_name,
                "_id": str(first_chunk["_id"]),
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
            (success_count, errors) = helpers.bulk(self.es_client, generate_actions())

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


    def search(self, query: str, index_name: str, size: int = 10) -> List[Dict[str, Any]]:
        """
        Elasticsearch에서 query로 검색
        """
        print(f"\n🔎 Searching index: {index_name} | query: {query}")

        response = self.es_client.search(
            index=index_name,
            size=size,
            query={
                "multi_match": {
                    "query": query,
                    "fields": ["content", "metadata"]   # 둘 다 검색
                }
            }
        )

        hits = response["hits"]["hits"]

        # 결과 데이터를 깔끔하게 정리
        results = [
            {
                "score": hit["_score"],
                "type": hit["_source"].get("type"),
                "content": hit["_source"].get("content"),
                "metadata": hit["_source"].get("metadata"),
                "file_name": hit["_source"].get("file_info", {}).get("file_name"),
                "page_num": hit["_source"].get("file_info", {}).get("page_num"),
            }
            for hit in hits
        ]

        print(f"✅ Found {len(results)} results")
        return results
