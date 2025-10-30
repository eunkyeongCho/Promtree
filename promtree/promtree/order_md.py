import ast


def get_output_txt(output_txt_path):
    txt_contents = {}
    with open(output_txt_path, 'r', encoding='utf-8') as f:
        key = None
        for line in f:
            stripped_line = line.strip()
            if stripped_line.startswith(">>>"):
                key = stripped_line[4:].strip().replace(" ", "_").lower()
                txt_contents[key] = []
            else:
                preprocessed_line = list(ast.literal_eval(stripped_line))
                txt_contents[key].append(preprocessed_line)
    return txt_contents

def get_layout_json(layout_json_path):
    import json
    with open(layout_json_path, 'r', encoding='utf-8') as f:
        layout = json.load(f)
    return layout

def check_bbox_overlap(layout_bbox, elem_bbox):
    x1_min, y1_min, x1_max, y1_max = layout_bbox
    x2_min, y2_min, x2_max, y2_max = elem_bbox

    if x1_max < x2_min or x2_max < x1_min:
        return False
    if y1_max < y2_min or y2_max < y1_min:
        return False
    return True

def order_and_save_md(output_txt_path, layout_json_path, save_md_path = None):
    if save_md_path is None:
        save_md_path = output_txt_path.replace('.txt', '.md')
    
    text_dict = get_output_txt(output_txt_path)
    layout = get_layout_json(layout_json_path)

    markdown = []

    for key_idx in range(len(layout)):
        page_key = f"page_{key_idx}"
        markdown.append(f">>> {page_key}\n")
        page_layout = layout[page_key]
        for element in page_layout:
            for bbox in element['bboxes']:
                elem_list = []
                for text_elem in text_dict.get(page_key, []):
                    if text_elem[5] == 1:
                        continue
                    elem_bbox = (text_elem[0], text_elem[1], text_elem[2], text_elem[3])
                    if check_bbox_overlap(bbox['bbox'], elem_bbox):
                        if bbox['label'] == 'SectionHeader':
                            elem_list.append((text_elem[0], text_elem[1], f"## {text_elem[4].strip()}"))
                        else:
                            elem_list.append((text_elem[0], text_elem[1], f"{text_elem[4].strip()}"))
                        text_elem[5] = 1
                
                sorted_elems = sorted(elem_list, key=lambda x: (x[1], x[0]))
                for _, _, content in sorted_elems:
                    markdown.append(content)

                
                        
    with open(save_md_path, 'w', encoding='utf-8') as f:
        for line in markdown:
            f.write(line)
            f.write('\n\n')
    
    print("Markdown 생성 완료")