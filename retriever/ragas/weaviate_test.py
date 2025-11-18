from retriever.chunker.markdown_chunker import MarkdownChunker
from sentence_transformers import SentenceTransformer

from pathlib import Path
from dotenv import load_dotenv
import os
import requests

from retriever.vector_store.weaviate_vector_store import WeaviateVectorStore

class WeaviateTest:
    BASE_DIR = Path(__file__).resolve().parents[2]  # root 경로
    load_dotenv(BASE_DIR / "common" / ".env")
    markdown_sample_data_folder_path = BASE_DIR / "retriever" / "markdown_sample_data" # markdown 샘플 데이터 경로

    def __init__(self):
        pass

    def test_weaviate(self):
        for markdown_file_path in self.markdown_sample_data_folder_path.rglob("*.md"): # md 파일만 순회돌기
            with open(markdown_file_path, "r", encoding="utf-8") as f:  # 파일로부터 md 문자열을 읽어옵니다.
                md = f.read()

                markdown_chunker = MarkdownChunker()
                chunks = markdown_chunker.chunk_markdown_file(md, "5bc0c676-018f-46de-bb0d-0103ff9c388c", "5bc0c676-018f-46de-bb0d-0103ff9c388c_3M-1509-DC-Polyethylene-Tape-TIS-Jun13", ["msds"]) # 임의로 하드코딩 했으므로 모든 샘플 파일의 file_info의 키 중 file_uuid, file_name, collections 값이 동일하게 청크가 만들어집니다.

                # Weaviate 벡터 저장
                weaviate = WeaviateVectorStore(os.getenv("WEAVIATE_CLOUD_CLUSTER_URL"), api_key=os.getenv("WEAVIATE_CLOUD_API_KEY"))
                weaviate.add_documents(chunks)

                # Weaviate 벡터 검색
                query = "아세톤의 권고 용도는?"
                vector_results = weaviate.similarity_search(query)

                # 답변생성
                prompt = f"""
                당신은 삼성전자 생산기술연구소의 소재 물성 문서 기반으로 근거 중심의 정확한 답변을 생성하는 전문 어시스턴트입니다.
                당신의 모든 답변은 아래 제공된 문서(JSON 형태)의 내용만을 기반으로 해야 합니다. 
                추론을 할 때도 반드시 문서의 내용을 근거로 해야 하며, 문서에 없는 내용은 절대 추측하지 말고 모르면 모른다고 하세요.

                -----------------------------
                [사용자 질문]
                {query}

                [벡터 검색 결과]
                아래 JSON 배열의 각 요소는 벡터 검색된 문서 조각(chunk)입니다.
                각 chunk는 다음 값을 포함합니다:
                - type: text/table/image/link 등 문서 유형
                - content: imgae의 경로 | link의 원본링크 | List[dict[str, str]] 형태로 언피봇된 html table의 내용 | text의 내용
                - metadata: image의 메타데이터 | link의 메타데이터 | None
                - file_info: {{
                    "file_uuid" : "백엔드에서 넘어오는 Doc ID",
                    "file_name" : "파일 이름",
                    "collections" : ["collection 이름1", "collection 이름2", ...],
                    "page_num" : 페이지 번호 정수 배열
                }}

                [벡터 검색 결과]
                {vector_results}

                -----------------------------
                [지침]

                1. 반드시 문서(JSON) 속 text 내용을 기반으로만 답변하세요.
                2. 답변에는 다음 두 가지를 반드시 포함해야 합니다:
                (A) 질문에 대한 명확한 답변
                (B) 답변에 사용된 근거의 출처 (file_uuid(파일 고유 UUID), file_name(파일명), page_num(페이지 번호))
                3. 여러 문서를 참조했다면 출처를 모두 표기하세요.
                4. 문서에 없는 정보는 "문서에 해당 정보가 없습니다."라고 답하세요. 이때에는 file_info에 대한 내용을 비워두세요.
                5. JSON 안의 구조(key 이름)는 절대 변경하지 말고 그대로 사용하세요.
                6. image / link 타입 chunk는 metadata를 요약해 텍스트처럼 다뤄도 됩니다.

                -----------------------------
                [출력 형식]
                다음 형식으로만 답변하세요:

                {{
                    "answer" : "답변",
                    "file_info" : {{
                        "file_uuid" : "백엔드에서 넘어오는 Doc ID",
                        "file_name" : "파일 이름",
                        "page_num" : 페이지 번호 정수 배열
                    }}
                }}
                """

                print("🔍 보낼 프롬프트: \n", prompt)

                RUNPOD_URI = os.getenv("RUNPOD_URI")
                RUNPOD_LLM_MODEL = os.getenv("RUNPOD_LLM_MODEL")
                TIMEOUT = os.getenv("TIMEOUT")

                # 답변 요청
                url = f"{RUNPOD_URI}/api/generate"
                payload = {"model": RUNPOD_LLM_MODEL, "prompt": prompt, "stream": False}
                timeout = float(TIMEOUT) if TIMEOUT else None
                response = requests.post(url, json=payload, timeout=timeout)

                try:
                    response.raise_for_status()
                except requests.RequestException as e:
                    print(f"❌ HTTP request failed: {e}")

                print(f"🔍 답변 생성결과: {response.json()['response']}")

                return response.json()['response']


if __name__ == "__main__":
    weaviate_test = WeaviateTest()
    weaviate_test.test_weaviate()