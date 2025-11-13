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
        아래 JSON 형식을 따라 두개의 주요개념과 그 둘 사이의 관계를 추출하세요.

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
        주어진 문자열 배열에서 노드 또는 관계를 추출합니다.

        Args:
            content(list[str]): 노드 또는 관계를 추출해야할 문자열 배열
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
                    print(f"🔍 LLM response: {json.loads(data)}")
                    return json.loads(data)
                else:
                    raw_data = response.text
                    print(f"⚠️ LLM Message: {raw_data}")
                    return raw_data

            except Exception as e:
                print(f"❌ LLM async request failed: {e}")
                return []

    
    # file_name을 받아서, MongoDB에서 해당 청크들을 찾아서, 반복문을 돌면서 각각 노드와 관계를 추출하고, neo4j에 저장하는 함수(저장할 때 merge 사용)
    async def async_ingest_chunks(self, chunks: list[dict]) -> bool:
        """
        청크들을 직접 매개값으로 받고 chunk 내용을 기반으로 노드/관계를 생성하여 Neo4j에 MERGE 합니다.

        Args:
            chunks(list[str]): 청크 배열

        Returns:
            bool: 하나 이상의 chunk가 정상 저장되면 True, 그렇지 않으면 False
        """

        if not chunks:
            print("⚠️ No chunks provided.")
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
                print("⚠️ Skipping chunk with empty content.")
                continue

            tasks.append(self._async_extract_nodes_or_relationships(semaphore, text_to_analyze, True))

        print(f"🚀 Sending {len(tasks)} LLM requests concurrently... (max concurrent: {self.MAX_CONCURRENT})")
        print(f"🔁 LLM responses received. Inserting into Neo4j...")

        all_chunks_nodes_and_relationships = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(all_chunks_nodes_and_relationships):
            if isinstance(result, Exception):
                print(f"❌ Task {i} failed with error: {result}")
                extract_fail_count += 1
            else:
                print(f"✅ Task {i} succeeded, got {len(result)} relationships")
                extract_success_count += 1

        for chunk_nodes_and_relationships in all_chunks_nodes_and_relationships:  # 바깥 list for문 돌면 list 하나씩 나옴!
            if not isinstance(chunk_nodes_and_relationships, list):
                continue

            for nodes_and_relationship in chunk_nodes_and_relationships:  # 그 list는 dict의 배열이기 때문에, 또 반복문 돌면 dict가 하나씩 나옴!
                relation_description = nodes_and_relationship.get("relationship_description")

                if not relation_description:
                    print("⚠️ Skipping relationship without description.")
                    continue

                try:
                    self.neo4j_driver.execute_query(
                        """
                        MERGE (source:Entity {name: $source_name, alias: $source_alias, file_info: $source_file_info})
                        MERGE (target:Entity {name: $target_name, alias: $target_alias, file_info: $target_file_info})
                        MERGE (source)-[relationship:`%s` {confidence: $confidence}]->(target)
                        """
                        % relation_description,
                        source_name=nodes_and_relationship["source_node"]["name"],
                        source_alias=nodes_and_relationship["source_node"]["alias"],
                        source_file_info=json.dumps(chunk.get("file_info", {})),
                        target_name=nodes_and_relationship["target_node"]["name"],
                        target_alias=nodes_and_relationship["target_node"]["alias"],
                        target_file_info=json.dumps(chunk.get("file_info", {})),
                        confidence=float(nodes_and_relationship["confidence"]),
                        database_="neo4j"  # 무료 버전은 이름이 neo4j인 데이터베이스 하나만 사용 가능
                    )
                    save_success_count += 1
                except Neo4jError as e:
                    print(f"❌ Failed to insert into Neo4j : {e.__cause__}")
                    save_fail_count += 1
                    continue

        if save_success_count > 0:
            print(f"✅ Successfully extracted {extract_success_count}/{extract_success_count + extract_fail_count} from chunks.")
            print(f"✅ Successfully inserted {save_success_count}/{save_success_count + save_fail_count} relationships into Neo4j.")
            return True
        else:
            print("❌ No relationships were inserted into Neo4j.")
            return False

    
    def search_graph(self, query: str) -> list[dict[str, Any]]:

        semaphore = asyncio.Semaphore(self.MAX_CONCURRENT)
        nodes = self._async_extract_nodes_or_relationships(semaphore, query, False)
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
                    RETURN source.name AS source,
                        source.file_info AS source_file_info,
                        type(r) AS relationship_description,
                        target.name AS target,
                        target.file_info AS target_file_info,
                        r.confidence AS confidence
                    """,
                    node_name=node['name'],
                    database_="neo4j"
                )
            except Neo4jError as e:
                print(f"❌ Failed to search graph(Neo4jError): {e.__cause__}")
                continue

            except Exception as e:
                print(f"❌ Failed to search graph: {e}")
                continue

            for record in records:
                confidence_results.append({
                    "graph": record["source"] + " - " + record["relationship_description"] + " -> " + record["target"],
                    "source_file_info": json.loads(record["source_file_info"]),
                    "target_file_info": json.loads(record["target_file_info"]),
                    "confidence": float(record["confidence"])
                })

        confidence_results.sort(key=lambda x: x["confidence"], reverse=True) # confidence 기준 내림차순 정렬

        results = [] # confidence 키 없앤 results
        for confidence_result in confidence_results:
            results.append({
                "graph": confidence_result["graph"],
                "source_file_info": confidence_result["source_file_info"],
                "target_file_info": confidence_result["target_file_info"]
            })

        print(f"🔍 Results: {results}")
        return results


    def generate_answer(self, query: str) -> str:
        """
        답변생성
        """

        results = self.search_graph(query)

        prompt = f"""
        당신은 질문에 답변하는 AI 어시스턴트입니다.
        벡터 검색 결과와 그래프 검색 결과를 모두 참고하여 정확하고 포괄적인 답변을 제공하세요.
        
        질문: {query}
        그래프 검색 결과: {results}
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

        print(f"🔍 LLM response: {response.json()['response']}")
        return response.json()['response']

        
def main():
    """
    Neo4jKnowledgeGraph 통해 그래프 저장 및 검색을 테스트하는 코드입니다.
    먼저 테스트하고 싶은 md 문서의 청킹을 완료한 후에 실행해주세요.
    """
    knowledge_graph = Neo4jKnowledgeGraph()

    asyncio.run(knowledge_graph.async_ingest_file("Copy of 5bc0c676-018f-46de-bb0d-0103ff9c388c")) # 청킹한 문서 이름으로 바꿔주세요
    # knowledge_graph.search_graph("ISA Kit는 무엇을 테스트하나요?") # 검색 대상인 문서에 대한 질문으로 바꿔주세요
    knowledge_graph.generate_answer("ISA Kit는 무엇을 테스트하나요?")
    knowledge_graph.close()

if __name__ == "__main__":
    main()