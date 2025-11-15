from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError
from pymongo import MongoClient

from pathlib import Path
import requests
from dotenv import load_dotenv
import os
import json
from typing import Any
import asyncio


class Neo4jKnowledgeGraph:

    BASE_DIR = Path(__file__).resolve().parents[2]  # root 경로
    load_dotenv(BASE_DIR / "common" / ".env")
    
    NEO4J_URI = os.getenv("NEO4J_URI")
    NEO4J_AUTH = ("neo4j", os.getenv("NEO4J_PASSWORD"))

    RUNPOD_URI = os.getenv("RUNPOD_URI")
    RUNPOD_LLM_MODEL = os.getenv("RUNPOD_LLM_MODEL")

    TIMEOUT = os.getenv("TIMEOUT")
    MAX_CONCURRENT = int(os.getenv("MAX_ASYNC_REQUESTS"))

    def __init__(self):
        

        self.neo4j_driver = GraphDatabase.driver(self.NEO4J_URI, auth=self.NEO4J_AUTH)

        USERNAME = os.getenv("MONGO_INITDB_ROOT_USERNAME", "root")
        PASSWORD = os.getenv("MONGO_INITDB_ROOT_PASSWORD", "example")
        HOST = os.getenv("MONGO_HOST", "localhost")
        PORT = int(os.getenv("MONGO_PORT", 27017))

        self.mongodb_client = MongoClient(f"mongodb://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/")
        self.chunk_collection = self.mongodb_client["chunk_db"]["chunk_collection"]

        try:
            self.neo4j_driver.verify_connectivity()
            print("Connection established.")
        except Neo4jError as e:
            print(f"Connection failed: {e.__cause__}")  # Neo4jError가 제공하는 __cause__ 속성이 에러 메세지가 자세하므로 이를 출력

        self.PROMPT_FOR_NODES_AND_RELATIONSHIPS = """당신은 RAG의 Knowledge Graph를 구축하기 위해, 주어진 문자열에서 주요개념과 그 관계를 추출하는 전문가입니다.
        아래 JSON 형식을 따라 두개의 주요개념과 그 둘 사이의 관계를 최대한 많이 추출하세요.

        [답변형식]
        [{{
            "source_node": {{
                "name": "source_node의 이름",
                "alias": ["source_node의 다양한 표현 방식1", "source_node의 다양한 표현 방식2", ...]
            }},
            "target_node": {{
                "name": "target_node의 이름",
                "alias": ["target_node의 다양한 표현 방식1", "target_node의 다양한 표현 방식2", ...]
            }},
            "relationship_description": "relationship의 이름",
            "confidence": 추출 결과의 신뢰도 (0과 1 사이의 값)
        }}]

        위에 제시된 답변 JSON 형식을 참고하여 아래 주의사항을 따라 주어진 문자열에서 주요개념과 관계를 추출하세요.

        1. 질문에서 중요한 주요개념(명사, 개념, 물질명, 화학물질, 조직, 인물 등)를 모두 추출하세요.
        2. 문서 내에서 추출한 주요개념의 다른 다양한 표현 방식이 등장한다면 함께 추출하고, source_node라면 source_node의 alias, target_node라면 target_node의 alias 키에 대한 값으로 제시하세요. 값이 여러개라면 문자열 배열 형태로 제시하세요. 단, 문서 내에 다른 표현 방식이 등장하지 않는다면 추출하지 않아도 됩니다. 다른 표현 방식이 1개여도 배열 형태로 제시하세요. (예: 염산 → ["HYDROCHLORIC ACID"])
        3. 추출한 주요개념 중 서로 연관관계를 가지는 것이 있다면 관계의 시작에 해당하는 주요개념을 source_node, 관계의 적용대상에 해당하는 주요개념을 target_node로 제시하세요. 제시할 수 있는 관계의 종류에는 제한이 없습니다. 단, 될 수 있는 한 간단한 한국어 문장으로 제시하세요. (ex. "구성물질을 가진다", "평가 결과를 가진다", "시험 방법으로 평가되었다")
        4. 관계의 이름은 relationship 키에 대한 값으로 제시하세요.
        5. 추출한 주요개념들과 그 관계에 대한 신뢰도를 0과 1 사이의 값으로 계산하고, confidence 키에 대한 값으로 제시하세요. 소수점은 최대 10자리까지만 제시하세요. 물론, 소수점 밑 자리가 10자리 보다 적다면 10자리를 채우지 말고 그대로 제시하세요.
        6. 답변에는 답변형식인 JSON 배열을 제외한 그 어떤 문구도 포함하지 마세요. 정확히 답변 JSON 배열만을 답변하세요. (단, 주요개념들과 관계의 쌍이 하나여도 배열 형태로 반환하세요.)

        [주요개념 및 관계를 추출해야 할 문자열]
        {text_to_analyze}

        [답변 예시]
        [{{
        "source_node": {{
            "name": "Triethylene Glycol",
            "alias": ["2,2 ethylenedioxydiethanol", "Ethylene triglycol", "glycol bis (hydroxyethyl) ether", "TEG", "Triglycol"]
        }},
        "target_node": {{
            "name": "SHELL EASTERN CHEMICALS (S) A",
            "alias": ["SHELL EASTERN TRADING (PTE) LTD", "Shell Eastern Chemicals"]
        }},
        "relationship_description": "제조 또는 공급한다",
        "confidence": 0.97
        }}]
        """

        self.PROMPT_FOR_NODES = """당신은 RAG의 Knowledge Graph를 구축하기 위해, 주어진 문자열에서 주요개념을 추출하는 전문가입니다.
        아래 JSON 형식을 따라 주요개념을 추출하세요.

        [답변형식]
        [{{
            "name": "주요개념의 이름",
            "alias": ["주요개념의 다양한 표현 방식1", "주요개념의 다양한 표현 방식2", ...]
            "confidence": 추출 결과의 신뢰도 (0과 1 사이의 값)
        }}]

        위에 제시된 답변 JSON 형식을 참고하여 아래 주의사항을 따라 주어진 문자열에서 주요개념을 추출하세요.

        1. 질문에서 중요한 주요개념(명사, 개념, 물질명, 화학물질, 조직, 인물 등)를 모두 추출하세요.
        2. 문서 내에서 추출한 주요개념의 다른 다양한 표현 방식이 등장한다면 함께 추출하고, alias 키에 대한 값으로 제시하세요. 값이 여러개라면 문자열 배열 형태로 제시하세요. 단, 문서 내에 다른 표현 방식이 등장하지 않는다면 추출하지 않아도 됩니다. 다른 표현 방식이 1개여도 배열 형태로 제시하세요. (예: 염산 → ["HYDROCHLORIC ACID"])
        3. 추출한 주요개념에 대한 신뢰도를 0과 1 사이의 값으로 계산하고, confidence 키에 대한 값으로 제시하세요. 소수점은 최대 10자리까지만 제시하세요. 물론, 소수점 밑 자리가 10자리 보다 적다면 10자리를 채우지 말고 그대로 제시하세요.
        4. 답변에는 답변형식인 JSON 배열을 제외한 그 어떤 문구도 포함하지 마세요. 정확히 답변 JSON 배열만을 답변하세요. (단, 주요개념이 하나여도 배열 형태로 반환하세요.)

        [주요개념을 추출해야 할 문자열]
        {text_to_analyze}

        [답변 예시]
        [{{
            "name": "SHELL EASTERN CHEMICALS (S)",
            "alias": ["SHELL EASTERN TRADING (PTE) LTD", "Shell Eastern Chemicals", "SHELL EASTERN CHEMICALS"],
            "confidence": 0.98
        }}]
        """


    def close(self):
        """
        Neo4j 드라이버를 종료합니다.
        - 드라이버 종료해도 데이터는 보존됩니다.
        - 리소스 관리를 위해, 한 파이프 라인에서 사용이 종료되면 반드시 close() 메서드를 호출해주세요.
        """
        self.neo4j_driver.close()
        print("☑️ Neo4j driver successfully closed.")


    async def _async_extract_nodes_or_relationships(self, semaphore: asyncio.Semaphore, text_to_analyze: str, need_relationships: bool) -> list[dict[str, Any]]:
        """
        주어진 문자열에서 노드 또는 관계를 추출합니다.

        Args:
            text_to_analyze(str): 노드 또는 관계를 추출해야할 문자열
            need_relationships(bool):
                - True: 노드와 관계 모두 추출 (청크를 neo4j에 저장할 때 사용)
                - False: 노드만 추출 (쿼리를 받아서 그래프를 검색할 때 사용)

        Returns:
            list[dict[str, Any]]: 노드와 관계 목록
        """

        if need_relationships:
            prompt = self.PROMPT_FOR_NODES_AND_RELATIONSHIPS.format(text_to_analyze=text_to_analyze)
        else:
            prompt = self.PROMPT_FOR_NODES.format(text_to_analyze=text_to_analyze)

        async with semaphore:
            def sync_request():
                url = f"{self.RUNPOD_URI}/api/generate"
                payload = {"model": self.RUNPOD_LLM_MODEL, "prompt": prompt, "stream": False}
                headers = {"Content-Type": "application/json"}
                timeout = float(self.TIMEOUT) if self.TIMEOUT else None
                return requests.post(url, json=payload, headers=headers, timeout=timeout)

            try:
                response = await asyncio.to_thread(sync_request)
                content_type = response.headers.get("Content-Type", "")

                if "application/json" in content_type:
                    raw_data = response.json()
                    data = raw_data['response']
                    print(f"🔍 [async_extract_nodes_or_relationships] LLM response: {json.loads(data)}")
                    return json.loads(data)
                else:
                    raw_data = response.text
                    print(f"⚠️ [async_extract_nodes_or_relationships] LLM Message: {raw_data}")
                    return raw_data

            except Exception as e:
                print(f"❌ [async_extract_nodes_or_relationships] LLM async request failed: {e}")
                return []

    
    async def async_ingest_chunks(self, chunks: list[dict]) -> bool:
        """
        청크들을 직접 매개값으로 받고 chunk 내용을 기반으로 노드/관계를 생성하여 Neo4j에 MERGE 합니다.

        Args:
            chunks(list[dict]): 청크 배열

        Returns:
            bool: 하나 이상의 chunk가 정상 저장되면 True, 그렇지 않으면 False
        """

        if not chunks:
            print("⚠️ [async_ingest_chunks] No chunks provided.")
            return False

        extract_success_count = 0  # 추출에 성공한
        extract_fail_count = 0  # 추출에 실패한
        save_success_count = 0  # 저장에 성공한
        save_fail_count = 0  # 저장에 실패한

        semaphore = asyncio.Semaphore(self.MAX_CONCURRENT)

        tasks = []
        for chunk in chunks:
            if chunk.get("type") in {"text", "table"}:
                text_to_analyze = chunk.get("content", "")
            else:
                text_to_analyze = chunk.get("metadata", "")

            if not text_to_analyze:
                print("⚠️ [async_ingest_chunks]Skipping chunk with empty content.")
                continue

            tasks.append(self._async_extract_nodes_or_relationships(semaphore, text_to_analyze, True))

        print(f"🚀 [async_ingest_chunks] Sending {len(tasks)} LLM requests concurrently... (max concurrent: {self.MAX_CONCURRENT})")
        print(f"🔁 [async_ingest_chunks] LLM responses received. Inserting into Neo4j...")

        all_chunks_nodes_and_relationships = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(all_chunks_nodes_and_relationships):
            if isinstance(result, Exception):
                print(f"❌ [async_ingest_chunks] Task {i} failed with error: {result}")
                extract_fail_count += 1
            else:
                print(f"✅ [async_ingest_chunks] Task {i} succeeded, got {len(result)} relationships")
                extract_success_count += 1

        for chunk_nodes_and_relationships in all_chunks_nodes_and_relationships:  # 바깥 list for문 돌면 list 하나씩 나옴!
            if not isinstance(chunk_nodes_and_relationships, list):
                continue

            for nodes_and_relationship in chunk_nodes_and_relationships:  # 그 list는 dict의 배열이기 때문에, 또 반복문 돌면 dict가 하나씩 나옴!
                relation_description = nodes_and_relationship.get("relationship_description")

                if not relation_description:
                    print("⚠️ [async_ingest_chunks] Skipping relationship without description.")
                    continue

                try:
                    self.neo4j_driver.execute_query(
                        f"""
                        MERGE (source:Entity {{name: $source_name}})
                        ON MATCH SET source.alias = apoc.coll.toSet(COALESCE(source.alias, []) + $source_alias)
                        ON CREATE SET source.alias = $source_alias

                        MERGE (target:Entity {{name: $target_name}})
                        ON MATCH SET target.alias = apoc.coll.toSet(COALESCE(target.alias, []) + $target_alias)
                        ON CREATE SET target.alias = $target_alias
                        
                        MERGE (source)-[r:`%s`]->(target)
                        ON MATCH SET r.confidence = CASE 
                                WHEN r.confidence < $confidence 
                                THEN $confidence 
                                ELSE r.confidence 
                            END,
                            r.file_info = COALESCE(r.file_info, {{}}) + $file_info
                        ON CREATE SET r.confidence = $confidence, r.file_info = $file_info
                        """
                        % relation_description,
                        source_name=nodes_and_relationship["source_node"]["name"],
                        source_alias=nodes_and_relationship["source_node"].get("alias", []),
                        target_name=nodes_and_relationship["target_node"]["name"],
                        target_alias=nodes_and_relationship["target_node"].get("alias", []),
                        confidence=float(nodes_and_relationship["confidence"]),
                        file_info=json.dumps(chunk.get("file_info", {})),
                        database_="neo4j"  # 무료 버전은 이름이 neo4j인 데이터베이스 하나만 사용 가능
                    )
                    save_success_count += 1

                except Neo4jError as e:
                    print(f"❌ [async_ingest_chunks] Failed to insert into Neo4j : {e.__cause__}")
                    print(f"❌ [async_ingest_chunks] Failed to insert into Neo4j (Detail...) : {e}")
                    save_fail_count += 1
                    continue

        if save_success_count > 0:
            print(f"✅ [async_ingest_chunks] Successfully extracted {extract_success_count}/{extract_success_count + extract_fail_count} from chunks.")
            print(f"✅ [async_ingest_chunks] Successfully inserted {save_success_count}/{save_success_count + save_fail_count} relationships into Neo4j.")
            return True
        else:
            print("❌ [async_ingest_chunks] No relationships were inserted into Neo4j.")
            return False

    
    async def async_search_graph(self, query: str) -> list[dict[str, Any]]:

        semaphore = asyncio.Semaphore(self.MAX_CONCURRENT)
        nodes = await self._async_extract_nodes_or_relationships(semaphore, query, False)
        confidence_results = []

        for node in nodes:
            try:
                records, summary, keys = self.neo4j_driver.execute_query(
                    """
                    MATCH (source:Entity)-[r]-(target:Entity)
                    WHERE source.name = $node_name
                        OR ANY(alias_item IN source.alias WHERE alias_item = $node_name)
                        OR target.name = $node_name
                        OR ANY(alias_item IN target.alias WHERE alias_item = $node_name)
                    RETURN
                        source.name AS source,
                        target.name AS target,
                        type(r) AS relationship_description,
                        r.confidence AS confidence,
                        r.file_info AS file_info
                    """,
                    node_name=node['name'],
                    database_="neo4j"
                )
            except Neo4jError as e:
                print(f"❌ [async_search_graph] Failed to search graph(Neo4jError): {e.__cause__}")
                continue

            except Exception as e:
                print(f"❌ [async_search_graph] Failed to search graph: {e}")
                continue

            for record in records:
                confidence_results.append({
                    "graph": record["source"] + " - " + record["relationship_description"] + " -> " + record["target"],
                    "file_info": json.loads(record["file_info"]),
                    "confidence": float(record["confidence"])
                })

        confidence_results.sort(key=lambda x: x["confidence"], reverse=True) # confidence 기준 내림차순 정렬
        confidence_results = confidence_results[:5]

        results = [] # confidence 키 없앤 results
        for confidence_result in confidence_results:
            results.append({
                "graph": confidence_result["graph"],
                "file_info": confidence_result["file_info"]
            })

            print("🔍 [async_search_graph] Results:")
            print(f"graph: {confidence_result['graph']}")
            print(f"file Info: {confidence_result['file_info']}")
            print(f"confidence: {confidence_result['confidence']}")

        return results

    async def generate_answer(self, query: str) -> str:
            """
            답변생성
            """

            results = await self.async_search_graph(query)

            prompt = f"""
            당신은 삼성전자 생산기술연구소의 소재 물성 문서 기반으로 근거 중심의 정확한 답변을 생성하는 전문 어시스턴트입니다.
            당신의 모든 답변은 아래 제공된 문서(JSON 형태)의 내용만을 기반으로 해야 합니다. 
            추론을 할 때도 반드시 문서의 내용을 근거로 해야 하며, 문서에 없는 내용은 절대 추측하지 말고 모르면 모른다고 하세요.
            -----------------------------
            [사용자 질문]
            {query}
            -----------------------------
            [그래프 검색 결과]
            {results}
            -----------------------------
            [지침]
            1. 반드시 문서(JSON) 속 text 내용을 기반으로만 답변하세요.
            2. 답변에는 다음 두 가지를 반드시 포함해야 합니다:
            (A) 질문에 대한 명확한 답변
            (B) 답변에 사용된 근거의 출처 (file_uuid(파일 고유 UUID), file_name(파일명), page_num(페이지 번호), collections(청크 컬렉션 이름))
            3. 여러 문서를 참조했다면 출처를 모두 표기하세요.
            4. 문서에 없는 정보는 "문서에 해당 정보가 없습니다."라고 답하세요. 이때에는 file_info에 대한 내용을 비워두세요.
            5. JSON 안의 구조(key 이름)는 절대 변경하지 말고 그대로 사용하세요.
            6. image / link 타입 chunk는 metadata를 요약해 텍스트처럼 다뤄도 됩니다.
            -----------------------------
            [출력 형식]
            다음 형식으로만 답변하세요:

            {{
                "answer" : "답변",
                "file_info" : {{
                    "file_uuid" : "백엔드에서 넘어오는 Doc ID",
                    "file_name" : "파일 이름",
                    "page_num" : 페이지 번호 정수 배열,
                    "collections" : 청크가 속한 컬렉션 이름 배열
                }}
            }}
            """

            # 답변 요청
            url = f"{self.RUNPOD_URI}/api/generate"
            payload = {"model": self.RUNPOD_LLM_MODEL, "prompt": prompt, "stream": False}
            timeout = float(self.TIMEOUT) if self.TIMEOUT else None
            response = requests.post(url, json=payload, timeout=timeout)

            try:
                response.raise_for_status() # 에러면 예외발생
            except requests.RequestException as e:
                print(f"HTTP request failed: {e}")

            print(f"🔍 [generate_answer] LLM response: {response.json()['response']}")
            return response.json()['response']


async def main():
    """
    Neo4jKnowledgeGraph 통해 그래프 저장 및 검색을 테스트하는 코드입니다.
    먼저 테스트하고 싶은 md 문서의 청킹을 완료한 후에 실행해주세요.
    """
    from retriever.chunker.markdown_chunker import MarkdownChunker


    BASE_DIR = Path(__file__).resolve().parents[2]  # root 경로
    markdown_sample_data_folder_path = BASE_DIR / "retriever" / "markdown_sample_data" # markdown 샘플 데이터 경로

    print("📂 Searching md files in:", markdown_sample_data_folder_path)

    for markdown_file_path in markdown_sample_data_folder_path.rglob("*.md"): # md 파일만 순회돌기
        with open(markdown_file_path, "r", encoding="utf-8") as f:  # 파일로부터 md 문자열을 읽어옵니다.
            md = f.read()

            markdown_chunker = MarkdownChunker()

            chunks = markdown_chunker.chunk_markdown_file(md, "5bc0c676-018f-46de-bb0d-0103ff9c388c", "5bc0c676-018f-46de-bb0d-0103ff9c388c_3M-1509-DC-Polyethylene-Tape-TIS-Jun13", ["msds"])

            knowledge_graph = Neo4jKnowledgeGraph()
            await knowledge_graph.async_ingest_chunks(chunks)

            # knowledge_graph.async_search_graph("ISA Kit는 무엇을 테스트하나요?") # 검색 대상인 문서에 대한 질문으로 바꿔주세요
            await knowledge_graph.generate_answer("아세톤의 권고용도는?")
            knowledge_graph.close()

if __name__ == "__main__":
    asyncio.run(main())