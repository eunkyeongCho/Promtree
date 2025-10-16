from typing import Dict, Any, List
import os

# 1. Root Object 생성
def get_root_object(pdf_path: str) -> Dict[str, Any]:
    """
    PDF 파일을 파싱하여 Root Object를 생성하는 함수
    
    Args:
        pdf_path: PDF 파일 경로

    Returns:
        root_object: Root Object
    """
    import pdfplumber

    pdf = pdfplumber.open(pdf_path)

    root_object = {
        "file_name": pdf_path.split("\\")[-1],
        "page_num": 0,
        "page_count": len(pdf.pages),
        "width": pdf.pages[0].width,
        "height": pdf.pages[0].height
    }

    pdf.close()
    # print("PDF file closed successfully!!")

    return root_object


# 2. 이미지 전처리
def image_preprocessing(image: Dict[str, Any], url: str) -> Dict[str, Any]:
    """
    Image Object의 Stream을 제거하고 URL을 추가 & colorspace와 tuple 형식을 수정

    Args:
        image: Image Object
        url: 이미지 저장 경로

    Returns:
        image: Preprocessed Image Object
    """
    import pdfplumber

    stream_value = image['stream']

    save_images(stream_value, url)

    del image['stream']
    image['url'] = url

    if "colorspace" in image:
        image["colorspace"] = [str(cs).lstrip("/") for cs in image["colorspace"]]

    if isinstance(image.get("srcsize"), tuple):
        image["srcsize"] = list(image["srcsize"])
    
    return image


# 3. 이미지 저장
def save_images(stream_value: Any, url: str):
    """
    Stream 값으로 이미지를 지정한 url에 저장하는 함수

    Args:
        stream_value: Stream 값
        url: 이미지 저장 경로
    """

    from PIL import Image
    from io import BytesIO
    
    img_data = stream_value.get_data()
    img_info = stream_value.attrs
    img_width = int(img_info['Width'])
    img_height = int(img_info['Height'])
    img_bits = int(img_info['BitsPerComponent'])
    img_colorspace = str(img_info['ColorSpace']).lstrip('/').upper()

    # print(img_colorspace)

    img_filter_raw = img_info.get('Filter')
    img_filters = (
        [] if img_filter_raw is None
        else ([str(x).lstrip('/').strip(" '\"").upper() for x in img_filter_raw]
            if isinstance(img_filter_raw, (list, tuple))
            else [str(img_filter_raw).lstrip('/').strip(" '\"").upper()])
    )
    has_jpeg_like = any(f in ('DCTDECODE', 'JPXDECODE') for f in img_filters)

    # 이미지 모드 설정
    if img_colorspace in ('RGB', 'DEVICERGB'):
        img_mode = 'RGB'
    elif img_colorspace in ('GRAY', 'DEVICEGRAY'):
        img_mode = '1' if img_bits == 1 else 'L'
    elif img_colorspace in ('CMYK', 'DEVICECMYK'):
        img_mode = 'CMYK'
    else:
        img_mode = 'RGB'
        
    img_size = (img_width, img_height)

    # filter별 이미지 처리
    if has_jpeg_like:
        # print("jpeg 이미지 발견\n")
        try:
            pil_image = Image.open(BytesIO(img_data))
            pil_image = pil_image.convert('RGB')
            pil_image.save(url)
            
            # print("이미지 저장 완료\n")

        except Exception as e:
            print(f"이미지 저장 오류: {e}")

    else:
        # print("그 외 이미지 발견\n")
        try:
            pil_image = Image.frombytes(img_mode, img_size, img_data)
            pil_image = pil_image.convert('RGB')
            pil_image.save(url)
            
            # print("이미지 저장 완료\n")

        except Exception as e:
            print(f"이미지 저장 오류: {e}")
            


# 4. Page Object 생성
def get_page_objects(pdf_path:str, storage_path:str) -> List[Dict[str, Any]]:
    """
    PDF 파일을 파싱하여 Page Object를 생성하는 함수

    Args:
        pdf_path: PDF 파일 경로

    Returns:
        page_objects: Page Object List
    """
    import pdfplumber

    pdf = pdfplumber.open(pdf_path)

    file_name = pdf_path.split("\\")[-1]

    page_objects = []

    for page_idx in range(len(pdf.pages)):
        page = pdf.pages[page_idx]

        keys = list(page.objects.keys())

        if "image" in keys:
            img_objects = []

            for img_idx, image in enumerate(page.images):
                dir_path = f"{storage_path}/{file_name}"
                os.makedirs(dir_path, exist_ok=True)
                url = f"{dir_path}/page{page_idx+1}_img{img_idx+1}.png"
                img_object = image_preprocessing(image, url)
                img_objects.append(img_object)

        page_object = {
            "file_name": file_name,
            "page_num": page_idx + 1,
            "keys": keys,
            **({"lines": page.lines} if "line" in keys else {}),
            **({"rects": page.rects} if "rect" in keys else {}),
            **({"chars": page.chars} if "char" in keys else {}),
            **({"curves": page.curves} if "curve" in keys else {}),
            **({"images": img_objects} if "image" in keys else {})
        }

        page_objects.append(page_object)
    
    pdf.close()
    # print("PDF file closed successfully!!")
    
    return page_objects


if __name__ == "__main__":

    # 단일 파일 테스트
    import os
    pdf_path = "../gpt-020-3m-sds.pdf"
    storage_path = "storage"
    os.makedirs(storage_path, exist_ok=True)

    root_object = get_root_object(pdf_path)
    print(root_object.keys())
    print("--------------------------------")
    page_objects = get_page_objects(pdf_path, storage_path)
    for page_object in page_objects:
        print(page_object.keys())
        print("--------------------------------")