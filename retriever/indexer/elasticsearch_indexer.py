from typing import List, Dict, Any, Iterable, Tuple
from elasticsearch import helpers
from db.mongodb import get_mongodb_client
from db.elasticsearch.elasticsearch import get_elasticsearch_client

# ✅ synonyms_path 는 "엘라스틱서치 노드의 config 기준 경로"여야 함
# 예) $ES_CONFIG/synonyms/synonyms_ko_en.txt  -> 여기서 "synonyms/synonyms_ko_en.txt" 로 지정
SYN_PATH = "synonyms/synonyms_ko_en.txt"

class ElasticSearchIndexer:
    """
    MongoDB의 청킹 데이터를 Elasticsearch에 색인/검색하는 유틸.
    - 한/영 분석기 분리 + 영어 검색 시 synonym_graph 적용
    - fuzziness 지원
    - 멀티 인덱스 동시 검색
    - 하이라이트
    """

    def __init__(self):
        self.mongodb_client = get_mongodb_client()
        self.elasticsearch_client = get_elasticsearch_client()
        self.chunk_collection = self.mongodb_client["chunk_db"]["chunk_collection"]

    # --------------------------
    # 0) 인덱스 생성 (매핑 + 분석기)
    # --------------------------
    def ensure_index(self, index_name: str) -> None:
        es = self.elasticsearch_client
        if es.indices.exists(index=index_name):
            return

        body = {
            "settings": {
                # file_name 같은 keyword 필드에 소문자 정규화가 필요하면 normalizer 추가 가능
                # "analysis": { ... } 안의 "normalizer" 블록에 정의 후 필드에 적용
                "analysis": {
                    "tokenizer": {
                        "edge_2_4": {"type": "edge_ngram", "min_gram": 2, "max_gram": 4}
                    },
                    "filter": {
                        # ✅ 검색(analyzer)에서 사용할 동의어. synonym_graph는 search_analyzer 쪽에만!
                        "syn_ko_en": {
                            "type": "synonym_graph",
                            "synonyms_path": SYN_PATH
                        },
                        "ko_pos_stop": {
                            "type": "nori_part_of_speech",
                            "stoptags": ["SP", "SSC", "SSO", "SC", "SE", "SF"]
                        }
                    },
                    "analyzer": {
                        # 한국어: 인덱스/검색 동일
                        "ko_index": {
                            "type": "custom",
                            "tokenizer": "nori_tokenizer",
                            "filter": ["ko_pos_stop"]
                        },
                        # 영어(인덱스): 동의어/그래프 없이 표준 토크나이징 + 소문자 + 스템
                        "en_index": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "porter_stem"]
                        },
                        # 영어(검색): 동의어 그래프 적용
                        "en_search_with_syn": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "syn_ko_en", "porter_stem"]
                        },
                        # (선택) 짧은 질의/자동완성 보조용
                        "ngram_ko": {
                            "tokenizer": "edge_2_4"
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "type": {"type": "keyword"},  # "text", "table", "image", "link" 등
                    "content": {
                        "type": "text",
                        "fields": {
                            "ko": {"type": "text", "analyzer": "ko_index"},
                            "en": {
                                "type": "text",
                                "analyzer": "en_index",
                                "search_analyzer": "en_search_with_syn"
                            },
                            # ⚠️ synonym_graph 와 ngram 은 섞지 않는 게 안정적
                            "ngram": {
                                "type": "text",
                                "analyzer": "ngram_ko",
                                "search_analyzer": "standard"
                            }
                        }
                    },
                    "metadata": {
                        "type": "text",
                        "fields": {
                            "ko": {"type": "text", "analyzer": "ko_index"},
                            "en": {
                                "type": "text",
                                "analyzer": "en_index",
                                "search_analyzer": "en_search_with_syn"
                            }
                        }
                    },
                    "file_info": {
                        "properties": {
                            "file_name": {"type": "keyword"},
                            "page_num": {"type": "integer"}  # ✅ 정수 단일값
                        }
                    }
                }
            }
        }

        es.indices.create(index=index_name, body=body)

    # --------------------------
    # 1) 동의어 재적용 (핫리로드)
    # --------------------------
    def reload_search_analyzers(self, index_name: str) -> Dict[str, Any]:
        """
        synonyms 파일을 갱신한 뒤 검색 분석기를 재로드.
        모든 ES 노드에 동일 경로/파일이 배포되어 있어야 함.
        """
        return self.elasticsearch_client.indices.reload_search_analyzers(index=index_name)

    # --------------------------
    # 2) 색인
    # --------------------------
    def index_file(self, file_name: str, index_name: str) -> bool:
        """
        특정 파일의 청킹 데이터를 Elasticsearch 인덱스에 일괄 색인.
        """
        self.ensure_index(index_name)

        cursor = self.chunk_collection.find({"file_info.file_name": file_name})
        first_chunk = next(cursor, None)
        if first_chunk is None:
            print(f"⚠️ No chunk data found for file: {file_name}")
            return False

        def _src(doc: Dict[str, Any]) -> Dict[str, Any]:
            fi = doc.get("file_info") or {}
            page_num = fi.get("page_num")
            # ✅ page_num은 정수로 보장. 없으면 0
            if isinstance(page_num, list):
                page_num = page_num[0] if page_num else 0
            elif page_num is None:
                page_num = 0

            return {
                "type": doc.get("type", ""),
                "content": doc.get("content") or "",
                "metadata": doc.get("metadata") or "",
                "file_info": {
                    "file_name": fi.get("file_name", ""),
                    "page_num": int(page_num)
                }
            }

        def generate_actions(first: Dict[str, Any], rest_cursor) -> Iterable[Dict[str, Any]]:
            yield {
                "_op_type": "index",
                "_index": index_name,
                "_id": str(first["_id"]),
                "_source": _src(first)
            }
            for doc in rest_cursor:
                yield {
                    "_op_type": "index",
                    "_index": index_name,
                    "_id": str(doc["_id"]),
                    "_source": _src(doc)
                }

        try:
            success_count, errors = helpers.bulk(
                self.elasticsearch_client,
                generate_actions(first_chunk, cursor),
                refresh="wait_for",
                raise_on_error=False
            )
        except Exception as e:
            print(f"❌ Error indexing chunks: {e}")
            return False

        error_count = len(errors) if errors else 0
        print(f"✅ Indexed {success_count} chunks into `{index_name}` with {error_count} errors.")
        if errors:
            print("\n⚠️ Detailed errors:")
            for i, err in enumerate(errors, start=1):
                print(f"  {i}. {err}\n")
        else:
            print("🎉 No errors during indexing!")
        return True

    # --------------------------
    # 3) 키워드 검색
    # --------------------------
    def keyword_search(self, query: str, index_names: List[str]) -> List[Dict[str, Any]]:
        """
        한/영 + 동의어(영어 검색 시) + 오타 허용 + 멀티 인덱스 검색.
        - type in ["text","table"] -> content.*
        - type in ["image","link"]  -> metadata.*
        """
        index_expr = ",".join(index_names)
        RETURN_SIZE = 10
        fuzz = 1 if len(query) <= 3 else "AUTO"

        es_query = {
            "bool": {
                "should": [
                    {
                        "bool": {
                            "filter": [{"terms": {"type": ["text", "table"]}}],
                            "must": [{
                                "multi_match": {
                                    "query": query,
                                    "fields": [
                                        "content.ko^2.5",
                                        "content.en^2.5",
                                        "content^1",
                                        "content.ngram^0.5"
                                    ],
                                    "type": "best_fields",
                                    "fuzziness": fuzz,
                                    "operator": "or"
                                }
                            }]
                        }
                    },
                    {
                        "bool": {
                            "filter": [{"terms": {"type": ["image", "link"]}}],
                            "must": [{
                                "multi_match": {
                                    "query": query,
                                    "fields": ["metadata.ko^1.5", "metadata.en^1.5", "metadata^1"],
                                    "fuzziness": fuzz,
                                    "operator": "or"
                                }
                            }]
                        }
                    }
                ],
                "minimum_should_match": 1
            }
        }

        resp = self.elasticsearch_client.search(
            index=index_expr,
            size=RETURN_SIZE,
            query=es_query,
            track_total_hits=False,
            highlight={
                "fields": {
                    "content": {}, "content.ko": {}, "content.en": {},
                    "metadata": {}, "metadata.ko": {}, "metadata.en": {}
                }
            }
        )

        hits = resp.get("hits", {}).get("hits", [])
        results: List[Dict[str, Any]] = []
        for h in hits:
            src = h.get("_source", {})
            results.append({
                "score": h.get("_score", 0.0),
                "type": src.get("type"),
                "content": src.get("content"),
                "metadata": src.get("metadata"),
                "file_info": src.get("file_info", {}),
                "highlight": h.get("highlight", {})
            })

        print(f"✅ Found {len(results)} results")
        for i, r in enumerate(results[:RETURN_SIZE], 1):
            fn = (r.get("file_info") or {}).get("file_name")
            pg = (r.get("file_info") or {}).get("page_num")
            print(f"--- Result {i} (score: {r['score']:.4f}) ---")
            print(f"Type: {r.get('type')} | File: {fn} | Page: {pg}")
            hl = r.get("highlight") or {}
            snippet_list = (
                hl.get("content.ko")
                or hl.get("content.en")
                or hl.get("content")
                or hl.get("metadata.ko")
                or hl.get("metadata.en")
                or hl.get("metadata")
                or [ (r.get("content") or r.get("metadata") or "")[:200] ]
            )
            print(f"Snippet: {snippet_list[0]}\n")
        return results


def main():
    """
    ElasticsearchIndexer를 통해 키워드 검색을 테스트하는 코드입니다.
    먼저 테스트하고 싶은 md 문서의 청킹을 완료한 후에 실행해주세요.
    """
    indexer = ElasticSearchIndexer()

    # MongoDB에 저장된 파일 목록 확인
    available_files = indexer.chunk_collection.distinct("file_info.file_name")
    print(f"[INFO] Available files in MongoDB ({len(available_files)} files):")
    for i, file in enumerate(available_files[:10], 1):  # 처음 10개만 출력
        print(f"  {i}. {file}")
    if len(available_files) > 10:
        print(f"  ... and {len(available_files) - 10} more files")
    print()

    # 실제 존재하는 파일명으로 테스트
    if available_files:
        test_file = available_files[0]
        print(f"[TEST] Testing with file: {test_file}\n")

        # 기존 인덱스 삭제 (동의어 설정 적용 위해)
        if indexer.elasticsearch_client.indices.exists(index="msds"):
            print("[DELETE] Deleting existing 'msds' index to apply new synonym settings...")
            indexer.elasticsearch_client.indices.delete(index="msds")

        # 새로 색인
        indexer.index_file(test_file, "msds")

        # 한글로 검색 테스트!
        print("\n" + "="*50)
        print("[SEARCH] Test 1: Search with Korean '카스번호'")
        print("="*50)
        indexer.keyword_search("카스번호", ["msds"])

        print("\n" + "="*50)
        print("[SEARCH] Test 2: Search with Korean '끓는점'")
        print("="*50)
        indexer.keyword_search("끓는점", ["msds"])
    else:
        print("❌ No files found in MongoDB. Please run chunking first.")


if __name__ == "__main__":
    main()
