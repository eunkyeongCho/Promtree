from dotenv import load_dotenv
import os
import re
from pymongo import MongoClient
from bson import ObjectId
import json
from datetime import datetime
from collections import Counter

load_dotenv()

# MongoDB 연결 설정
USERNAME = os.getenv("MONGO_INITDB_ROOT_USERNAME", "admin")
PASSWORD = os.getenv("MONGO_INITDB_ROOT_PASSWORD", "password")
HOST = os.getenv("MONGO_HOST", "localhost")
PORT = int(os.getenv("MONGO_PORT", "27017"))

url = f"mongodb://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/"

# MongoDB 연결
client = MongoClient(url)
db = client['s307_db']
collection = db['s307_collection']
chunks_collection = db['chunks']

# 청킹 규칙 상수
MAX_CHUNK_SIZE = 500      # 최대 청크 크기
MIN_CHUNK_SIZE = 80       # 최소 청크 크기
OVERLAP_SIZE = 75         # 오버랩 크기
WINDOW_SIZE = 100         # 문장 경계 탐색 범위


def extract_page_numbers(content: str) -> list:
    """
    content에서 >>> page_n 마커를 찾아서 페이지 번호들을 추출

    Args:
        content: 페이지 마커가 포함된 텍스트

    Returns:
        list: 추출된 페이지 번호들의 정렬된 리스트
    """
    page_numbers = []
    page_matches = re.findall(r'>>> page_(\d+)', content)
    for match in page_matches:
        page_numbers.append(int(match))

    # 중복 제거하고 정렬
    page_numbers = sorted(list(set(page_numbers)))
    return page_numbers


def clean_content(content: str) -> str:
    """
    content에서 >>> page_n 마커 제거하고 정리

    Args:
        content: 정리할 텍스트

    Returns:
        str: 마커가 제거된 정리된 텍스트
    """
    # >>> page_n 마커 제거 (pend는 이미 없음)
    content = re.sub(r'>>> page_\d+', '', content)

    # 연속된 빈 줄을 하나로 정리
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)

    return content.strip()


def get_page_number_for_section_final(section_content: str, original_content: str) -> list:
    """
    섹션 페이지 번호 감지 - 섹션 범위 내의 모든 페이지 번호 추출
    
    Args:
        section_content: 섹션 내용
        original_content: 원본 문서 내용 (페이지 마커 포함)
        
    Returns:
        list: 섹션이 속한 모든 페이지 번호들
    """
    # 섹션의 첫 번째 줄(헤딩)을 사용해서 원본에서 위치 찾기
    lines = section_content.split('\n')
    if not lines:
        return [1]
    
    # 첫 번째 줄(헤딩)을 사용해서 위치 찾기
    heading = lines[0].strip()
    if not heading:
        return [1]
    
    # 원본 content에서 헤딩 찾기
    heading_start = original_content.find(heading)
    
    if heading_start == -1:
        return [1]  # 찾을 수 없으면 기본값 1
    
    # 섹션의 시작과 끝 위치 찾기
    section_start = heading_start
    section_end = section_start + len(section_content)
    
    # 섹션 범위 내의 모든 페이지 번호 찾기
    page_numbers = []
    
    # 섹션 시작 이전의 마지막 페이지 번호
    content_before_section = original_content[:section_start]
    page_matches_before = re.findall(r'>>> page_(\d+)', content_before_section)
    if page_matches_before:
        page_numbers.append(int(page_matches_before[-1]))

    # 섹션 범위 내의 모든 페이지 번호 찾기
    section_range = original_content[section_start:section_end]
    page_matches_in_section = re.findall(r'>>> page_(\d+)', section_range)
    for match in page_matches_in_section:
        page_numbers.append(int(match))
    
    # 중복 제거하고 정렬
    page_numbers = sorted(list(set(page_numbers)))
    
    if page_numbers:
        return page_numbers
    else:
        return [1]  # 페이지 마커가 없으면 기본값 1


def get_page_number_for_table(table_lines: list, original_content: str) -> list:
    """
    표 내용이 원본 content에서 어느 페이지에 속하는지 찾기
    
    Args:
        table_lines: 표의 각 줄들
        original_content: 원본 문서 내용 (페이지 마커 포함)
        
    Returns:
        list: 표가 속한 모든 페이지 번호들
    """
    if not table_lines:
        return [1]
    
    # 표의 첫 번째 줄을 사용해서 위치 찾기
    first_line = table_lines[0].strip()
    if not first_line:
        return [1]
    
    # 원본 content에서 표 첫 줄 찾기
    table_start = original_content.find(first_line)
    
    if table_start == -1:
        return [1]  # 찾을 수 없으면 기본값 1
    
    # 표의 시작과 끝 위치 찾기
    table_content = '\n'.join(table_lines)
    table_end = table_start + len(table_content)
    
    # 표 범위 내의 모든 페이지 번호 찾기
    page_numbers = []
    
    # 표 시작 이전의 마지막 페이지 번호
    content_before_table = original_content[:table_start]
    page_matches_before = re.findall(r'>>> page_(\d+)', content_before_table)
    if page_matches_before:
        page_numbers.append(int(page_matches_before[-1]))

    # 표 범위 내의 모든 페이지 번호 찾기
    table_range = original_content[table_start:table_end]
    page_matches_in_table = re.findall(r'>>> page_(\d+)', table_range)
    for match in page_matches_in_table:
        page_numbers.append(int(match))
    
    # 중복 제거하고 정렬
    page_numbers = sorted(list(set(page_numbers)))
    
    if page_numbers:
        return page_numbers
    else:
        return [1]  # 페이지 마커가 없으면 기본값 1


def is_json_table_start(line: str) -> bool:
    """
    라인이 JSON 표 시작인지 확인 (<table>)

    Args:
        line: 확인할 라인

    Returns:
        bool: JSON 표 시작 여부
    """
    return line.strip() == '<table>'


def is_json_table_end(line: str) -> bool:
    """
    라인이 JSON 표 종료인지 확인 (</table>)

    Args:
        line: 확인할 라인

    Returns:
        bool: JSON 표 종료 여부
    """
    return line.strip() == '</table>'


def parse_json_table_lines(table_lines: list) -> list:
    """
    <table> 태그 내의 JSON 라인들을 파싱

    Args:
        table_lines: <table>과 </table> 사이의 모든 라인들 (태그 제외)

    Returns:
        list: 파싱된 key-value 딕셔너리 리스트
    """
    result = []

    for line in table_lines:
        line = line.strip()

        # 빈 줄 건너뛰기
        if not line:
            continue

        # 마지막 콤마 제거
        if line.endswith(','):
            line = line[:-1]

        try:
            # JSON 파싱
            data = json.loads(line)
            if isinstance(data, dict):
                result.append(data)
        except json.JSONDecodeError:
            # 파싱 실패시 건너뛰기
            continue

    return result


def json_table_to_text(table_data: list) -> str:
    """
    JSON 표 데이터를 검색 가능한 텍스트로 변환

    Args:
        table_data: key-value 딕셔너리 리스트

    Returns:
        str: 변환된 텍스트
    """
    text_lines = []

    for item in table_data:
        # 각 row를 텍스트로 변환
        row_parts = []
        for key, value in item.items():
            row_parts.append(f"{key}: {value}")
        text_lines.append(" | ".join(row_parts))

    return '\n'.join(text_lines)


def extract_headings_and_sections(content: str) -> tuple:
    """
    마크다운 content에서 섹션과 표를 분리
    
    Args:
        content: 마크다운 텍스트
        
    Returns:
        tuple: (sections, tables) - 섹션과 표의 리스트
    """
    lines = content.split('\n')
    sections = []
    tables = []
    current_section = []
    current_table = []
    in_table = False
    section_path = []
    current_heading = ""
    current_level = 0
    
    for line in lines:
        original_line = line

        # JSON 표 시작 감지
        if is_json_table_start(line):
            # 이전 섹션 저장
            if current_section and not in_table:
                sections.append({
                    'content': '\n'.join(current_section),
                    'section_path': section_path.copy(),
                    'heading': current_heading,
                    'level': current_level
                })
                current_section = []

            in_table = True
            current_table = []  # <table> 태그는 포함하지 않음
            continue

        # JSON 표 종료 감지
        elif is_json_table_end(line):
            if in_table and current_table:
                tables.append({
                    'table_lines': current_table,
                    'section_path': section_path.copy(),
                    'heading': current_heading
                })
                current_table = []
            in_table = False
            continue

        # 표 내부인 경우
        elif in_table:
            current_table.append(original_line)

        # 헤딩 감지
        elif line.strip().startswith('#'):
            # 이전 섹션 저장
            if current_section:
                sections.append({
                    'content': '\n'.join(current_section),
                    'section_path': section_path.copy(),
                    'heading': current_heading,
                    'level': current_level
                })

            # 새 섹션 시작
            stripped_line = line.strip()
            level = len(stripped_line) - len(stripped_line.lstrip('#'))
            heading = stripped_line.lstrip('#').strip()

            # section_path 업데이트
            # 모든 헤딩을 단일 요소 배열로 저장 (계층 구조 없음)
            # 이유: 문서에 level 1이 없고 모두 level 2이므로 계층이 없음
            section_path = [heading]
            current_heading = heading
            current_level = level

            current_section = [original_line]

        # 일반 텍스트
        else:
            current_section.append(original_line)
    
    # 마지막 섹션/표 저장
    if current_section and not in_table:
        sections.append({
            'content': '\n'.join(current_section),
            'section_path': section_path.copy(),
            'heading': current_heading,
            'level': current_level
        })
    
    if current_table:
        tables.append({
            'table_lines': current_table,
            'section_path': section_path.copy(),
            'heading': current_heading
        })
    
    return sections, tables


def find_sentence_boundary(text: str, target_pos: int, window_size: int = WINDOW_SIZE) -> int:
    """
    target_pos 근처에서 가장 가까운 문장 경계를 찾음
    
    Args:
        text: 전체 텍스트
        target_pos: 목표 위치
        window_size: 탐색 범위
        
    Returns:
        int: 문장 경계 위치 (찾지 못하면 target_pos)
    """
    # 탐색 범위 설정
    start = max(0, target_pos - window_size)
    end = min(len(text), target_pos + window_size)
    search_region = text[start:end]
    
    # 문장 종료 기호 찾기 (., ?, !, 。, 줄바꿈)
    sentence_endings = ['.', '?', '!', '。', '\n']
    
    # target_pos에서 가장 가까운 문장 경계 찾기
    best_pos = target_pos
    min_distance = float('inf')
    
    for ending in sentence_endings:
        # target_pos 이전에서 찾기
        pos = search_region.rfind(ending, 0, target_pos - start)
        if pos != -1:
            actual_pos = start + pos + 1  # 종료 기호 다음 위치
            distance = abs(actual_pos - target_pos)
            if distance < min_distance:
                min_distance = distance
                best_pos = actual_pos
        
        # target_pos 이후에서 찾기
        pos = search_region.find(ending, target_pos - start)
        if pos != -1:
            actual_pos = start + pos + 1  # 종료 기호 다음 위치
            distance = abs(actual_pos - target_pos)
            if distance < min_distance:
                min_distance = distance
                best_pos = actual_pos
    
    return best_pos


def smart_split_with_overlap(text: str, level: int, section_start_in_doc: int = 0) -> list:
    """
    같은 섹션 내에서 분할할 때 오버랩 적용
    (섹션 간 오버랩은 별도로 처리됨)
    
    Args:
        text: 분할할 텍스트
        level: 섹션 레벨 (1, 2, 3)
        section_start_in_doc: 문서 내에서 섹션 시작 위치 (오버랩 제한용)
        
    Returns:
        list: 분할된 텍스트 조각들
    """
    if len(text) <= MAX_CHUNK_SIZE:
        return [text]
    
    chunks = []
    current_pos = 0
    
    while current_pos < len(text):
        # 청크 끝 위치 계산
        chunk_end = min(current_pos + MAX_CHUNK_SIZE, len(text))
        
        # 문장 경계로 조정 (마지막 청크가 아닌 경우)
        if chunk_end < len(text):
            chunk_end = find_sentence_boundary(text, chunk_end)
        
        # 청크 추출
        chunk_text = text[current_pos:chunk_end].strip()
        
        if chunk_text:
            chunks.append(chunk_text)
        
        # 다음 청크 시작 위치 계산
        if chunk_end >= len(text):
            break
        
        # 모든 레벨에서 같은 섹션 내 분할에는 오버랩 적용
        overlap_start = max(chunk_end - OVERLAP_SIZE, current_pos)
        
        # 문장 경계로 스냅
        overlap_start = find_sentence_boundary(text, overlap_start)
        
        # 섹션 시작보다 앞으로 가지 않도록 제한
        overlap_start = max(overlap_start, 0)
        
        # MIN 길이 보장 체크
        remaining_text = text[overlap_start:].strip()
        if len(remaining_text) < MIN_CHUNK_SIZE and len(remaining_text) > 0:
            # 남은 텍스트가 너무 짧으면 이전 청크에 합치기
            if chunks:
                chunks[-1] = text[current_pos:].strip()
                break
        
        current_pos = overlap_start
    
    # 꼬리 보정: 마지막 청크가 MIN보다 짧으면 처리
    if len(chunks) > 1 and len(chunks[-1]) < MIN_CHUNK_SIZE:
        last_chunk = chunks.pop()
        
        # 직전 청크에서 문장 하나 빼서 마지막 청크와 합치기
        prev_chunk = chunks[-1]
        
        # 직전 청크에서 마지막 문장 경계 찾기
        split_pos = find_sentence_boundary(prev_chunk, len(prev_chunk) - MIN_CHUNK_SIZE)
        
        if split_pos > MIN_CHUNK_SIZE:
            # 직전 청크 분할
            chunks[-1] = prev_chunk[:split_pos].strip()
            # 마지막 청크 재구성
            chunks.append((prev_chunk[split_pos:] + " " + last_chunk).strip())
        else:
            # 분할할 수 없으면 그냥 합치기
            chunks[-1] = (prev_chunk + " " + last_chunk).strip()
    
    return chunks


def merge_small_chunks(chunks_list: list) -> list:
    """
    작은 청크들을 병합 (Level 2/3만, 50자 미만)
    단, 다음이 Level 1이면 병합 금지
    
    Args:
        chunks_list: 청크 리스트
        
    Returns:
        list: 병합된 청크 리스트
    """
    if not chunks_list:
        return []
    
    merged = []
    i = 0
    
    while i < len(chunks_list):
        chunk = chunks_list[i]
        content_len = len(chunk['content'])
        
        # Level 1은 병합하지 않고 그대로 추가
        if chunk['level'] == 1:
            merged.append(chunk)
            i += 1
            continue
        
        # Level 2/3에서 50자 미만인 경우
        if content_len < 50:
            # 다음 청크 확인
            if i + 1 < len(chunks_list):
                next_chunk = chunks_list[i + 1]
                
                # 다음이 Level 1이면 병합하지 않음
                if next_chunk['level'] == 1:
                    merged.append(chunk)
                    i += 1
                    continue
                
                # 같은 레벨이면 병합
                if chunk['level'] == next_chunk['level']:
                    merged_chunk = chunk.copy()
                    merged_chunk['content'] += '\n\n' + next_chunk['content']
                    merged_chunk['keywords'].extend(next_chunk['keywords'])
                    # 페이지 번호 병합
                    merged_chunk['page_num'] = sorted(list(set(chunk['page_num'] + next_chunk['page_num'])))
                    merged.append(merged_chunk)
                    i += 2  # 두 개 처리했으므로 +2
                    continue
            
            # 병합할 수 없으면 그대로 추가
            merged.append(chunk)
            i += 1
        else:
            # 정상 크기는 그대로 추가
            merged.append(chunk)
            i += 1
    
    return merged


def split_large_chunks(chunks_list: list) -> list:
    """
    큰 청크들을 분할 (새로운 규칙 적용)
    
    Args:
        chunks_list: 청크 리스트
        
    Returns:
        list: 분할된 청크 리스트
    """
    result = []
    
    for chunk in chunks_list:
        content_len = len(chunk['content'])
        
        # MAX_CHUNK_SIZE 이하면 그대로 유지
        if content_len <= MAX_CHUNK_SIZE:
            result.append(chunk)
            continue
        
        # 큰 청크는 smart_split_with_overlap로 분할
        split_texts = smart_split_with_overlap(
            chunk['content'], 
            chunk['level']
        )
        
        for idx, split_text in enumerate(split_texts):
            new_chunk = chunk.copy()
            new_chunk['content'] = split_text
            new_chunk['chunk_id'] = f"{chunk['chunk_id']}_split_{idx}"
            result.append(new_chunk)
    
    return result


def process_document_final(doc: dict) -> list:
    """
    단일 문서를 처리하여 청크 생성 (섹션/표 기반 페이지 번호)
    
    Args:
        doc: MongoDB 문서 객체
        
    Returns:
        list: 생성된 청크들의 리스트
    """
    print(f"\n[DEBUG] 문서 처리 시작: {doc['file_name']}")
    
    # 1. content 정리
    cleaned_content = clean_content(doc['content'])
    print(f"[DEBUG] content 정리 완료 (길이: {len(cleaned_content)})")
    
    # 2. 섹션과 표 분리
    sections, tables = extract_headings_and_sections(cleaned_content)
    print(f"[DEBUG] 섹션 {len(sections)}개, 표 {len(tables)}개 추출")
    
    # 3. 텍스트 청크 생성 (섹션별로 페이지 번호 설정)
    text_chunks = []
    for idx, section in enumerate(sections):
        # 섹션의 페이지 번호 찾기 (최종 개선된 버전 사용)
        section_page_num = get_page_number_for_section_final(section['content'], doc['content'])
        heading_preview = section['heading'][:30] + '...' if len(section['heading']) > 30 else section['heading']
        print(f"[DEBUG] 섹션 {idx+1}/{len(sections)}: '{heading_preview}' -> 페이지 {section_page_num}")
        
        # 섹션을 청크로 변환
        content = section['content'].strip()
        if not content:
            continue

        # 키워드 추출 (볼드 텍스트)
        keywords = re.findall(r'\*\*(.*?)\*\*', content)

        chunk = {
            'chunk_type': 'text',
            'content': content,
            'section_path': section['section_path'],
            'heading': section['heading'],
            'level': section['level'],
            'keywords': keywords,
            'source_file_name': doc['file_name'],
            'page_num': section_page_num,  # 섹션 기반 페이지 번호
            'chunk_id': f"{doc['_id']}_text_{len(text_chunks)}"
        }
        text_chunks.append(chunk)
    
    print(f"[DEBUG] 초기 텍스트 청크 생성 완료: {len(text_chunks)}개")
    
    # 4. 헤딩 없는 텍스트 처리 (level이 0인 경우)
    no_heading_chunks = []
    for chunk in text_chunks:
        if chunk['level'] == 0:  # 헤딩이 없는 텍스트
            # MAX_CHUNK_SIZE 단위로 분할 (Level 2 규칙 적용)
            if len(chunk['content']) > MAX_CHUNK_SIZE:
                split_texts = smart_split_with_overlap(chunk['content'], level=2)
                for idx, split_text in enumerate(split_texts):
                    new_chunk = chunk.copy()
                    new_chunk['content'] = split_text
                    new_chunk['chunk_id'] = f"{chunk['chunk_id']}_noheading_{idx}"
                    no_heading_chunks.append(new_chunk)
            else:
                no_heading_chunks.append(chunk)
        else:
            no_heading_chunks.append(chunk)
    
    text_chunks = no_heading_chunks
    print(f"[DEBUG] 헤딩 없는 텍스트 처리 완료: {len(text_chunks)}개")
    
    # 5. 글자 수 기반 청크 조정
    # 5-1. 작은 청크 병합 (50자 미만, Level 2/3만, Level 1 다음은 병합 금지)
    before_merge = len(text_chunks)
    text_chunks = merge_small_chunks(text_chunks)
    print(f"[DEBUG] 작은 청크 병합: {before_merge}개 -> {len(text_chunks)}개")
    
    # 5-2. 큰 청크 분할 (MAX_CHUNK_SIZE 이상, 새로운 규칙)
    before_split = len(text_chunks)
    text_chunks = split_large_chunks(text_chunks)
    print(f"[DEBUG] 큰 청크 분할: {before_split}개 -> {len(text_chunks)}개")
    
    # 6. 표 청크 생성 (표 전체를 하나의 청크로, 오버랩 없음)
    table_chunks = []
    for idx, table in enumerate(tables):
        # 표의 페이지 번호 찾기
        table_page_num = get_page_number_for_table(table['table_lines'], doc['content'])

        # JSON 표 파싱
        table_data = parse_json_table_lines(table['table_lines'])
        if table_data:
            print(f"[DEBUG] 표 {idx+1}/{len(tables)}: {len(table_data)}행 -> 페이지 {table_page_num}")

            # 표 전체를 하나의 청크로 생성 (오버랩 없음)
            # 검색 가능한 텍스트 형태로 변환
            table_text = json_table_to_text(table_data)

            # 표 원본 데이터도 함께 저장
            table_json = json.dumps(table_data, ensure_ascii=False)

            chunk = {
                'chunk_type': 'table',
                'content': table_text,  # 검색 가능한 텍스트
                'table_data': table_data,  # 원본 JSON 데이터
                'table_json': table_json,  # JSON 문자열
                'section_path': table['section_path'],
                'heading': table['heading'],
                'level': len(table['section_path']),
                'keywords': [],
                'source_file_name': doc['file_name'],
                'page_num': table_page_num,
                'chunk_id': f"{doc['_id']}_table_{len(table_chunks)}"
            }
            table_chunks.append(chunk)
    
    all_chunks = text_chunks + table_chunks
    print(f"[DEBUG] 문서 처리 완료: 텍스트 청크 {len(text_chunks)}개 + 표 청크 {len(table_chunks)}개 = 총 {len(all_chunks)}개\n")
    return all_chunks


def save_chunks_to_mongodb(chunks: list, batch_id: str = None) -> None:
    """
    생성된 청크들을 MongoDB에 저장
    
    Args:
        chunks: 저장할 청크들의 리스트
        batch_id: 배치 ID (선택사항)
        
    Returns:
        None
    """
    if not chunks:
        print("[DEBUG] 저장할 청크가 없습니다")
        return
    
    print(f"[DEBUG] MongoDB 저장 시작: {len(chunks)}개 청크")
    
    # 기존 청크 삭제
    deleted_count = chunks_collection.delete_many({}).deleted_count
    print(f"[DEBUG] 기존 청크 {deleted_count}개 삭제")
    
    # 배치로 저장
    batch_size = 100
    saved_count = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        
        # created_at 추가
        for chunk in batch:
            chunk['created_at'] = datetime.now()
            chunk['batch_id'] = batch_id or f'batch_{i//batch_size + 1}'
        
        # MongoDB에 저장
        chunks_collection.insert_many(batch)
        saved_count += len(batch)
        print(f"[DEBUG] 배치 저장 진행중... ({saved_count}/{len(chunks)})")
    
    print(f"[DEBUG] MongoDB 저장 완료: 총 {len(chunks)}개 청크")


def search_chunks(query: str = None, chunk_type: str = None, file_name: str = None, 
                 section_path: list = None, limit: int = 10) -> list:
    """
    청크 검색 함수
    
    Args:
        query: 내용 검색 쿼리
        chunk_type: 청크 타입 ('text' 또는 'table_row')
        file_name: 소스 파일명
        section_path: 섹션 경로 리스트
        limit: 결과 제한 수
        
    Returns:
        list: 검색된 청크들의 리스트
    """
    filter_dict = {}
    
    if query:
        filter_dict['content'] = {'$regex': query, '$options': 'i'}
    
    if chunk_type:
        filter_dict['chunk_type'] = chunk_type
    
    if file_name:
        filter_dict['source_file_name'] = file_name
    
    if section_path:
        filter_dict['section_path'] = {'$in': section_path}
    
    results = list(chunks_collection.find(filter_dict).limit(limit))
    return results


def process_all_documents() -> list:
    """
    모든 processing 문서를 처리하여 청크 생성
    
    Returns:
        list: 생성된 모든 청크들
    """
    # processing 타입 문서 조회
    processing_docs_list = list(collection.find({"doc_type": "processing"}))
    print(f"[DEBUG] 처리할 문서 수: {len(processing_docs_list)}개\n")
    
    all_chunks = []
    for idx, doc in enumerate(processing_docs_list):
        print(f"[DEBUG] === 문서 {idx+1}/{len(processing_docs_list)} 처리 중 ===")
        doc_chunks = process_document_final(doc)
        all_chunks.extend(doc_chunks)
    
    print(f"\n[DEBUG] 전체 처리 완료: 총 {len(all_chunks)}개 청크 생성")
    return all_chunks


def get_chunk_statistics() -> dict:
    """
    현재 저장된 청크들의 통계 정보 반환
    
    Returns:
        dict: 청크 통계 정보
    """
    print("[DEBUG] 통계 정보 수집 중...")
    
    total_chunks = chunks_collection.count_documents({})
    
    # 청크 타입별 분포
    chunk_types = chunks_collection.aggregate([
        {"$group": {"_id": "$chunk_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ])
    
    # 페이지 번호 분포
    page_distribution = chunks_collection.aggregate([
        {"$unwind": "$page_num"},
        {"$group": {"_id": "$page_num", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ])
    
    # 여러 페이지를 가진 청크 수
    multi_page_count = chunks_collection.count_documents({"$expr": {"$gt": [{"$size": "$page_num"}, 1]}})
    
    stats = {
        'total_chunks': total_chunks,
        'chunk_types': list(chunk_types),
        'page_distribution': list(page_distribution),
        'multi_page_chunks': multi_page_count
    }
    
    print(f"[DEBUG] 통계 수집 완료: 총 {total_chunks}개 청크")
    return stats


if __name__ == "__main__":
    # 모든 문서 처리 및 저장
    print("\n" + "="*60)
    print("=== PDF 파싱 데이터 청킹 시작 ===")
    print("="*60 + "\n")
    
    # 1. 모든 문서 처리
    all_chunks = process_all_documents()
    
    # 2. MongoDB에 저장
    print("\n" + "="*60)
    save_chunks_to_mongodb(all_chunks)
    print("="*60 + "\n")
    