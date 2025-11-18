from __future__ import annotations
import json
from get_mongo_postgre_db import get_mongodb, get_postgres
from msds_db_section1_pipeline import extract_section1_and_fields_from_text
from msds_db_section1_slicer import slice_section1_debug
from msds_db_create_pg_tables import init_msds_schema, check_tables_exist, save_current_parse_to_postgres
from msds_db_ingredients_pipeline import extract_section23_and_ingredients

"""
[pipeline]

MSDS 자동 분석 및 데이터베이스 저장 파이프라인 실행 스크립트.

이 스크립트는 전체 MSDS(물질안전보건자료) 분석 파이프라인을 실행하는
메인 진입점(entry point)입니다.

프로세스 흐름:
1.  **데이터베이스 연결**: `get_mongo_postgre_db` 모듈을 사용하여 MongoDB와
    PostgreSQL에 연결합니다.
2.  **데이터 로딩**: MongoDB에서 분석할 특정 MSDS 문서를 `document_id`를
    이용하여 가져옵니다.
3.  **섹션 1 분석**: `msds_db_section1_pipeline` 모듈을 호출하여 문서에서
    섹션 1(제품 및 회사 정보)을 추출하고, 제품명과 회사명을 분석합니다.
4.  **섹션 2/3 분석**: `msds_db_ingredients_pipeline` 모듈을 호출하여
    문서에서 섹션 2 또는 3(구성성분 정보)을 추출하고, LLM을 통해 구조화된
    성분 데이터를 생성한 뒤 후처리합니다.
5.  **데이터베이스 스키마 초기화**: `msds_db_create_pg_tables` 모듈을 통해
    PostgreSQL에 데이터 저장을 위한 테이블과 인덱스가 준비되었는지 확인하고
    필요 시 생성합니다.
6.  **데이터 저장**: 분석이 완료된 제품 정보와 성분 정보를 PostgreSQL
    데이터베이스에 저장합니다.
7.  **결과 검증**: 데이터베이스에 저장된 내용의 일부를 다시 조회하여
    저장 과정이 성공적으로 완료되었는지 간단히 확인합니다.

실행 전 요구사항:
- `.env` 파일에 MongoDB 및 PostgreSQL 연결 정보가 올바르게 설정되어 있어야 합니다.
- 로컬 Ollama 서버가 실행 중이어야 합니다.
- 필요한 모든 파이썬 라이브러리가 설치되어 있어야 합니다.
"""


# ================= MongoDB에서 문서 가져오기 ==================
print("\n[INFO] MongoDB에서 MSDS 문서 조회 중...")

mongodb = get_mongodb()
if mongodb is None:
    raise RuntimeError("MongoDB 연결 실패")

collection = mongodb['msds_markdown_collection']
document_id = 'MOCK_MSDS_007'
doc = collection.find_one({'document_id': document_id})

if doc is None:
    raise RuntimeError("MongoDB에서 MSDS 문서를 찾을 수 없습니다.")

md_path = doc.get('file_name', 'unknown.pdf')
text = doc.get('content', '')

if not text:
    raise ValueError(f"문서 content가 비어있습니다. document_id={doc.get('document_id')}")

print(f"문서 로딩 완료: {doc.get('document_id')} - {md_path}")
print("="*80)

# ================= section 1 정보 추출 ==================
section1_result = extract_section1_and_fields_from_text(text)

# Section 1 추출 결과를 출력
print(json.dumps(section1_result, ensure_ascii=False, indent=2))

sec1_text, dbg = slice_section1_debug(text)
print("\n" + "="*80)
print("== Section 1 전체 슬라이스 ==")
print(f"(start_idx={dbg['start_idx']}, end_idx={dbg['end_idx']}, next={dbg['found_next']})")
print("-"*80)
print(sec1_text)
print("="*80 + "\n")


# ================= ingredients ==================
sec23_result = extract_section23_and_ingredients(text, debug=True)

# 디버그 출력용
print("\n== 최종 ingredients (JSON) ==")
print(json.dumps(sec23_result["ingredients"], ensure_ascii=False, indent=2))

print("\n" + "="*80)
print("== 추출된 Section 2/3 CLEAN 블록 ==")
print(f"(start_idx={sec23_result['section_info']['start_idx']}, "
      f"end_idx={sec23_result['section_info']['end_idx']}, "
      f"section={sec23_result['section_info']['found_section']})")
print("-"*80)
print(sec23_result["section2_3_text"])
print("="*80)

# ================= PostgreSQL 저장 ==================
# 1) PostgreSQL 연결
conn = get_postgres()

# 스키마 초기화
init_msds_schema(conn)

# 생성된 테이블 확인
check_tables_exist(conn)

# 2) 저장 호출 (파싱된 변수들을 그대로 전달)
try:
    pid = save_current_parse_to_postgres(
        conn=conn,
        md_path=md_path,
        section1_result=section1_result,
        sec1_text=sec1_text,
        ingredients=sec23_result["ingredients"],
        document_id=document_id
    )
    print("저장된 product_id =", pid)
except Exception as e:
    import traceback
    traceback.print_exc()
    raise

# 3) 검증(옵션)
with conn.cursor() as cur:
    cur.execute("SELECT id, file_name, product_name, company_name FROM products WHERE id = %s", (pid,))
    print("-"*80)
    print("products:", cur.fetchone())
    
    cur.execute("SELECT name, cas, conc_min, conc_max, conc_unit FROM ingredients WHERE product_id = %s ORDER BY id", (pid,))
    print("-"*80)
    print("ingredients:", cur.fetchall())

conn.close()
