from typing import Dict, Any, List, Tuple
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

    del image['stream']
    image['url'] = url

    if "colorspace" in image:
        image["colorspace"] = [str(cs).lstrip("/") for cs in image["colorspace"]]

    if isinstance(image.get("srcsize"), tuple):
        image["srcsize"] = list(image["srcsize"])
    
    return image


# 3-1. 이미지 저장(/XObject 의 경우)
def save_images_with_xref(doc: Any, img_xref: int, url: str) -> None:
    """
    xref 값으로 이미지를 지정한 url에 저장하는 함수

    Args:
        doc: MuPDF 문서 객체
        img_xref: 이미지 xref 값
        url: 이미지 저장 경로
    
    Returns:
        None
    """
    import fitz

    pix = None

    try:
        # xref로 Pixmap 생성
        pix = fitz.Pixmap(doc, img_xref)

        # Alpha 포함 또는 CMYK 등 RGB가 아닌 경우 RGB로 변환
        if (pix.n - (1 if pix.alpha else 0)) >= 4 or pix.alpha:
            rgb_pix = fitz.Pixmap(fitz.csRGB, pix)
            pix.close()
            pix = rgb_pix

        pix.save(url)  # 확장자가 .png면 PNG로 저장

    except Exception as e:
        print("xref 값에 따른 이미지 저장 오류")
        print(f"이미지 저장 오류: {e}")
    finally:
        if pix is not None:
            pix = None


# 3-2. 인라인 이미지 저장
def save_inline_image(doc: Any, page_idx: int, bbox: Tuple[float, float, float, float], url: str, zoom: float = 3.0) -> None:
    """
    인라인 이미지를 지정한 url에 저장하는 함수

    Args:
        doc: MuPDF 문서 객체
        page_idx: 페이지 번호
        bbox: 이미지 박스 좌표
        url: 이미지 저장 경로
        zoom: 렌더링 해상도(배율. 웹/문서 표시 권장 3.0)

    Returns:
        None
    """
    import fitz

    pix = None

    try:
        page = doc.load_page(page_idx)
        clip = fitz.Rect(*bbox)
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix = mat, clip = clip, alpha =False)
        pix.save(url)

    except Exception as e:
        print("인라인 이미지 저장 오류")
        print(f"이미지 저장 오류: {e}")
    finally:
        if pix is not None:
            pix = None


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
    import fitz

    pdf = pdfplumber.open(pdf_path)
    mupdf = fitz.open(pdf_path)

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

                # 이미지 저장을 위해 xref 값 추출
                stream = image.get("stream")
                xref = getattr(stream, "objid", None)

                # xref 값에 따른 저장 방식 분기
                if xref is not None:
                    save_images_with_xref(mupdf, xref, url) 
                else:
                    bbox = (image["x0"], image["y0"], image["x1"], image["y1"])
                    save_inline_image(mupdf, page_idx, bbox, url)
                    
                # 이미지 전처리
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
    mupdf.close()
    # print("PDF file closed successfully!!")
    
    return page_objects


if __name__ == "__main__":

    # 단일 파일 테스트
    import os
    pdf_path = "./pdfs/000000001112_US_EN.pdf"
    storage_path = "storage"
    os.makedirs(storage_path, exist_ok=True)

    root_object = get_root_object(pdf_path)
    print(root_object.keys())
    print("--------------------------------")
    page_objects = get_page_objects(pdf_path, storage_path)
    for page_object in page_objects:
        print(page_object.keys())
        print("--------------------------------")