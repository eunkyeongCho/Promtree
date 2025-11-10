import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# --- 싱글톤 MongoClient 인스턴스 생성 ---
USERNAME = os.getenv("MONGO_INITDB_ROOT_USERNAME", "root")
PASSWORD = os.getenv("MONGO_INITDB_ROOT_PASSWORD", "example")
HOST = os.getenv("MONGO_HOST", "localhost")
PORT = int(os.getenv("MONGO_PORT", 27017))

_MONGO_CLIENT = MongoClient(f"mongodb://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/")

def get_mongo_client():
    return _MONGO_CLIENT
