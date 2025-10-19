# Intelligent Chat System - Quick Reference

## 📍 **Current Status**
**Phase 1: Infrastructure & Setup - ✅ COMPLETE**

---

## 🗄️ **Database Tables (All Created)**

```
ic_conversations          - Single conversation per user
ic_messages              - All chat messages (full-text search enabled)
ic_documents             - Uploaded files (S3 + Pinecone)
ic_vet_reports           - Health mode vet reports
ic_reminders             - Reminder system
ic_user_corrections      - Learning from mistakes
ic_message_feedback      - Like/dislike tracking
ic_user_preferences      - User personalization
ic_conversation_context  - Active mode & session state
ic_credit_usage          - Credit tracking
ic_book_comments_access  - Way of Dog mode
```

---

## 📂 **File Locations**

```
/backend/intelligent_chat/
├── config/
│   ├── settings.py              # All configuration settings
│   └── PINECONE_SETUP.md        # Pinecone setup guide
├── migrations/
│   ├── 001_create_initial_schema.sql  # Database schema
│   └── run_migration.py               # Migration runner
├── README.md                    # Full documentation
├── PHASE_1_VERIFIED_COMPLETE.md # Completion report
└── QUICK_REFERENCE.md           # This file
```

---

## 🔧 **Key Configuration Values**

### **Models:**
- **Chat:** `anthropic.claude-3-5-sonnet-20241022-v2:0`
- **Embedding:** `amazon.titan-embed-text-v2:0` (1024 dimensions)

### **Pinecone:**
- **Index:** `intelligent-chat`
- **Namespaces:**
  - `intelligent-chat-documents-{env}`
  - `intelligent-chat-vet-reports-{env}`
  - `intelligent-chat-conversations-{env}`
  - `intelligent-chat-book-comments-{env}`

### **Credits:**
- Message: 0.01 credits
- Document: 0.05 credits
- Image analysis: 0.03 credits
- Voice (per minute): 0.10 credits

### **Limits:**
- Max messages/minute: 30
- Max documents/message: 5
- Max file size: 25 MB
- Max context messages: 20

---

## 🚀 **How to Run Migration**

```bash
cd /home/ubuntu/Mr-White-Project/backend/intelligent_chat/migrations
psql 'postgresql://mrwhite:master_white@54.174.252.184/mrwhite_db' \
  -f 001_create_initial_schema.sql
```

---

## 📊 **Verify Tables**

```bash
# Activate venv
cd /home/ubuntu/Mr-White-Project/backend
source venv/bin/activate

# Check tables via Python
python -c "
from fastapi_chat.models import async_engine
from sqlalchemy import text
import asyncio

async def check():
    async with async_engine.begin() as conn:
        result = await conn.execute(
            text('SELECT table_name FROM information_schema.tables WHERE table_name LIKE \\'ic_%\\' ORDER BY table_name')
        )
        for row in result:
            print(f'✅ {row[0]}')

asyncio.run(check())
"
```

---

## 🎯 **What's Next - Phase 2**

### **To Build:**
1. **models/** - SQLAlchemy ORM models for all 11 tables
2. **schemas/** - Pydantic request/response schemas
3. **services/chat_service.py** - Main chat logic + streaming
4. **services/memory_service.py** - Pinecone retrieval
5. **utils/embeddings.py** - Embedding generation
6. **utils/s3_client.py** - S3 file operations
7. **api/routes/chat.py** - Chat API endpoints

---

## 🔍 **Quick Commands**

### **Check Table Structure:**
```sql
\d ic_messages
```

### **Count Records:**
```sql
SELECT 
    'ic_conversations' as table, COUNT(*) FROM ic_conversations
UNION ALL
SELECT 'ic_messages', COUNT(*) FROM ic_messages
UNION ALL
SELECT 'ic_documents', COUNT(*) FROM ic_documents;
```

### **Check Indexes:**
```sql
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename LIKE 'ic_%' 
ORDER BY tablename, indexname;
```

---

## 📝 **Important Notes**

1. **Separate from fastapi_chat** - All tables use `ic_` prefix
2. **Pinecone namespaces** - Include environment (dev/prod)
3. **Single conversation** - One per user, cleared on demand
4. **Date grouping** - Auto-populated via trigger
5. **Full-text search** - Ready on ic_messages.content
6. **Soft deletes** - is_deleted flag (no hard deletes)

---

## 🆘 **Troubleshooting**

### **Migration Failed:**
```bash
# Drop all ic_ tables and retry
psql $DATABASE_URL -c "
DROP TABLE IF EXISTS 
  ic_book_comments_access,
  ic_conversation_context,
  ic_conversations,
  ic_credit_usage,
  ic_documents,
  ic_message_feedback,
  ic_messages,
  ic_reminders,
  ic_user_corrections,
  ic_user_preferences,
  ic_vet_reports
CASCADE;"

# Re-run migration
psql $DATABASE_URL -f 001_create_initial_schema.sql
```

### **Check Environment:**
```bash
cd /home/ubuntu/Mr-White-Project/backend
source venv/bin/activate
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('DATABASE_URL:', os.getenv('DATABASE_URL')[:30] + '...')
print('PINECONE_API_KEY:', 'Set' if os.getenv('PINECONE_API_KEY') else 'Missing')
"
```

---

## 📚 **Documentation**

- **Full docs:** `README.md`
- **Pinecone setup:** `config/PINECONE_SETUP.md`
- **Phase 1 completion:** `PHASE_1_VERIFIED_COMPLETE.md`
- **Settings reference:** `config/settings.py`

---

**Phase 1 Complete ✅ | Ready for Phase 2 🚀**






