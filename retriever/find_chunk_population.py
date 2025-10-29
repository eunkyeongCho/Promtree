# mongo db의 chunks collection에서 페이지별 청크 분포를 확인하는 코드
from dotenv import load_dotenv
import os
from pymongo import MongoClient

load_dotenv()
USERNAME = os.getenv('MONGO_INITDB_ROOT_USERNAME')
PASSWORD = os.getenv('MONGO_INITDB_ROOT_PASSWORD')
HOST = os.getenv('MONGO_HOST')
PORT = int(os.getenv('MONGO_PORT'))

url = f'mongodb://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/'
client = MongoClient(url)
db = client['s307_db']
chunks_collection = db['chunks']

# 페이지 분포 확인
pipeline = [
    {'$unwind': '$page_num'},
    {'$group': {'_id': '$page_num', 'count': {'$sum': 1}}},
    {'$sort': {'_id': 1}}
]

page_dist = list(chunks_collection.aggregate(pipeline))
print('페이지 분포:')
for item in page_dist:
    print(f'페이지 {item["_id"]}: {item["count"]}개 청크')

# 소스 파일별 분포도 확인
source_dist = list(chunks_collection.aggregate([
    {'$group': {'_id': '$source_file_name', 'count': {'$sum': 1}}},
    {'$sort': {'count': -1}}
]))
print('\n소스 파일별 분포:')
for item in source_dist:
    print(f'{item["_id"]}: {item["count"]}개 청크')