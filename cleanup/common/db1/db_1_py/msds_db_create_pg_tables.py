import json
from pathlib import Path

"""
[DB관련]

MSDS 데이터 저장을 위한 PostgreSQL 데이터베이스 스키마 관리 모듈.

- init_msds_schema: products, ingredients, ingredient_synonyms 테이블과 인덱스를 생성
- save_current_parse_to_postgres: 파싱된 제품/성분 정보를 받아 저장(업서트)
"""


def create_products_table(conn):
    """제품(MSDS 문서) 정보 저장 테이블 생성"""
    with conn.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id BIGSERIAL PRIMARY KEY,
                file_name TEXT NOT NULL,
                document_id TEXT NOT NULL,
                product_name TEXT NOT NULL,
                company_name TEXT,
                UNIQUE (file_name, product_name)
            );
        """)
    conn.commit()
    print("products 테이블 생성 완료")

def create_ingredients_table(conn):
    """성분 정보 저장 테이블 생성"""
    with conn.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingredients (
                id BIGSERIAL PRIMARY KEY,
                product_id BIGINT NOT NULL,
                name TEXT,
                cas TEXT,
                ec_number TEXT,
                conc_raw TEXT,
                conc_value NUMERIC,
                conc_min NUMERIC,
                conc_max NUMERIC,
                conc_unit TEXT,
                conc_basis TEXT,
                conc_op_min TEXT,
                conc_op_max TEXT,
                conc_adjusted NUMERIC,
                is_cas_secret BOOLEAN DEFAULT FALSE,
                is_conc_secret  BOOLEAN DEFAULT FALSE,
                synonym_jsonb JSONB,
                additional_info JSONB,
                CONSTRAINT fk_ingredients_products
                    FOREIGN KEY (product_id) REFERENCES products(id)
                    ON DELETE CASCADE
            );
        """)
    conn.commit()
    print("ingredients 테이블 생성 완료")

def create_ingredient_synonyms_table(conn):
    """성분 동의어 저장 테이블 생성"""
    with conn.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingredient_synonyms (
                id BIGSERIAL PRIMARY KEY,
                ingredient_id BIGINT NOT NULL,
                synonym TEXT NOT NULL,
                CONSTRAINT uq_ing_syn UNIQUE (ingredient_id, synonym),
                CONSTRAINT fk_syn_ingredient
                    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id)
                    ON DELETE CASCADE
            );
        """)
    conn.commit()
    print("ingredient_synonyms 테이블 생성 완료")

def create_indexes(conn):
    """데이터 조회 성능 향상을 위해 주요 컬럼에 인덱스를 생성"""
    with conn.cursor() as cursor:
        # CAS 번호 조회용 인덱스
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ingredients_cas 
            ON ingredients(cas);
        """)
        # 농도 범위 검색용 복합 인덱스
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ingredients_conc 
            ON ingredients(conc_unit, conc_basis, conc_min, conc_max);
        """)
        # JSONB 동의어 검색용 GIN 인덱스
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ingredients_syn_gin 
            ON ingredients USING GIN (synonym_jsonb);
        """)
    conn.commit()
    print("인덱스 생성 완료")




def init_msds_schema(conn):
    """MSDS 스키마 전체 초기화 (테이블 + 인덱스)"""
    print("=" * 50)
    print("MSDS PostgreSQL 스키마 초기화")
    print("=" * 50)

    create_products_table(conn)
    create_ingredients_table(conn)
    create_ingredient_synonyms_table(conn)
    create_indexes(conn)

    print("\n모든 테이블 및 인덱스 생성 완료")

def check_tables_exist(conn):
    """생성된 테이블 확인"""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
              AND table_name IN ('products', 'ingredients', 'ingredient_synonyms')
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()

    print("\n 생성된 테이블 목록:")
    for table in tables:
        print(f"  - {table[0]}")
    return [t[0] for t in tables]



def upsert_product(conn, file_name: str, document_id: str, product_name: str, company_name: str | None = None):
    sql = """
        INSERT INTO products (file_name, document_id, product_name, company_name)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (file_name, product_name)
        DO UPDATE SET 
            document_id = EXCLUDED.document_id,
            company_name = EXCLUDED.company_name
        RETURNING id;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (file_name, document_id, product_name, company_name))
        row = cur.fetchone()
        if not row:
            raise RuntimeError("RETURNING id 결과가 없습니다")
        pid = row[0]
    conn.commit()
    return pid


def insert_ingredient(conn, product_id: int, ing: dict) -> int:
    """ingredients에 한 개 성분 삽입 후 id 반환"""
    c = ing.get("concentration") or {}
    syn = ing.get("synonym") or []
    add = ing.get("additional_info") or {}

    sql = """
        INSERT INTO ingredients (
            product_id, name, cas, ec_number,
            conc_raw, conc_value, conc_min, conc_max,
            conc_unit, conc_basis, conc_op_min, conc_op_max,
            conc_adjusted, is_cas_secret, is_conc_secret,
            synonym_jsonb, additional_info
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s,
            %s::jsonb, %s::jsonb
        )
        RETURNING id;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (
            product_id,
            ing.get("name"),
            ing.get("cas"),
            ing.get("ec_number"),
            c.get("raw"),
            c.get("value"),
            c.get("min"),
            c.get("max"),
            c.get("unit"),
            c.get("basis"),
            c.get("op_min"),
            c.get("op_max"),
            ing.get("conc_adjusted"),
            ing.get("is_cas_secret", False),
            ing.get("is_conc_secret", False),
            json.dumps(syn, ensure_ascii=False),
            json.dumps(add, ensure_ascii=False),
        ))
        ingredient_id = cur.fetchone()[0]
        conn.commit()
    return ingredient_id

def insert_synonyms_rows(conn, ingredient_id: int, synonyms: list[str]):
    """ingredient_synonyms 테이블에 동의어 다건 삽입"""
    if not synonyms:
        return
    sql = """
        INSERT INTO ingredient_synonyms (ingredient_id, synonym)
        VALUES (%s, %s)
        ON CONFLICT (ingredient_id, synonym) DO NOTHING;
    """
    with conn.cursor() as cur:
        for s in synonyms:
            if s and s.strip():
                cur.execute(sql, (ingredient_id, s.strip()))
    conn.commit()



def save_current_parse_to_postgres(
    conn,
    md_path: str,
    section1_result: dict,
    sec1_text: str,
    ingredients: list[dict],
    document_id: str | None = None
) -> int:
    # 1) 제품 upsert
    file_name = Path(md_path).name
    product_name = section1_result.get("product_name")
    company_name = section1_result.get("company_name")

    if document_id is None:
        document_id = file_name

    print(file_name, product_name, company_name, document_id)

    product_id = upsert_product(
        conn,
        file_name=file_name,
        document_id=document_id,
        product_name=product_name,
        company_name=company_name
    )

    # 2) 성분 저장
    for it in ingredients:
        ing_id = insert_ingredient(conn, product_id, it)
        insert_synonyms_rows(conn, ing_id, it.get("synonym") or [])

    return product_id
