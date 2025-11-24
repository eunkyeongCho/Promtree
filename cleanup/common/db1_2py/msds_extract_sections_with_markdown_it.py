import json
from pathlib import Path
from markdown_it import MarkdownIt

def extract_sections_with_markdown_it(content: str) -> tuple:
    """
    markdown-it-py를 사용하여 마크다운 content에서 섹션과 표를 분리
    """
    md = MarkdownIt()
    tokens = md.parse(content)
    lines = content.split('\n')

    sections = []
    tables = []
    
    section_path = []
    current_heading = ""
    current_level = 0
    
    last_block_end_line = 0

    for i, token in enumerate(tokens):
        # 헤딩 블록을 찾았을 때
        if token.type == 'heading_open':
            # 이전 블록이 있었다면, 그 내용을 이전 섹션의 일부로 저장
            prose_start_line = last_block_end_line
            prose_end_line = token.map[0]
            if prose_start_line < prose_end_line:
                prose_content = '\n'.join(lines[prose_start_line:prose_end_line]).strip()
                if prose_content:
                    # 헤딩이 없는 첫 부분을 처리
                    if not sections and not tables:
                         sections.append({
                            'content': prose_content,
                            'section_path': [], 'heading': '', 'level': 0
                        })
                    # 이전 섹션에 텍스트 추가 (헤딩과 테이블 사이의 텍스트)
                    elif sections:
                        sections[-1]['content'] += '\n\n' + prose_content

            # 새 섹션 정보 추출
            level = int(token.tag[1])
            heading_content = tokens[i+1].content.strip()
            
            section_path = section_path[:level-1] + [heading_content]
            current_heading = heading_content
            current_level = level

            # 헤딩 자체를 포함하는 새로운 섹션 생성
            new_section = {
                'content': f"{'#' * level} {heading_content}",
                'section_path': section_path.copy(),
                'heading': current_heading,
                'level': current_level
            }
            sections.append(new_section)
            last_block_end_line = token.map[1]

        # 테이블 블록을 찾았을 때
        elif token.type == 'table_open':
            # 테이블 이전까지의 텍스트를 이전 섹션에 추가
            prose_start_line = last_block_end_line
            prose_end_line = token.map[0]
            if prose_start_line < prose_end_line:
                prose_content = '\n'.join(lines[prose_start_line:prose_end_line]).strip()
                if prose_content and sections:
                    sections[-1]['content'] += '\n\n' + prose_content

            # 테이블 내용 추출
            table_start_line = token.map[0]
            table_end_line = token.map[1]
            table_lines = lines[table_start_line:table_end_line]
            
            # 테이블 블록 추가
            tables.append({
                'table_lines': table_lines,
                'section_path': section_path.copy(),
                'heading': current_heading
            })
            last_block_end_line = table_end_line
            
    # 문서의 마지막 부분 (마지막 헤딩/테이블 이후의 텍스트) 처리
    if last_block_end_line < len(lines):
        final_content = '\n'.join(lines[last_block_end_line:]).strip()
        if final_content and sections:
            sections[-1]['content'] += '\n\n' + final_content

    return sections, tables