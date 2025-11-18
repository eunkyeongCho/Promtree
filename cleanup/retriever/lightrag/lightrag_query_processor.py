"""
LightRAG Query Processor - 질문 전처리 및 엔티티 추출
질문에서 중요 엔티티를 LLM으로 추출하여 그래프 검색 성능 향상
"""

from dotenv import load_dotenv
import os
from typing import List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json
import re

load_dotenv()


class QueryProcessor:
    """
    질문 전처리 프로세서
    - LLM을 활용한 엔티티 추출
    - 질문 의도 파악
    """

    def __init__(self, llm_model: str = "gemini-2.5-flash"):
        """
        초기화

        Args:
            llm_model: LLM 모델명
        """
        self.llm = ChatGoogleGenerativeAI(
            model=llm_model,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.0,
        )

        # 엔티티 추출 프롬프트
        self.entity_extraction_prompt = ChatPromptTemplate.from_messages([
            ("system",
             "당신은 질문에서 핵심 엔티티(고유명사, 개념, 물질명 등)를 추출하는 전문가입니다. "
             "사용자의 질문을 분석하여 그래프 검색에 사용할 수 있는 엔티티를 추출하세요."),
            ("human",
             "# 질문:\n{question}\n\n"
             "# 지시사항:\n"
             "1. 질문에서 중요한 엔티티(명사, 개념, 물질명, 화학물질, 조직, 인물 등)를 모두 추출하세요\n"
             "2. 엔티티의 다양한 표현 방식도 함께 제시하세요 (예: 염산 → HYDROCHLORIC ACID)\n"
             "3. 질문의 의도와 관련된 개념도 포함하세요\n\n"
             "# 출력 형식 (JSON):\n"
             "{{\n"
             '  "entities": ["엔티티1", "엔티티2", ...],\n'
             '  "query_type": "질문 유형 (사실 조회/비교/설명 등)",\n'
             '  "intent": "질문 의도 요약"\n'
             "}}\n\n"
             "JSON만 출력하세요:")
        ])

        self.chain = self.entity_extraction_prompt | self.llm | StrOutputParser()

    async def extract_entities_from_query(self, question: str) -> Dict[str, Any]:
        """
        질문에서 엔티티 추출

        Args:
            question: 사용자 질문

        Returns:
            Dict: 추출 결과
                - entities: 엔티티 리스트
                - query_type: 질문 유형
                - intent: 질문 의도
        """
        try:
            result_str = await self.chain.ainvoke({"question": question})
            result = self._parse_json(result_str)

            return {
                'entities': result.get('entities', []),
                'query_type': result.get('query_type', 'unknown'),
                'intent': result.get('intent', '')
            }
        except Exception as e:
            print(f"[QueryProcessor] 엔티티 추출 실패: {e}")
            # 실패 시 간단한 키워드 추출
            return {
                'entities': self._simple_keyword_extraction(question),
                'query_type': 'unknown',
                'intent': ''
            }

    def _simple_keyword_extraction(self, question: str) -> List[str]:
        """
        간단한 키워드 추출 (fallback)

        Args:
            question: 질문

        Returns:
            List[str]: 키워드 리스트
        """
        # 불용어 제거
        stopwords = ['이', '가', '은', '는', '을', '를', '에', '의', '에서', '로', '으로',
                    '와', '과', '도', '만', '뭐', '어떤', '무엇', '있어', '없어', '해',
                    '하는', '되는', '대해', '관련', '알려', '줘', '주세요', '?']

        # 공백 기준 분리
        words = question.split()
        keywords = [w.strip('?.,!') for w in words if w not in stopwords and len(w) > 1]

        return keywords

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

            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"[QueryProcessor] JSON 파싱 실패: {e}")
            print(f"원본 텍스트: {text[:500]}...")
            return {"entities": [], "query_type": "unknown", "intent": ""}
