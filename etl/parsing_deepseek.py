import os
import base64
import logging
from io import BytesIO
from pathlib import Path
from typing import List

import requests
from dotenv import load_dotenv
from pdf2image import convert_from_path
from PIL import Image

# ============================================
# 설정 & 로깅
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

load_dotenv()

DEEPSEEK_OCR_API_KEY = os.getenv("DEEPSEEK_OCR_API_KEY")
DEEPSEEK_OCR_URI = os.getenv("DEEPSEEK_OCR_URI")  # 예시: https://...proxy.runpod.net/
DEEPSEEK_OCR_MODEL = os.getenv("DEEPSEEK_OCR_MODEL", "deepseek-ai/DeepSeek-OCR")
TIMEOUT = int(os.getenv("TIMEOUT", "200"))

MAX_PAGES_PER_PDF = 5  # 각 PDF당 최대 페이지 수

BASE_DIR = Path(__file__).resolve().parent
PDF_INPUT_DIR = BASE_DIR / "pdf2s"
OUTPUT_DIR = BASE_DIR / "output"


# ============================================
# 유틸
# ============================================
def ensure_env():
    if not DEEPSEEK_OCR_API_KEY:
        raise RuntimeError("DEEPSEEK_OCR_API_KEY 환경변수가 없습니다.")
    if not DEEPSEEK_OCR_URI:
        raise RuntimeError("DEEPSEEK_OCR_URI 환경변수가 없습니다.")
    if not DEEPSEEK_OCR_MODEL:
        raise RuntimeError("DEEPSEEK_OCR_MODEL 환경변수가 없습니다.")


def image_to_base64(image: Image.Image, fmt: str = "PNG") -> str:
    """PIL 이미지를 base64 문자열로 변환"""
    buf = BytesIO()
    image.save(buf, format=fmt)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


# ============================================
# DeepSeek-OCR 호출 함수
# ============================================
def call_deepseek_ocr(image: Image.Image) -> str:
    """
    단일 이미지(페이지)를 DeepSeek-OCR 서버(런팟)로 보내서
    마크다운 텍스트를 받아오는 함수.

    ⚠️ 이 코드는 RunPod 서버가 "OpenAI 호환 /v1/chat/completions" 인터페이스를
    사용한다고 가정하고 작성됨. 엔드포인트가 다르면 endpoint 변수만 수정해줘.
    """
    ensure_env()

    img_b64 = image_to_base64(image, fmt="PNG")

    # 엔드포인트: 기본 URI + /v1/chat/completions (필요시 수정)
    endpoint = DEEPSEEK_OCR_URI.rstrip("/") + "/v1/chat/completions"

    payload = {
        "model": DEEPSEEK_OCR_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_b64}"
                        },
                    },
                    {
                        "type": "text",
                        "text": "Convert the document to markdown format with structured output including tables.",
                    },
                ],
            }
        ],
        "temperature": 0.0,
        "max_tokens": 4096,
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_OCR_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.HTTPError as e:
        logging.error(f"API 호출 실패: {e}")
        logging.error(f"응답 내용: {resp.text}")
        raise

    # 응답 구조 파싱 (OpenAI 호환 형식 가정)
    if "choices" in data and data["choices"]:
        choice = data["choices"][0]
        msg = choice.get("message")
        if isinstance(msg, dict):
            content = msg.get("content", "")
            # content가 리스트인 멀티모달 구조일 경우
            if isinstance(content, list):
                texts = [
                    c.get("text", "")
                    for c in content
                    if isinstance(c, dict) and c.get("type") == "text"
                ]
                return "\n".join(texts).strip()
            return str(content).strip()
        # text 기반 completions인 경우
        if "text" in choice:
            return str(choice["text"]).strip()

    # 폴백: 전체 응답을 문자열로 반환
    return str(data)


# ============================================
# PDF -> (앞 n페이지) -> Markdown
# ============================================
def pdf_to_markdown(pdf_path: Path, max_pages: int = MAX_PAGES_PER_PDF) -> str:
    """
    단일 PDF 파일의 앞 max_pages 페이지를 DeepSeek-OCR로 처리하여
    페이지별 마크다운을 합쳐서 하나의 문자열로 반환
    """
    logging.info(f"PDF 변환 시작: {pdf_path.name}")

    # pdf2image로 페이지를 이미지 리스트로 변환
    # dpi는 200 정도가 속도/품질 측면에서 적당 (필요시 300으로 상향 가능)
    try:
        pages: List[Image.Image] = convert_from_path(
            pdf_path,
            dpi=200,
        )
    except Exception as e:
        logging.error(f"PDF -> 이미지 변환 실패: {pdf_path.name}: {e}")
        return ""

    if not pages:
        logging.warning(f"페이지 없음: {pdf_path.name}")
        return ""

    markdown_chunks: List[str] = []
    page_count = min(len(pages), max_pages)

    for idx in range(page_count):
        page_num = idx + 1
        logging.info(f"  - {pdf_path.name} 페이지 {page_num}/{page_count} OCR 호출 중...")

        page_img = pages[idx]
        try:
            md_text = call_deepseek_ocr(page_img)
        except Exception as e:
            logging.error(f"  [오류] {pdf_path.name} p.{page_num} OCR 실패: {e}")
            continue

        # 페이지 구분용 헤더 및 내용
        page_header = f"# Page {page_num}\n\n"
        markdown_chunks.append(page_header + md_text.strip() + "\n\n")

    full_markdown = "\n---\n\n".join(markdown_chunks).strip()
    return full_markdown


# ============================================
# 배치 처리: pdf2s 안의 모든 PDF -> output/*.md
# ============================================
def batch_pdf_to_md(
    input_dir: Path = PDF_INPUT_DIR,
    output_dir: Path = OUTPUT_DIR,
    max_pages: int = MAX_PAGES_PER_PDF,
):
    ensure_env()

    if not input_dir.exists():
        raise FileNotFoundError(f"입력 폴더가 없습니다: {input_dir.resolve()}")

    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(
        [p for p in input_dir.iterdir() if p.suffix.lower() == ".pdf"]
    )

    if not pdf_files:
        logging.info(f"{input_dir} 안에 PDF 파일이 없습니다.")
        return

    logging.info(f"총 {len(pdf_files)}개 PDF 처리 시작")
    logging.info(f"입력 폴더: {input_dir.resolve()}")
    logging.info(f"출력 폴더: {output_dir.resolve()}")
    logging.info(f"PDF당 최대 {max_pages}페이지만 OCR 수행")

    for pdf_path in pdf_files:
        logging.info(f"\n[PROCESS] {pdf_path.name}")
        try:
            md_text = pdf_to_markdown(pdf_path, max_pages=max_pages)
            if not md_text:
                logging.warning(f"[SKIP] {pdf_path.name} → OCR 결과 비어 있음")
                continue

            md_output_path = output_dir / f"{pdf_path.stem}.md"
            md_output_path.write_text(md_text, encoding="utf-8")
            logging.info(f"[DONE] {pdf_path.name} → {md_output_path.name} 저장 완료")

        except Exception as e:
            logging.error(f"[ERROR] {pdf_path.name} 처리 중 오류: {e}")


# ============================================
# CLI
# ============================================
if __name__ == "__main__":
    batch_pdf_to_md()
