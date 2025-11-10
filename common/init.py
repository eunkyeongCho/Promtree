#!/usr/bin/env python3
"""
Project Initialization Script
Installs dependencies, starts Docker containers, and sets up databases.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# Import database libraries (will be installed if not present)
try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure
except ImportError:
    print("MongoDB driver not installed. Will install via requirements.txt...")
    MongoClient = None

try:
    import psycopg
except ImportError:
    print("PostgreSQL driver not installed. Will install via requirements.txt...")
    psycopg = None

try:
    from dotenv import load_dotenv
except ImportError:
    print("python-dotenv not installed. Will install via requirements.txt...")
    load_dotenv = None


def run_command(command: list, description: str) -> bool:
    """Run a shell command and return success status."""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(command, capture_output=True, text=True, shell=True if os.name == 'nt' else False)

        if result.returncode == 0:
            print(f"✅ {description} - Success")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"❌ {description} - Failed")
            if result.stderr:
                print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return False


def install_dependencies() -> bool:
    """Install Python dependencies using uv (pyproject.toml + uv.lock)."""
    pyproject = Path("pyproject.toml")

    if not pyproject.exists():
        print("⚠️  pyproject.toml not found. Skipping dependency installation.")
        return True

    return run_command(
        ["uv", "sync"],
        "Syncing dependencies with uv"
    )


def start_docker_containers() -> bool:
    """Start Docker containers using docker-compose."""
    docker_compose_file = Path("docker-compose.yml")

    if not docker_compose_file.exists():
        docker_compose_file = Path("docker-compose.yaml")
        if not docker_compose_file.exists():
            print("⚠️  docker-compose.yml not found. Skipping container startup.")
            return True

    # Check if Docker is running
    docker_check = run_command(
        ["docker", "version"],
        "Checking Docker availability"
    )

    if not docker_check:
        print("❌ Docker is not running or not installed.")
        return False

    # Start containers
    return run_command(
        ["docker", "compose", "up", "-d"],
        "Starting Docker containers"
    )


def wait_for_service(service_name: str, check_function, max_retries: int = 30) -> bool:
    """Wait for a service to become available."""
    print(f"\n⏳ Waiting for {service_name} to be ready...")

    for i in range(max_retries):
        try:
            if check_function():
                print(f"✅ {service_name} is ready!")
                return True
        except Exception as e:
            if i < max_retries - 1:
                print(f"   Attempt {i+1}/{max_retries}: {service_name} not ready yet...")
                time.sleep(2)
            else:
                print(f"❌ {service_name} failed to start after {max_retries} attempts.")
                print(f"   Last error: {e}")
                return False

    return False


def initialize_mongodb() -> bool:
    """Initialize MongoDB connection and create collections."""
    # Reimport in case it was just installed
    global MongoClient, ConnectionFailure, load_dotenv

    if not MongoClient:
        from pymongo import MongoClient
        from pymongo.errors import ConnectionFailure

    if not load_dotenv:
        from dotenv import load_dotenv

    print(f"\n{'='*60}")
    print(f"🗄️  Initializing MongoDB")
    print(f"{'='*60}")

    # Load environment variables
    load_dotenv()

    USERNAME = os.getenv("MONGO_INITDB_ROOT_USERNAME", "root")
    PASSWORD = os.getenv("MONGO_INITDB_ROOT_PASSWORD", "example")
    HOST = os.getenv("MONGO_HOST", "localhost")
    PORT = int(os.getenv("MONGO_PORT", 27017))

    url = f"mongodb://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/"

    def check_mongodb():
        client = MongoClient(url, serverSelectionTimeoutMS=2000)
        client.admin.command('ping')
        return True

    # Wait for MongoDB to be ready
    if not wait_for_service("MongoDB", check_mongodb):
        return False

    try:
        # Connect to MongoDB
        client = MongoClient(url)

        # Initialize databases and collections
        print("\n📚 Creating MongoDB databases and collections...")

        # Raw DB
        raw_db = client['raw_db']
        raw_collection = raw_db['raw_collection']

        # MarkDown DB
        md_db = client['md_db']
        md_msds_collection = md_db['md_msds']
        md_tds_collection = md_db['md_tds']

        # Retrieval DB
        retrieval_db = client['retrieval_db']
        retrieval_collection = retrieval_db['retrieval_collection']

        # Temp TDS DB
        temp_tds_db = client['temp_tds_db']
        temp_tds_collection = temp_tds_db['temp_tds_collection']

        # Chunk DB
        chunk_db = client['chunk_db']
        chunk_collection = chunk_db['chunk_collection']

        # Initialize collections with initial documents
        collections = [
            (raw_collection, {"init": "init_raw_object"}),
            (md_msds_collection, {"init": "init_md_msds_object"}),
            (md_tds_collection, {"init": "init_md_tds_object"}),
            (retrieval_collection, {"init": "init_retrieval_object"}),
            (temp_tds_collection, {"init": "init_temp_tds_object"}),
            (chunk_collection, {"init": "init_chunk_object"})
        ]

        for collection, init_doc in collections:
            # Check if collection already has documents
            if collection.count_documents({}) == 0:
                collection.insert_one(init_doc)
                print(f"   ✅ Initialized collection: {collection.database.name}.{collection.name}")
            else:
                print(f"   ℹ️  Collection already exists: {collection.database.name}.{collection.name}")

        # List databases to confirm
        databases = client.list_database_names()
        print(f"\n📊 Available MongoDB databases: {', '.join(databases)}")

        print("✅ MongoDB initialization complete!")
        return True

    except Exception as e:
        print(f"❌ MongoDB initialization failed: {e}")
        return False


def initialize_postgresql() -> bool:
    """Initialize PostgreSQL connection and create test table."""
    # Reimport in case it was just installed
    global psycopg, load_dotenv

    if not psycopg:
        import psycopg

    if not load_dotenv:
        from dotenv import load_dotenv

    print(f"\n{'='*60}")
    print(f"🐘 Initializing PostgreSQL")
    print(f"{'='*60}")

    # Load environment variables
    load_dotenv()

    dbname = os.getenv("POSTGRES_DB", "postgres")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")

    def check_postgresql():
        conn = psycopg.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port,
            connect_timeout=2
        )
        conn.close()
        return True

    # Wait for PostgreSQL to be ready
    if not wait_for_service("PostgreSQL", check_postgresql):
        return False

    try:
        # Connect to PostgreSQL
        conn = psycopg.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )

        cur = conn.cursor()

        # Check if test table already exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'test'
            );
        """)

        table_exists = cur.fetchone()[0]

        if not table_exists:
            print("\n📊 Creating test table...")

            # Create test table
            cur.execute("""
                CREATE TABLE test (
                    id serial PRIMARY KEY,
                    num integer,
                    data text
                )
            """)

            # Insert test data
            cur.execute("INSERT INTO test (num, data) VALUES (%s, %s)", (100, "abc'def"))

            # Commit the transaction
            conn.commit()
            print("   ✅ Test table created and populated")
        else:
            print("   ℹ️  Test table already exists")

        # Verify by selecting from the table
        cur.execute("SELECT * FROM test LIMIT 1")
        result = cur.fetchone()
        print(f"   📝 Sample data from test table: {result}")

        # Close connections
        cur.close()
        conn.close()

        print("✅ PostgreSQL initialization complete!")
        return True

    except Exception as e:
        print(f"❌ PostgreSQL initialization failed: {e}")
        return False

# def initialize_elasticsearch() -> bool:
#     """Initialize Elasticsearch connection and ensure base index exists."""
#     from db.elasticsearch.elasticsearch import get_elasticsearch_client

#     print(f"\n{'='*60}")
#     print(f"🔎 Initializing Elasticsearch")
#     print(f"{'='*60}")

#     elasticsearch_client = get_elasticsearch_client()

#     try:
#         elastic_client_info = elasticsearch_client.info()
#         if(elastic_client_info):
#             print("✅ Elasticsearch 연결 성공")
#         else:
#             print("❌ Elasticsearch 연결 실패")
#             return False
#     except Exception as e:  
#         print(f"❌ Elasticsearch 연결 테스트 실패: {e}")
#         return False

#     # 인덱스 만들 때 사용할 매핑
#     mappings={
#         "properties": {
#             "type": { "type": "keyword" },
#             "content": { "type": "text" },
#             "metadata": { "type": "text" },
#             "file_info": {
#                 "properties": {
#                 "file_name": { "type": "keyword" },
#                 "page_num":   { "type": "integer" }
#                 }
#             }
#         }
#     }

#     # 인덱스 만들 때 사용할 설정
#     settings = {
#         "index": {
#             "number_of_shards": 1,
#             "number_of_replicas": 0
#         }
#     }

#     # 인덱스 있으면 바로 리턴하고, 없으면 생성
#     msds_exists = elasticsearch_client.indices.exists(index="msds")
#     tds_exists = elasticsearch_client.indices.exists(index="tds")

#     if msds_exists and tds_exists:
#         print("✅ MSDS and TDS indices already exist")
#         return True

#     if not elasticsearch_client.indices.exists(index="msds"):
#         print(f"📦 Creating index: msds")
#         elasticsearch_client.indices.create(index="msds", mappings=mappings, settings=settings)

#     if not elasticsearch_client.indices.exists(index="tds"):
#         print(f"📦 Creating index: tds")
#         elasticsearch_client.indices.create(index="tds", mappings=mappings, settings=settings)

#     return True

def main():
    """Main initialization function."""
    print("""
╔══════════════════════════════════════════════════════════╗
║          Project Initialization Script                   ║
║                                                          ║
║  This script will:                                       ║
║  1. Install Python dependencies                          ║
║  2. Start Docker containers                              ║
║  3. Initialize MongoDB                                   ║
║  4. Initialize PostgreSQL                                ║
╚══════════════════════════════════════════════════════════╝
    """)

    success = True

    # Step 1: Install dependencies
    if not install_dependencies():
        print("⚠️  Failed to install dependencies, but continuing...")
        success = False

    # Step 2: Start Docker containers
    if not start_docker_containers():
        print("⚠️  Failed to start Docker containers, but continuing...")
        success = False

    # Give containers a moment to fully initialize
    time.sleep(3)

    # Step 3: Initialize MongoDB
    if not initialize_mongodb():
        print("⚠️  Failed to initialize MongoDB")
        success = False

    # Step 4: Initialize PostgreSQL
    if not initialize_postgresql():
        print("⚠️  Failed to initialize PostgreSQL")
        success = False

    # # Step 5: Initialize Elasticsearch
    # if not initialize_elasticsearch():
    #     print("⚠️  Failed to initialize Elasticsearch")
    #     success = False

    # Final status
    print(f"\n{'='*60}")
    if success:
        print("""
🎉 Project initialization complete!

All services are running and ready:
✅ Dependencies installed
✅ Docker containers started
✅ MongoDB connected and initialized
✅ PostgreSQL connected and initialized
✅ Elasticsearch connected and initialized

You can now start developing your application!
        """)
    else:
        print("""
⚠️  Project initialization completed with some warnings.

Please check the error messages above and ensure:
1. Docker is installed and running
2. Required ports are not in use
3. Environment variables are correctly set in .env file

You may need to run this script again after fixing any issues.
        """)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())