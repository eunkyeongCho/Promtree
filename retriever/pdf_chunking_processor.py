from dotenv import load_dotenv
import os
import re
import pandas as pd
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


def extract_page_numbers(content: str) -> list:
    """
    content에서 >>> page n 마커를 찾아서 페이지 번호들을 추출
    
    Args:
        content: 페이지 마커가 포함된 텍스트
        
    Returns:
        list: 추출된 페이지 번호들의 정렬된 리스트
    """
    page_numbers = []
    page_matches = re.findall(r'>>> page (\d+)', content)
    for match in page_matches:
        page_numbers.append(int(match))
    
    # 중복 제거하고 정렬
    page_numbers = sorted(list(set(page_numbers)))
    return page_numbers


def clean_content(content: str) -> str:
    """
    content에서 >>> page n, >>> pend 마커 제거하고 정리
    
    Args:
        content: 정리할 텍스트
        
    Returns:
        str: 마커가 제거된 정리된 텍스트
    """
    # >>> page n, >>> pend 마커 제거
    content = re.sub(r'>>> page \d+', '', content)
    content = re.sub(r'>>> pend', '', content)
    
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
    page_matches_before = re.findall(r'>>> page (\d+)', content_before_section)
    if page_matches_before:
        page_numbers.append(int(page_matches_before[-1]))
    
    # 섹션 범위 내의 모든 페이지 번호 찾기
    section_range = original_content[section_start:section_end]
    page_matches_in_section = re.findall(r'>>> page (\d+)', section_range)
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
    page_matches_before = re.findall(r'>>> page (\d+)', content_before_table)
    if page_matches_before:
        page_numbers.append(int(page_matches_before[-1]))
    
    # 표 범위 내의 모든 페이지 번호 찾기
    table_range = original_content[table_start:table_end]
    page_matches_in_table = re.findall(r'>>> page (\d+)', table_range)
    for match in page_matches_in_table:
        page_numbers.append(int(match))
    
    # 중복 제거하고 정렬
    page_numbers = sorted(list(set(page_numbers)))
    
    if page_numbers:
        return page_numbers
    else:
        return [1]  # 페이지 마커가 없으면 기본값 1


def is_table_line(line: str) -> bool:
    """
    라인이 표 라인인지 확인 (더 정확한 표 감지)
    
    Args:
        line: 확인할 라인
        
    Returns:
        bool: 표 라인 여부
    """
    line = line.strip()
    
    # 빈 줄이면 표가 아님
    if not line:
        return False
    
    # |로 시작하고 끝나며, 중간에 |가 있는지 확인
    if line.startswith('|') and line.endswith('|'):
        # | 사이에 내용이 있는지 확인
        parts = line.split('|')
        if len(parts) >= 3:  # 시작|내용|끝
            # 각 부분에 실제 내용이 있는지 확인
            content_parts = [part.strip() for part in parts[1:-1]]
            if any(part for part in content_parts):  # 빈 부분이 아닌 부분이 있으면
                return True
    
    return False


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
        line = line.strip()
        
        # 헤딩 감지
        if line.startswith('#'):
            # 이전 섹션 저장
            if current_section and not in_table:
                sections.append({
                    'content': '\n'.join(current_section),
                    'section_path': section_path.copy(),
                    'heading': current_heading,
                    'level': current_level
                })
            
            # 새 섹션 시작
            level = len(line) - len(line.lstrip('#'))
            heading = line.lstrip('#').strip()
            
            # section_path 업데이트
            section_path = section_path[:level-1] + [heading]
            current_heading = heading
            current_level = level
            
            current_section = [original_line]
            in_table = False
            current_table = []
            
        # 표 감지 (개선된 로직)
        elif is_table_line(original_line):
            if not in_table:
                # 이전 섹션 저장
                if current_section:
                    sections.append({
                        'content': '\n'.join(current_section),
                        'section_path': section_path.copy(),
                        'heading': current_heading,
                        'level': current_level
                    })
                current_section = []
            
            in_table = True
            current_table.append(original_line)
            
        # 표가 아닌 일반 텍스트
        elif not in_table:
            current_section.append(original_line)
        else:
            # 표 내부의 빈 줄이나 다른 내용
            if line == '' or not is_table_line(original_line):
                # 표 종료
                if current_table:
                    tables.append({
                        'table_lines': current_table,
                        'section_path': section_path.copy(),
                        'heading': current_heading
                    })
                current_table = []
                in_table = False
                current_section = [original_line] if original_line else []
            else:
                current_table.append(original_line)
    
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


def parse_markdown_table(table_lines: list) -> pd.DataFrame:
    """
    마크다운 표를 pandas DataFrame으로 변환
    
    Args:
        table_lines: 표의 각 줄들
        
    Returns:
        pd.DataFrame: 변환된 DataFrame (실패시 None)
    """
    if len(table_lines) < 2:
        return None
    
    # 헤더와 구분선 제거
    header_line = table_lines[0]
    data_lines = [line for line in table_lines[2:] if line.strip() and is_table_line(line)]
    
    if not data_lines:
        return None
    
    # 헤더 파싱
    headers = [col.strip() for col in header_line.split('|')[1:-1]]
    
    # 데이터 파싱
    data = []
    for line in data_lines:
        if line.strip() and is_table_line(line):
            row = [col.strip() for col in line.split('|')[1:-1]]
            if len(row) == len(headers):
                data.append(row)
    
    if not data:
        return None
    
    return pd.DataFrame(data, columns=headers)


def process_document_final(doc: dict) -> list:
    """
    단일 문서를 처리하여 청크 생성 (섹션/표 기반 페이지 번호)
    
    Args:
        doc: MongoDB 문서 객체
        
    Returns:
        list: 생성된 청크들의 리스트
    """
    # 1. content 정리
    cleaned_content = clean_content(doc['content'])
    
    # 2. 섹션과 표 분리
    sections, tables = extract_headings_and_sections(cleaned_content)
    
    # 3. 텍스트 청크 생성 (섹션별로 페이지 번호 설정)
    text_chunks = []
    for section in sections:
        # 섹션의 페이지 번호 찾기 (최종 개선된 버전 사용)
        section_page_num = get_page_number_for_section_final(section['content'], doc['content'])
        
        # 섹션을 청크로 변환
        content = section['content'].strip()
        if not content:
            continue
        
        # 인라인 표 제거 (|로 시작하는 줄들)
        lines = content.split('\n')
        text_lines = []
        
        for line in lines:
            if not is_table_line(line):  # 표 라인이 아니면 추가
                text_lines.append(line)
        
        cleaned_content = '\n'.join(text_lines).strip()
        if not cleaned_content:
            continue
        
        # 키워드 추출 (볼드 텍스트)
        keywords = re.findall(r'\*\*(.*?)\*\*', cleaned_content)
        
        chunk = {
            'chunk_type': 'text',
            'content': cleaned_content,
            'section_path': section['section_path'],
            'heading': section['heading'],
            'level': section['level'],
            'keywords': keywords,
            'source_file_name': doc['file_name'],
            'page_num': section_page_num,  # 섹션 기반 페이지 번호
            'chunk_id': f"{doc['_id']}_text_{len(text_chunks)}"
        }
        text_chunks.append(chunk)
    
    # 4. 표 청크 생성 (표별로 페이지 번호 설정)
    table_chunks = []
    for table in tables:
        # 표의 페이지 번호 찾기
        table_page_num = get_page_number_for_table(table['table_lines'], doc['content'])
        
        table_df = parse_markdown_table(table['table_lines'])
        if table_df is not None:
            # 표의 각 행을 청크로 변환
            for idx, row in table_df.iterrows():
                row_dict = row.to_dict()
                
                chunk = {
                    'chunk_type': 'table_row',
                    'content': json.dumps(row_dict, ensure_ascii=False),
                    'section_path': table['section_path'],
                    'heading': table['heading'],
                    'level': len(table['section_path']),
                    'keywords': [],
                    'row_data': row_dict,
                    'row_index': idx,
                    'source_file_name': doc['file_name'],
                    'page_num': table_page_num,  # 표 기반 페이지 번호
                    'chunk_id': f"{doc['_id']}_table_{len(table_chunks)}"
                }
                table_chunks.append(chunk)
    
    all_chunks = text_chunks + table_chunks
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
        print("저장할 청크가 없습니다")
        return
    
    # 기존 청크 삭제
    chunks_collection.delete_many({})
    
    # 배치로 저장
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        
        # created_at 추가
        for chunk in batch:
            chunk['created_at'] = datetime.now()
            chunk['batch_id'] = batch_id or f'batch_{i//batch_size + 1}'
        
        # MongoDB에 저장
        chunks_collection.insert_many(batch)
    
    print(f"총 {len(chunks)}개 청크 저장 완료")


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
    
    all_chunks = []
    for doc in processing_docs_list:
        doc_chunks = process_document_final(doc)
        all_chunks.extend(doc_chunks)
    
    print(f"총 {len(all_chunks)}개 청크 생성 완료")
    return all_chunks


def get_chunk_statistics() -> dict:
    """
    현재 저장된 청크들의 통계 정보 반환
    
    Returns:
        dict: 청크 통계 정보
    """
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
    
    return {
        'total_chunks': total_chunks,
        'chunk_types': list(chunk_types),
        'page_distribution': list(page_distribution),
        'multi_page_chunks': multi_page_count
    }


if __name__ == "__main__":
    # 모든 문서 처리 및 저장
    print("=== PDF 파싱 데이터 청킹 시작 ===")
    
    # 1. 모든 문서 처리
    all_chunks = process_all_documents()
    
    # 2. MongoDB에 저장
    save_chunks_to_mongodb(all_chunks, "main_batch")
    
    # 3. 통계 정보 출력
    # stats = get_chunk_statistics()
    # print(f"\n=== 처리 완료 ===")
    # print(f"총 청크 수: {stats['total_chunks']}")
    # print(f"여러 페이지를 가진 청크 수: {stats['multi_page_chunks']}")
    
    # # 4. 사용 예시
    # print(f"\n=== 사용 예시 ===")
    # print("# 특정 파일의 모든 청크 검색:")
    # print("results = search_chunks(file_name='gpt-020-3m-sds.md')")
    # print("\n# 텍스트 청크만 검색:")
    # print("results = search_chunks(chunk_type='text')")
    # print("\n# 특정 키워드 검색:")
    # print("results = search_chunks(query='물질안전보건자료')")
