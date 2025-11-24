import requests
import json
import re
from typing import List, Dict

def get_key_section_headers_with_llm(
    sections: List[Dict], 
    model: str = "gpt-oss:20b",
    ollama_url: str = "https://bcb7tjvf0wm6jb-11434.proxy.runpod.net/api/generate",
    temperature: float = 0.0,
    timeout: int = 120
) -> Dict[str, str]:
    """
    LLM에게 헤더 구조를 보내 '기본 정보'와 '구성 성분' 섹션의 제목을 물어봅니다.
    """
    print("\n2단계: LLM에게 헤더 구조를 바탕으로 핵심 섹션의 제목을 물어봅니다...")

    # LLM에게 전달할 헤더 목록 텍스트 생성
    # 너무 많은 정보를 주면 오히려 혼란스러워하므로, 헤딩과 레벨만 간결하게 전달합니다.
    header_list_str = "\n".join([f"- Level {s['level']}: {s['heading']}" for s in sections if s.get('heading')])

    # 가장 중요한 프롬프트 설계
    prompt = f"""
You are an expert analyst specializing in the structure of Safety Data Sheets (SDS).
Your task is to identify the exact titles of two key sections from the provided list of headers.

The two key sections are:
1.  **Identification Section**: Contains basic product and company information.
2.  **Composition Section**: Contains information about the chemical composition and ingredients.

Based on the following list of markdown headers, find the most appropriate header for each key section.

[Header List]
{header_list_str}

Provide the answer ONLY in the following JSON format. Do not add any other text or explanation.

{{
  "identification_header": "The exact title of the 'Identification Section'",
  "composition_header": "The exact title of the 'Composition Section'"
}}
"""

    print(f"  - 모델: {model}")
    print(f"  - 대상 URL: {ollama_url}")
    print("  - LLM에 프롬프트를 전송하고 응답을 기다립니다...")

    try:
        # API 호출
        response = requests.post(
            ollama_url,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature}
            },
            timeout=timeout
        )
        response.raise_for_status()  # HTTP 오류가 발생하면 예외를 발생시킴

        # 응답 파싱
        response_data = response.json()
        
        # LLM 응답에서 순수 JSON 부분만 추출 (가장 중요)
        # LLM은 종종 JSON 앞뒤에 `````` 같은 마크다운이나 다른 설명을 붙이는 경향이 있습니다.
        json_str = response_data.get('response', '{}')
        
        # 정규식을 사용하여 `````` 블록 안의 내용만 정확히 추출
        match = re.search(r'\{.*\}', json_str, re.DOTALL)
        if match:
            clean_json_str = match.group(0)
            parsed_json = json.loads(clean_json_str)
            print("  - LLM 응답 (JSON 파싱 성공):", parsed_json)
            return parsed_json
        else:
            print("[ERROR] LLM 응답에서 유효한 JSON 객체를 찾지 못했습니다.")
            print("  - 원본 응답:", json_str)
            return {}

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] LLM API 호출 중 오류가 발생했습니다: {e}")
        return {}
    except json.JSONDecodeError as e:
        print(f"[ERROR] LLM 응답을 JSON으로 파싱하는 중 오류가 발생했습니다: {e}")
        print("  - 파싱 시도 내용:", response_data.get('response', ''))
        return {}