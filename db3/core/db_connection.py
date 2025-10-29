"""
[핵심] DB Connection Module

역할:
- MongoDB 연결 관리 (마크다운 문서 저장소)
- PostgreSQL 연결 관리 (추출된 물성 데이터 저장소)

환경 변수 (.env):
    MONGO_USERNAME, MONGO_PASSWORD, MONGO_HOST, MONGO_PORT
    PG_HOST, PG_PORT, PG_DATABASE, PG_USER, PG_PASSWORD

함수:
    get_mongodb()     → MongoDB Database 객체 (또는 None)
    get_postgresql()  → PostgreSQL Connection 객체 (또는 None)

특이사항:
    - MongoDB: authSource=admin, directConnection=true 설정
    - 연결 실패 시 None 반환 (에러 출력)
"""

from pymongo import MongoClient
from dotenv import load_dotenv
import os

try:
    import psycopg2
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    print("⚠️  psycopg2가 설치되지 않았습니다. PostgreSQL 기능을 사용할 수 없습니다.")


def get_mongodb():
    """
    MongoDB 연결

    Returns:
        MongoDB database object
    """
    try:
        load_dotenv()

        username = os.getenv("MONGO_USERNAME")
        password = os.getenv("MONGO_PASSWORD")
        host = os.getenv("MONGO_HOST", "localhost")
        port = int(os.getenv("MONGO_PORT", "27017"))

        url = f"mongodb://{username}:{password}@{host}:{port}/?authSource=admin&directConnection=true"

        client = MongoClient(url, serverSelectionTimeoutMS=3000)
        client.admin.command('ping')

        db = client['s307_db']
        print("✅ MongoDB 연결 성공")
        return db

    except Exception as e:
        print(f"❌ MongoDB 연결 실패: {e}")
        return None


def get_postgresql():
    """
    PostgreSQL 연결

    Returns:
        PostgreSQL connection object
    """
    if not POSTGRES_AVAILABLE:
        print("❌ PostgreSQL 사용 불가 (psycopg2 미설치)")
        return None

    try:
        load_dotenv()

        conn = psycopg2.connect(
            host=os.getenv("PG_HOST", "localhost"),
            database=os.getenv("PG_DATABASE", "tds_db"),
            user=os.getenv("PG_USER", "postgres"),
            password=os.getenv("PG_PASSWORD")
        )

        print("✅ PostgreSQL 연결 성공")
        return conn

    except Exception as e:
        print(f"❌ PostgreSQL 연결 실패: {e}")
        return None


if __name__ == "__main__":
    print("=" * 50)
    print("DB 연결 테스트")
    print("=" * 50)

    mongodb = get_mongodb()
    postgres = get_postgresql()

    if mongodb:
        print(f"\n사용 가능한 컬렉션: {mongodb.list_collection_names()}")

    if postgres:
        cursor = postgres.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"\nPostgreSQL 버전: {version[0]}")
        postgres.close()
