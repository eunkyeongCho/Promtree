from __future__ import annotations
import re, json, requests

"""
[ingredients table 관련]

Ollama를 사용하여 MSDS 텍스트에서 성분 정보를 추출하는 모듈.

이 모듈은 대규모 언어 모델(LLM)을 활용하여 MSDS(물질안전보건자료) 문서의
구성성분 섹션 텍스트로부터 구조화된 성분 데이터를 JSON 형식으로 추출하는
기능을 제공합니다.

주요 기능:
- `FEW_SHOT` 프롬프트: 모델에게 역할, 스키마, 규칙, 그리고 다양한 예시
  (Few-shot examples)를 제공하여 정확한 결과물을 유도합니다.
- `build_prompt_for_sds`: 입력 텍스트와 사전 정의된 프롬프트를 결합하여
  LLM에 전달할 최종 프롬프트를 구성합니다.
- `ask_ollama`: 로컬 Ollama API에 HTTP POST 요청을 보내 모델의 응답을 받습니다.
- `extract_ingredients_with_ollama`: 전체 파이프라인을 실행하여 텍스트를
  입력받고, 최종적으로 파싱된 JSON 데이터를 반환합니다.
"""

MODEL = "qwen2.5:14b-instruct-q4_K_M"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"


FEW_SHOT = """
System:
You are a chemical composition extraction expert. Extract structured data strictly following the JSON schema. Return only a valid JSON array; no prose, no markdown, no code fences.

Schema (all keys required; use null when unknown):
[
{
"name": string,
"synonym": string[],
"cas": string|null,
"ec_number": string|null,
"concentration": {
"raw": string|null,
"value": number|null,
"min": number|null,
"max": number|null,
"unit": string|null,
"basis": string|null,
"op_min": string|null,
"op_max": string|null
},
"additional_info": {}
}
]

Normalization rules:

Copy original text literally into: cas (raw cell), concentration.raw (raw cell).

For concentration: parse numbers only when explicit unit/operator/basis exists; otherwise leave parsed fields null.

Headers mapping (KR/EN): "Chemical name/화학 물질명"→name, "Synonyms/관용명"→synonym, "CAS-No./CAS번호"→cas, "Concentration/함유량(%)"→concentration.

Percent unit: always "unit":"%".

Basis mapping: 'wt%', '(w/w)', 'w/w' → "basis":"w/w"; 'vol%', '(v/v)', 'v/v' → "basis":"v/v".

Ranges: 'a–b%', 'a-b%', 'a to b%' → min=a, max=b, value/op_*=null.

Operators: '>x%' → min/op_min='>'; '≥x%' → min/op_min='>='; '<x%' → max/op_max='<'; '≤x%' → max/op_max='<='.

Approximate: '~x%' or 'about x%' → value=x only (no min/max/op_*).

Split synonyms by comma/semicolon/slash/vertical bar/newline; trim/deduplicate; keep parentheses with token.

Always include all keys; use null or [] when missing.

Trade secret: preserve literal strings like '영업 비밀', 'Trade Secret', 'not disclosed' in cas and concentration.raw; do not invent values.

Output constraints:

Return a single JSON array only; no comments or fences.

Few-shot examples:

Example A:
Section:
| Chemical name | Synonyms | CAS-No. | Concentration |
| Hydrogen | HYDROGEN GAS | 1333-74-0| >99% |
Expected JSON:
[
{"name":"Hydrogen","synonym":["HYDROGEN GAS"],"cas":"1333-74-0","ec_number":null,
"concentration":{"raw":">99%","value":null,"min":99,"max":null,"unit":"%","basis":null,"op_min":">","op_max":null},
"additional_info":{}}
]

Example B:
Section:
| 화학 물질명 | 관용명 | CAS번호 | 함유량 (%) |
| 수소 | HYDROGEN GAS, HYDROGEN | 1333-74-0 | >99% |
Expected JSON:
[
{"name":"수소","synonym":["HYDROGEN GAS","HYDROGEN"],"cas":"1333-74-0","ec_number":null,
"concentration":{"raw":">99%","value":null,"min":99,"max":null,"unit":"%","basis":null,"op_min":">","op_max":null},
"additional_info":{}}
]

Example C:
Section:
Propoxylated Sorbitol 50–60% w/w; Propoxylated glycerol 40–50% (w/w)
Expected JSON:
[
{"name":"Propoxylated Sorbitol","synonym":[],"cas":null,"ec_number":null,
"concentration":{"raw":"50–60% w/w","value":null,"min":50,"max":60,"unit":"%","basis":"w/w","op_min":null,"op_max":null},
"additional_info":{}},
{"name":"Propoxylated glycerol","synonym":[],"cas":null,"ec_number":null,
"concentration":{"raw":"40–50% (w/w)","value":null,"min":40,"max":50,"unit":"%","basis":"w/w","op_min":null,"op_max":null},
"additional_info":{}}
]

Example D:
Section:
Hydrogen; H2 | CAS 1333-74-0 | ≥99.999 vol% (v/v)
Acetone ~0.5 wt%
Expected JSON:
[
{"name":"Hydrogen","synonym":["H2"],"cas":"1333-74-0","ec_number":null,
"concentration":{"raw":"≥99.999 vol% (v/v)","value":null,"min":99.999,"max":null,"unit":"%","basis":"v/v","op_min":">=","op_max":null},
"additional_info":{}},
{"name":"Acetone","synonym":[],"cas":null,"ec_number":null,
"concentration":{"raw":"~0.5 wt%","value":0.5,"min":null,"max":null,"unit":"%","basis":"w/w","op_min":null,"op_max":null},
"additional_info":{}}
]

Example E (미기재/혼합물):
Section:
3. 구성성분의 명칭 및 함유량
이 제품의 물질은 혼합물로 구성
물질안전보건자료에 기재된 구성성분 외에 다른 구성성분은 산업안전보건법 상 유해인자 분류기준에 해당되지 않음
Expected JSON:
[
{"name":"혼합물","synonym":[],"cas":null,"ec_number":null,
"concentration":{"raw":null,"value":null,"min":null,"max":null,"unit":null,"basis":null,"op_min":null,"op_max":null},
"additional_info":{"reason":"성분 미기재"}}
]

Example F (영업 비밀: 한국어):
Section:
| Chemical name | Synonyms | CAS-No. | Concentration |
| Component A | - | 영업 비밀 | 영업 비밀 |
Expected JSON:
[
{"name":"Component A","synonym":[],"cas":"영업 비밀","ec_number":null,
"concentration":{"raw":"영업 비밀","value":null,"min":null,"max":null,"unit":null,"basis":null,"op_min":null,"op_max":null},
"additional_info":{}}
]

Example G (영업 비밀: 영어):
Section:
| Chemical name | Synonyms | CAS-No. | Concentration |
| Trade Secret | Trade Secret | Trade Secret| Trade Secret |
Expected JSON:
[
{"name":"Trade Secret","synonym":["Trade Secret"],"cas":"Trade Secret","ec_number":null,
"concentration":{"raw":"Trade Secret","value":null,"min":null,"max":null,"unit":null,"basis":null,"op_min":null,"op_max":null},
"additional_info":{}}
]

Example H (단일 항목):
Section:
시클로헥사논
화학물질명
Cyclohexanone
관용명 및 이명(異名)
108-94-1
CAS번호 또는 식별번호
100%
함유량(%)
Expected JSON:
[
{"name":"시클로헥사논","synonym":["Cyclohexanone"],"cas":"108-94-1","ec_number":null,
"concentration":{"raw":"100%","value":100,"min":null,"max":null,"unit":"%","basis":null,"op_min":null,"op_max":null},
"additional_info":{}}
]

Example I (여러 항목):
Section:
시클로헥사논
화학물질명
Cyclohexanone
관용명 및 이명(異명)
108-94-1
CAS번호 또는 식별번호
100%
함유량(%)
화학물질 A
Component A
관용명 및 이명(異名)
123-12-1
CAS번호 또는 식별번호
0-5%
함유량(%)
Expected JSON:
[
{"name":"시클로헥사논","synonym":["Cyclohexanone"],"cas":"108-94-1","ec_number":null,
"concentration":{"raw":"100%","value":100,"min":null,"max":null,"unit":"%","basis":null,"op_min":null,"op_max":null},
"additional_info":{}},
{"name":"화학물질 A","synonym":["Component A"],"cas":"123-12-1","ec_number":null,
"concentration":{"raw":"0-5%","value":null,"min":0,"max":5,"unit":"%","basis":null,"op_min":null,"op_max":null},
"additional_info":{}}
]

Example J (HTML 테이블):
Section:
<table> <thead> <tr> <th>Chemical name</th><th>Synonyms</th><th>CAS-No.</th><th>Concentration</th> </tr> </thead> <tbody> <tr> <td>Hydrogen</td><td>HYDROGEN GAS</td><td>1333-74-0</td><td>&gt;99%</td> </tr> </tbody> </table>
Expected JSON: 
[ {"name":"Hydrogen","synonym":["HYDROGEN GAS"],"cas":"1333-74-0","ec_number":null, "concentration":{"raw":">99%","value":null,"min":99,"max":null,"unit":"%","basis":null,"op_min":">","op_max":null}, "additional_info":{}} ]

Example K (HTML 행 여러 개):
Section:
<table> <tr><th>화학 물질명</th><th>관용명</th><th>CAS번호</th><th>함유량(%)</th></tr> <tr><td>시클로헥사논</td><td>Cyclohexanone</td><td>108-94-1</td><td>100%</td></tr> <tr><td>화학물질 A</td><td>Component A</td><td>123-12-1</td><td>0–5%</td></tr> </table> 
Expected JSON: 
[ {"name":"시클로헥사논","synonym":["Cyclohexanone"],"cas":"108-94-1","ec_number":null, "concentration":{"raw":"100%","value":100,"min":null,"max":null,"unit":"%","basis":null,"op_min":null,"op_max":null}, "additional_info":{}}, {"name":"화학물질 A","synonym":["Component A"],"cas":"123-12-1","ec_number":null, "concentration":{"raw":"0–5%","value":null,"min":0,"max":5,"unit":"%","basis":null,"op_min":null,"op_max":null}, "additional_info":{}} ]

Example L (HTML 리스트/문단 혼합):
Section:
<ul> <li>Hydrogen; H2 — CAS 1333-74-0 — ≥99.999 vol% (v/v)</li> <li>Acetone — ~0.5 wt%</li> </ul> 
Expected JSON: 
[ {"name":"Hydrogen","synonym":["H2"],"cas":"1333-74-0","ec_number":null, "concentration":{"raw":"≥99.999 vol% (v/v)","value":null,"min":99.999,"max":null,"unit":"%","basis":"v/v","op_min":">=","op_max":null}, "additional_info":{}}, {"name":"Acetone","synonym":[],"cas":null,"ec_number":null, "concentration":{"raw":"~0.5 wt%","value":0.5,"min":null,"max":null,"unit":"%","basis":"w/w","op_min":null,"op_max":null}, "additional_info":{}} ]

Task:
Extract from the following input as "Section" and return only the JSON array.

Section:
{markdown_text}
"""

# 로컬 Ollama REST API에 POST 요청
def ask_ollama(prompt: str, model: str = MODEL, temperature: float = 0.0, timeout=180):
    try:
        r = requests.post(
            OLLAMA_URL,
            json={"model": model, "prompt": prompt, "stream": False, "options":{"temperature": temperature}},
            timeout=timeout
        )
        r.raise_for_status()
        return r.json().get("response","").strip()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Ollama request failed: {e}")
        return ""

# FEW_SHOT(시스템 규칙/예제), 스키마/규칙/초안을 프롬프트로 구성
def build_prompt_for_sds(section_text: str, draft_items=None, max_chars=2800):
    schema = {
      "name": "string|null",
      "synonym": ["string"],
      "cas": "string|null",
      "ec_number": "string|null",
      "concentration": {
        "raw": "string|null",
        "value": "number|null",
        "min": "number|null",
        "max": "number|null",
        "unit": "string|null",
        "basis": "string|null",
        "op_min": "string|null",
        "op_max": "string|null"
      },
      "additional_info": {}
    }
    t = re.sub(r"\n{3,}", "\n\n", section_text).strip()[:max_chars]
    draft = draft_items or []
    return f"""
You are an SDS composition extractor. Output ONLY a JSON array following the schema below.


{FEW_SHOT}


Rules:
- Output MUST be a complete JSON array; missing values are null/empty.
- Copy original cell text literally into cas and concentration.raw.
- Parse-only fields:
  - concentration value/min/max/unit/basis/op_* only if explicit numeric/unit/operator present.
- Name priority: Korean as name, English as synonym when both exist.
- Split synonyms by comma, semicolon, slash, vertical bar, or newline; keep parentheses; deduplicate.


Schema:
{json.dumps(schema, ensure_ascii=False, indent=2)}


Section:
{t}


Draft items (may be empty):
{json.dumps(draft, ensure_ascii=False)}
"""

# build_prompt_for_sds로 프롬프트를 만들고 ask_ollama로 모델 응답을 수신
def extract_ingredients_with_ollama(sec_text: str, draft_items=None):
    prompt = build_prompt_for_sds(sec_text, draft_items=draft_items)
    txt = ask_ollama(prompt)
    m = re.search(r"\[\s*\{.*\}\s*\]", txt, re.S)
    if not m:
        m = re.match(r"\s*\[.*\]\s*$", txt, re.S)
    if not m:
        print("[ERROR] Failed to find a valid JSON array in LLM response.")
        return []
    try:
        return json.loads(m.group(0))
    except Exception as e:
        print(f"[ERROR] Failed to parse JSON from LLM response: {e}")
        return []


