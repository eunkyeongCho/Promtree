"""
LightRAG Entity Extractor - ApeRAG 방식 구현
LLM 기반 엔티티 및 관계 추출 (Multi-round Gleaning)
"""

from dotenv import load_dotenv
import os
from typing import Dict, List, Tuple, Any
import asyncio
from collections import defaultdict
import json
import re

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

# LLM 설정
LLM_MODEL = "gemini-2.5-flash"
ENTITY_EXTRACT_MAX_GLEANING = 1  # 추가 추출 라운드 수


class EntityExtractor:
    """
    ApeRAG 방식 엔티티 추출기
    - Multi-round extraction (Gleaning)
    - 병렬 청크 처리
    - 엔티티 및 관계 추출
    """

    def __init__(self, llm_model: str = LLM_MODEL, max_gleaning: int = ENTITY_EXTRACT_MAX_GLEANING):
        """
        엔티티 추출기 초기화

        Args:
            llm_model: LLM 모델 이름
            max_gleaning: 최대 추가 추출 라운드
        """
        self.llm = ChatGoogleGenerativeAI(
            model=llm_model,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.0,  # 일관성을 위해 0
        )

        self.max_gleaning = max_gleaning

        # 엔티티 추출 프롬프트 (초기)
        self.entity_prompt = ChatPromptTemplate.from_messages([
            ("system",
             "당신은 텍스트에서 핵심 엔티티와 관계를 추출하는 전문가입니다. "
             "다음 텍스트에서 중요한 엔티티(인물, 조직, 개념, 물질 등)와 그들 간의 관계를 추출하세요."),
            ("human",
             "# 텍스트:\n{content}\n\n"
             "# 출력 형식 (JSON):\n"
             "{{\n"
             '  "entities": [\n'
             '    {{"entity_name": "엔티티명", "entity_type": "타입", "description": "설명"}}\n'
             "  ],\n"
             '  "relationships": [\n'
             '    {{"src_id": "출발엔티티", "tgt_id": "도착엔티티", "description": "관계설명", "keywords": "키워드1, 키워드2"}}\n'
             "  ]\n"
             "}}\n\n"
             "JSON만 출력하세요:")
        ])

        # 추가 추출 프롬프트 (Gleaning)
        self.continue_prompt = ChatPromptTemplate.from_messages([
            ("system", "이전 추출에서 놓친 엔티티나 관계가 있으면 추가로 추출하세요."),
            ("human",
             "# 원본 텍스트:\n{content}\n\n"
             "# 이미 추출된 엔티티:\n{existing_entities}\n\n"
             "# 추가로 발견한 엔티티와 관계를 JSON 형식으로 출력하세요. 없으면 빈 리스트를 반환하세요:")
        ])

        # 계속 여부 판단 프롬프트
        self.if_loop_prompt = ChatPromptTemplate.from_messages([
            ("system", "추출 작업을 계속할지 판단하세요."),
            ("human",
             "지금까지 추출한 결과가 충분합니까? 더 추출할 엔티티가 있으면 'yes', 없으면 'no'라고만 답하세요:")
        ])

        self.chain = self.entity_prompt | self.llm | StrOutputParser()
        self.continue_chain = self.continue_prompt | self.llm | StrOutputParser()
        self.loop_chain = self.if_loop_prompt | self.llm | StrOutputParser()

    async def _extract_from_single_chunk(
        self,
        content: str,
        chunk_key: str,
        file_path: str = "unknown"
    ) -> Tuple[Dict[str, List[Dict]], Dict[Tuple[str, str], List[Dict]]]:
        """
        단일 청크에서 엔티티 및 관계 추출 (Multi-round Gleaning 적용)

        Args:
            content: 청크 텍스트
            chunk_key: 청크 고유 ID
            file_path: 파일 경로

        Returns:
            Tuple[maybe_nodes, maybe_edges]:
                - maybe_nodes: {entity_name: [entity_dict, ...]}
                - maybe_edges: {(src, tgt): [edge_dict, ...]}
        """
        maybe_nodes = defaultdict(list)  # 엔티티 후보
        maybe_edges = defaultdict(list)  # 관계 후보

        # Round 1: 초기 추출
        try:
            result_str = await self.chain.ainvoke({"content": content})
            result = self._parse_json(result_str)

            # 엔티티 수집
            for entity in result.get("entities", []):
                entity_name = entity.get("entity_name", "").strip()
                if entity_name:
                    maybe_nodes[entity_name].append({
                        "entity_name": entity_name,
                        "entity_type": entity.get("entity_type", "Unknown"),
                        "description": entity.get("description", ""),
                        "source_id": chunk_key,
                        "file_path": file_path
                    })

            # 관계 수집
            for rel in result.get("relationships", []):
                src = rel.get("src_id", "").strip()
                tgt = rel.get("tgt_id", "").strip()
                if src and tgt:
                    edge_key = tuple(sorted([src, tgt]))  # 양방향 정규화
                    maybe_edges[edge_key].append({
                        "src_id": src,
                        "tgt_id": tgt,
                        "weight": 1.0,
                        "description": rel.get("description", ""),
                        "keywords": rel.get("keywords", ""),
                        "source_id": chunk_key,
                        "file_path": file_path
                    })

        except Exception as e:
            print(f"[EntityExtractor] 초기 추출 실패 ({chunk_key}): {e}")
            return maybe_nodes, maybe_edges

        # Round 2+: Gleaning (추가 추출)
        for glean_round in range(self.max_gleaning):
            try:
                existing_entities = ", ".join(maybe_nodes.keys())

                glean_result_str = await self.continue_chain.ainvoke({
                    "content": content,
                    "existing_entities": existing_entities
                })

                glean_result = self._parse_json(glean_result_str)

                # 새로운 엔티티만 추가
                for entity in glean_result.get("entities", []):
                    entity_name = entity.get("entity_name", "").strip()
                    if entity_name and entity_name not in maybe_nodes:  # 새 엔티티만
                        maybe_nodes[entity_name].append({
                            "entity_name": entity_name,
                            "entity_type": entity.get("entity_type", "Unknown"),
                            "description": entity.get("description", ""),
                            "source_id": chunk_key,
                            "file_path": file_path
                        })

                # 새로운 관계만 추가
                for rel in glean_result.get("relationships", []):
                    src = rel.get("src_id", "").strip()
                    tgt = rel.get("tgt_id", "").strip()
                    if src and tgt:
                        edge_key = tuple(sorted([src, tgt]))
                        if edge_key not in maybe_edges:  # 새 관계만
                            maybe_edges[edge_key].append({
                                "src_id": src,
                                "tgt_id": tgt,
                                "weight": 1.0,
                                "description": rel.get("description", ""),
                                "keywords": rel.get("keywords", ""),
                                "source_id": chunk_key,
                                "file_path": file_path
                            })

                # 계속 여부 판단
                if_continue_str = await self.loop_chain.ainvoke({})
                if "yes" not in if_continue_str.strip().lower():
                    break

            except Exception as e:
                print(f"[EntityExtractor] Gleaning 실패 (round {glean_round + 1}, {chunk_key}): {e}")
                break

        return dict(maybe_nodes), dict(maybe_edges)

    async def extract_entities(
        self,
        chunks: List[Dict[str, Any]],
        max_concurrent: int = 3
    ) -> List[Tuple[Dict, Dict]]:
        """
        여러 청크에서 병렬로 엔티티 추출

        Args:
            chunks: 청크 리스트 [{"content": "...", "chunk_id": "...", "file_path": "..."}, ...]
            max_concurrent: 최대 동시 처리 수

        Returns:
            List[Tuple[maybe_nodes, maybe_edges]]: 각 청크의 추출 결과
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _process_with_semaphore(chunk):
            async with semaphore:
                return await self._extract_from_single_chunk(
                    content=chunk.get("content", ""),
                    chunk_key=chunk.get("chunk_id", "unknown"),
                    file_path=chunk.get("file_path", "unknown")
                )

        tasks = [_process_with_semaphore(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 예외 처리
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"[EntityExtractor] 청크 {i} 처리 실패: {result}")
                valid_results.append(({}, {}))  # 빈 결과
            else:
                valid_results.append(result)

        return valid_results

    def _parse_json(self, text: str) -> Dict:
        """
        LLM 출력에서 JSON 파싱

        Args:
            text: LLM 응답 텍스트

        Returns:
            Dict: 파싱된 JSON
        """
        try:
            # JSON 코드 블록 제거
            text = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
            text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE)
            text = text.strip()

            parsed = json.loads(text)

            # 파싱 결과가 딕셔너리가 아닌 경우 처리
            if not isinstance(parsed, dict):
                print(f"[EntityExtractor] JSON이 딕셔너리가 아닙니다 (타입: {type(parsed).__name__})")
                return {"entities": [], "relationships": []}

            return parsed

        except json.JSONDecodeError as e:
            print(f"[EntityExtractor] JSON 파싱 실패: {e}")
            print(f"원본 텍스트: {text[:500]}...")
            return {"entities": [], "relationships": []}
