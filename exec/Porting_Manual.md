```

\# PROMTREE 실행 가이드



\## 초기 설정 (최초 1회만)



```bash

\# 1. uv 설치

curl -LsSf https://astral.sh/uv/install.sh | sh



\# 2. 프로젝트 클론

git clone https://lab.ssafy.com/s13-final/S13P31S307.git

cd S13P31S307



\# 3. 백엔드 의존성 설치

uv sync



\# 4. 프론트엔드 의존성 설치

cd frontend

npm install

cd ..

```



\## 서비스 실행



```bash

\# 1. Docker 시작

docker-compose up -d



\# 2. 백엔드 시작 (터미널 1)

uv run python main.py



\# 3. 프론트엔드 시작 (터미널 2)

cd frontend \&\& npm run dev

```



\*\*접속:\*\* http://localhost:5173



\## 서비스 종료



```bash

\# 프론트엔드/백엔드 종료

Ctrl + C



\# Docker 종료

docker-compose down

```



\## 포트 충돌 시



```bash

lsof -ti:8000 | xargs kill -9   # 백엔드

lsof -ti:5173 | xargs kill -9   # 프론트엔드

```



\## 주요 URL



\- 프론트엔드: http://localhost:5173

\- 백엔드 API: http://localhost:8000/docs

\- Neo4j: http://localhost:7474 (neo4j / ssafy13s307)

\- Qdrant: http://localhost:6333/dashboard



```

