# Intelligent Chat System - Mr. White AI

## 🎯 **Overview**

A production-grade, intelligent AI chatbot system that learns, remembers, and converses naturally with users. Built as a complete replacement for the legacy `fastapi_chat` system with significantly improved capabilities.

### **Key Features:**
- 🧠 **Intelligent Memory**: Remembers everything user shares (documents, images, conversations)
- 💬 **Streaming Responses**: Real-time typing effect like ChatGPT
- 📁 **Multi-Format Support**: Images, PDFs, DOCX, text files
- 🐕 **Dog Profile Integration**: Personalized responses based on dog profiles
- 🎛️ **Three Modes**: Reminders, Health, Way of Dog
- 🔍 **Advanced Search**: Keyword and date-based search with navigation
- 🎤 **Voice Input**: Speech-to-text integration
- 📊 **Contextual Retrieval**: Uses Anthropic's advanced retrieval techniques
- 🔄 **Learning System**: Learns from mistakes and user corrections

---

## 📁 **Project Structure**

```
intelligent_chat/
├── api/                    # API endpoints
│   ├── __init__.py
│   ├── routes/
│   │   ├── chat.py        # Main chat endpoints
│   │   ├── documents.py   # Document upload/management
│   │   ├── reminders.py   # Reminder mode endpoints
│   │   ├── health.py      # Health mode endpoints
│   │   ├── wayofdog.py    # Way of Dog mode endpoints
│   │   └── conversation.py # Conversation management
├── services/               # Business logic
│   ├── __init__.py
│   ├── chat_service.py    # Core chat logic
│   ├── streaming_service.py # Streaming responses
│   ├── document_service.py  # Document processing
│   ├── memory_service.py    # Memory & retrieval
│   ├── learning_service.py  # Learning system
│   ├── mode_service.py      # Mode handling
│   └── credit_service.py    # Credit tracking
├── models/                 # SQLAlchemy models
│   ├── __init__.py
│   ├── conversation.py
│   ├── message.py
│   ├── document.py
│   ├── reminder.py
│   └── user_preference.py
├── schemas/                # Pydantic schemas
│   ├── __init__.py
│   ├── chat.py
│   ├── document.py
│   ├── reminder.py
│   └── conversation.py
├── utils/                  # Utility functions
│   ├── __init__.py
│   ├── embeddings.py      # Embedding generation
│   ├── chunking.py        # Document chunking
│   ├── s3_client.py       # S3 operations
│   ├── pinecone_client.py # Pinecone operations
│   └── formatters.py      # Response formatting
├── config/                 # Configuration
│   ├── __init__.py
│   ├── settings.py        # Application settings
│   └── PINECONE_SETUP.md  # Pinecone setup guide
├── migrations/             # Database migrations
│   ├── 001_create_initial_schema.sql
│   └── run_migration.py
└── README.md              # This file
```

---

## 🗄️ **Database Schema**

### **Tables (Prefix: `ic_`)**

| Table | Purpose | Key Features |
|-------|---------|--------------|
| `ic_conversations` | Single conversation per user | Unique user constraint |
| `ic_messages` | All chat messages | Full-text search, date grouping |
| `ic_documents` | Uploaded documents | S3 + Pinecone integration |
| `ic_vet_reports` | Vet reports for health mode | Linked to dog profiles |
| `ic_reminders` | Reminders from reminder mode | Recurrence support |
| `ic_user_corrections` | Learning from mistakes | Tracks corrections |
| `ic_message_feedback` | Like/dislike feedback | Per-message feedback |
| `ic_user_preferences` | User preferences | Learned behaviors |
| `ic_conversation_context` | Active mode & state | Session management |
| `ic_credit_usage` | Credit tracking | Per-message/action |
| `ic_book_comments_access` | Way of Dog comments | Links to book_notes |

---

## 🔧 **Setup & Installation**

### **1. Run Database Migration**

```bash
cd /home/ubuntu/Mr-White-Project/backend/intelligent_chat/migrations
python run_migration.py
```

### **2. Configure Pinecone**

Follow the setup guide in `config/PINECONE_SETUP.md`

### **3. Environment Variables**

Create `.env` file with:
```env
ENVIRONMENT=development
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET_NAME=...
PINECONE_API_KEY=...
PINECONE_ENVIRONMENT=...
```

### **4. Install Dependencies**

```bash
pip install -r requirements.txt
```

---

## 🚀 **Development Phases**

### **✅ Phase 1: Infrastructure & Setup** (COMPLETED)
- [x] Folder structure
- [x] Database schema
- [x] Pinecone configuration
- [x] Core settings

### **📝 Phase 2: Core Chat Engine** (NEXT)
- [ ] Streaming response system
- [ ] Message processing pipeline
- [ ] Intelligent prompt engineering
- [ ] Contextual retrieval + re-ranking

### **📝 Phase 3: Memory & Learning System**
- [ ] Conversation memory
- [ ] Document memory
- [ ] Learning system
- [ ] Vet report system

### **📝 Phase 4: Mode System**
- [ ] Reminder mode
- [ ] Health mode
- [ ] Way of Dog mode
- [ ] Mode switching

### **📝 Phase 5: Dog Profile Integration**
- [ ] Profile management
- [ ] Context injection
- [ ] Tailored responses

### **📝 Phase 6: Voice Input**
- [ ] Voice recording
- [ ] Speech-to-text

### **📝 Phase 7: Search & Navigation**
- [ ] Keyword search
- [ ] Date search
- [ ] Date grouping

### **📝 Phase 8: Conversation Management**
- [ ] Clear chat
- [ ] Download PDF
- [ ] Credits system

### **📝 Phase 9: Action Buttons**
- [ ] Copy button
- [ ] Like/dislike
- [ ] Read aloud

### **📝 Phase 10: Testing & Optimization**
- [ ] Performance testing
- [ ] Edge case testing
- [ ] Error handling

---

## 📊 **Key Design Decisions**

### **1. Single Conversation Model**
- Each user has ONE continuous conversation
- Messages organized by date groups (Today, Yesterday, etc.)
- Clearable with optional Pinecone memory wipe

### **2. Separate Pinecone Namespaces**
- Documents, Vet Reports, Conversations, Book Comments
- Enables targeted retrieval per mode
- Easier maintenance and monitoring

### **3. Contextual Retrieval**
- Implements Anthropic's recommendations
- Enriched chunks with document context
- Hybrid BM25 + semantic search
- Re-ranking for precision

### **4. Mode-Based Context**
- Each mode has specific retrieval strategy
- Health mode: Priority on vet reports
- Way of Dog mode: Only book comments
- Reminder mode: Conversation context

### **5. Learning System**
- Tracks user corrections
- Stores feedback
- Adapts prompts based on patterns
- Never repeats mistakes

---

## 🔒 **Security & Privacy**

- User ID filtering on all queries
- S3 secure URLs with expiration
- Encrypted vectors in Pinecone
- Audit logs for all operations
- GDPR-compliant data deletion

---

## 📈 **Monitoring & Metrics**

### **Key Metrics:**
- Response latency (<500ms target)
- Streaming latency (<100ms first token)
- Search recall rate (>95%)
- User satisfaction (like rate)
- Credit usage per user
- Error rates

---

## 🆘 **Support & Troubleshooting**

### **Common Issues:**

**Database Connection Failed:**
```bash
# Check DATABASE_URL in .env
# Verify PostgreSQL is running
# Test connection: psql $DATABASE_URL
```

**Pinecone Queries Slow:**
```bash
# Check index size
# Verify namespace exists
# Monitor query filters
```

**Streaming Not Working:**
```bash
# Check ENABLE_STREAMING setting
# Verify SSE endpoint configuration
# Test with curl
```

---

## 📝 **License**

Proprietary - Mr. White Project

---

## 🤝 **Contributing**

This is a production system. All changes must:
1. Pass tests
2. Include documentation
3. Follow code style
4. Be reviewed

---

**Built with ❤️ for intelligent dog care**






