"""
Database connection management
"""
from pymongo import MongoClient
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from typing import Optional
from .config import settings


# MongoDB Client
mongodb_client: Optional[MongoClient] = None

def get_mongodb() -> MongoClient:
    """Get MongoDB client (singleton)"""
    global mongodb_client
    if mongodb_client is None:
        mongodb_client = MongoClient(settings.mongodb_url)
    return mongodb_client

def get_mongodb_database(db_name: str = None):
    """Get MongoDB database"""
    client = get_mongodb()
    return client[db_name or settings.MONGO_DATABASE]


# PostgreSQL Connection Pool
postgres_pool: Optional[SimpleConnectionPool] = None

def get_postgres_pool() -> SimpleConnectionPool:
    """Get PostgreSQL connection pool (singleton)"""
    global postgres_pool
    if postgres_pool is None:
        postgres_pool = SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=settings.postgres_url
        )
    return postgres_pool

def get_postgres_connection():
    """Get PostgreSQL connection from pool"""
    pool = get_postgres_pool()
    return pool.getconn()

def release_postgres_connection(conn):
    """Release PostgreSQL connection back to pool"""
    pool = get_postgres_pool()
    pool.putconn(conn)


# Cleanup functions
def close_mongodb():
    """Close MongoDB connection"""
    global mongodb_client
    if mongodb_client:
        mongodb_client.close()
        mongodb_client = None

def close_postgres():
    """Close PostgreSQL connection pool"""
    global postgres_pool
    if postgres_pool:
        postgres_pool.closeall()
        postgres_pool = None
