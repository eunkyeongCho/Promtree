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

MODEL = "gpt-oss:20b"
OLLAMA_URL = "https://bcb7tjvf0wm6jb-11434.proxy.runpod.net/api/generate"


FEW_SHOT = """
System:
You are a chemical composition extraction expert. Extract structured data strictly following the JSON schema. Return only a valid JSON array; no prose, no markdown, no code fences.


Schema (all keys required; use null when unknown):
  {
    "product_name": "string|null",
    "company_name": "string|null",
    "ingredients": [{
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
        "op_max": "string|null",
        "is_cas_secret" : BOOLEAN DEFAULT FALSE,
        "is_conc_secret" :  BOOLEAN DEFAULT FALSE,
      },
      "additional_info": {}
    }]}


Normalization rules:
- Copy original text: For concentration, copy the original cell text literally into concentration.raw.
- cas field processing: The cas field should only contain the CAS number string (e.g., "123-45-6"), extracted from the source text. Any other numbers or identifiers (like EC Numbers) present in the same cell must be excluded.
- For concentration, if raw contains numbers and explicit unit/op/basis, fill value/min/max/unit/basis/op_*; otherwise leave them null.
- Headers mapping (KR/EN): "Chemical name/화학 물질명"→name, "Synonyms/관용명"→synonym, "CAS-No./CAS번호"→cas, "Concentration/함유량(%)"→concentration.
- Percent unit: normalized to '%' if percentage.
- Basis mapping: 'wt%', '(w/w)', 'w/w' → basis='w/w'; 'vol%', '(v/v)', 'v/v' → basis='v/v'. If no basis is explicitly mentioned, set to null.
- Ranges: 'a–b%', 'a-b%', 'a to b%' → min=a, max=b, value/op_*=null.
- Operators: '>x%' → min/op_min='>'; '≥x%' → min/op_min='>='; '<x%' → max/op_max='<'; '≤x%' → max/op_max='<='.
- Approximate: '~x%' or 'about x%' → value=x only.
- Split synonyms by comma, semicolon, slash, vertical bar, or newline; trim/deduplicate; keep parentheses with their token.
- Missing pieces: always include keys; use null/[] accordingly.


Output constraints:
- Return a single JSON array only; no comments or fences.


Few-shot examples:

SECTION 1. PRODUCT AND COMPANY IDENTIFICATION

Product name :

Triethylene Glycol

Product code :

U1251

Synonyms :

2,2 ethylenedioxydiethanol, Ethylene triglycol, glycol bis (hydroxyethyl) ether, TEG, Triglycol

CAS-No. :

112-27-6

Manufacturer or supplier's details
Supplier :

SHELL EASTERN CHEMICALS (S) A REGISTERED BUSINESS OF SHELL EASTERN TRADING (PTE) LTD (UEN:198902087C) 9 North Buona Vista Drive , #07-01 The Metropolis Tower 1 Singapore 138588 Singapore

SECTION 3. COMPOSITION/INFORMATION ON INGREDIENTS

Substance / Mixture :

Substance

3.1 Substances
Components
<table><tbody><tr><td>Chemical name</td><td>CAS-No.</td><td>Classification</td><td>Concentration (% w/w)</td></tr><tr><td>Triethylene glycol</td><td>112-27-6</td><td></td><td>&gt; 99</td></tr><tr><td>Diethylene glycol</td><td>111-46-6</td><td>Acute Tox.4; H302</td><td>&lt; 1</td></tr></tbody></table>

Expected JSON:
{
  "product_name": "Triethylene Glycol",
  "company_name": "SHELL EASTERN CHEMICALS (S) A REGISTERED BUSINESS OF SHELL EASTERN TRADING (PTE) LTD",
  "ingredients": [
    {
      "name": "Triethylene glycol",
      "synonym": [],
      "cas": "112-27-6",
      "ec_number": null,
      "concentration": {
        "raw": "> 99",
        "value": null,
        "min": 99,
        "max": null,
        "unit": "%",
        "basis": "w/w",
        "op_min": ">",
        "op_max": null,
        "is_cas_secret": false,
        "is_conc_secret": false
      },
      "additional_info": {}
    },
    {
      "name": "Diethylene glycol",
      "synonym": [],
      "cas": "111-46-6",
      "ec_number": null,
      "concentration": {
        "raw": "< 1",
        "value": null,
        "min": null,
        "max": 1,
        "unit": "%",
        "basis": "w/w",
        "op_min": null,
        "op_max": "<",
        "is_cas_secret": false,
        "is_conc_secret": false
      },
      "additional_info": {}
    }
  ]
}

### Few-Shot 예시 2: 영문 MSDS (Acetylene)
#### 입력 텍스트
Section 1. Identification

Acetylene

GHS product identifier

Other means of :

identification

Ethyne; Ethine; Narcylen; C2H2; Acetylen; UN 1001; Vinylene

Supplier's details :

Airgas USA, LLC and its affiliates 259 North Radnor-Chester Road Suite 100 Radnor, PA 19087-5283

Section 3. Composition/information on ingredients

Substance/mixture

Substance

<table><tbody><tr><td>Ingredient name</td><th>%</th><th>CAS number</th></tr><tr><th>Acetylene</th><td>100</td><td>74-86-2</td></tr></tbody></table> ```

출력 JSON

{
  "product_name": "Acetylene",
  "company_name": "Airgas USA, LLC and its affiliates",
  "ingredients": [
    {
      "name": "Acetylene",
      "synonym": ["Ethyne", "Ethine", "Narcylen", "C2H2", "Acetylen", "UN 1001", "Vinylene"],
      "cas": "74-86-2",
      "ec_number": null,
      "concentration": {
        "raw": "100",
        "value": 100,
        "min": 100,
        "max": 100,
        "unit": "%",
        "basis": null,
        "op_min": null,
        "op_max": null,
        "is_cas_secret": false,
        "is_conc_secret": false
      },
      "additional_info": {}
    }
  ]
}

Example 3:
## 1. 화학제품과 회사에 관한 정보

## 1.1. 제품명

3M Choke & Carb Cleaner, 03735

## 1.2. 제품의 권고 용도와 사용상의 제한

## 권장 사용

자동차 카브렛타 클리너 용

## 1.3. 공급자 정보

회사명 :

한국쓰리엠

## 3. 구성성분의 명칭 및 함유량

이 제품의 물질은 혼합물로 구성

<table>
{"화학물질명": "Light Distillates - Hydrotreated", "관용명": "자료 없음 .", "카스 번호": "64742-47-8", "함유량 (%)": "60 - 70"},
{"화학물질명": "카나우바 왁스", "관용명": "자료 없음 .", "카스 번호": "8015-86-9", "함유량 (%)": "15 - 25"}
<table>

Expected JSON:
{
  "product_name": "3M Choke & Carb Cleaner, 03735",
  "company_name": "한국쓰리엠",
  "ingredients": [
  {"name":"Light Distillates - Hydrotreated","synonym":[],"cas":"64742-47-8","ec_number":null,
   "concentration":{"raw":"60 - 70","value":null,"min":60,"max":70,"unit":"%","basis":null,"op_min":null,"op_max":null},
   "additional_info":{}},
  {"name":"카나우바 왁스","synonym":[],"cas":"8015-86-9","ec_number":null,
   "concentration":{"raw":"15 - 25","value":null,"min":15,"max":25,"unit":"%","basis":null,"op_min":null,"op_max":null},
   "additional_info":{}}
]
}

Example 4:
SECTION 1: Identification

## 1.1. Product identifier

3M™ Printed Squeegee VTS6

## Product Identification Numbers

70-0075-4583-6 7100232701

## 1.2. Recommended use and restrictions on use

## Recommended use

Applying foils, facings, or other tapes

## 1.3. Supplier's details

MANUFACTURER:

3M

DIVISION:

Industrial Specialties Division 3M Center, St. Paul, MN 55144-1000, USA 1-888-3M HELPS (1-888-364-3577)

ADDRESS:

Telephone:

## 1.4. Emergency telephone number

1-800-364-3577 or (651) 737-6501 (24 hours)

SECTION 3: Composition/information on ingredients

{"col_0": "Ingredient", "col_1": "C.A.S. No.", "col_2": "%byWt"},
{"col_0": "Plastic Squeegee", "col_1": "Mixture", "col_2": "100 Trade Secret *"}

__________________________________________________________________________________________

1


*The specific chemical identity and/or exact percentage (concentration) of this composition has been withheld as a trade secret.


Expected JSON:
{
  "product_name": "3M™ Printed Squeegee VTS6",
  "company_name": "3M",
  "ingredients": [
    {
      "name": "Plastic Squeegee",
      "synonym": [],
      "cas": "Mixture",
      "ec_number": null,
      "concentration": {
        "raw": "100 Trade Secret *",
        "value": 100.0,
        "min": null,
        "max": null,
        "unit": "%",
        "basis": "Wt",
        "op_min": null,
        "op_max": null,
        "is_cas_secret": false,
        "is_conc_secret": True
      },
      "additional_info": {}
    }
  ]
}
Example:
## 1. 화학제품과 회사에 관한 정보

## 가. 제품명

## 나. 제품의 권고 용도와 사용상의 제한

제품의 권고 용도

제품의 사용상의 제한

## 다.공급자 정보

회사명

주소

제공서비스 또는 긴급전화번호

담당부서 / 담당자

경기도 평택시 포승읍 포승공단로 118번길 45

원료 및 중간체, 코팅, 페인트, 신너, 페인트 제거제, 점도 조정제, 세정 및 세척제 권고 용도 이외에 사용하지 마십시오.

㈜켐트로닉스

070-4923-0475

환경안전팀 / 유근화

ANONE


## 3. 구성성분의 명칭 및 함유량

화학물질명

관용명 및 이명(異名)

시클로헥사논

Cyclohexanone


CAS번호 또는 식별번호

함유량(%)

108-94-1

100%

Expected JSON:
{
  "product_name": "ANONE",
  "company_name": "㈜켐트로닉스",
  "ingredients": [
    {
      "name": "시클로헥사논",
      "synonym": ["Cyclohexanone"],
      "cas": "108-94-1",
      "ec_number": null,
      "concentration": {
        "raw": "100%",
        "value": 100.0,
        "min": null,
        "max": null,
        "unit": "%",
        "basis": null,
        "op_min": null,
        "op_max": null,
        "is_cas_secret": false,
        "is_conc_secret": True
      },
      "additional_info": {}
    }
  ]
}

Example:
## 1. 화학제품과 회사에 관한 정보

가. 제품명 : 메틸 알코올

나. 제품의 권고 용도와 사용상의 제한

제품의 권고용도 실험용 화학물질(시약), 기타(합성 및 공정약품)

사용상의 제한

제품의 권고 용도 이외에 사용을 금함

다. 공급자 정보

제조자

회사명 : 에스케이케미칼대정주식회사

주소 : 경기도 분당구 판교로 310 (삼평동)

긴급전화번호 : 02-2008-2757

## 3. 구성성분의 명칭 및 함유량

<table>
{"col_0": "구성성분", "col_1": "관용명 및 이명", "col_2": "CAS No.", "col_3": "대표함유율", "col_4": "승인번호", "col_5": "유효기간"},
{"col_0": "Methanol ; Methyl alcohol", "col_1": "메틸알코올", "col_2": "67-56-1", "col_3": "100", "col_4": "", "col_5": ""}
</table>

Expected JSON:

"product_name": "메틸 알코올",
    "company_name": "에스케이케미칼대정주식회사",
    "ingredients": [
      {
        "name": "Methanol ; Methyl alcohol",
        "synonym": [
          "메틸알코올"
        ],
        "cas": "67-56-1",
        "ec_number": null,
        "concentration": {
          "raw": "100",
          "value": 100,
          "min": 100,
          "max": 100,
          "unit": null,
          "basis": null,
          "op_min": null,
          "op_max": null,
          "is_cas_secret": false,
          "is_conc_secret": false
        },
        "additional_info": {}
      }
    ]
  }


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
    schema =   {
    "product_name": "string|null",
    "company_name": "string|null",
    "ingredients": [{
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
        "op_max": "string|null",
        "is_cas_secret": "BOOLEAN DEFAULT FALSE",
        "is_conc_secret":  "BOOLEAN DEFAULT FALSE",
      },
      "additional_info": {}
    }]}
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

def extract_integrated_sds_info(llm_input_text: str):
    prompt = build_prompt_for_sds(llm_input_text)
    txt = ask_ollama(prompt)
    
    # LLM이 단일 JSON 객체 { ... } 를 반환하도록 기대합니다.
    # 배열 매칭 정규식 r"\[\s*\{.*\}\s*\]" 대신 객체 매칭 정규식 r"\{\s*\"HeaderInfo\":.*\}\s*" 등을 사용하거나,
    # 응답 전체가 JSON 객체라고 가정하고 파싱을 시도합니다.
    try:
        # 응답 텍스트가 JSON으로 시작하고 끝나는지 확인 후 파싱 시도
        json_match = re.search(r"\{\s*\"HeaderInfo\":.*\}\s*", txt, re.S) or re.match(r"\s*\{.*\}\s*$", txt, re.S)
        if json_match:
            return json.loads(json_match.group(0))
        
        # 파싱 실패 시 원본 텍스트 전체를 파싱 시도
        return json.loads(txt.strip())
        
    except Exception as e:
        print(f"[ERROR] Failed to parse integrated JSON from LLM response: {e}")
        return None

