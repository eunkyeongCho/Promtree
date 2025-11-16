# base64로 된 이미지를 PIL로 이미지로 바꾸어 qwen3-vl로 메타데이터 뽑기.
import base64
import io
from PIL import Image
import os
import torch
from transformers import AutoModelForImageTextToText, AutoProcessor


def b64_2_img(b64_str: str) -> Image.Image:
    """Base64 문자열을 PIL Image로 변환"""
    # base64 문자열 디코딩
    img_data = base64.b64decode(b64_str)
    # 바이트 데이터를 이미지로 변환
    img = Image.open(io.BytesIO(img_data))
    return img


def load_model_and_processor():
    """Qwen2-VL-2B 모델과 프로세서 로드"""
    model_name = "Qwen/Qwen2-VL-2B-Instruct"

    # 프로세서 로드
    processor = AutoProcessor.from_pretrained(
        model_name,
        trust_remote_code=True
    )

    # 모델 로드
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = AutoModelForImageTextToText.from_pretrained(
        model_name,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map="auto" if device == "cuda" else None,
        trust_remote_code=True
    )

    if device == "cpu":
        model = model.to(device)
        print("cpu사용")

    return model, processor

def extract_metadata_from_img(b64_str: str, model, processor) -> str:
    """이미지에서 메타데이터 추출"""
    img = b64_2_img(b64_str)
    prompt = build_metadata_prompt()

    # Qwen2-VL 형식의 메시지 구성
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": img},
                {"type": "text", "text": prompt}
            ]
        }
    ]

    # 프로세서로 입력 준비
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = processor(
        text=[text],
        images=[img],
        return_tensors="pt",
        padding=True
    )

    # 모델이 있는 디바이스로 입력 이동
    device = next(model.parameters()).device
    inputs = {k: v.to(device) for k, v in inputs.items()}

    # 생성
    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=300,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            repetition_penalty=1.2
        )

    # 디코딩
    generated_ids = [
        output_ids[len(input_ids):]
        for input_ids, output_ids in zip(inputs["input_ids"], output_ids)
    ]
    metadata = processor.batch_decode(
        generated_ids,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False
    )[0]

    return metadata


def build_metadata_prompt():
    """메타데이터 추출을 위한 프롬프트 생성"""
    prompt = """이 이미지의 모든 데이터를 빠짐없이 추출하여 한국어로 설명하세요.
다음 내용을 포함해서 설명하세요:
- 이미지 종류 (그래프/표/제품사진/다이어그램/로고 등)
- 이미지에 보이는 모든 텍스트와 숫자
- 주요 내용과 데이터
- 검색에 유용한 키워드

자연스러운 문장으로 상세하게 설명해주세요."""

    return prompt




if __name__ == "__main__":
    b64 = input("이미지 base64를 입력하세요:")
    model, processor = load_model_and_processor()
    meta = extract_metadata_from_img(b64, model, processor)
    print(meta)