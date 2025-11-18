'''
1. markdown it py 를 활용해서 md파일에서 제목만 골라내기
2. 1에서 골라낸 제목 중에서 LLM에게 기본정보와 구성성분이 들어있는 섹션 골라내기
3. 2에서 골라낸 기본정보와 구성성분 섹션을 분해, 같은 패턴의 다음 제목 
4. 전체 텍스트 전처리(이미지 태그, 페이지 태그 등)
5. 4에서 전처리한 텍스트를 기준으로 슬라이싱
6. 슬라이싱 한 텍스트를 바탕으로 LLM으로 정보 추출
'''
import json
from pathlib import Path
import re
import traceback

from msds_get_key_section_headers_with_llm import get_key_section_headers_with_llm
from msds_extract_sections_with_markdown_it import extract_sections_with_markdown_it
from msds_find_next_main_header import find_next_main_header
from msds_preprocess_md_text import preprocess_md_text
from msds_extract_section_content import extract_section_content
from msds_extract_integrated_sds_info_LLM import extract_integrated_sds_info

from get_postgre_db import get_postgres
from msds_db_create_pg_tables import init_msds_schema, check_tables_exist, save_current_parse_to_postgres

# --- 설정 ---
MODEL = "gpt-oss:20b"
OLLAMA_URL = "https://bcb7tjvf0wm6jb-11434.proxy.runpod.net/api/generate"
MD_DIRECTORY = "testmd/testmd_p"

def create_flexible_pattern(header_str):
    """
    헤더 문자열을 기반으로 유연한 정규식 패턴을 생성합니다.
    문자열 내부의 모든 공백을 '\\s+'로 변환하여 다양한 공백 차이를 무시합니다.
    """
    if not header_str:
        return None
    
    # 1. re.escape()로 모든 특수문자(.)를 처리
    escaped_str = re.escape(header_str.strip())
    
    # 2. 이스케이프된 일반 공백('\\ ')을 '하나 이상의 공백'(\\s+)으로 교체
    flexible_str = escaped_str.replace('\\ ', '\\s+')
    
    # 3. 줄 시작과 마크다운 헤더 문자를 고려한 최종 패턴을 완성
    return f"^[#\\s]*{flexible_str}"


def main(md_text):
    """
    md_text로 md 문자열을 받아 결과 출력
    """

    conn = None

    try:
        print("[DB] PostgreSQL에 연결합니다...")
        conn = get_postgres()
        print("[DB] 스키마를 초기화하고 테이블 존재 여부를 확인합니다.")
        init_msds_schema(conn)
        check_tables_exist(conn)
    except Exception as e:
        print(f"[CRITICAL ERROR] 데이터베이스 초기화 중 오류 발생: {e}")
        if conn:
            conn.close()
        return
    
    # 1단계: 헤더 구조 추출 (모듈에서 함수 임포트)
    sections, tables = extract_sections_with_markdown_it(md_text)
    # print(sections)
    if not sections:
        print("  - [결과] 추출된 헤더가 없어 다음 파일로 넘어갑니다.")
        pass

    print(f"  - [1단계] {len(sections)}개의 헤더를 성공적으로 추출했습니다.")

    # 2단계: LLM 호출 (모듈에서 함수 임포트)
    print("  - [2단계] LLM에게 핵심 섹션 제목을 요청합니다...")
    key_headers = get_key_section_headers_with_llm(
        sections, 
        model=MODEL,
        ollama_url=OLLAMA_URL
    )

    # LLM으로 추출한 섹션 헤더 저장
    id_header = key_headers.get("identification_header")
    comp_header = key_headers.get("composition_header")
    print(id_header, comp_header)

    # 둘 중 하나라도 없는 경우 우선 패스
    if id_header == None or comp_header == None or len(id_header) == 0 or len(comp_header) == 0 :
        print('id_header = ',id_header, 'comp_header = ', comp_header)
        pass

    # LLM으로 추출한 섹션 헤더를 바탕으로 다음 헤더 추출
    next_id_header = find_next_main_header(sections, id_header)
    next_comp_header = find_next_main_header(sections, comp_header)
    print(id_header, next_id_header)
    print(comp_header, next_comp_header)

    # md 텍스트 전처리 
    text = preprocess_md_text(md_text)

    # 섹션 슬라이스 전 정규식 패턴 적용
    start_id_pattern = create_flexible_pattern(id_header)
    end_id_pattern = create_flexible_pattern(next_id_header)
    start_comp_pattern = create_flexible_pattern(comp_header)
    end_comp_pattern = create_flexible_pattern(next_comp_header)

    # 섹션 슬라이스
    id_text = extract_section_content(text, start_id_pattern, end_id_pattern)
    comp_text = extract_section_content(text, start_comp_pattern, end_comp_pattern)

    # LLM에서 구성성분 출력
    llm_input_text = id_text.strip() + "\n\n" + comp_text.strip()

    llm_result = extract_integrated_sds_info(llm_input_text)
    
    if llm_result:
        actual_result = None
        
        if isinstance(llm_result, list):
            if not llm_result:
                print("  - [WARN] LLM 결과가 빈 리스트이므로 처리를 건너뜁니다.")
            else:
                actual_result = llm_result[0]
        else:
            actual_result = llm_result

        if isinstance(actual_result, dict):
            product_name_from_llm = actual_result.get("product_name")
            
            if not product_name_from_llm:
                print(f"  - [WARN] LLM이 제품명을 추출하지 못해 DB 저장을 건너뜁니다.")
            else:
                try:
                    pid = save_current_parse_to_postgres(
                        conn=conn,
                        section1_result=actual_result,
                        sec1_text=id_text,
                        ingredients=actual_result.get("ingredients", []),
                    )
                    print(f"  - [DB] 성공적으로 저장되었습니다. (product_id = {pid})")

                except Exception as e:
                    print(f"  - [DB ERROR] 데이터를 저장하는 중 오류가 발생했습니다.")
                    traceback.print_exc()
                    print("  - [DB] 트랜잭션을 롤백합니다.")
                    if conn:
                        conn.rollback()


        elif actual_result is not None:
            print(f"  - [WARN] 처리할 수 없는 형태의 데이터이므로 DB 저장을 건너뜁니다. (데이터: {actual_result})")


    else:
        print("  - [결과] 최종 정보 추출 LLM으로부터 유효한 결과를 받지 못했습니다.")


