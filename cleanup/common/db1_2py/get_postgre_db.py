from dotenv import load_dotenv
import os
import psycopg2

"""
[DB관련]

데이터베이스 연결을 관리하고 생성하는 모듈.

이 모듈은 어플리케이션의 다른 부분에서 필요로 하는 MongoDB와 PostgreSQL
데이터베이스 연결 객체를 생성하는 함수를 제공합니다. 연결 정보는 .env 파일에서
환경 변수를 로드하여 사용합니다.

주요 기능:
- `get_postgres()`: PostgreSQL 서버에 연결하고 커넥션 객체를 반환합니다.

이 스크립트를 직접 실행하면 각 데이터베이스에 대한 연결 테스트를 수행합니다.
"""

# PostgreSQL 연결
def get_postgres():
    load_dotenv()

    password = os.getenv('POSTGRES_PASSWORD')
    if not password:
        raise ValueError("POSTGRES_PASSWORD 환경 변수가 설정되지 않았습니다. .env 파일을 확인하세요.")

    return psycopg2.connect(
        host=os.getenv('PG_HOST', 'localhost'),
        port=int(os.getenv('PG_PORT', 5432)),
        database=os.getenv('PG_DATABASE', 'CoreDB'),
        user=os.getenv('PG_USER', 'promtree'),
        password=password,
        connect_timeout=10
    )
    


print("=" * 50)
print("DB 연결 테스트")
print("=" * 50)

postgres = get_postgres()


if postgres is not None:
    cursor = postgres.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print("✅ nPostgreSQL 연결 성공")
    postgres.close()
