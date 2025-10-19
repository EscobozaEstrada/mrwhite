# Intelligent Chat - Comprehensive Database Schema Migration

## Overview

This migration file creates **all** database tables required for the Intelligent Chat functionality in a single, comprehensive SQL script.

## Migration File

**File:** `000_comprehensive_intelligent_chat_schema.sql`

This file contains the complete schema for the Intelligent Chat system, including:

### Tables Created (13 total)

1. **`ic_conversations`** - Conversation management (one per user)
2. **`ic_messages`** - All chat messages with metadata
3. **`ic_conversation_context`** - Active mode and state tracking
4. **`ic_dog_profiles`** - Dog profile context for chat
5. **`ic_documents`** - Document uploads during chat
6. **`ic_message_documents`** - Junction table for message-document links
7. **`ic_vet_reports`** - Vet reports for Health Mode
8. **`ic_message_feedback`** - Like/dislike feedback on AI responses
9. **`ic_user_corrections`** - User corrections for AI learning
10. **`ic_user_preferences`** - User communication preferences
11. **`ic_reminders`** - Reminders created via Reminder Mode
12. **`ic_book_comments_access`** - Way of Dog mode book notes tracking
13. **`ic_credit_usage`** - Credit consumption tracking

### Features Included

- ✅ **Full-text search** on messages (`search_vector` with triggers)
- ✅ **Date grouping** for messages (auto-populated via trigger)
- ✅ **Cascade deletes** for data cleanup
- ✅ **Soft deletes** for messages and documents
- ✅ **JSONB fields** for flexible metadata
- ✅ **Array fields** for document IDs, Pinecone IDs, etc.
- ✅ **Check constraints** for data validation
- ✅ **Unique constraints** to prevent duplicates
- ✅ **Comprehensive indexes** for performance
- ✅ **Auto-update triggers** for `updated_at` columns

## Prerequisites

Before running the migration, ensure:

1. **PostgreSQL database is running**
2. **Required external tables exist:**
   - `users` (main user table)
   - `pet_profiles` (for dog profile references)
   - `book_notes` (for Way of Dog mode)

3. **Database connection configured** in `backend/intelligent_chat/config/database.py`

## How to Run

### Method 1: Using the Python Script (Recommended)

```bash
cd /home/ubuntu/Mr-White-Project/backend/intelligent_chat

# Activate virtual environment (if using one)
source venv/bin/activate

# Run the migration
python migrations/run_comprehensive_migration.py
```

### Method 2: Direct SQL Execution

```bash
# Using psql
psql -U your_username -d your_database -f migrations/000_comprehensive_intelligent_chat_schema.sql

# Or using environment variable
psql $DATABASE_URL -f migrations/000_comprehensive_intelligent_chat_schema.sql
```

## What Gets Created

### Primary Tables

#### ic_conversations
- Single conversation per user
- Tracks conversation title and archive status
- Unique constraint on `user_id`

#### ic_messages
- All chat messages (user and assistant)
- Rich metadata: tokens, credits, response time
- Document references via `document_ids` array
- Mode context: active_mode, dog_profile_id
- **Auto-populated fields:**
  - `date_group` - Date grouping (via trigger)
  - `search_vector` - Full-text search (via trigger)

#### ic_documents
- Documents uploaded during conversations
- S3 storage information
- Pinecone vector storage tracking
- Processing status and extracted content
- Supports images, PDFs, DOCX, TXT

### Supporting Tables

#### ic_message_feedback
- Like/dislike feedback on AI responses
- Unique per message-user combination

#### ic_user_preferences
- User communication preferences
- Learned behavior patterns
- Feature toggles

#### ic_reminders
- Reminders created via Reminder Mode
- Supports recurrence patterns
- Status tracking (pending, sent, completed, cancelled)

#### ic_vet_reports
- Vet reports for Health Mode
- Linked to specific dogs
- Pinecone vector storage for RAG

#### ic_book_comments_access
- Tracks user book notes for Way of Dog Mode
- Links to book_notes table
- Access tracking and Pinecone references

#### ic_credit_usage
- Detailed credit consumption tracking
- Per-action breakdown
- Model and token usage

## Database Triggers

The migration creates several triggers for automation:

### 1. Message Date Grouping
```sql
ic_messages_set_date_group
```
- Auto-populates `date_group` from `created_at`
- Enables efficient date-based filtering

### 2. Message Search Vector
```sql
ic_messages_update_search_vector
```
- Auto-populates `search_vector` from `content`
- Enables full-text search on messages

### 3. Updated At Timestamps
Multiple triggers for auto-updating `updated_at`:
- `ic_conversations_updated_at`
- `ic_conversation_context_updated_at`
- `ic_user_preferences_updated_at`
- `ic_reminders_updated_at`
- `ic_documents_updated_at`
- `ic_vet_reports_updated_at`
- `ic_dog_profiles_updated_at`

## Indexes Created

All tables include optimized indexes for:
- Foreign key lookups
- Timestamp sorting
- Status filtering
- Full-text search (GIN index on search_vector)
- Composite unique constraints

## Foreign Key Relationships

### Cascade Deletes
When a user is deleted, **all** related intelligent chat data is automatically deleted:
- Conversations → Messages → Feedback/Corrections/Credits
- Documents, Reminders, Preferences, etc.

### Soft Deletes
Messages and Documents support soft deletion:
- `is_deleted` flag allows "hiding" without removing
- Enables recovery and audit trails

## Verification

After running the migration, verify with:

```sql
-- Check all tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_name LIKE 'ic_%' 
ORDER BY table_name;

-- Should return 13 tables

-- Check triggers
SELECT trigger_name, event_manipulation, event_object_table 
FROM information_schema.triggers 
WHERE trigger_name LIKE 'ic_%';

-- Check indexes
SELECT tablename, indexname 
FROM pg_indexes 
WHERE tablename LIKE 'ic_%' 
ORDER BY tablename, indexname;
```

## Rollback

To remove all tables:

```sql
-- WARNING: This will delete ALL intelligent chat data!
DROP TABLE IF EXISTS ic_credit_usage CASCADE;
DROP TABLE IF EXISTS ic_book_comments_access CASCADE;
DROP TABLE IF EXISTS ic_reminders CASCADE;
DROP TABLE IF EXISTS ic_user_preferences CASCADE;
DROP TABLE IF EXISTS ic_user_corrections CASCADE;
DROP TABLE IF EXISTS ic_message_feedback CASCADE;
DROP TABLE IF EXISTS ic_vet_reports CASCADE;
DROP TABLE IF EXISTS ic_message_documents CASCADE;
DROP TABLE IF EXISTS ic_documents CASCADE;
DROP TABLE IF EXISTS ic_dog_profiles CASCADE;
DROP TABLE IF EXISTS ic_conversation_context CASCADE;
DROP TABLE IF EXISTS ic_messages CASCADE;
DROP TABLE IF EXISTS ic_conversations CASCADE;

-- Drop trigger functions
DROP FUNCTION IF EXISTS ic_update_message_date_group() CASCADE;
DROP FUNCTION IF EXISTS ic_update_message_search_vector() CASCADE;
DROP FUNCTION IF EXISTS ic_update_updated_at_column() CASCADE;
```

## Troubleshooting

### Error: "relation already exists"
Tables already exist. This is safe - the migration uses `CREATE TABLE IF NOT EXISTS`.

### Error: "relation does not exist" (for foreign keys)
Ensure prerequisite tables exist:
- `users`
- `pet_profiles`
- `book_notes`

### Error: "permission denied"
Ensure your database user has CREATE TABLE privileges:
```sql
GRANT CREATE ON DATABASE your_database TO your_user;
```

## Schema Version

- **Version:** 2.0.0
- **Date:** 2025-10-13
- **Prefix:** `ic_` (intelligent_chat)

## Related Files

- **Models:** `/backend/intelligent_chat/models/`
- **Services:** `/backend/intelligent_chat/services/`
- **API Routes:** `/backend/intelligent_chat/api/routes/`
- **Config:** `/backend/intelligent_chat/config/`

## Support

For issues or questions:
1. Check model files in `/models/` for field definitions
2. Review SQLAlchemy models for relationships
3. Check logs during migration execution
4. Verify database connection settings

---

**Created:** 2025-10-13  
**Author:** AI Assistant  
**Purpose:** Comprehensive schema setup for Intelligent Chat System

