from pathlib import Path
import pymupdf
import os

def pdf_to_text(pdf_path: str, output_path: str = None) -> None:
    
    # 파일명
    pdf_stem = os.path.splitext(os.path.basename(pdf_path))[0]
    
    # 기본 output_path 경로 지정 (현위치)
    if output_path is None:
        output_path = os.path.join(os.getcwd(), pdf_stem)
        os.makedirs(output_path, exist_ok=True)
    
    # 결과물 저장할 경로 세팅
    # 이미지 저장할 폴더
    img_output_dir = os.path.join(output_path, "images")
    os.makedirs(img_output_dir, exist_ok=True)
    # 텍스트 저장할 파일
    txt_output = os.path.join(output_path, "output.txt")
    
    # PDF Open
    doc = pymupdf.open(pdf_path)

    doc_element = []

    # 페이지별 탐색
    for page_num in range(len(doc)):
        doc_element.append(f">>> page {page_num}")

        # 페이지 내 블록 탐색
        blocks = doc[page_num].get_text("dict")["blocks"]

        for block in blocks:
            btype = block["type"]

            if btype == 0: # 텍스트
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        doc_element.append((*span['bbox'], span['text']))

            elif btype == 1: # 이미지
                img_name = f"page{page_num}_{block['number']}.{block['ext']}"
                url = os.path.join(img_output_dir, img_name)

                with open(url, 'wb') as img_file:
                    img_file.write(block['image'])

                doc_element.append((*block['bbox'], f"![](./images/{img_name})"))

            else:
                raise TypeError(f"Unsupported block type: {btype}")

        doc_element.append(">>> pend")

    print("PDF의 ELEMENT 추출 완료.")

    with open(txt_output, 'w', encoding='utf-8') as txt_file:
        for element in doc_element:
            if element[:4] == ">>>":
                txt_file.write(f"{element}")
            else:
                txt_file.write(f"{element}")
            txt_file.write("\n")

    print("텍스트로 저장 완료.")