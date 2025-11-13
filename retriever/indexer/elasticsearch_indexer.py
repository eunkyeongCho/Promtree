from elasticsearch import Elasticsearch, helpers
from pymongo import MongoClient
from typing import List, Dict, Any, Iterable
import os
from pathlib import Path
from dotenv import load_dotenv

SYN_PATH = "synonyms/synonyms_ko_en.txt"

class ElasticsearchIndexer:
    """MongoDB 청크 데이터를 Elasticsearch에 색인하고 검색하는 클래스"""

    def __init__(self):
        BASE_DIR = Path(__file__).resolve().parents[2]
        load_dotenv(BASE_DIR / ".env")

        USERNAME = os.getenv("MONGO_INITDB_ROOT_USERNAME", "root")
        PASSWORD = os.getenv("MONGO_INITDB_ROOT_PASSWORD", "example")
        HOST = os.getenv("MONGO_HOST", "localhost")
        PORT = int(os.getenv("MONGO_PORT", 27017))

        self.mongodb_client = MongoClient(f"mongodb://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/")
        self.chunk_collection = self.mongodb_client["chunk_db"]["chunk_collection"]

        ELASTIC_PASSWORD = os.getenv("ELASTIC_PASSWORD")
        self.elasticsearch_client = Elasticsearch(
            "http://localhost:9200",
            basic_auth=("elastic", ELASTIC_PASSWORD)
        )

    def ensure_index(self, index_name: str) -> None:
        """Elasticsearch 인덱스가 없으면 생성하는 함수 (한/영 분석기, 동의어 설정 포함)"""
        es = self.elasticsearch_client
        if es.indices.exists(index=index_name):
            return

        body = {
            "settings": {
                "index": {"max_ngram_diff": 50},
                "analysis": {
                    "tokenizer": {
                        "edge_2_4": {"type": "edge_ngram", "min_gram": 2, "max_gram": 4}
                    },
                    "filter": {
                        "syn_ko_en": {
                            "type": "synonym_graph",
                            "synonyms_path": SYN_PATH
                        },
                        "ko_pos_stop": {
                            "type": "nori_part_of_speech",
                            "stoptags": ["SP", "SSC", "SSO", "SC", "SE", "SF"]
                        }
                    },
                    "normalizer": {
                        "lower_norm": {
                            "type": "custom",
                            "char_filter": [],
                            "filter": ["lowercase"]
                        }
                    },
                    "analyzer": {
                        "ko_index": {
                            "type": "custom",
                            "tokenizer": "nori_tokenizer",
                            "filter": ["ko_pos_stop"]
                        },
                        "ko_search_with_syn": {
                            "type": "custom",
                            "tokenizer": "nori_tokenizer",
                            "filter": ["ko_pos_stop", "syn_ko_en"]
                        },
                        "en_index": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "porter_stem"]
                        },
                        "en_search_with_syn": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "syn_ko_en", "porter_stem"]
                        },
                        "ngram_ko": {
                            "tokenizer": "edge_2_4"
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "type": {"type": "keyword"},
                    "content": {
                        "type": "text",
                        "fields": {
                            "ko": {
                                "type": "text",
                                "analyzer": "ko_index",
                                "search_analyzer": "ko_search_with_syn"
                            },
                            "en": {
                                "type": "text",
                                "analyzer": "en_index",
                                "search_analyzer": "en_search_with_syn"
                            },
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
                            "ko": {
                                "type": "text",
                                "analyzer": "ko_index",
                                "search_analyzer": "ko_search_with_syn"
                            },
                            "en": {
                                "type": "text",
                                "analyzer": "en_index",
                                "search_analyzer": "en_search_with_syn"
                            }
                        }
                    },
                    "file_info": {
                        "properties": {
                            "file_name": {"type": "keyword", "normalizer": "lower_norm"},
                            "page_num": {"type": "integer"}
                        }
                    }
                }
            }
        }

        es.indices.create(index=index_name, body=body)

    def reload_search_analyzers(self, index_name: str) -> Dict[str, Any]:
        """동의어 파일 변경 시 검색 분석기를 핫 리로드하는 함수"""
        return self.elasticsearch_client.indices.reload_search_analyzers(index=index_name)

    def index_file(self, file_name: str, index_name: str) -> bool:
        """MongoDB에서 특정 파일의 청크 데이터를 Elasticsearch에 색인하는 함수"""
        self.ensure_index(index_name)

        cursor = self.chunk_collection.find({"file_info.file_name": file_name})
        first_chunk = next(cursor, None)
        if first_chunk is None:
            print(f"⚠️ No chunk data found for file: {file_name}")
            return False

        def _src(doc: Dict[str, Any]) -> Dict[str, Any]:
            fi = doc.get("file_info") or {}
            page_num = fi.get("page_num")
            if isinstance(page_num, list):
                page_num = page_num[0] if page_num else 0
            elif page_num is None:
                page_num = 0

            return {
                "type": doc.get("type", ""),
                "content": doc.get("content") or "",
                "metadata": doc.get("metadata") or "",
                "file_info": {
                    "file_name": (fi.get("file_name", "") or "").lower(),
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

    def keyword_search(self, query: str, index_names: List[str]) -> List[Dict[str, Any]]:
        """한/영 동의어, 오타 허용, 하이라이트를 적용한 키워드 검색 함수"""
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
                                        "content.ngram^0.5"
                                    ],
                                    "type": "best_fields",
                                    "fuzziness": fuzz,
                                    "operator": "or",
                                    "tie_breaker": 0.3
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
                                    "fields": ["metadata.ko^1.5", "metadata.en^1.5"],
                                    "fuzziness": fuzz,
                                    "operator": "or",
                                    "tie_breaker": 0.2
                                }
                            }]
                        }
                    }
                ],
                "minimum_should_match": 1
            }
        }

        resp = self.elasticsearch_client.search(
            index=index_names,
            size=RETURN_SIZE,
            track_total_hits=False,
            _source_includes=[
                "type", "content", "metadata", "file_info.file_name", "file_info.page_num"
            ],
            body={
                "query": es_query,
                "highlight": {
                    "require_field_match": False,
                    "fields": {
                        "content.ko": {},
                        "content.en": {},
                        "metadata.ko": {},
                        "metadata.en": {}
                    }
                }
            }
        )

        hits = resp.get("hits", {}).get("hits", [])
        results: List[Dict[str, Any]] = []
        for h in hits:
            src = h.get("_source", {}) or {}
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
            fi = (r.get("file_info") or {})
            fn = fi.get("file_name")
            pg = fi.get("page_num")
            print(f"--- Result {i} (score: {r['score']:.4f}) ---")
            print(f"Type: {r.get('type')} | File: {fn} | Page: {pg}")
            hl = r.get("highlight") or {}
            snippet_list = (
                hl.get("content.en")
                or hl.get("content.ko")
                or hl.get("metadata.en")
                or hl.get("metadata.ko")
                or [(r.get("content") or r.get("metadata") or "")[:200]]
            )
            print(f"Snippet: {snippet_list[0]}\n")
        return results

    def retrieve_contexts(
        self,
        query: str,
        index_names: List[str],
        top_k: int = 5,
    ) -> List[str]:
        """검색 결과를 RAG용 컨텍스트 텍스트 리스트로 변환하는 함수"""
        results = self.keyword_search(query, index_names)
        contexts: List[str] = []

        for r in results[:top_k]:
            text = (r.get("content") or "") or (r.get("metadata") or "")
            if text:
                contexts.append(text)

        return contexts
    
def main():
    """MongoDB의 모든 파일을 Elasticsearch에 색인하고 테스트 검색을 수행하는 메인 함수"""
    indexer = ElasticSearchIndexer()

    available_files = indexer.chunk_collection.distinct("file_info.file_name")
    print(f"[INFO] Available files in MongoDB ({len(available_files)} files):")
    for i, file in enumerate(available_files[:10], 1):
        print(f"  {i}. {file}")
    if len(available_files) > 10:
        print(f"  ... and {len(available_files) - 10} more files")
    print()

    if available_files:
        if indexer.elasticsearch_client.indices.exists(index="msds"):
            print("[DELETE] Deleting existing 'msds' index...")
            indexer.elasticsearch_client.indices.delete(index="msds")

        print(f"[INDEX] Indexing all {len(available_files)} files...\n")
        success_count = 0
        for i, file_name in enumerate(available_files, 1):
            print(f"[{i}/{len(available_files)}] Indexing: {file_name}")
            if indexer.index_file(file_name, "msds"):
                success_count += 1

        print(f"\n✅ Successfully indexed {success_count}/{len(available_files)} files\n")

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
