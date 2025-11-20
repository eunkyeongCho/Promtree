# 🚀 PROMTREE 프로젝트 시작 가이드

프론트엔드 + 백엔드 + DB를 로컬에서 실행하는 방법입니다.

## 📁 프로젝트 구조

```
S13P31S307/
├── frontend/          # React + TypeScript + Vite UI
├── backend/           # FastAPI 백엔드 서버
├── retriever/         # RAG 시스템 (벡터 검색, 그래프 검색)
├── db3/              # TDS 물성 정보 추출
├── common/           # Docker Compose (MongoDB, PostgreSQL, Elasticsearch, Neo4j 등)
├── promtree/         # PDF to Markdown 파서
└── db/               # DB 유틸리티
```

---

## ⚡ 빠른 시작 (Quick Start)

### 1️⃣ 데이터베이스 서비스 실행

```bash
cd common
docker-compose up -d mongodb postgres
```

**확인:**
- MongoDB: http://localhost:8888 (Mongo Express)
- PostgreSQL: http://localhost:9999 (Adminer)

### 2️⃣ 백엔드 API 서버 실행

```bash
cd backend

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # macOS/Linux
# Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일을 열고 GOOGLE_API_KEY를 추가하세요

# 서버 실행
python -m app.main
```

**확인:**
- API 서버: http://localhost:8000
- API 문서: http://localhost:8000/docs

### 3️⃣ 프론트엔드 실행

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

**확인:**
- 프론트엔드: http://localhost:5173

---

## 🔧 환경 설정

### Backend 환경 변수 (`backend/.env`)

```bash
# Database
MONGO_INITDB_ROOT_USERNAME=promtree
MONGO_INITDB_ROOT_PASSWORD=ssafy13s307
MONGO_HOST=localhost
MONGO_PORT=27017

POSTGRES_USER=promtree
POSTGRES_PASSWORD=ssafy13s307
POSTGRES_DB=CoreDB
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# API
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# LLM (Google Gemini API Key 필요)
GOOGLE_API_KEY=your_api_key_here
```

### Frontend 환경 변수 (`frontend/.env`) - 선택사항

```bash
VITE_API_BASE_URL=http://localhost:8000/api
```

---

## 📊 API 엔드포인트 (Phase 1)

### 채팅 관리
- `POST /api/chats` - 새 채팅 생성
- `GET /api/chats?userId={userId}` - 채팅 목록 조회
- `DELETE /api/chats/{chatId}` - 채팅 삭제
- `PATCH /api/chats/{chatId}` - 채팅 제목 수정

### 메시지 (RAG 쿼리)
- `POST /api/chats/{chatId}/messages` - 메시지 전송 (RAG 응답)
- `GET /api/chats/{chatId}/messages` - 메시지 히스토리 조회

### 컬렉션 관리
- `POST /api/collections` - 컬렉션 생성
- `GET /api/collections?userId={userId}` - 컬렉션 목록 조회
- `DELETE /api/collections/{collectionId}` - 컬렉션 삭제

**자세한 API 명세:** `frontend/API_SPEC.md` 참고

---

## 🧪 테스트

### API 테스트 (curl)

```bash
# 채팅 생성
curl -X POST http://localhost:8000/api/chats \
  -H "Content-Type: application/json" \
  -d '{"userId": "user_123", "title": "테스트 채팅"}'

# 메시지 전송 (RAG 쿼리)
curl -X POST http://localhost:8000/api/chats/chat_xxx/messages \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the glass transition temperature?"}'
```

### Swagger UI로 테스트
http://localhost:8000/docs 에서 인터랙티브하게 API 테스트 가능

---

## 🐳 전체 스택을 Docker Compose로 실행 (선택사항)

**TODO:** 아직 구현 안됨. 현재는 수동으로 각각 실행해야 합니다.

---

## 📚 추가 문서

- **프론트엔드**: `frontend/README.md`, `frontend/API_SPEC.md`
- **백엔드**: `backend/README.md`
- **프로젝트 전체**: `CLAUDE.md` (개발자 가이드)

---

## 🛠️ 개발 워크플로우

### 새로운 기능 개발 시

1. **브랜치 생성**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b S13P31S307-<issue-number>-<description>
   ```

2. **개발**
   - 프론트엔드: `frontend/src/` 수정
   - 백엔드: `backend/app/` 수정
   - API 변경 시: `frontend/API_SPEC.md` 업데이트

3. **커밋**
   ```bash
   git add .
   git commit -m "[S13P31S307-<issue>] Type: 설명"
   ```

4. **Merge Request**
   - Target: `develop` 브랜치
   - 이슈 번호 참조

---

## 🆘 문제 해결

### 포트가 이미 사용 중인 경우

**Backend (8000):**
```bash
lsof -ti:8000 | xargs kill -9
```

**Frontend (5173):**
```bash
lsof -ti:5173 | xargs kill -9
```

**MongoDB (27017):**
```bash
docker-compose -f common/docker-compose.yaml restart mongodb
```

### DB 연결 실패

```bash
# Docker 서비스 상태 확인
cd common
docker-compose ps

# 재시작
docker-compose restart mongodb postgres
```

### RAG 시스템 초기화 오류

RAG 시스템은 처음 실행 시 시간이 걸립니다. `/api/chats/{chatId}/messages` 호출 시 자동으로 초기화됩니다.

---

## ✅ 체크리스트

실행 전 확인사항:

- [ ] Docker가 실행 중인가?
- [ ] `common/docker-compose.yaml`로 MongoDB, PostgreSQL이 실행 중인가?
- [ ] `backend/.env` 파일에 `GOOGLE_API_KEY`가 설정되어 있나?
- [ ] Backend 가상환경이 활성화되어 있나?
- [ ] Frontend `node_modules`가 설치되어 있나?

모두 체크되었다면 시작! 🚀
