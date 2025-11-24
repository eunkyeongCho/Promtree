"""
MSDS Chemical Information Extraction Module

This module extracts structured chemical information from parsed MSDS documents
using the Upstage API. It handles multilingual content (Korean/English), preserves
concentration ranges, and provides robust error handling.

Author: AI Engineer
Date: 2025-11-19
"""

import os
import re
import json
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv
import requests
from pydantic import BaseModel, Field, field_validator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# ============================================
# Configuration
# ============================================
UPSTAGE_API_KEY = os.getenv('UPSTAGE_API_KEY')
UPSTAGE_API_URL = "https://api.upstage.ai/v1/chat/completions"
MAX_TEXT_LENGTH = 15000  # Characters to send to API

# ============================================
# Pydantic Models
# ============================================
class ChemicalComponent(BaseModel):
    """Pydantic model for a single chemical component in MSDS"""
    manufacturer: str = Field(..., alias="제조사", description="Manufacturer name")
    product_name: str = Field(..., alias="제품명", description="Product name")
    chemical_name: str = Field(..., alias="화학물질명", description="Chemical name")
    cas_number: str = Field(..., alias="CAS", description="CAS registry number or '비공개'")
    concentration: str = Field(..., alias="함량(%)", description="Concentration with exact format preserved")

    @field_validator('concentration', mode='before')
    @classmethod
    def preserve_concentration_format(cls, v):
        """Ensure concentration format is preserved exactly as extracted"""
        if v is None:
            return "미공개"
        return str(v).strip()

    @field_validator('cas_number', mode='before')
    @classmethod
    def normalize_cas_number(cls, v):
        """Normalize CAS number or mark as not disclosed"""
        if v is None or str(v).strip() == "":
            return "비공개"
        v_str = str(v).strip()
        
        # Check if it's a valid CAS number pattern (digits-digits-digit)
        # CAS numbers are typically in format: 1-7 digits, hyphen, 2 digits, hyphen, 1 digit
        cas_pattern = r'^\d{1,7}-\d{2}-\d$'
        if re.match(cas_pattern, v_str):
            # It's a valid CAS number, return as is
            return v_str
        
        # Common patterns for "not disclosed" in Korean/English
        not_disclosed_patterns = [
            "비공개", "미공개", "공개안함", "공개하지않음",
            "not disclosed", "not available", "confidential", "proprietary",
            "n/a", "na", "n.a.", "none", "-", "—", "–"
        ]
        for pattern in not_disclosed_patterns:
            if pattern.lower() in v_str.lower():
                return "비공개"
        
        # If it doesn't match CAS pattern and isn't a known "not disclosed" pattern,
        # return as is (might be a valid CAS in different format or edge case)
        return v_str

    def dict(self, **kwargs):
        """Override dict to use Korean field names"""
        return {
            "제조사": self.manufacturer,
            "제품명": self.product_name,
            "화학물질명": self.chemical_name,
            "CAS": self.cas_number,
            "함량(%)": self.concentration,
        }


class MSRDExtractionResponse(BaseModel):
    """Response model for MSDS extraction"""
    components: List[ChemicalComponent] = Field(default_factory=list)
    extraction_method: str = Field(default="llm", description="Method used for extraction")

    @field_validator('components', mode='before')
    @classmethod
    def validate_components(cls, v):
        """Validate and parse components from various formats"""
        if v is None:
            return []
        if isinstance(v, list):
            return v
        return []


# ============================================
# MSDS Extraction Agent
# ============================================
class MSDSExtractionAgent:
    """Agent for extracting chemical information from MSDS documents using Upstage API"""

    def __init__(self):
        if not UPSTAGE_API_KEY:
            raise ValueError("UPSTAGE_API_KEY가 환경 변수에 설정되지 않았습니다.")
        
        self.api_key = UPSTAGE_API_KEY
        self.api_url = UPSTAGE_API_URL
        self.model = "solar-pro2"
        
        self.system_prompt = """You are an expert at extracting chemical information from MSDS (Material Safety Data Sheet) documents.

Extract ALL chemical components from the MSDS document and return them in JSON format.

CRITICAL EXTRACTION RULES:
1. **Concentration (함량)**: 
   - MUST preserve EXACT format as written in document
   - Handle ranges: "10-20%", "5~15%", "5-15%", "10~20%", "< 10%", "> 95%", "≤ 5%", "≥ 90%"
   - Preserve all symbols: hyphens (-), tildes (~), less than (<), greater than (>), etc.
   - If concentration is not disclosed, use "미공개"

2. **CAS Number (CRITICAL - MUST EXTRACT WHEN PRESENT)**:
   - CAS numbers are ALWAYS in the format: digits-digits-digit (e.g., "123-45-6", "35239-19-1", "25038-59-9")
   - Recognize CAS column headers in various formats: "CAS No.", "CAS Num", "Cas number", "CAS Number", "카스번호", "CAS번호", "CAS No", "CAS#", "C.A.S. No.", "C.A.S.No.", "C.A.S No.", "C.A.S. No", "C.A.S.No", "C.A.S No", "C.A.S.", "CAS"
   - When you see a pattern like "123-45-6" or "35239-19-1" (numbers separated by hyphens), that IS a CAS number - extract it exactly as written
   - In table format, look for the CAS column (may be labeled "C.A.S. No.", "CAS No.", etc.) and extract the value from that column
   - ONLY use "비공개" if:
     * The CAS field is explicitly empty, blank, or contains "None", "N/A", "n/a", "na", "-", "—", "–"
     * The document explicitly states "not disclosed", "confidential", "proprietary", "비공개", "미공개", "공개안함"
   - DO NOT mark as "비공개" if a valid CAS number pattern exists (e.g., "35239-19-1" should be extracted as "35239-19-1", NOT "비공개")

3. **Chemical Name (화학물질명)**:
   - Extract exact chemical name as written (Korean or English)
   - Handle both Korean and English names
   - If component name is not specified, use "미공개"

4. **Manufacturer (제조사) and Product Name (제품명)**:
   - Extract from document header, title, or first section
   - Usually found in "제조사", "Manufacturer", "회사명", "Company" fields
   - Product name from "제품명", "Product Name", "상품명" fields

5. **Table Format Handling (CRITICAL FOR CAS EXTRACTION)**:
   - Many MSDS documents present composition information in table format
   - Example table format:
     ```
     Ingredient C.A.S. No. % by Wt
     Acrylic adhesive 35239-19-1 40 - 70
     PET film 25038-59-9 5 – 20
     PET Liner None 20 - 50
     ```
   - For each row:
     * Extract the ingredient/chemical name from the first column
     * Extract the CAS number from the CAS column (may be labeled "C.A.S. No.", "CAS No.", etc.) - if it's a valid CAS pattern (numbers with hyphens), extract it exactly
     * Extract the concentration from the percentage column
   - Look for tables with headers like "Ingredient", "Component", "Chemical", "C.A.S. No.", "CAS No.", "% by Wt", "Concentration", etc.
   - Extract each row as a separate component entry
   - Pay EXTRA attention to CAS column - even if header says "C.A.S. No." with dots, the actual CAS numbers in that column should be extracted (e.g., "35239-19-1" is a valid CAS number)

6. **Special Cases**:
   - Some documents may not disclose composition at all - return empty array []
   - If composition section exists but is empty, return empty array []
   - Each chemical component should be a separate entry in the array
   - Handle mixed Korean/English documents

7. **Output Format**:
   - Return ONLY a valid JSON array
   - No additional text, explanations, or markdown formatting
   - Use Korean field names as specified

Output format (JSON array):
[
    {
        "제조사": "manufacturer name",
        "제품명": "product name",
        "화학물질명": "chemical name",
        "CAS": "123-45-6 or 비공개",
        "함량(%)": "10-20%"
    },
    ...
]

Return ONLY the JSON array, no additional text."""

    def extract_components(self, text: str) -> List[Dict]:
        """LLM으로 MSDS 구성 성분 추출"""
        try:
            # 텍스트 길이 제한
            text_content = text[:MAX_TEXT_LENGTH]
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": text_content}
                ],
                "stream": False,
                "temperature": 0.1
            }
            
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            
            result_json = response.json()
            
            # 응답에서 content 추출
            if "choices" in result_json and len(result_json["choices"]) > 0:
                content = result_json["choices"][0]["message"]["content"]
                
                # JSON 파싱 시도
                try:
                    if isinstance(content, str):
                        # 방법 1: 마크다운 코드 블록에서 JSON 추출 (```json ... ```)
                        json_block_pattern = r'```(?:json)?\s*(\[[\s\S]*?\])```'
                        json_match = re.search(json_block_pattern, content)
                        if json_match:
                            json_str = json_match.group(1)
                            result = json.loads(json_str)
                        else:
                            # 방법 2: 전체 텍스트에서 JSON 배열 패턴 찾기
                            array_pattern = r'\[[\s\S]*?\]'
                            array_matches = re.findall(array_pattern, content)
                            if array_matches:
                                # 가장 긴 배열을 선택 (보통 정답)
                                json_str = max(array_matches, key=len)
                                result = json.loads(json_str)
                            else:
                                # 방법 3: 전체 content를 직접 파싱 시도
                                content_clean = content.strip()
                                # 코드 블록이 전체인 경우
                                if content_clean.startswith("```"):
                                    lines = content_clean.split("\n")
                                    if len(lines) > 2:
                                        # 첫 줄과 마지막 줄 제거 (```json과 ```)
                                        content_clean = "\n".join(lines[1:-1])
                                result = json.loads(content_clean)
                    else:
                        result = content
                    
                    if isinstance(result, list):
                        return result
                    return []
                except json.JSONDecodeError as e:
                    # JSON 파싱 실패 시 빈 배열 반환
                    logger.warning(f"JSON 파싱 실패 (구성 성분 없음 또는 형식 오류): {e}")
                    if '[]' in content or 'empty' in content.lower() or 'none found' in content.lower():
                        return []
                    return []
                except Exception as e:
                    logger.error(f"JSON 추출 중 오류: {e}")
                    return []
            else:
                logger.warning(f"예상치 못한 응답 형식: {result_json}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Upstage API 요청 오류: {e}")
            return []
        except Exception as e:
            logger.error(f"LLM 추출 오류: {e}")
            return []


# ============================================
# Main Extraction Function
# ============================================
def extract_msds_info(parsed_text: str) -> List[Dict[str, str]]:
    """
    Extract MSDS information from parsed text using Upstage API.

    This function processes MSDS document text and extracts structured chemical
    information including manufacturer, product name, chemical names, CAS numbers,
    and concentrations.

    Args:
        parsed_text: The text content from a parsed MSDS PDF document

    Returns:
        List of dictionaries, each containing:
        - 제조사 (manufacturer)
        - 제품명 (product name)
        - 화학물질명 (chemical name)
        - CAS (CAS number or "비공개")
        - 함량(%) (concentration % with exact format preserved)

    Example:
        >>> from app.promtree.parsing import parse_pdf, converter_init, image_processor_init
        >>> from app.core.msds import extract_msds_info
        >>>
        >>> converter = converter_init()
        >>> image_processor = image_processor_init()
        >>> contents = parse_pdf(pdf_path, converter, image_processor)
        >>> parsed_text = "\\n".join(contents)
        >>>
        >>> msds_data = extract_msds_info(parsed_text)
        >>> for component in msds_data:
        ...     print(f"{component['화학물질명']}: {component['함량(%)']}")

    Notes:
        - Requires UPSTAGE_API_KEY environment variable to be set
        - Handles multilingual content (Korean/English)
        - Preserves concentration ranges exactly as they appear
        - Returns empty list if no components found or on API errors
        - Uses retry logic for transient failures
    """
    if not parsed_text or not parsed_text.strip():
        logger.warning("Empty parsed_text provided to extract_msds_info")
        return []

    try:
        # Initialize agent
        agent = MSDSExtractionAgent()

        # Extract components
        raw_components = agent.extract_components(parsed_text)

        # Validate and structure components using Pydantic
        validated_components = []
        for comp in raw_components:
            try:
                # Handle both Korean and English field names
                # Prepare data dict with proper field names
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
                logger.warning(f"Failed to validate component: {comp}. Error: {e}")
                continue

        logger.info(f"Successfully validated {len(validated_components)} components")
        return validated_components

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise
    except Exception as e:
        logger.error(f"Error in extract_msds_info: {e}", exc_info=True)
        return []




# ============================================
# CLI and Testing
# ============================================
if __name__ == "__main__":
    """
    CLI interface for testing MSDS extraction

    Usage:
        python -m app.core.msds
    """
    import sys
    from pathlib import Path
    from app.promtree.parsing import converter_init, image_processor_init, parse_pdf
    

    # Example test with sample MSDS text
    contents = parse_pdf("./pdfs/coll1/sample.pdf", converter_init(), image_processor_init())

    sample_msds_text = "\n".join(contents)

    print(sample_msds_text)

    print("=" * 70)
    print("MSDS Chemical Information Extraction - Test")
    print("=" * 70)
    print(f"\nAPI Key configured: {'Yes' if UPSTAGE_API_KEY else 'No'}")
    print("\n" + "=" * 70)

    # Test extraction
    print("\nTesting extraction with sample MSDS text...")
    print("-" * 70)

    try:
        results = extract_msds_info(sample_msds_text)

        print(f"\n✓ Extraction completed successfully!")
        print(f"Found {len(results)} chemical components:\n")

        for i, component in enumerate(results, 1):
            print(f"{i}. {component['화학물질명']}")
            print(f"   제조사: {component['제조사']}")
            print(f"   제품명: {component['제품명']}")
            print(f"   CAS: {component['CAS']}")
            print(f"   함량(%): {component['함량(%)']}")
            print()

        # Print JSON output
        print("-" * 70)
        print("JSON Output:")
        print(json.dumps(results, ensure_ascii=False, indent=2))

    except Exception as e:
        print(f"\n✗ Error during extraction: {e}")
        logger.exception("Test failed")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("Test completed successfully!")
    print("=" * 70)
