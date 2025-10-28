import pymupdf
import os

def pdf_to_png_high_res(pdf_path, output_dir="outputs", zoom_factor=2.0):

    os.makedirs(output_dir, exist_ok=True)
    doc = pymupdf.open(pdf_path)
    mat = pymupdf.Matrix(zoom_factor, zoom_factor) 

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        
        pix = page.get_pixmap(matrix=mat) 

        output_filename = f"{output_dir}/page_{page_num}.png"
        pix.save(output_filename)
    
    # 이미지 추출 및 저장 완료
    print("PDF to PNG 변환 완료.")

if __name__ == "__main__":
    pdf_path = "sample.pdf"
    pdf_to_png_high_res(pdf_path, zoom_factor=1.0)