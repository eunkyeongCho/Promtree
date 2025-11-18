import os
from .pdf_to_png import pdf_to_png_high_res
from .structure import detect_layout
from .pdf_to_txt import pdf_to_text
from .order_md import order_and_save_md


def PromTree(pdf_path, output_md: str = None, cleanup: bool = False) -> None:

    """
    PDF를 입력받아 마크다운을 생성하는 함수.

    Args:
        pdf_path (str): 입력 PDF 파일 경로.
        output_md (str, optional): 출력 마크다운 파일 경로. 기본값은 None이며, 이 경우 PDF 파일명과 동일한 디렉토리에 저장됨.
        cleanup (bool, optional): 중간 생성된 파일들을 삭제할지 여부. 기본값은 False.
    Returns:
        None
    """

    pdf_stem = os.path.splitext(os.path.basename(pdf_path))[0]
    output_dir = os.path.join(pdf_stem, "outputs")
    layout_dir = os.path.join(pdf_stem, "layouts")
    result_path = pdf_stem

    
    pdf_to_png_high_res(pdf_path, output_dir=output_dir, zoom_factor=1.0)

    pdf_to_text(pdf_path=pdf_path)

    detect_layout(img_dir=output_dir, output_dir=layout_dir)

    order_and_save_md(output_txt_path=os.path.join(result_path, "output.txt"), layout_json_path=os.path.join(layout_dir, "results.json"), save_md_path=output_md)

    if cleanup:
        import shutil
        shutil.rmtree(output_dir)
        shutil.rmtree(layout_dir)
        os.remove(os.path.join(result_path, "output.txt"))
