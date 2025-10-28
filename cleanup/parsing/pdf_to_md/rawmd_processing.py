from dotenv import load_dotenv
import os
import re
from collections import defaultdict
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson import ObjectId

load_dotenv()

USERNAME = os.getenv("MONGO_INITDB_ROOT_USERNAME")
PASSWORD = os.getenv("MONGO_INITDB_ROOT_PASSWORD")
HOST = os.getenv("MONGO_HOST")
PORT = int(os.getenv("MONGO_PORT"))

url = f"mongodb://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/"

# mongodb 연결
try:
    client = MongoClient(url)
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")

except ConnectionFailure as e:
    print(f"MongoDB connection failed: {e}")

# db와 collection 선택
db = client['s307_db']
collection = db['s307_collection']



def save_markdown_to_mongodb(file_path: str) -> None:
    """
    .md 파일을 읽어서 MongoDB에 저장하는 함수
    
    Args:
        file_path: .md 파일의 경로

    Returns:
        None
    """
    # 파일명 추출 (경로에서 마지막 부분)
    file_name = file_path.split("\\")[-1]
    
    try:
        # .md 파일 읽기
        with open(file_path, "r", encoding="utf-8") as file:
            markdown_content = file.read()
        
        # MongoDB에 저장할 문서 생성
        markdown_object = {
            "file_name": file_name,
            "doc_type": "markdown",
            "context": markdown_content
        }
        
        # MongoDB에 저장
        result = collection.insert_one(markdown_object)
        print(f"Inserted Markdown | File: {file_name} | ID: {result.inserted_id}")
        
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
    except Exception as e:
        print(f"❌ 저장 중 오류 발생: {e}")

 
def normalize_variable_numbers(text: str, total_pages: int) -> str:
    """
    구분자(/, 의, of, -)를 감지하여 그 주변의 숫자를 변수화
    연도나 불필요한 패턴은 제외
    Args:
        text: 정규화할 텍스트
        total_pages: 총 페이지 수
    Returns:
        str: 정규화된 텍스트
    """
    normalized_text = text
    
    # 제외할 패턴들 (연도, 버전 등)
    exclude_patterns = [
        r'\d{4}',  # 4자리 연도 (2013, 2020 등)
        r'\d{2}-\d{2}',  # 2자리-2자리 (13-08 등)
        r'Copy\)',  # Copy)로 끝나는 것
        r'Printed',  # Printed가 포함된 것
        r'Uncontrolled',  # Uncontrolled가 포함된 것
    ]
    
    # 제외 패턴이 있는지 확인
    for pattern in exclude_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return text  # 제외 패턴이 있으면 원본 그대로 반환
    
    # 구분자 패턴들: 숫자 + (공백 허용) 구분자 + 숫자
    patterns = [
        (r'(\d+)\s*/\s*(\d+)', r'n/{}'),          # 1/15, 1 / 15 -> n/15
        (r'(\d+)\s*-\s*(\d+)', r'n-{}'),          # 1-15, 1 - 15 -> n-15
        (r'(\d+)\s*의\s*(\d+)', r'n 의 {}'),       # 1 의 11 -> n 의 11
        (r'(\d+)\s+of\s+(\d+)', r'n of {}'),      # 1 of 11 -> n of 11
    ]
    
    for pattern, replacement in patterns:
        # 패턴이 매치되는지 확인
        if re.search(pattern, text, re.IGNORECASE):
            # 첫 번째 숫자를 'n'으로, 두 번째 숫자를 total_pages로 변경 (공백 제거하여 생성)
            normalized_text = re.sub(pattern, replacement.format(total_pages), normalized_text, flags=re.IGNORECASE)
    
    return normalized_text



def get_zone(page, which: str, ratio: float = 0.3):
    """
    각 페이지의 상단 30% 또는 하단 30% 영역을 추출하는 함수
    Args:
        page: 페이지 내용
        which: 'header' 또는 'footer'
        ratio: 영역 비율 (기본값: 0.3)
    Returns:
        zone: 추출된 영역 내용
    """
    if which == 'header':
        end = max(1, int(len(page) * ratio))
        return page[:end]
    else:
        count = max(1, int(len(page) * ratio))
        start = max(0, len(page) - count)
        return page[start:]


def collect_common(all_pages, which: str, total_pages: int, exclude_first: bool):
    """
    상/하단 윈도우에서 페이지별로 텍스트를 수집해 모든 유효 페이지에 존재하는 항목만 반환
    Args:
        all_pages: 모든 페이지 내용
        which: 추출 대상. 'header' 또는 'footer'
        total_pages: 총 페이지 수
        exclude_first: 첫 페이지 제외 여부
    Returns:
        common: 모든 유효 페이지에 존재하는 공통 항목만 추출(header 또는 footer)
    """
    first_seen = {}
    page_count = defaultdict(int)
    effective_pages = (total_pages - 1) if exclude_first else total_pages

    for page_idx, page in enumerate(all_pages):
        zone = get_zone(page, which)
        # 최초 등장 좌표 기록
        for local_idx, line in enumerate(zone):
            text = line.strip()
            if not text:
                continue
            key = normalize_variable_numbers(text, total_pages) if which == 'footer' else text
            first_seen.setdefault(key, (page_idx, local_idx if which == 'header' else (len(page) - len(zone) + local_idx)))

        # 빈도 집계 (첫 페이지 제외 가능)
        if exclude_first and page_idx == 0:
            continue
        uniq = set()
        for line in zone:
            text = line.strip()
            if not text:
                continue
            key = normalize_variable_numbers(text, total_pages) if which == 'footer' else text
            uniq.add(key)
        for key in uniq:
            page_count[key] += 1

    # 모든 유효 페이지에 등장한 항목만
    commons = [k for k, c in page_count.items() if c == effective_pages]
    # 최초 등장 좌표 순으로 정렬해 문서 순서 보존
    return [k for k in sorted(commons, key=lambda x: first_seen.get(x, (9999, 9999)))]

def get_header_footer_info(context: str) -> dict:
    """
    Header/Footer 분석을 수행하여 공통 패턴을 추출하는 함수
    
    Args:
        context: 저장된 context 문자열

    Returns:
        dict: {
            'header': 공통 header 텍스트,
            'footer': 공통 footer 텍스트 (숫자는 n으로 표시),
            'content': header와 footer를 제외한 순수 content 텍스트들
        }
    """
    # 1. 페이지별로 분할 (>>> page X ~ >>> pend 구조)
    # >>> page x 와 >>> pend 제외하고 나머지 내용 추출
    page_pattern = r'>>> page \d+\n(.*?)\n>>> pend'
    page_matches = re.findall(page_pattern, context, re.DOTALL)

    # 초기화 처리
    if not page_matches:
        return {'header': '', 'footer': '', 'content': ''}

    all_pages = []
    for page_content in page_matches:
        page_lines = page_content.strip().split('\n')
        all_pages.append(page_lines)
    
    # header, footer 초기화(빈 리스트로 초기화)
    common_headers = []
    common_footers = []
    total_pages = len(all_pages)

    if total_pages == 1:
        # 1페이지: Header/Footer 로직 스킵
        pass
    elif total_pages == 2:
        # 2페이지: 두 페이지 직접 비교
        common_headers = collect_common(all_pages, 'header', total_pages, exclude_first=False)
        common_footers = collect_common(all_pages, 'footer', total_pages, exclude_first=False)
    else:
        # 3페이지 이상: 첫 페이지 제외 후 모든 유효 페이지에 존재하는 항목만
        common_headers = collect_common(all_pages, 'header', total_pages, exclude_first=True)
        common_footers = collect_common(all_pages, 'footer', total_pages, exclude_first=True)
    
    print(f"동시 분석 결과 - Header: {len(common_headers)}줄, Footer: {len(common_footers)}줄")
    
    # Footer는 이미 정규화된 텍스트로 수집됨
    total_pages = len(page_matches)
    processed_footers = list(common_footers)
    
    # Header 텍스트 조합
    header_text = '\n'.join(common_headers) if common_headers else ""
    
    # Footer 텍스트 조합
    footer_text = '\n'.join(processed_footers) if processed_footers else ""
    
    # Content 추출 (원본 텍스트에서 header와 footer를 제거한 내용, 구분자 유지)
    content_text = context
    
    # Header 제거 (한 번의 스캔으로 처리)
    if common_headers:
        lines = content_text.split('\n')
        header_set = set(common_headers)
        filtered_lines = []
        for line in lines:
            if line.strip() in header_set:
                continue
            filtered_lines.append(line)
        content_text = '\n'.join(filtered_lines)
    
    # Footer 제거 (정규화 비교, 한 번의 스캔)
    if common_footers:
        lines = content_text.split('\n')
        footer_set = set(common_footers)
        filtered_lines = []
        for line in lines:
            normalized_line = normalize_variable_numbers(line.strip(), total_pages)
            if normalized_line in footer_set:
                continue
            filtered_lines.append(line)
        content_text = '\n'.join(filtered_lines)
    
    return {
        'header': header_text,
        'footer': footer_text,
        'content': content_text
    }


def save_processing_to_mongodb(file_name: str, header_footer_info: dict) -> None:
    """
    Header/Footer 분석 결과를 processing 객체로 MongoDB에 저장하는 함수
    
    Args:
        file_name: 원본 파일명
        header_footer_info: get_header_footer_info()의 반환값 (dict)
    """
    try:
        # MongoDB에 저장할 processing 객체 생성
        processing_object = {
            "file_name": file_name,
            "doc_type": "processing",
            "header": header_footer_info['header'],
            "footer": header_footer_info['footer'],
            "content": header_footer_info['content']
        }
        
        # MongoDB에 저장
        result = collection.insert_one(processing_object)
        print(f"✅ Processing 객체 저장 완료 | File: {file_name} | ID: {result.inserted_id}")
        
    except Exception as e:
        print(f"❌ Processing 객체 저장 중 오류 발생: {e}")




if __name__ == "__main__":
    # # 특정 ObjectId로 문서 삭제
    # target_id = ObjectId("68f8e4b6efb465991543e50e")
    # # 특정 ID의 문서 삭제
    # result = collection.delete_one({"_id": target_id})
    # if result.deleted_count > 0:
    #     print(f"✅ 문서 삭제 완료: {target_id}")
    # else:
    #     print(f"❌ 문서를 찾을 수 없습니다: {target_id}")



    # t1,t2,t3,t4 폴더의 output.md 파일 처리
    t1_md_path = r"C:\Users\SSAFY\Desktop\S13P31S307\parsing\testmds\t1\44-1206-SDS11757.md"
    
    # 1. .md 파일을 MongoDB에 저장
    print("=== 1단계: .md 파일 저장 ===")
    save_markdown_to_mongodb(t1_md_path)
    
    # 2. 저장된 문서 찾기
    print("\n=== 2단계: 저장된 문서 확인 ===")
    file_name = t1_md_path.split("\\")[-1]  # Windows 경로이므로 \\로 분할
    saved_doc = collection.find_one({"file_name": file_name, "doc_type": "markdown"})
    
    if saved_doc:
        print(f"✅ 문서 찾음: {file_name}")
        print(f"문서 ID: {saved_doc['_id']}")
        print(f"Context 길이: {len(saved_doc['context'])} 문자")
        
        # 3. Header/Footer 분석
        print("\n=== 3단계: Header/Footer 분석 ===")
        header_footer_info = get_header_footer_info(saved_doc['context'])
        
        # print(f"\n📄 Header ({len(header_footer_info['header'])} 문자):")
        # print(header_footer_info['header'])
        
        # print(f"\n📄 Footer ({len(header_footer_info['footer'])} 문자):")
        # print(header_footer_info['footer'])
        
        # print(f"\n📄 Content (처음 100자):")
        # content_preview = header_footer_info['content'][:100]
        # print(content_preview + "..." if len(header_footer_info['content']) > 100 else content_preview)
        
        # print(f"\n📊 통계:")
        # print(f"Header 길이: {len(header_footer_info['header'])} 문자")
        # print(f"Footer 길이: {len(header_footer_info['footer'])} 문자") 
        # print(f"Content 길이: {len(header_footer_info['content'])} 문자")
        
        # 4. Processing 객체로 MongoDB에 저장
        print("\n=== 4단계: Processing 객체 저장 ===")
        save_processing_to_mongodb(file_name, header_footer_info)
        
    else:
        print(f"❌ 문서를 찾을 수 없습니다: {file_name}")