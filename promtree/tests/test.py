import os
from promtree.pdf_to_png import pdf_to_png_high_res
from promtree.structure import detect_layout
from promtree.pdf_to_txt import pdf_to_text
from promtree.order_md import order_and_save_md

target = "44-1206-SDS11757"

pdf_path = target + ".pdf"
outputs_dir = os.path.join(target, "outputs")
layout_path = os.path.join(target, "layouts")
result_path = target

pdf_to_png_high_res(pdf_path, output_dir=outputs_dir, zoom_factor=1.0)

pdf_to_text(pdf_path=pdf_path)

detect_layout(img_dir=outputs_dir, output_dir=layout_path)

order_and_save_md(output_txt_path=os.path.join(result_path, "output.txt"), layout_json_path=os.path.join(layout_path, "results.json"))  
