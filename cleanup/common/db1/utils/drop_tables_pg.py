import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'db_1_py'))

from get_mongo_postgre_db  import get_postgres

def drop_all_msds_tables(conn):
    """모든 MSDS 테이블 삭제 (주의: 데이터 손실)"""
    with conn.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS ingredient_synonyms CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS ingredients CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS products CASCADE;")
    conn.commit()
    print("모든 MSDS 테이블이 삭제되었습니다.")


conn = get_postgres()
drop_all_msds_tables(conn)