# 테스트를 위해 이미지 경로 넣으면 base64로 바꿔주는 코드
import base64
from pathlib import Path


def image_to_base64(image_path: str) -> str:
    """이미지 파일을 base64 문자열로 변환"""
    img_path = Path(image_path)

    if not img_path.exists():
        raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {image_path}")

    # 이미지 파일을 바이너리로 읽기
    with open(img_path, 'rb') as img_file:
        img_data = img_file.read()

    # base64로 인코딩
    base64_str = base64.b64encode(img_data).decode('utf-8')

    return base64_str


if __name__ == "__main__":
    img_path = input("이미지 파일 경로를 입력하세요: ")

    try:
        b64_string = image_to_base64(img_path)
        print("\n=== Base64 인코딩 결과 ===")
        print(b64_string)
        print(f"\n길이: {len(b64_string)} 문자")

        # 결과를 파일로 저장할지 물어보기
        save = input("\nbase64 문자열을 파일로 저장하시겠습니까? (y/n): ")
        if save.lower() == 'y':
            output_file = Path(img_path).stem + "_base64.txt"
            with open(output_file, 'w') as f:
                f.write(b64_string)
            print(f"저장 완료: {output_file}")

    except Exception as e:
        print(f"에러 발생: {e}")