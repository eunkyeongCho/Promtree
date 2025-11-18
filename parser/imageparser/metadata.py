import os
from dotenv import load_dotenv
import requests


# 환경변수 read 줄이기 위해 class 방식으로 구현
load_dotenv()

class VLLMMetadataExtractor:
    def __init__(self, vllm_uri=None, auth_key=None, model_name=None):
        """초기화 시점에 설정 검증"""
        self.vllm_uri = os.getenv("RUNPOD_VLLM_URI")
        self.auth_key = os.getenv("AUTH_KEY")
        self.model_name = os.getenv("RUNPOD_VLLM_MODEL", "Qwen/Qwen3-VL-4B-Instruct-FP8")
        self.prompt = self._build_metadata_prompt()
        
        # 초기화 시점에 검증
        self._validate_config()
        
    
    def _validate_config(self):
        """설정 검증"""
        if not self.vllm_uri:
            raise ValueError("RUNPOD_VLLM_URI가 설정되지 않았습니다.")
        if not self.auth_key:
            raise ValueError("AUTH_KEY가 설정되지 않았습니다.")
    

    @staticmethod
    def _build_metadata_prompt() -> str:
        """메타데이터 추출을 위한 프롬프트 생성"""
        prompt = """이미지를 분석하고 한국어로 자연스러운 문장으로 설명하세요.

        **중요: 이미지 유형에 따른 설명 방식**

        1. **간단 처리 대상 (한 문장으로만 끝내기):**
        - 로고: "해당 이미지는 [회사명]의 로고입니다."
        - 제품명/브랜드명: "해당 이미지는 [제품명/브랜드명]입니다."
        - 슬로건: "해당 이미지는 '[슬로건 내용]'이라는 슬로건입니다."
        - QR코드: "해당 이미지는 QR코드입니다."
        - 제품 사진: "해당 이미지는 [제품명]의 제품 사진입니다."
        - 단색 배경/빈 이미지: "해당 이미지는 [색상]의 단색 배경입니다." 또는 "해당 이미지는 빈 이미지입니다."
        - 장식용 이미지/구분선: "해당 이미지는 장식용 요소입니다."
        
        **위 항목들은 색상, 디자인, 부가 설명, 키워드 등 일체 추가하지 마세요.**

        2. **상세 설명 대상 (데이터 중심 이미지):**

        **그래프/차트:**
        - 제목이 있다면 먼저 밝히세요
        - 그래프 종류를 설명하세요 (막대그래프, 선그래프, 원그래프 등)
        - X축과 Y축이 무엇을 나타내는지 설명하세요
        - 각 데이터 계열의 이름과 구체적인 수치값들을 모두 서술하세요
        - 범례가 있다면 각 항목의 의미를 설명하세요
        - 전체적인 트렌드나 패턴을 언급하세요
        - 검색에 유용한 키워드를 자연스럽게 포함하세요

        **표:**
        - 표의 제목이 있다면 먼저 밝히세요
        - 표의 주제를 설명하세요
        - 각 열과 행의 헤더를 밝히세요
        - 표에 담긴 모든 데이터 값들을 빠짐없이 서술하세요
        - 단위가 있다면 함께 명시하세요
        - 검색에 유용한 키워드를 자연스럽게 포함하세요

        **다이어그램:**
        - 제목이나 주제가 있다면 먼저 밝히세요
        - 다이어그램의 종류와 목적을 설명하세요
        - 각 구성요소들이 무엇을 나타내는지 서술하세요
        - 요소들 간의 연결이나 흐름을 자세히 설명하세요
        - 검색에 유용한 키워드를 자연스럽게 포함하세요

        **기타 사진/이미지:**
        - 캡션이나 제목이 있다면 먼저 밝히세요
        - 사진이 무엇을 보여주는지 설명하세요
        - 어떤 개념이나 현상을 설명하는지 서술하세요
        - 보이는 텍스트나 라벨을 언급하세요
        - 검색에 유용한 키워드를 자연스럽게 포함하세요

        **설명 원칙:**
        - 완전한 문장으로 서술하세요
        - "단어, 단어, 단어" 나열 형식은 피하세요
        - 마치 누군가에게 이미지를 설명하듯이 자연스럽게 작성하세요
        - 데이터가 포함된 이미지는 모든 수치와 라벨을 문장 안에 녹여서 서술하세요"""

        return prompt
        
    def extract(self, b64_str: str) -> str:
        """메타데이터 추출 (논스트리밍 모드)"""
        api_url = f"{self.vllm_uri.rstrip('/')}/v1/chat/completions"
        image_data_uri = f"data:image/png;base64,{b64_str}"

        messages = [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": "답변만 자연스럽게 출력하세요. 생각 과정은 숨기세요."
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": self.prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data_uri
                        }
                    }
                ]
            }
        ]

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 1200,
            "stream": False
        }

        headers = {
            "Authorization": f"Bearer {self.auth_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=180)
            response.raise_for_status()
            result = response.json()

            # 응답에서 content 추출 (간소화)
            choices = result.get("choices", [])
            if not choices:
                raise ValueError("API 응답에 choices가 없습니다.")

            content = choices[0].get("message", {}).get("content", "")

            if not content:
                raise ValueError("API 응답 content가 비어있습니다.")

            return content

        except requests.exceptions.RequestException as e:
            print(f"RunPod vLLM API 호출 오류: {e}")
            if hasattr(e, "response") and e.response is not None:
                print(f"응답 내용: {e.response.text}")
            raise


# class 안 쓴 편의 함수
def extract_image_metadata(b64_str: str) -> str:
    """
    편의 함수: 이미지 base64로부터 메타데이터 추출

    Args:
        b64_str: base64 인코딩된 이미지 문자열

    Returns:
        str: 추출된 메타데이터 (한국어 설명)

    Example:
        >>> metadata = extract_image_metadata(base64_image)
        >>> print(metadata)
    """
    vllm_uri = os.getenv("RUNPOD_VLLM_URI")
    auth_key = os.getenv("AUTH_KEY")
    model_name = os.getenv("RUNPOD_VLLM_MODEL", "Qwen/Qwen3-VL-4B-Instruct-FP8")
    prompt = """이미지를 분석하고 한국어로 자연스러운 문장으로 설명하세요.

        **중요: 이미지 유형에 따른 설명 방식**

        1. **간단 처리 대상 (한 문장으로만 끝내기):**
        - 로고: "해당 이미지는 [회사명]의 로고입니다."
        - 제품명/브랜드명: "해당 이미지는 [제품명/브랜드명]입니다."
        - 슬로건: "해당 이미지는 '[슬로건 내용]'이라는 슬로건입니다."
        - QR코드: "해당 이미지는 QR코드입니다."
        - 제품 사진: "해당 이미지는 [제품명]의 제품 사진입니다."
        - 단색 배경/빈 이미지: "해당 이미지는 [색상]의 단색 배경입니다." 또는 "해당 이미지는 빈 이미지입니다."
        - 장식용 이미지/구분선: "해당 이미지는 장식용 요소입니다."
        
        **위 항목들은 색상, 디자인, 부가 설명, 키워드 등 일체 추가하지 마세요.**

        2. **상세 설명 대상 (데이터 중심 이미지):**

        **그래프/차트:**
        - 제목이 있다면 먼저 밝히세요
        - 그래프 종류를 설명하세요 (막대그래프, 선그래프, 원그래프 등)
        - X축과 Y축이 무엇을 나타내는지 설명하세요
        - 각 데이터 계열의 이름과 구체적인 수치값들을 모두 서술하세요
        - 범례가 있다면 각 항목의 의미를 설명하세요
        - 전체적인 트렌드나 패턴을 언급하세요
        - 검색에 유용한 키워드를 자연스럽게 포함하세요

        **표:**
        - 표의 제목이 있다면 먼저 밝히세요
        - 표의 주제를 설명하세요
        - 각 열과 행의 헤더를 밝히세요
        - 표에 담긴 모든 데이터 값들을 빠짐없이 서술하세요
        - 단위가 있다면 함께 명시하세요
        - 검색에 유용한 키워드를 자연스럽게 포함하세요

        **다이어그램:**
        - 제목이나 주제가 있다면 먼저 밝히세요
        - 다이어그램의 종류와 목적을 설명하세요
        - 각 구성요소들이 무엇을 나타내는지 서술하세요
        - 요소들 간의 연결이나 흐름을 자세히 설명하세요
        - 검색에 유용한 키워드를 자연스럽게 포함하세요

        **기타 사진/이미지:**
        - 캡션이나 제목이 있다면 먼저 밝히세요
        - 사진이 무엇을 보여주는지 설명하세요
        - 어떤 개념이나 현상을 설명하는지 서술하세요
        - 보이는 텍스트나 라벨을 언급하세요
        - 검색에 유용한 키워드를 자연스럽게 포함하세요

        **설명 원칙:**
        - 완전한 문장으로 서술하세요
        - "단어, 단어, 단어" 나열 형식은 피하세요
        - 마치 누군가에게 이미지를 설명하듯이 자연스럽게 작성하세요
        - 데이터가 포함된 이미지는 모든 수치와 라벨을 문장 안에 녹여서 서술하세요"""

    api_url = f"{vllm_uri.rstrip('/')}/v1/chat/completions"
    image_data_uri = f"data:image/png;base64,{b64_str}"

    messages = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": "답변만 자연스럽게 출력하세요. 생각 과정은 숨기세요."
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_data_uri
                    }
                }
            ]
        }
    ]

    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 1200,
        "stream": False
    }

    headers = {
        "Authorization": f"Bearer {auth_key}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=180)
        response.raise_for_status()
        result = response.json()

        # 응답에서 content 추출 (간소화)
        choices = result.get("choices", [])
        if not choices:
            raise ValueError("API 응답에 choices가 없습니다.")

        content = choices[0].get("message", {}).get("content", "")

        if not content:
            raise ValueError("API 응답 content가 비어있습니다.")

        return content

    except requests.exceptions.RequestException as e:
        print(f"RunPod vLLM API 호출 오류: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"응답 내용: {e.response.text}")
        raise




if __name__ == "__main__":
    # input.txt 파일에서 base64 문자열 읽기
    input_file = os.path.join(os.path.dirname(__file__), "input.txt")

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            b64 = f.read().strip()
        print(f"input.txt에서 base64 문자열을 읽었습니다. (길이: {len(b64)})")
    except FileNotFoundError:
        print("input.txt 파일을 찾을 수 없습니다. 직접 입력하세요.")
        b64 = input("이미지 base64를 입력하세요:")

    # class 사용
    extractor = VLLMMetadataExtractor()
    answer = extractor.extract(b64)

    # 편의 함수 사용
    result = extract_image_metadata(b64)
    print('class 사용 answer:\n', answer)
    print('\n편의 함수 사용 answers\n', result)