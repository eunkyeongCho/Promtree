# Layout Test

## Test Model List
1. PaddlePaddle/PP-DocLayout-L
2. datalab-to/marker_benchmark
3. datalab-to/surya_layout0
4. https://layout-parser.github.io/

## Test Method
PDF -> Image -> Model -> Layout Object & Image Boxing


# PromTree.Parser

**변경 가능한 요소**
1. layout 모델 변경 가능
2. router 변경 가능
3. parser 변경 가능

**고정 요소**
1. MongoDB
    - Database  : promtree
    - Collection: pdfs 
2. Objects
    Structure
    - Root      {"type", "file_name", "page_count", "file_url"}
    - Page      {"type", "file_name", "page_num", "layout_count"}
    - Layout    {"type", "file_name", "page_num", "layout_num", "range"}
    - Text      {"type", "file_name", "page_num", "layout_num", "context"}
    - Image     {"type", "file_name", "page_num", "layout_num", "image_url"}
    - Table     {"type", "file_name", "page_num", "layout_num", "context", "unpivot_context"}

**사용 흐름**

pt = PromTree()
pp = pt.parsing_pipeline()
img -> pp.set_layout("") -> Layout Object List [{type, file_name, page_num, layout_num, range}, ...]
img, Layout -> pp.set_router("") -> Text or Image or Table
pdf, Layout -> pp.set_text_parser("") -> 
pp.set_img_parser("")
pp.set_tb_parser("")

1. pdf -> img
2. img를 활용해 layout 분리 -> layout object list
3. pdf, img, layout을 자유롭게 사용해서 routing
4. pdf, img, layout을 자유롭게 사용해서 parsing


| Storage |
/pdfs
- ex1.pdf
- ex2.pdf

/imgs
- /ex1
- - pg1.jpeg
- - pg2.jpeg
- /ex2
- - pg1.jpeg
- - pg2.jpeg

| MongoDB |
promtree
- pdfs
- - {"type": "Layout", "file_name": "ex1.pdf", "page_num": "1", "layout_num":"1", "range": [1.0, 3.0, 1.0, 3.0]}