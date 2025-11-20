# PROMTREE Backend API

FastAPI backend server for PROMTREE RAG system.

## Quick Start

### 1. Setup Environment

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Copy .env file
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

### 2. Start Database Services

```bash
cd ../common
docker-compose up -d mongodb postgres
```

### 3. Run Backend Server

```bash
cd ../backend
python -m app.main
```

Server will start at: http://localhost:8000

**API Documentation**: http://localhost:8000/docs

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── routes/          # API endpoints
│   │       ├── chats.py     # Chat management
│   │       ├── messages.py  # Message + RAG query
│   │       └── collections.py  # Collection management
│   ├── core/
│   │   ├── config.py        # Configuration
│   │   └── database.py      # Database connections
│   ├── models/
│   │   └── schemas.py       # Pydantic models
│   ├── services/
│   │   └── rag_service.py   # RAG system wrapper
│   └── main.py              # FastAPI app
├── requirements.txt
└── .env.example
```

## API Endpoints (Phase 1)

### Chats
- `POST /api/chats` - Create new chat
- `GET /api/chats?userId={userId}` - Get user's chats
- `DELETE /api/chats/{chatId}` - Delete chat
- `PATCH /api/chats/{chatId}` - Update chat title

### Messages
- `POST /api/chats/{chatId}/messages` - Send message (RAG query)
- `GET /api/chats/{chatId}/messages` - Get message history

### Collections
- `POST /api/collections` - Create collection
- `GET /api/collections?userId={userId}` - Get collections
- `DELETE /api/collections/{collectionId}` - Delete collection
- `GET /api/collections/search?q={query}&userId={userId}` - Search collections

## Development

### Test API with curl

```bash
# Create chat
curl -X POST http://localhost:8000/api/chats \
  -H "Content-Type: application/json" \
  -d '{"userId": "user_123", "title": "테스트 채팅"}'

# Send message (RAG query)
curl -X POST http://localhost:8000/api/chats/chat_xxx/messages \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the Tg of polymer X?"}'
```

### Interactive API Docs

Visit http://localhost:8000/docs for Swagger UI

## Next Steps

1. ✅ Phase 1 APIs implemented (in-memory storage)
2. TODO: Move to MongoDB/PostgreSQL storage
3. TODO: Add document upload functionality
4. TODO: Integrate hybrid RAG (vector + graph)
5. TODO: Add authentication
