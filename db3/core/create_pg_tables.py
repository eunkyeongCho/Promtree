"""
[핵심] PostgreSQL 테이블 생성 및 스키마 관리

역할:
- tds_properties 테이블 생성 (최종 물성 데이터)
- temp_extraction 테이블 생성 (임시 추출 결과)
- 동적 스키마: 새로운 물성 발견 시 컬럼 자동 추가

주요 함수:
    get_postgres()              → PostgreSQL 연결
    create_tds_table(conn)      → tds_properties 테이블 생성
    create_temp_table(conn)     → temp_extraction 테이블 생성
    ensure_column_exists(property_key, conn)  → 컬럼 동적 추가

테이블 구조:
    tds_properties:
        - id (SERIAL PRIMARY KEY)
        - document_id (VARCHAR UNIQUE)
        - {property}_value (FLOAT)    ← 동적 추가
        - {property}_unit (VARCHAR)    ← 동적 추가
        - created_at, updated_at (TIMESTAMP)

실행:
    python create_pg_tables.py  → 테이블 초기화
"""

import psycopg2
from dotenv import load_dotenv
import os

# .env 로드
load_dotenv()

# PostgreSQL 연결
def get_postgres():
    return psycopg2.connect(
        host=os.getenv('PG_HOST', 'localhost'),
        port=int(os.getenv('PG_PORT', 5432)),
        database=os.getenv('PG_DATABASE', 'CoreDB'),
        user=os.getenv('PG_USER', 'promtree'),
        password=os.getenv('PG_PASSWORD', 'ssafy13s307'),
        connect_timeout=10
    )

def create_tds_table(conn):
    """TDS 물성 정보 저장 테이블 생성"""
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tds_properties (
            id SERIAL PRIMARY KEY,
            document_id VARCHAR(100) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    print("✅ TDS 테이블 생성 완료")

def create_temp_table(conn):
    """임시 결과 저장 테이블"""
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS temp_extraction (
            id SERIAL PRIMARY KEY,
            document_id VARCHAR(100),
            property_field VARCHAR(100),
            property_value FLOAT,
            property_unit VARCHAR(50),
            confidence FLOAT,
            source_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    print("✅ Temp 테이블 생성 완료")

def ensure_column_exists(property_key, conn):
    """PostgreSQL에 컬럼이 없으면 자동 생성"""
    cursor = conn.cursor()

    # 컬럼명 정리
    col_name = property_key.replace(' ', '_').replace('(', '').replace(')', '').lower()

    # 컬럼 존재 확인
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name='tds_properties' AND column_name=%s
    """, (f"{col_name}_value",))

    if not cursor.fetchone():
        try:
            cursor.execute(f"""
                ALTER TABLE tds_properties
                ADD COLUMN {col_name}_value FLOAT,
                ADD COLUMN {col_name}_unit VARCHAR(50)
            """)
            conn.commit()
            print(f"✅ 새 컬럼 추가: {col_name}")
        except Exception as e:
            print(f"❌ 컬럼 추가 실패 ({col_name}): {e}")
            conn.rollback()

if __name__ == "__main__":
    print("=" * 50)
    print("PostgreSQL 테이블 생성")
    print("=" * 50)

    try:
        conn = get_postgres()
        print("✅ PostgreSQL 연결 성공")

        create_tds_table(conn)
        create_temp_table(conn)

        # 테스트: 샘플 컬럼 추가
        print("\n테스트: 샘플 물성 컬럼 추가")
        test_properties = ['Tg', 'Tm', 'Td', 'DC', 'YS', 'YM']
        for prop in test_properties:
            ensure_column_exists(prop, conn)

        conn.close()
        print("\n✅ 모든 테이블 생성 완료")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
