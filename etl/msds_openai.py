"""
MSDS 화학물질 정보 추출 모듈 (OpenAI 버전)

파싱된 MSDS 문서에서 구조화된 화학물질 정보를 OpenAI API를 사용하여 추출합니다.
다국어 콘텐츠(한글/영어)를 처리하고, 농도 범위를 보존하며, 강력한 오류 처리를 제공합니다.
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field, field_validator

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 환경 변수 로드
load_dotenv()

# ============================================
# 설정
# ============================================
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
MAX_TEXT_LENGTH = 15000  # API로 전송할 최대 문자 수


# ============================================
# Pydantic 모델
# ============================================
class ChemicalComponent(BaseModel):
    """MSDS 내 단일 화학물질 구성 성분을 위한 Pydantic 모델"""
    manufacturer: str = Field(..., alias="제조사", description="제조사명")
    product_name: str = Field(..., alias="제품명", description="제품명")
    chemical_name: str = Field(..., alias="화학물질명", description="화학물질명")
    cas_number: str = Field(..., alias="CAS", description="CAS 등록번호 또는 '비공개'")
    concentration: str = Field(..., alias="함량(%)", description="정확한 형식이 보존된 농도")

    @field_validator('concentration', mode='before')
    @classmethod
    def preserve_concentration_format(cls, v):
        """추출된 농도 형식을 정확하게 보존"""
        if v is None:
            return "미공개"
        return str(v).strip()

    @field_validator('cas_number', mode='before')
    @classmethod
    def normalize_cas_number(cls, v):
        """CAS 번호를 정규화하거나 비공개로 표시"""
        if v is None or str(v).strip() == "":
            return "비공개"
        v_str = str(v).strip()

        cas_pattern = r'^\d{1,7}-\d{2}-\d$'
        if re.match(cas_pattern, v_str):
            return v_str

        not_disclosed_patterns = [
            "비공개", "미공개", "공개안함", "공개하지않음",
            "not disclosed", "not available", "confidential", "proprietary",
            "n/a", "na", "n.a.", "none", "-", "—", "–"
        ]
        for pattern in not_disclosed_patterns:
            if pattern.lower() in v_str.lower():
                return "비공개"

        return v_str

    def dict(self, **kwargs):
        """한글 필드명을 사용하도록 dict 메서드 오버라이드"""
        return {
            "제조사": self.manufacturer,
            "제품명": self.product_name,
            "화학물질명": self.chemical_name,
            "CAS": self.cas_number,
            "함량(%)": self.concentration,
        }


# ============================================
# MSDS 추출 에이전트 (OpenAI)
# ============================================
class MSDSExtractionAgent:
    """OpenAI API를 사용하여 MSDS 문서에서 화학물질 정보를 추출하는 에이전트"""

    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY가 환경 변수에 설정되지 않았습니다.")

        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = "gpt-4o-mini"

        self.system_prompt = """You are an expert at extracting chemical information from MSDS (Material Safety Data Sheet) documents.

Extract ALL chemical components from the MSDS document and return them in JSON format.

CRITICAL EXTRACTION RULES:

1. **CAS Number (MOST CRITICAL - MUST EXTRACT)**:
   - CAS numbers ALWAYS follow pattern: digits-digits-digit (e.g., "68130-40-5", "91082-17-6", "1333-86-4")
   - SCAN the entire text for ANY pattern matching \\d+-\\d+-\\d (numbers with two hyphens)
   - These patterns ARE CAS numbers - extract them exactly
   - "자료 없음" (no data) next to a CAS number does NOT mean CAS is missing - it refers to other fields
   - Example: "Polyurethane Propolymer자료 없음68130-40-530 - 60" → CAS is "68130-40-5"
   - ONLY use "비공개" if there is truly NO CAS pattern present for that chemical

2. **Parsing concatenated/compressed table data**:
   - Data may appear without delimiters like: "화학물질명관용명카스번호함유량(%)Chemical1Alias168130-40-530-60"
   - You MUST parse this by identifying:
     * Chemical names (text before CAS pattern)
     * CAS numbers (digit-digit-digit pattern like 68130-40-5)
     * Concentrations (patterns like "30 - 60", "< 3", "10-30" at the end)
   - "자료 없음" means "no data" for the alias/common name field, NOT for CAS

3. **Concentration (함량)**:
   - Preserve EXACT format: "30 - 60", "< 3", "10 - 30", "0.1 - 1"
   - Usually appears after CAS number
   - If not found, use "미공개"

4. **Chemical Name (화학물질명)**:
   - Extract the chemical name (first text field in each row)
   - May be in Korean or English

5. **Manufacturer (제조사) and Product Name (제품명)**:
   - Extract from document header/title

Output format (JSON object with components array):
{
    "components": [
        {
            "제조사": "manufacturer name",
            "제품명": "product name",
            "화학물질명": "chemical name",
            "CAS": "68130-40-5",
            "함량(%)": "30 - 60"
        }
    ]
}

Return ONLY valid JSON object, no additional text or markdown formatting."""

    def extract_components(self, text: str) -> List[Dict]:
        """OpenAI를 사용하여 MSDS 구성 성분 추출"""
        try:
            text_content = text[:MAX_TEXT_LENGTH]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": text_content}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content

            # JSON 파싱 - 강화된 오류 처리
            try:
                if isinstance(content, str):
                    content = content.strip()

                    # 1. 마크다운 코드 블록 제거 (```json ... ``` 또는 ``` ... ```)
                    if content.startswith("```"):
                        # 코드 블록에서 JSON 추출
                        json_block_pattern = r'```(?:json)?\s*([\s\S]*?)```'
                        json_match = re.search(json_block_pattern, content)
                        if json_match:
                            content = json_match.group(1).strip()

                    # 2. JSON 파싱 시도
                    result = json.loads(content)

                    # 3. 결과가 배열인지 확인
                    if isinstance(result, list):
                        return result
                    # 4. 결과가 딕셔너리이고 "components" 같은 키가 있으면 추출
                    elif isinstance(result, dict):
                        # 가능한 키 순서대로 확인
                        for key in ["components", "data", "results", "items"]:
                            if key in result and isinstance(result[key], list):
                                return result[key]
                        # 배열을 포함한 첫 번째 값 반환
                        for value in result.values():
                            if isinstance(value, list):
                                return value
                        logger.warning(f"JSON 응답에 배열이 없습니다: {result}")
                        return []
                    else:
                        logger.warning(f"예상치 못한 JSON 형식: {type(result)}")
                        return []
                else:
                    result = content
                    if isinstance(result, list):
                        return result
                    return []

            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 실패: {e}")
                logger.error(f"파싱 실패한 내용 (처음 500자): {content[:500]}")

                # 최후의 방법: JSON 배열 패턴을 직접 추출 시도
                try:
                    array_pattern = r'\[[\s\S]*\]'
                    array_matches = re.findall(array_pattern, content)
                    if array_matches:
                        # 가장 긴 배열 선택
                        json_str = max(array_matches, key=len)
                        result = json.loads(json_str)
                        if isinstance(result, list):
                            logger.info("배열 패턴 추출로 JSON 파싱 성공")
                            return result
                except Exception as fallback_error:
                    logger.error(f"배열 패턴 추출도 실패: {fallback_error}")

                return []

        except Exception as e:
            logger.error(f"OpenAI API 요청 오류: {e}")
            return []


# ============================================
# 주요 추출 함수
# ============================================
def extract_msds_info(parsed_text: str) -> List[Dict[str, str]]:
    """
    OpenAI API를 사용하여 파싱된 텍스트에서 MSDS 정보 추출
    """
    if not parsed_text or not parsed_text.strip():
        logger.warning("extract_msds_info에 빈 parsed_text가 제공됨")
        return []

    try:
        agent = MSDSExtractionAgent()
        raw_components = agent.extract_components(parsed_text)

        validated_components = []
        for comp in raw_components:
            try:
                comp_data = {
                    "제조사": comp.get("제조사", comp.get("manufacturer", "")),
                    "제품명": comp.get("제품명", comp.get("product_name", "")),
                    "화학물질명": comp.get("화학물질명", comp.get("chemical_name", "")),
                    "CAS": comp.get("CAS", comp.get("cas_number", "비공개")),
                    "함량(%)": comp.get("함량(%)", comp.get("concentration", "미공개")),
                }
                component = ChemicalComponent(**comp_data)
                validated_components.append(component.dict())
            except Exception as e:
                logger.warning(f"성분 검증 실패: {comp}. 오류: {e}")
                continue

        logger.info(f"{len(validated_components)}개 성분 검증 성공")
        return validated_components

    except ValueError as e:
        logger.error(f"설정 오류: {e}")
        raise
    except Exception as e:
        logger.error(f"extract_msds_info 오류: {e}", exc_info=True)
        return []


# ============================================
# 일괄 처리: 문서별 개별 JSON 저장
# ============================================
def batch_extract_msds(
    input_dir: Path = Path("output"),
    output_dir: Path = Path("msds_results"),
) -> None:
    """
    input_dir 내의 모든 .md 파일을 읽어서
    각 문서별로 개별 JSON 파일을 생성

    예시:
      output/1.5_eng.md  ->  msds_results/1.5_eng.json
    """
    if not input_dir.exists():
        raise FileNotFoundError(f"입력 폴더가 없습니다: {input_dir.resolve()}")

    md_files = sorted(input_dir.glob("*.md"))
    if not md_files:
        print(f"[정보] {input_dir} 내에 .md 파일이 없습니다.")
        return

    # 출력 폴더 생성
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[정보] 총 {len(md_files)}개 MD 파일 처리 시작")
    print(f"[정보] OpenAI API 사용 (gpt-4o-mini)")
    print(f"[정보] 결과 JSON 폴더: {output_dir.resolve()}")

    for md_path in md_files:
        print(f"\n[정보] 처리 중: {md_path.name}")
        try:
            # MD 파일 읽기
            md_content = md_path.read_text(encoding="utf-8")

            # MSDS 정보 추출
            components = extract_msds_info(md_content)

            result = {
                "file": md_path.name,
                "components": components if components else []
            }

            # 문서별 JSON 파일 경로 (예시: msds_results/1.5_eng.json)
            json_path = output_dir / f"{md_path.stem}.json"

            json_path.write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

            if components:
                print(f"[완료] {md_path.name} → {len(components)}개 성분 추출 → {json_path.name} 저장")
            else:
                print(f"[경고] {md_path.name} → 추출된 성분 없음 (빈 components로 {json_path.name} 저장)")

        except Exception as e:
            print(f"[오류] {md_path.name} 처리 중 오류: {e}")

    print(f"\n[완료] 모든 문서 처리 및 개별 JSON 생성 완료")


# ============================================
# CLI
# ============================================
if __name__ == "__main__":
    batch_extract_msds()
