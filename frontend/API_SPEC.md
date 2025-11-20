# PROMTREE API 명세서

백엔드 개발을 위한 API 엔드포인트 정의서입니다.

## 기본 정보
- Base URL: `http://localhost:8000/api` (개발 환경)
- Content-Type: `application/json`
- 모든 응답은 다음 형식을 따릅니다:
```json
{
  "success": true,
  "data": { ... },
  "error": "에러 메시지 (실패시)"
}
```

---

## 1️⃣ 채팅 관련 API

### 1.1 새 채팅 생성
```
POST /api/chats
```

**Request Body:**
```json
{
  "userId": "user_123",
  "title": "새로운 채팅" // 선택적, 없으면 자동 생성
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "chatId": "chat_456",
    "title": "새로운 채팅",
    "createdAt": "2024-11-06T23:45:00Z"
  }
}
```

---

### 1.2 채팅 목록 조회
```
GET /api/chats?userId={userId}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "chats": [
      {
        "chatId": "chat_456",
        "title": "새로운 채팅",
        "createdAt": "2024-11-06T23:45:00Z",
        "updatedAt": "2024-11-06T23:50:00Z"
      }
    ]
  }
}
```

---

### 1.3 채팅 삭제
```
DELETE /api/chats/{chatId}
```

**Response:**
```json
{
  "success": true
}
```

---

### 1.4 채팅 제목 수정
```
PATCH /api/chats/{chatId}
```

**Request Body:**
```json
{
  "title": "수정된 제목"
}
```

**Response:**
```json
{
  "success": true
}
```

---

## 2️⃣ 메시지 관련 API

### 2.1 메시지 전송 (RAG 쿼리)
```
POST /api/chats/{chatId}/messages
```

**Request Body:**
```json
{
  "message": "질문 내용",
  "collectionIds": ["collection_123", "collection_456"], // 선택적, @ 멘션한 컬렉션
  "useWebSearch": false // 선택적, Globe 버튼 활성화 여부
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "messageId": "msg_789",
    "response": "AI 응답 내용",
    "sources": [
      {
        "title": "출처 문서 제목",
        "url": "https://example.com/doc",
        "snippet": "관련 내용 발췌"
      }
    ],
    "timestamp": "2024-11-06T23:45:00Z"
  }
}
```

---

### 2.2 채팅 히스토리 조회
```
GET /api/chats/{chatId}/messages
```

**Response:**
```json
{
  "success": true,
  "data": {
    "messages": [
      {
        "messageId": "msg_001",
        "role": "user",
        "content": "사용자 질문",
        "timestamp": "2024-11-06T23:45:00Z"
      },
      {
        "messageId": "msg_002",
        "role": "assistant",
        "content": "AI 응답",
        "timestamp": "2024-11-06T23:45:05Z",
        "sources": [...]
      }
    ]
  }
}
```

---

## 3️⃣ 컬렉션(지식 베이스) 관련 API

### 3.1 컬렉션 목록 조회
```
GET /api/collections?userId={userId}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "collections": [
      {
        "collectionId": "col_123",
        "name": "프로젝트 문서",
        "description": "프로젝트 관련 문서 모음",
        "documentCount": 15,
        "createdAt": "2024-11-06T10:00:00Z",
        "updatedAt": "2024-11-06T23:00:00Z"
      }
    ]
  }
}
```

---

### 3.2 컬렉션 생성
```
POST /api/collections
```

**Request Body:**
```json
{
  "name": "새 컬렉션",
  "description": "설명 (선택적)",
  "userId": "user_123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "collectionId": "col_456",
    "name": "새 컬렉션",
    "description": "설명",
    "documentCount": 0,
    "createdAt": "2024-11-06T23:45:00Z"
  }
}
```

---

### 3.3 컬렉션 삭제
```
DELETE /api/collections/{collectionId}
```

**Response:**
```json
{
  "success": true
}
```

---

### 3.4 컬렉션 검색
```
GET /api/collections/search?q={query}&userId={userId}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "collections": [...]
  }
}
```

---

## 4️⃣ 문서 업로드 관련 API

### 4.1 문서 업로드
```
POST /api/collections/{collectionId}/documents
Content-Type: multipart/form-data
```

**Request (FormData):**
- `files`: File[] (여러 파일 가능)
- `collectionId`: string

**Response:**
```json
{
  "success": true,
  "data": {
    "uploadedCount": 3,
    "documents": [
      {
        "documentId": "doc_123",
        "filename": "document.pdf",
        "size": 1024000,
        "uploadedAt": "2024-11-06T23:45:00Z",
        "status": "processing"
      }
    ]
  }
}
```

---

### 4.2 문서 목록 조회
```
GET /api/collections/{collectionId}/documents
```

**Response:**
```json
{
  "success": true,
  "data": {
    "documents": [
      {
        "documentId": "doc_123",
        "filename": "document.pdf",
        "size": 1024000,
        "uploadedAt": "2024-11-06T23:45:00Z",
        "status": "completed"
      }
    ]
  }
}
```

---

### 4.3 문서 삭제
```
DELETE /api/documents/{documentId}
```

**Response:**
```json
{
  "success": true
}
```

---

## 5️⃣ 사용자 관련 API

### 5.1 사용자 정보 조회
```
GET /api/users/{userId}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "userId": "user_123",
    "username": "rhgdwkdy",
    "email": "user@example.com",
    "settings": {
      "theme": "dark",
      "language": "ko"
    }
  }
}
```

---

### 5.2 사용자 설정 업데이트
```
PATCH /api/users/{userId}/settings
```

**Request Body:**
```json
{
  "theme": "dark",
  "language": "ko"
}
```

**Response:**
```json
{
  "success": true
}
```

---

## 6️⃣ RAG 설정 API (선택적)

### 6.1 사용 가능한 모델 목록 조회
```
GET /api/models
```

**Response:**
```json
{
  "success": true,
  "data": {
    "models": [
      {
        "id": "google/gemini-2.5-flash",
        "name": "Gemini 2.5 Flash",
        "provider": "Google"
      },
      {
        "id": "openai/gpt-4",
        "name": "GPT-4",
        "provider": "OpenAI"
      }
    ]
  }
}
```

---

### 6.2 하이브리드 검색 설정
```
POST /api/search/config
```

**Request Body:**
```json
{
  "vectorWeight": 0.4,
  "graphWeight": 0.3,
  "fullTextWeight": 0.3
}
```

**Response:**
```json
{
  "success": true
}
```

---

## 에러 응답 형식

```json
{
  "success": false,
  "error": "에러 메시지",
  "code": "ERROR_CODE" // 선택적
}
```

**공통 HTTP 상태 코드:**
- `200` - 성공
- `201` - 생성 성공
- `400` - 잘못된 요청
- `401` - 인증 필요
- `404` - 리소스 없음
- `500` - 서버 오류

---

## 개발 우선순위

**Phase 1 (필수):**
1. 채팅 생성/조회
2. 메시지 전송/조회
3. 컬렉션 생성/조회

**Phase 2 (중요):**
4. 문서 업로드
5. 채팅/컬렉션 삭제

**Phase 3 (부가기능):**
6. 사용자 설정
7. 검색 설정
