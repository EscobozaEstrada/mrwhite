# Environment Setup for Intelligent Chat

## Required Environment Variables

Create a `.env.local` file in `/backend/intelligent_chat/` directory with the following variables:

```bash
# ================================
# INTELLIGENT CHAT SYSTEM ENV
# Port: 8001 (Separate from fastapi_chat:8000)
# ================================

# Environment
ENVIRONMENT=development

# Database (shared with fastapi_chat)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/mrwhite

# Redis (shared with fastapi_chat)  
REDIS_URL=redis://localhost:6379/1

# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here

# S3 Configuration
S3_BUCKET_NAME=mrwhite-bucket

# Pinecone Configuration (SEPARATE from fastapi_chat)
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_ENVIRONMENT=us-east-1-aws

# Logging
LOG_LEVEL=INFO
```

---

## System Architecture

### Separation Strategy:
1. **Port**: 8001 (fastapi_chat uses 8000)
2. **Tables**: All use `ic_` prefix (e.g., `ic_conversations`, `ic_messages`)
3. **Pinecone**: Separate index named `"intelligent-chat"`
4. **Code**: Separate folder `/backend/intelligent_chat/`
5. **Database**: Shares PostgreSQL with fastapi_chat but has separate tables

### Shared Resources:
- PostgreSQL database (different tables)
- AWS S3 bucket (different prefix: `intelligent-chat/`)
- Redis instance (can use different DB number if needed)
- Existing tables referenced via FK:
  - `users` table (from fastapi_chat)
  - `pet_profiles` table (from fastapi_chat)

---

## How to Start

```bash
# 1. Navigate to intelligent_chat directory
cd /home/ubuntu/Mr-White-Project/backend/intelligent_chat

# 2. Activate virtual environment
source ../venv/bin/activate

# 3. Run the server
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

---

## Frontend Connection

The chat page (`/chat`) connects to this backend:
- **Base URL**: `http://localhost:8001/api/v2/`
- **Endpoints**:
  - `/api/v2/status` - Health check
  - `/api/v2/send` - Send message (non-streaming)
  - `/api/v2/stream` - Send message (SSE streaming)
  - `/api/v2/history` - Get conversation history
  - `/api/v2/clear` - Clear chat/memory
  - `/api/v2/search` - Search messages
  - `/api/v2/upload` - Upload documents

---

## Pinecone Setup

You need to create a **new Pinecone index** named `"intelligent-chat"`:

```python
# Index Specification
name = "intelligent-chat"
dimension = 1024  # Titan embeddings
metric = "cosine"
cloud = "aws"
region = "us-east-1"
```

### Namespaces (auto-created):
- `intelligent-chat-documents-development`
- `intelligent-chat-vet-reports-development`
- `intelligent-chat-conversations-development`
- `intelligent-chat-book-comments-development`

See `PINECONE_SETUP.md` for detailed instructions.

---

## Why This Separation Works

1. **No Code Conflicts**: Separate Python modules, no import clashes
2. **No Database Conflicts**: Separate tables with `ic_` prefix
3. **No Port Conflicts**: Different ports (8000 vs 8001)
4. **Shared Data Access**: Can reference existing `users` and `pet_profiles` via foreign keys
5. **Independent Deployment**: Can be updated/restarted independently

This is exactly how `fastapi_chat` runs, just with a different port and table prefix! ✅





