# DB
from pymongo.errors import ConnectionFailure
from pymongo import MongoClient

# 텍스트 전처리
import re
from urlextract import URLExtract
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 예외처리
import traceback

# 기타
from dotenv import load_dotenv
import os
from pathlib import Path


# =====================================================
# DB 커넥팅 (setup.ipynb -> py파일로 바뀌면 그거 import하고 이 부분은 삭제될 예정)
# =====================================================
load_dotenv() # 환경변수 불러오기

USERNAME = os.getenv("MONGODB_INITDB_ROOT_USERNAME") # 환경변수에 있던 값들 메모리 변수에 할당
PASSWORD = os.getenv("MONGODB_INITDB_ROOT_PASSWORD")
HOST = os.getenv("MONGO_HOST")
PORT = int(os.getenv("MONGO_PORT"))

url = f"mongodb://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/" # 위 값들 조합해서 MongoDB 연결하기 위한 url 만들기
print(url) # 만들어진 url 출력

try:
    client = MongoClient(url)
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")

except ConnectionFailure as e:
    print(f"MongoDB connection failed: {e}")

# chunk에 쓸 database, collection 변수 선언 및 할당
# 아직 네이밍 협의 전이므로 각자 실행하는 로컬에서의 db, collection 이름과 겹치지 않는지 확인필요
chunk_db = client['chunk_db']
chunk_collection = chunk_db['chunk_collection']

# =====================================================

def get_pages_info(md: str) -> list:
    """
    마크다운 텍스트에서 각 페이지의 실제 내용의 시작과 끝 인덱스를 추출합니다.

    Args:
        md(str): 처리해야할 마크다운 형식 문자열

    Returns: list[tuple[int, tuple[int, int]]]: 각 페이지의 인덱스 정보를 담은 리스트.
        형식: [[page_num, (content_start_index, content_end_index)]]
        설명:
            - page_num (int): 페이지 번호
            - content_start_index (int): '>>> page' 다음에 나오는 실제 내용의 시작 인덱스.
            - content_end_index (int): '>>> pend' 직전에 끝나는 실제 내용의 끝 인덱스.
    """

    # >>> page_0 ... 정규식 (그 다음 >>> page_1이 나오기 직전까지)
    page_pattern = re.compile(
        r">>> page_(\d+)(.*?)(?=>>> page_\d+|$)",
        re.DOTALL
    )

    pages_info = [] # 각 페이지에서 >>> page_0을 제외한 실제 내용의 시작과 끝 인덱스 정보를 저장할 배열

    for page_match in page_pattern.finditer(md): # md에서 정규식이 매칭될 때 마다 re.Match 객체를 반환
        
        is_last_page = not re.match(r">>> page_\d+", md[page_match.end(2):]) # 마지막 페이지인지 여부를 판단

        content_start_index = page_match.start(2) # page 덩어리 시작 인덱스

        if is_last_page:
            content_end_index = len(md)
        else:
            content_end_index = page_match.end(2) - 1 # page 덩어리 끝 인덱스 (re.Match.end() 인덱스가 끝 인덱스의 다음 인덱스를 반환하기 때문에 -1)
        
        page_num = int(page_match.group(1)) # 현재 페이지 번호

        pages_info.append([page_num, (content_start_index, content_end_index)])

    return pages_info

def remove_page(md: str) -> str:
    """
    마크다운 텍스트에서 '>>> page_0' 마커를 제거하고 그 만큼 공백으로 치환합니다.
    제거한 만큼 공백으로 채우기 때문에 원본 인덱스가 보존됩니다.

    Args:
        md(str): 처리해야할 마크다운 형식 문자열 (pdf 파일 1개 단위)

    Returns:
        '>>> page_0' 마커가 제거된 마크다운 형식 문자열
    """

    page_pattern = re.compile(
        r">>> page_\d+",
        re.DOTALL
    )

    md_without_page = page_pattern.sub(lambda m: " " * len(m.group(0)), md)

    return md_without_page

def generate_image_chunk(md: str) -> dict[str, str | list[dict]]:
    """
    마크다운 문자열에서 image에 해당하는 부분을 전부 공백으로 치환하고 image 타입 청크를 생성합니다.

    Args:
        md(str): >>> page, >>> pend가 제거된 마크다운 문자열

    Returns:
        dict: 다음 두 개의 key를 포함한 딕셔너리
            - md_without_image(str): 모든 이미지지가 공백으로 치환된 마크다운 문자열
            - image_raw_chunks(list[dict]): image 타입 raw 청크 리스트 (file_name, page_num 키 생성 전)
    """

    # image 정규식
    image_pattern = re.compile(
        r"!\[(.*?)\]\((.*?)\)",
        re.DOTALL
    )

    image_raw_chunks = []

    for image_match in re.finditer(image_pattern, md):
        image_raw_chunks.append({
                "type": "image",
                "content": image_match.group(2),
                "metadata": image_match.group(1),
                "start_index": image_match.start(),
                "end_index": image_match.end() - 1
            })
        
    # image 부분 공백으로 치환
    md_without_image = image_pattern.sub(lambda m: " " * len(m.group(0)), md)

    image_dict = {
        "md_without_image": md_without_image,
        "image_raw_chunks": image_raw_chunks
    }
    
    return image_dict

def generate_link_chunk(md: str) -> dict[str, str | list[dict]]:
    """
    마크다운 문자열에서 link에 해당하는 부분을 전부 공백으로 치환하고 link 타입 청크를 생성합니다.

    Args:
        md(str): image가 제거된 마크다운 문자열

    Returns:
        dict: 다음 두 개의 key를 포함한 딕셔너리
            - md_without_link(str): 모든 링크가 공백으로 치환된 마크다운 문자열
            - link_raw_chunks(list[dict]): link 타입 청크 리스트 (file_name, page_num 키 생성 전)
    """

    # link 찾기
    link_extractor = URLExtract()
    links = link_extractor.find_urls(md)

    link_raw_chunks = [] # link 타입 raw chunk들 저장할 배열 (page_num, file_name이 붙기 전)

    for link in links: # 찾은 링크들에 대해 해당 부분을 공백으로 치환하고 청크 생성해서 chunk_collection에 저장

        link_pattern = re.compile(re.escape(link)) # 현재 link를 정규식으로 추출

        for link_match in re.finditer(link_pattern, md):

            link_start = link_match.start()
            link_end = link_match.end()

            # link에 대한 metadata로 쓸 문맥 추출
            context_start = max(0, link_start - 100)
            context_end = min(len(md), link_end + 100)
            context_snippet = md[context_start:link_start] + md[link_end:context_end]

            # 청크로 만들어서 link_raw_chunks 배열에 저장
            link_raw_chunks.append({
                "type": "link",
                "content": link,
                "metadata": context_snippet,
                "start_index": context_start, # page_num 만드는 함수 통과하면서 없어질 키
                "end_index": context_end # 이것도 마찬가지
            })

        # link 부분 공백으로 치환 (이전 루프의 link가 제거된 md가 다음 루프로 전달됨)
        md = link_pattern.sub(lambda m: " " * len(m.group(0)), md)

    link_dict = {
        "md_without_link": md,
        "link_raw_chunks": link_raw_chunks
    }
    
    return link_dict

def generate_table_chunk(md: str) -> dict[str, str | list[dict]]:
    """
    마크다운 문자열에서 table에 해당하는 부분을 전부 공백으로 치환하고 table 타입 청크를 생성합니다.
    같은 파일 내에 table이 여러개 있는 경우 각 table 별로 청크를 생성합니다.
    
    단, 테이블과 테이블 사이에 그 어떤 문자도 없고 바로 다음 테이블이 등장하는 경우에는 두개의 테이블이 하나의 청크로 묶이게 됩니다.
    이 경우를 대비하는 로직이 어려워서 아직 만들지 못했는데 추후 보강할 수 있다면 보강하겠습니다.

    table에 해당하는 마크다운 문자열에서 |와 -를 공백으로 치환합니다. 또한, 한 table에 속하는 내용을 여러 청크로 나누지 않고 하나의 청크로 생성합니다.

    Args:
        md(str): link가 제거된 마크다운 문자열

    Returns:
        dict: 다음 두 개의 key를 포함한 딕셔너리
            - md_without_table(str): 모든 표가 공백으로 치환된 마크다운 문자열
            - table_raw_chunks(list[dict]): table 타입 청크 리스트 (file_name, page_num 키 생성 전)
    """

    # table 정규식
    table_pattern = re.compile(
        r"((?:^\s*\|.*\n)+)", # |로 시작하는 라인이 발견되면, |로 시작하지 않는 라인이 나올 때 까지 계속해서 한 덩어리로 합쳐서 매칭
        re.MULTILINE
    )

    table_raw_chunks = [] # link 타입 raw chunk들 저장할 배열 (page_num, file_name이 붙기 전)

    for table_match in re.finditer(table_pattern, md):

        table_str = table_match.group(0)
        table_start_index = table_match.start()
        table_end_index = table_match.end() - 1

        replaced_table_str = re.sub(r"[|\-]", " ", table_str) # | 또는 -을 전부 공백으로 치환

        # 청크로 만들어서 table_chunks 배열에 저장
        table_raw_chunks.append({
            "type": "table",
            "content": replaced_table_str,
            "start_index": table_start_index,
            "end_index": table_end_index
        })

    # table 부분 공백으로 치환
    md = table_pattern.sub(lambda m: " " * len(m.group(0)), md)

    table_dict = {
        "md_without_table": md,
        "table_raw_chunks": table_raw_chunks
    }
        
    return table_dict

def generate_text_chunk(md: str) -> list:
    """
    마크다운 형식 문자열에 Header(# ~ ######)가 포함됐는지 여부에 따라 분기해서 text 타입 청크를 생성합니다.

    Header가 포함된 문자열이라면, 같은 header path를 공유하는 텍스트 단위로 청킹합니다.
    각 청크 앞에는 해당 청크의 header path 문자열을 결합해서 retrieve 시 각 청크에 대해 맥락정보가 효과적으로 반영되도록 하였습니다.
    header path란, 각 청크가 속한 header가 속한 최상위 header까지의 모든 header를 공백 하나를 사이에 두고 이어붙인 문자열입니다.

    Header가 포함되지 않은 문자열이라면, Recursive Chunking 합니다.
    청크 하나의 크기는 1000자, overlap 크기는 200자 입니다.

    Args:
        md(str): table이 제거된 마크다운 문자열

    Returns:
        list: text 타입 청크 리스트 (file_name, page_num 키 생성 전)
    """

    header_pattern = re.compile(r"^#{1,6}\s", re.MULTILINE) # header 패턴
    has_header = bool(header_pattern.search(md)) # header 존재여부 판단

    text_raw_chunks = [] # text 타입 raw chunk들 저장할 배열 (page_num, file_name이 붙기 전)

    if has_header: # header가 있는 문서인 경우

        header_hierarchy = [] # Header 문장의 앞에 # 부분만 저장
        header_titles = [] # Header 문장의 # 제외 제목 부분만 저장
        texts = {} # 텍스트를 누적해서 저장할 문자열 (header path가 달라지면 초기화)

        # \n으로 끝나는 문자열(문장)을 매칭하는 정규식
        line_pattern = re.compile(
            r".*?\n|.*$",
            re.DOTALL)

        header_capture_pattern = re.compile(r"^(#{1,6})\s(.*)") # header 정보 캡쳐용 패턴

        for line_match in re.finditer(line_pattern, md):

            line = line_match.group(0) # 현재 line의 내용

            if not line.strip():
                continue

            header_match = header_capture_pattern.match(line) # Header로 시작하는 문장인지 정규식 적용

            if header_match: # Header로 시작하는 문장이라면
                
                if texts: # 여태 누적돼있는 texts가 있다면 raw text chunk 제작해서 append
                    text_raw_chunks.append({
                        "type": "text",
                        "content": texts['content'],
                        "start_index": texts['start_index'],
                        "end_index": texts['end_index']
                    })

                    texts = {} # texts 딕셔너리 초기화

                hashs = header_match.group(1).strip() # 현재 hashs
                title = header_match.group(2).strip() # 현재 title

                current_level = len(hashs) # 현재 level

                while header_hierarchy: # header_hierarchy 배열이 비어있지 않을 동안 반복

                    if len(header_hierarchy[-1]) >= current_level: # header_hierarchy 배열의 끝부터 검사하면서 현재 레벨보다 같거나 낮은 레벨이라면 pop
                        header_hierarchy.pop()
                        header_titles.pop()

                    else: # 현재 레벨보다 높다면 append
                        break

                header_hierarchy.append(hashs)
                header_titles.append(title)

            else: # Header로 시작하지 않는 일반 텍스트 문장이라면

                if not texts: # 기존에 쌓인 text가 없다면 header path 만들어서 현재 문장 내용이랑 문자열 결합
                    header_path = " > ".join(header_titles) # 현재 header path

                    # header path와 결합한 content 만들기
                    if header_path:
                        content = header_path + " " + line
                    else:
                        content = line

                    texts['content'] = content
                    texts['start_index'] = line_match.start()
                    texts['end_index'] = line_match.end() - 1

                else: # 기존에 쌓인 text가 있다면 그냥 텍스트만 append
                    texts['content'] = texts['content'] + line
                    texts['end_index'] = line_match.end() - 1

        if texts: # 쌓인 texts가 있으면 text_raw_chunks에 append
            text_raw_chunks.append({
                "type": "text",
                "content": texts['content'],
                "start_index": texts['start_index'],
                "end_index": texts['end_index']
            })

    else: # header가 없는 문서인 경우 (Recursive Chunking)

        print("⚠️ No headers detected — applying RecursiveCharacterTextSplitter.")

        recursive_splitter = RecursiveCharacterTextSplitter(
            separators=[
                "\n\n",
                "\n",
                ". ",
                ", ",
                "! ",
                "? ",
                "; ",
                ": ",
                "- ",
                "• ",
                "\t",
                " "
            ],
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            is_separator_regex=False
        )

        recursive_split_mds = recursive_splitter.create_documents([md])
 
        for recursive_split_md in recursive_split_mds:

            text_pattern = re.escape(recursive_split_md.page_content)
            text_pattern = text_pattern.replace(r"\n", "\n")
            text_pattern = re.compile(text_pattern, re.DOTALL)

            text_match = text_pattern.search(md)

            if text_match:
                text_raw_chunks.append({
                    "type": "text",
                    "content": recursive_split_md.page_content,
                    "start_index": text_match.start(),
                    "end_index": text_match.end() - 1
                })
                
            else: # 청크 내용이 매칭이 안돼도 일단 인덱스 정보 0으로 해서 text raw chunk 만들고 append
                text_raw_chunks.append({
                    "type": "text",
                    "content": recursive_split_md.page_content,
                    "start_index": 0,
                    "end_index": 0
                })

    return text_raw_chunks

def attach_page_num_and_file_name(raw_chunks: list[dict], pages_info: list, file_name: str) -> list:
    """
    각 청크에 page_num과 file_name을 생성하고 start_index, end_index 키는 삭제합니다.

    Args:
        raw_chunks(list[dict]): 미완성 chunk 딕셔너리의 배열
        pages_info(list): get_pages_info() 함수가 반환한 각 페이지의 인덱스 범위 정보
        file_name(str): 사용자로부터 받은 md 파일의 이름

    Returns:
        list: 완전한 청크 리스트
    """

    for raw_chunk in raw_chunks:
        start_page = 0
        end_page = 0

        if raw_chunk['start_index'] == 0 and raw_chunk['end_index'] == 0:
            
            raw_chunk['page_num'] = [0]
            raw_chunk['file_name'] = file_name
            raw_chunk.pop('start_index', None)
            raw_chunk.pop('end_index', None)

            continue

        for page_num, (content_start_index, content_end_index) in pages_info:
            if content_start_index <= raw_chunk['start_index'] <= content_end_index:
                start_page = page_num

            if content_start_index <= raw_chunk['end_index'] <= content_end_index:
                end_page = page_num
                break

        raw_chunk['page_num'] = list(range(start_page, end_page + 1))
        raw_chunk['file_name'] = file_name
        raw_chunk.pop('start_index', None)
        raw_chunk.pop('end_index', None)

    return raw_chunks

def save_chunks_to_db(chunks: list[dict]) -> bool:
    """
    완성된 청크들을 현재 사용 중인 Chunk DB에 저장합니다.

    Args:
        chunks(list): 완성된 chunk 딕셔너리의 배열

    Returns:
        bool: 저장 성공여부
    """

    if not chunks:
        print("ℹ️ No chunks to save. Skipping DB insert.")
        return True

    try:
        chunk_collection.insert_many(chunks)
        print(f"✅ Saved {len(chunks)} chunks to DB.")
        return True

    except Exception as e:
        print(f"❌ Failed to save chunks")
        traceback.print_exc()
        return False

def chunk_markdown_file(file_path: Path) -> bool:
    """
    주어진 markdown 텍스트 파일을 chunking하고, 완성된 청크들을 Chunk DB에 저장합니다.

    Args:
        file_path(Path): 처리할 markdown 파일 경로

    Returns:
        bool: chunking 프로세스 성공여부
            - True: chunking 및 DB 저장 성공
            - False: chunking 과정 또는 저장 과정에서 오류 발생
    """

    try:
        with file_path.open("r", encoding="utf-8") as f:
            md = f.read()

            pages_info = get_pages_info(md) # page 인덱스 범위 정보 추출

            md_without_page = remove_page(md) # >>> page 마커 제거

            image_dict = generate_image_chunk(md_without_page) # image 타입 처리
            md_without_image = image_dict['md_without_image']
            raw_chunks = image_dict['image_raw_chunks'].copy()

            link_dict = generate_link_chunk(md_without_image) # link 타입 처리
            md_without_link = link_dict['md_without_link']
            raw_chunks = link_dict['link_raw_chunks'].copy()

            # table_dict = generate_table_chunk(md_without_link) # table 타입 처리
            # md_without_table = table_dict['md_without_table']
            # raw_chunks.extend(table_dict['table_raw_chunks'])

            text_raw_chunks = generate_text_chunk(md_without_link) # text 타입 처리
            raw_chunks.extend(text_raw_chunks)

            chunks = attach_page_num_and_file_name(raw_chunks, pages_info, file_path.stem) # raw chunks에 page_num, file_name 추가

            return save_chunks_to_db(chunks) # 청크들 DB에 저장

    except Exception as e:
        print(f"😢 Chunking failed for {file_path.name}: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":

    # 샘플로 사용할 markdown data 불러오기
    # 현재는 프로젝트 내부에 있는 샘플 데이터 폴더에서 불러옵니다.

    BASE_DIR = Path(__file__).resolve().parent # 현재폴더의 경로
    markdown_sample_data_folder_path = BASE_DIR / "markdown_sample_data" # 샘플로 쓸 markdown 데이터 폴더의 경로

    for file_path in markdown_sample_data_folder_path.rglob("*.md"): # md 파일만 순회돌기

        is_chunking_succeeded = chunk_markdown_file(file_path)

        if is_chunking_succeeded:
            print(f"🎉 Chunking succeeded for {file_path.name}")
