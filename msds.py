import os
import re
import json
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field, field_validator

load_dotenv()

MAX_TEXT_LENGTH = 30000
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

class ChemicalComponent(BaseModel):
    manufacturer: str = Field(..., alias="제조사", description="Manufacturer")
    product_name: str = Field(..., alias="제품명", description="Product Name")
    chemical_name: str = Field(..., alias="화학물질명", description="Chemical Name")
    cas_number: str = Field(..., alias="CAS", description="CAS Number")
    concentration: str = Field(..., alias="함량(%)", description="Concentration")

    @field_validator('concentration', mode='before')
    @classmethod
    def preserve_concentration_format(cls, v):
        if v is None:
            return "미공개"
        v_str = str(v).strip()
        if v_str in ["-", "자료없음", "자료 없음", "None", "N/A"]:
            return "미공개"
        return v_str

    @field_validator('cas_number', mode='before')
    @classmethod
    def normalize_cas_number(cls, v):
        if v is None or str(v).strip() == "":
            return "비공개"
        
        v_str = str(v).strip()
        cas_pattern = r'^\d{1,7}-\d{2}-\d$'
        
        if re.match(cas_pattern, v_str):
            return v_str

        not_disclosed_patterns = [
            "비공개", "미공개", "공개안함", "공개하지않음", "자료없음", "자료 없음", "영업비밀",
            "not disclosed", "not available", "confidential", "proprietary", "secret", "trade secret",
            "n/a", "na", "n.a.", "none", "-", "—", "–"
        ]
        
        if any(pattern.lower() in v_str.lower() for pattern in not_disclosed_patterns):
            return "비공개"

        search_match = re.search(r'(\d{1,7}-\d{2}-\d)', v_str)
        if search_match:
            return search_match.group(1)

        return v_str

    def dict(self, **kwargs):
        return {
            "제조사": self.manufacturer,
            "제품명": self.product_name,
            "화학물질명": self.chemical_name,
            "CAS": self.cas_number,
            "함량(%)": self.concentration,
        }

class MSDSExtract:
    def __init__(self):
        if not OPENAI_API_KEY:
            print("OPENAI_API_KEY env variable is missing.")
            self.client = None
        else:
            self.client = OpenAI(api_key=OPENAI_API_KEY)
        
        self.model = "gpt-4.1"
        
        self.system_prompt = """You are an expert Chemical Safety Consultant specializing in parsing MSDS (Material Safety Data Sheet) documents.

Your goal is to extract ALL chemical composition data from the provided text, handling OCR errors and unstructured formats accurately.

### CRITICAL EXTRACTION RULES (Must Follow):

1. **CAS Number Strategy (Highest Priority)**:
    - **Pattern Recognition**: Look specifically for the regex pattern `\\d{1,7}-\\d{2}-\\d` (e.g., 100-41-4, 7631-86-9).
    - If you see a number matching this pattern anywhere in a row context, it IS the CAS number.
    - **Valid Columns**: Look for headers like "CAS No", "CAS#", "Identifier", "Chemical ID".
    - **"No Data" Confusion**: Do NOT mark CAS as "비공개" just because one column says "No data". Only mark "비공개" if the CAS field itself is empty, "-", or clearly states "Confidential"/"Secret".

2. **Concentration (함량(%)) Strategy**:
    - **Preserve Exact Format**: Do NOT convert to decimals. Keep ranges and symbols exactly as appear.
    - Examples: "10 ~ 20 %", ">= 1.0", "< 5.5", "45-50".
    - If a range is split (e.g., "Min: 10, Max: 20"), combine them as "10-20".

3. **Chemical Name Strategy**:
    - Extract the full chemical name (Korean or English).
    - If synonyms or common names are present (e.g., "Xylene (Xylol)"), include the primary name.

4. **Manufacturer & Product Info**:
    - Extract `제조사` (Manufacturer) and `제품명` (Product Name) from the top metadata section of the document.
    - This info applies to ALL components in the list.

5. **Table Parsing Heuristics (Broken Lines)**:
    - The text might look like: `Chemical Name CAS Concentration` compressed without spaces.
    - Example: `Ethylbenzene100-41-410~20%` -> You must separate this based on the CAS pattern `100-41-4`.
    - Broken lines: Sometimes the CAS appears on the next line. Use the CAS pattern `\\d-\\d-\\d` as an anchor to identify the row.

### OUTPUT FORMAT (JSON Only):

Return a JSON Object with a single key "components" containing a list of objects.

```json
{
  "components": [
    {
      "제조사": "ABC Chemicals",
      "제품명": "Super Solvent",
      "화학물질명": "Xylene",
      "CAS": "1330-20-7",
      "함량(%)": "10 ~ 20"
    }
  ]
}
```
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
                    {"role": "user", "content": f"Analyze the following MSDS content and extract chemical data:\n\n{truncated_text}"}
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
                for key in ["components", "data", "results", "items", "composition"]:
                    if key in result and isinstance(result[key], list):
                        final_list = result[key]
                        found_list = True
                        break
                
                if not found_list:
                    for val in result.values():
                        if isinstance(val, list):
                            final_list = val
                            break
            
            return final_list

        except Exception as e:
            print(f"Parsing Error: {e}")
            return []

def extract_msds_info(parsed_text: str) -> List[Dict[str, str]]:
    if not parsed_text or not parsed_text.strip():
        print("Empty text input.")
        return []
    
    agent = MSDSExtract()
    if not agent.client:
        return []

    print("Requesting AI analysis...")
    ai_response = agent.request_ai(parsed_text)
    
    raw_components = agent.parse_response(ai_response)
    
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
            
            if not comp_data["화학물질명"]:
                comp_data["화학물질명"] = "미공개"

            component = ChemicalComponent(**comp_data)
            validated_components.append(component.dict())
            
        except Exception as e:
            print(f"Validation failed for item: {comp} / Reason: {e}")
            continue

    print(f"Completed. {len(validated_components)} components extracted.")
    return validated_components

def main(markdown_dir: Path = Path("markdown/msds"), output_dir: Path = Path("output/msds")):
    if not markdown_dir.exists():
        print(f"Input directory not found: {markdown_dir.resolve()}")
        return

    md_files = sorted(markdown_dir.glob("*.md"))
    if not md_files:
        print(f"No .md files found in {markdown_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Starting process for {len(md_files)} files.")

    for md_path in md_files:
        try:
            print(f"\nProcessing: {md_path.name}")
            
            md_content = md_path.read_text(encoding="utf-8")
            
            components = extract_msds_info(md_content)

            result = {
                "file": md_path.name,
                "count": len(components),
                "components": components if components else []
            }

            json_path = output_dir / f"{md_path.stem}.json"
            json_path.write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

            if components:
                print(f"Saved: {json_path.name}")
            else:
                print(f"Warning: No components found for {json_path.name}")

        except Exception as e:
            print(f"Error processing {md_path.name}: {e}")

if __name__ == "__main__":
    main()