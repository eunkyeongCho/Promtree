from pymongo import MongoClient

import os
from pathlib import Path
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]  # root 경로
load_dotenv(BASE_DIR / "common" / ".env")

# --- 싱글톤 MongoClient 인스턴스 생성 ---
USERNAME = os.getenv("MONGO_INITDB_ROOT_USERNAME", "root")
PASSWORD = os.getenv("MONGO_INITDB_ROOT_PASSWORD", "example")
HOST = os.getenv("MONGO_HOST", "localhost")
PORT = int(os.getenv("MONGO_PORT", 27017))

_MONGO_CLIENT = MongoClient(f"mongodb://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/")

def get_mongodb_client():
    return _MONGO_CLIENT
