
## MongoDB 

1. Docker Desktop 실행하기
2. `common`폴더의 `docker-compose.yaml` 실행하기
```bash
cd common
docker compose up -d
```


## Python에서 MongoDB 사용하기

**순서**
연결 -> 적재 -> 검색

1. MongoDB 연결
```python
# Connection Info (환경 변수에서 값 불러오기)
from dotenv import load_dotenv
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

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

except ConnectionFailure as e:
    print(f"MongoDB connection failed: {e}")
```

원하는 db와 collection 지정하기
```python
db = client['database_name']
collection = db['collection_name']
```

2. 적재
```python
# 하나만 적재
collection.insert_one({"key": "value"})

# 여러개 적재
collection.insert_many([{"key": "value1"}, {"key": "value2"}, ...])
```

3. 검색
```python
# 하나만 검색
collection.find_one({"key": "value"})

# 여러개 검색
collection.find({filter})
```

4. 추가 기능
```python
# 단일 문서 수정
client.update_one({filter})

# upsert = update + insert
client.update_one({"key": "value"}, upsert=True)

# 여러 문서 수정 (upsert 가능)
client.update_many({filter})

# 단일 문서 삭제
client.delete_one({"key": "value"})

# 여러 문서 삭제
client.delete_many({filter})
```

## Filter 사용하기

**비교 연산자**
​
| 연산자   | 의미               | 예시                          |
|---------|--------------------|------------------------------|
| $eq     | 같다 (=)           | {"age": {"$eq": 25}}         |
| $ne     | 같지 않다 (!=)      | {"status": {"$ne": "active"}}|
| $gt     | 크다 (>)           | {"age": {"$gt": 30}}         |
| $gte    | 크거나 같다 (>=)    | {"age": {"$gte": 18}}        |
| $lt     | 작다 (<)           | {"age": {"$lt": 50}}         |
| $lte    | 작거나 같다 (<=)    | {"age": {"$lte": 40}}        |

---

**논리 연산자**
​
| 연산자  | 설명               | 예시                                                          |
|--------|--------------------|--------------------------------------------------------------|
| $and   | 모든 조건이 참일 때   | {"$and": [{"age": {"$gt": 20}}, {"city": "Seoul"}]}         |
| $or    | 하나라도 참일 때     | {"$or": [{"status": "A"}, {"age": {"$lt": 25}}]}             |
| $nor   | 모든 조건이 거짓일 때 | {"$nor": [{"status": "A"}, {"age": {"$lt": 25}}]}           |
| $not   | 부정                | {"age": {"$not": {"$gt": 30}}}                              |
