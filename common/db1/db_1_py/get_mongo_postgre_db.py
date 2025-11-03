from pymongo import MongoClient
from dotenv import load_dotenv
from pymongo.errors import ConnectionFailure
import os

"""
[DB관련]

데이터베이스 연결을 관리하고 생성하는 모듈.

이 모듈은 어플리케이션의 다른 부분에서 필요로 하는 MongoDB와 PostgreSQL
데이터베이스 연결 객체를 생성하는 함수를 제공합니다. 연결 정보는 .env 파일에서
환경 변수를 로드하여 사용합니다.

주요 기능:
- `get_mongodb()`: MongoDB 서버에 연결하고 데이터베이스 객체를 반환합니다.
- `get_postgres()`: PostgreSQL 서버에 연결하고 커넥션 객체를 반환합니다.
- PostgreSQL 드라이버(`psycopg2`)가 없을 경우, 사용자에게 알리는 예외 처리를 포함합니다.

이 스크립트를 직접 실행하면 각 데이터베이스에 대한 연결 테스트를 수행합니다.
"""

try:
    import psycopg2
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    print("psycopg2가 설치되지 않았습니다. PostgreSQL 기능을 사용할 수 없습니다.")

# mongodb 연결
def get_mongodb():
    load_dotenv()

    USERNAME = os.getenv("MONGO_INITDB_ROOT_USERNAME")
    PASSWORD = os.getenv("MONGO_INITDB_ROOT_PASSWORD")
    HOST = os.getenv("MONGO_HOST")
    PORT = int(os.getenv("MONGO_PORT"))

    url = f"mongodb://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/"

    try:
        client = MongoClient(url)
        client.admin.command('ping')
        print("Successfully connected to MongoDB!")
        db = client['md_db']
        print("✅ MongoDB 연결 성공")
        return db

    except ConnectionFailure as e:
        print(f"MongoDB connection failed: {e}")




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

mongodb = get_mongodb()
postgres = get_postgres()

if mongodb is not None:
    print(f"사용 가능한 컬렉션: {mongodb.list_collection_names()}")


if mongodb is not None:
    cursor = postgres.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print("✅ nPostgreSQL 연결 성공")
    postgres.close()
