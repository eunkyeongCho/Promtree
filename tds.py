import os
import re
import json
import glob
from typing import List, Dict, Any
from dotenv import load_dotenv
from openai import OpenAI

# 환경 변수 로드
load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
MAX_TEXT_LENGTH = 15000

# 추출 대상 속성 매핑
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

# 정규식 패턴 정의
REGEX_PATTERNS = {
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

class TDSExtract:
    def __init__(self):
        if not OPENAI_API_KEY:
            print("Warning: OPENAI_API_KEY env variable is missing.")
            self.client = None
        else:
            self.client = OpenAI(api_key=OPENAI_API_KEY)
        
        self.model = "gpt-4o"
        
        self.system_prompt = """You are an expert Material Science Engineer specializing in parsing TDS (Technical Data Sheet) documents.

Your goal is to extract material properties from the provided text.

### EXTRACTION TARGETS:
Extract the following properties if available:
Tg, Tm, Td, DC, Eg, YS, YM, BS, Tensile_Strength, Elongation_Rate, Hardness, HDT, Thermal_Conductivity, Density, Viscosity, Permeability(He, H2, O2, N2, CO2, CH4).

### OUTPUT FORMAT (JSON Only):
Return a JSON Object with a single key "properties" containing a list of objects.

```json
{
  "properties": [
    {
      "property": "Tg",
      "value": 120.5,
      "unit": "°C",
      "matched_name": "Glass Transition Temperature"
    },
    {
      "property": "Tensile_Strength",
      "value": 50,
      "unit": "MPa",
      "matched_name": "Tensile Strength"
    }
  ]
}
```

### RULES:
1. Value must be a number.
2. If a property is not found, do not include it.
3. Normalize units where possible.
"""

    def request_ai(self, text: str) -> str:
        if not self.client:
            return ""

        cleaned_text = re.sub(r'\n{3,}', '\n\n', text)
        truncated_text = cleaned_text[:MAX_TEXT_LENGTH]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Analyze the following TDS content and extract material properties:\n\n{truncated_text}"}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"API Error: {e}")
            return ""

    def parse_response(self, content: str) -> List[Dict[str, Any]]:
        if not content:
            return []

        try:
            content = content.strip()
            result = None

            json_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
            if json_block_match:
                content = json_block_match.group(1).strip()

            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                array_match = re.search(r'\[[\s\S]*\]', content)
                if array_match:
                    try:
                        result = json.loads(array_match.group(0))
                    except: pass
                
                if result is None:
                    obj_match = re.search(r'\{[\s\S]*\}', content)
                    if obj_match:
                        try:
                            result = json.loads(obj_match.group(0))
                        except: pass
            
            if result is None:
                return []

            final_list = []
            
            if isinstance(result, list):
                final_list = result
            elif isinstance(result, dict):
                found_list = False
                for key in ["properties", "data", "results", "items"]:
                    if key in result and isinstance(result[key], list):
                        final_list = result[key]
                        found_list = True
                        break
                
                if not found_list:
                    for val in result.values():
                        if isinstance(val, list):
                            final_list = val
                            break
            
            for item in final_list:
                item['extraction_method'] = 'llm'
                if 'matched_name' not in item and 'property' in item:
                    item['matched_name'] = PROPERTY_NAMES.get(item['property'], item['property'])

            return final_list

        except Exception as e:
            print(f"Parsing Error: {e}")
            return []

def detect_regex_properties(text: str) -> List[Dict]:
    properties = []
    seen = set()

    for prop_name, patterns in REGEX_PATTERNS.items():
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

def merge_properties(llm_props: List[Dict], regex_props: List[Dict]) -> List[Dict]:
    merged = {}

    for prop in llm_props:
        if 'property' in prop:
            merged[prop['property']] = prop

    for prop in regex_props:
        if prop['property'] not in merged:
            merged[prop['property']] = prop

    return list(merged.values())

def extract_tds_info(parsed_text: str, use_llm: bool = True) -> List[Dict]:
    if not parsed_text or not parsed_text.strip():
        return []

    llm_properties = []

    if use_llm:
        agent = TDSExtract()
        if agent.client:
            # print("Requesting AI analysis...") # 로깅 최소화
            ai_response = agent.request_ai(parsed_text)
            llm_properties = agent.parse_response(ai_response)

    regex_properties = detect_regex_properties(parsed_text)
    final_properties = merge_properties(llm_properties, regex_properties)

    return final_properties

def process_directory(input_dir: str, output_dir: str):
    # 입력 디렉토리 확인
    if not os.path.exists(input_dir):
        print(f"Input directory not found: {input_dir}")
        return

    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)

    # Markdown 파일 검색 (*.md)
    file_pattern = os.path.join(input_dir, "*.md")
    files = glob.glob(file_pattern)

    if not files:
        print(f"No markdown files found in {input_dir}")
        return

    print(f"Found {len(files)} files. Starting processing...")

    for file_path in files:
        try:
            file_name = os.path.basename(file_path)
            print(f"Processing: {file_name}")

            # 파일 읽기
            with open(file_path, 'r', encoding='utf-8') as f:
                text_content = f.read()

            # 데이터 추출
            extracted_data = extract_tds_info(text_content)

            # 결과 저장을 위한 파일명 생성
            file_name_no_ext = os.path.splitext(file_name)[0]
            output_file_path = os.path.join(output_dir, f"{file_name_no_ext}.json")

            # JSON 저장
            with open(output_file_path, 'w', encoding='utf-8') as f:
                json.dump(extracted_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"Error processing {file_name}: {e}")

    print("All processing complete.")

if __name__ == "__main__":
    # 입력 및 출력 디렉토리 설정
    INPUT_DIR = "markdown/tds"
    OUTPUT_DIR = "output/tds"

    process_directory(INPUT_DIR, OUTPUT_DIR)