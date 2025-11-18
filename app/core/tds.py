"""
TDS Material Properties Extraction Module

This module extracts material properties from parsed TDS (Technical Data Sheet) documents
using the Upstage API and regex patterns. It handles hybrid extraction (LLM + regex)
and provides robust error handling.

Author: AI Engineer
Date: 2025-11-19
"""

import os
import re
import json
import logging
from typing import List, Dict
from dotenv import load_dotenv
import requests

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
MAX_TEXT_LENGTH = 8000  # Characters to send to API
# ============================================
# 물성 타입 정의
# ============================================
PROPERTY_NAMES = {
    'Tg': 'Glass Transition Temperature',
    'Tm': 'Melting Temperature',
    'Td': 'Decomposition Temperature',
    'DC': 'Degree of Crystallinity',
    'Eg': 'Band Gap Energy',
    'YS': 'Yield Strength',
    'YM': "Young's Modulus",
    'BS': 'Bending Strength',
    'Tensile_Strength': 'Tensile Strength',
    'Elongation_Rate': 'Elongation at Break',
    'Hardness': 'Hardness',
    'HDT': 'Heat Deflection Temperature',
    'Thermal_Conductivity': 'Thermal Conductivity',
    'Density': 'Density',
    'Viscosity': 'Viscosity',
    'Thixotropic_index': 'Thixotropic Index',
    'He_permeability': 'Helium Permeability',
    'H2_permeability': 'Hydrogen Permeability',
    'O2_permeability': 'Oxygen Permeability',
    'N2_permeability': 'Nitrogen Permeability',
    'CO2_permeability': 'Carbon Dioxide Permeability',
    'CH4_permeability': 'Methane Permeability',
}

# ============================================
# Regex 패턴
# ============================================
PATTERNS = {
    'Tg': [(r'(?:Glass Transition|Tg)[\s:]+(-?\d+\.?\d*)\s*°?\s*([CF℃])', 1, 2)],
    'Tm': [(r'(?:Melting|Tm)[\s:]+(\d+\.?\d*)\s*°?\s*([CF℃])', 1, 2)],
    'Td': [(r'(?:Decomposition|Td)[\s:]+(\d+\.?\d*)\s*°?\s*([CF℃])', 1, 2)],
    'DC': [(r'(?:Crystallinity|DC)[\s:]+(\d+\.?\d*)\s*%', 1, '%')],
    'YS': [(r'(?:Yield Strength|YS)[\s:]+(\d+\.?\d*)\s*(MPa|GPa|psi)', 1, 2)],
    'YM': [(r"(?:Young's Modulus|YM)[\s:]+(\d+\.?\d*)\s*(MPa|GPa|psi)", 1, 2)],
    'Tensile_Strength': [(r'(?:Tensile Strength)[\s:]+(\d+\.?\d*)\s*(MPa|GPa|psi)', 1, 2)],
    'Elongation_Rate': [(r'(?:Elongation)[\s:]+(\d+\.?\d*)\s*%', 1, '%')],
    'Density': [(r'(?:Density)[\s:]+(\d+\.?\d*)\s*(g/cm³|kg/m³)', 1, 2)],
    'Thermal_Conductivity': [(r'(?:Thermal Conductivity)[\s:]+(\d+\.?\d*)\s*(W/m·K|W/mK)', 1, 2)],
}

# ============================================
# Regex 추출
# ============================================
def detect_all_properties(text: str) -> List[Dict]:
    """Regex로 물성 추출"""
    properties = []
    seen = set()

    for prop_name, patterns in PATTERNS.items():
        for pattern, value_group, unit_group in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    value = float(match.group(value_group))
                    unit = match.group(unit_group) if isinstance(unit_group, int) else unit_group

                    key = (prop_name, value, unit)
                    if key not in seen:
                        properties.append({
                            'property': prop_name,
                            'value': value,
                            'unit': unit,
                            'matched_name': PROPERTY_NAMES.get(prop_name, prop_name),
                            'extraction_method': 'regex',
                        })
                        seen.add(key)
                except (ValueError, IndexError):
                    continue

    return properties

# ============================================
# LLM 추출 (Upstage API 사용)
# ============================================
class PropertyExtractionAgent:
    def __init__(self):
        if not UPSTAGE_API_KEY:
            raise ValueError("UPSTAGE_API_KEY가 환경 변수에 설정되지 않았습니다.")
        
        self.api_key = UPSTAGE_API_KEY
        self.api_url = UPSTAGE_API_URL
        self.model = "solar-pro2"
        
        self.system_prompt = """Extract material properties from TDS markdown.
Output JSON array: [{"property": "Tg", "value": 120.5, "unit": "°C", "matched_name": "Glass Transition Temperature"}]
Property types: Tg, Tm, Td, DC, Eg, YS, YM, BS, Tensile_Strength, Elongation_Rate, Hardness, HDT, Thermal_Conductivity, Density, Viscosity
Return [] if none found."""

    def extract_properties(self, text: str) -> List[Dict]:
        """LLM으로 물성 추출"""
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
                "stream": False
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
                            # 중괄호로 시작하는 배열 찾기
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
                        for prop in result:
                            prop['extraction_method'] = 'llm'
                            # matched_name이 없으면 추가
                            if 'matched_name' not in prop:
                                prop['matched_name'] = PROPERTY_NAMES.get(prop.get('property', ''), prop.get('property', ''))
                        return result
                    return []
                except json.JSONDecodeError as e:
                    # JSON 파싱 실패 시 빈 배열 반환 (LLM이 물성을 찾지 못한 경우)
                    logger.warning(f"JSON 파싱 실패 (물성 없음 또는 형식 오류): {e}")
                    # 빈 배열 []을 반환하는 경우도 정상 처리
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
# 하이브리드 병합
# ============================================
def merge_properties(llm_props: List[Dict], regex_props: List[Dict]) -> List[Dict]:
    """LLM 우선, Regex 보완"""
    merged = {}

    for prop in llm_props:
        merged[prop['property']] = prop

    for prop in regex_props:
        if prop['property'] not in merged:
            merged[prop['property']] = prop

    return list(merged.values())

# ============================================
# Main Extraction Function
# ============================================
def extract_tds_info(parsed_text: str, use_llm: bool = True) -> List[Dict]:
    """
    Extract material properties from parsed TDS text using Upstage API and regex.

    This function processes TDS document text and extracts material properties
    using a hybrid approach: LLM extraction (primary) and regex extraction (fallback).

    Args:
        parsed_text: The text content from a parsed TDS PDF document
        use_llm: Whether to use LLM extraction (default: True). If False, only regex is used.

    Returns:
        List of dictionaries, each containing:
        - property: Property type code (e.g., "Tg", "Tm", "YS")
        - value: Numeric value of the property
        - unit: Unit of measurement (e.g., "°C", "MPa", "%")
        - matched_name: Full name of the property (e.g., "Glass Transition Temperature")
        - extraction_method: "llm" or "regex"

    Example:
        >>> from app.promtree.parsing import parse_pdf, converter_init, image_processor_init
        >>> from app.core.tds import extract_tds_info
        >>>
        >>> converter = converter_init()
        >>> image_processor = image_processor_init()
        >>> contents = parse_pdf(pdf_path, converter, image_processor)
        >>> parsed_text = "\\n".join(contents)
        >>>
        >>> properties = extract_tds_info(parsed_text)
        >>> for prop in properties:
        ...     print(f"{prop['property']}: {prop['value']} {prop['unit']}")

    Notes:
        - Requires UPSTAGE_API_KEY environment variable to be set (if use_llm=True)
        - Uses hybrid extraction: LLM first, regex as fallback
        - Returns empty list if no properties found or on API errors
    """
    if not parsed_text or not parsed_text.strip():
        logger.warning("Empty parsed_text provided to extract_tds_info")
        return []

    try:
        # 1) LLM 추출
        llm_properties: List[Dict] = []
        if use_llm:
            try:
                logger.info("Starting TDS extraction with LLM")
                llm_agent = PropertyExtractionAgent()
                llm_properties = llm_agent.extract_properties(parsed_text)
                logger.info(f"LLM extracted {len(llm_properties)} properties")
            except Exception as e:
                logger.warning(f"LLM extraction failed: {e}")

        # 2) Regex 추출
        regex_properties = detect_all_properties(parsed_text)
        logger.info(f"Regex extracted {len(regex_properties)} properties")

        # 3) 병합 (LLM 우선, Regex 보완)
        if llm_properties:
            properties = merge_properties(llm_properties, regex_properties)
            logger.info(f"Merged total: {len(properties)} properties")
        else:
            properties = regex_properties
            logger.info(f"LLM failed - using regex only: {len(properties)} properties")

        return properties

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise
    except Exception as e:
        logger.error(f"Error in extract_tds_info: {e}", exc_info=True)
        return []


# ============================================
# CLI and Testing
# ============================================
if __name__ == "__main__":
    """
    CLI interface for testing TDS extraction

    Usage:
        python -m app.core.tds
    """
    import sys
    from pathlib import Path
    from app.promtree.parsing import converter_init, image_processor_init, parse_pdf

    # Example test with sample TDS text
    contents = parse_pdf("./pdfs/coll1/tds2.pdf", converter_init(), image_processor_init())
    sample_tds_text = "\n".join(contents)

    print("=" * 70)
    print("TDS Material Properties Extraction - Test")
    print("=" * 70)
    print(f"\nAPI Key configured: {'Yes' if UPSTAGE_API_KEY else 'No'}")
    print("\n" + "=" * 70)

    # Test extraction
    print("\nTesting extraction with sample TDS text...")
    print("-" * 70)

    try:
        results = extract_tds_info(sample_tds_text, use_llm=True)

        print(f"\n✓ Extraction completed successfully!")
        print(f"Found {len(results)} material properties:\n")

        for i, prop in enumerate(results, 1):
            print(f"{i}. {prop['property']} ({prop.get('matched_name', 'N/A')})")
            print(f"   Value: {prop['value']} {prop['unit']}")
            print(f"   Method: {prop.get('extraction_method', 'unknown')}")
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
