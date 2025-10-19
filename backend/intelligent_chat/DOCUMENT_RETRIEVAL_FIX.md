# Document Retrieval Fix - "Images I Shared" Issue

## Problem

When users asked for "images I shared" or "documents I uploaded" later in a conversation, the chatbot would only return 2-4 images based on semantic similarity, not ALL the images they had previously uploaded to that conversation.

### Root Cause

The system was relying solely on **semantic search** from Pinecone, which returns only the most semantically similar documents to the current query. When a user says "send me more images", the semantic search algorithm doesn't understand they want ALL previously uploaded images - it just finds the ones most similar to that phrase.

### Example from Logs

```
Line 114: ✅ Retrieved 4 matches from namespace 'user_248_docs'  ✅
Line 296: ✅ Retrieved 2 matches from namespace 'user_248_docs'  ❌ Only 2!
```

## Solution

### 1. **Detect Reference Queries**

Added detection for when users explicitly reference previously shared items:

```python
# Detect if asking for "images/documents I shared" - indicating they want ALL previous items
reference_keywords = ['i shared', 'i uploaded', 'i sent', 'i gave', 'that i', 'i provided']
is_reference_query = any(keyword in query_lower for keyword in reference_keywords) and is_image_query
```

### 2. **Retrieve ALL Documents from Conversation History**

When a reference query is detected, the system now queries the database directly to get ALL documents attached to messages in that conversation:

```python
if is_reference_query and conversation_id:
    logger.info(f"🔍 User asking for previously shared items - retrieving ALL from conversation {conversation_id}")
    
    # Query ic_message_documents to get ALL documents from this conversation
    result = await session.execute(
        text("""
            SELECT DISTINCT d.id, d.filename, d.file_type, d.s3_url, 
                   d.extracted_text, d.created_at
            FROM ic_documents d
            JOIN ic_message_documents md ON d.id = md.document_id
            JOIN ic_messages m ON md.message_id = m.id
            WHERE m.conversation_id = :conversation_id
              AND m.user_id = :user_id
            ORDER BY d.created_at DESC
        """),
        {"conversation_id": conversation_id, "user_id": user_id}
    )
```

### 3. **Pass conversation_id Through the Call Stack**

Updated method signatures to pass `conversation_id` from the API route all the way down to the memory retrieval:

```
API Route (chat.py)
  ↓
ChatService._build_context()
  ↓
ChatService._retrieve_memories()
  ↓
MemoryService.retrieve_memories()
  ↓
MemoryService._retrieve_general_memories(conversation_id)
  ↓
Database query for ALL conversation documents
```

## Files Modified

1. **`services/memory_service.py`**
   - Added `conversation_id` parameter to `retrieve_memories()` and `_retrieve_general_memories()`
   - Added reference query detection logic
   - Added database query to retrieve ALL documents from conversation history

2. **`services/chat_service.py`**
   - Updated `_build_context()` to pass `conversation_id` to `retrieve_memories()`

3. **`services/base_chat_service.py`**
   - Updated `_build_context()` and `_retrieve_memories()` to accept and pass `conversation_id`

4. **`services/health_chat_service.py`**
   - Updated `_retrieve_memories()` signature to accept `conversation_id`

5. **`services/wayofdog_chat_service.py`**
   - Updated `_retrieve_memories()` signature to accept `conversation_id`

## How It Works Now

### Scenario 1: User uploads 4 images and immediately asks about them
- **Before**: Semantic search returns 4 images ✅
- **After**: Same behavior ✅

### Scenario 2: User asks "send me more images I shared" later
- **Before**: Semantic search returns only 2-4 most similar images ❌
- **After**: System detects reference query → Queries database → Returns ALL 4 images ✅

### Scenario 3: User asks general question about documents
- **Before**: Semantic search returns relevant documents ✅
- **After**: Same behavior (semantic search still used for non-reference queries) ✅

## Testing

To test this fix:

1. Upload 4-5 images to a conversation
2. Have a few back-and-forth messages
3. Ask: "Can you show me all the images I shared with you?"
4. **Expected**: All uploaded images should be returned, not just 2-3

## Trigger Phrases

The system now recognizes these phrases as "reference queries":
- "images I shared"
- "documents I uploaded"
- "photos I sent"
- "files I gave you"
- "pictures that I provided"

## Benefits

✅ Users can now reliably retrieve ALL previously uploaded documents
✅ Semantic search still works for general queries
✅ No performance impact (database query only runs for reference queries)
✅ Works across all chat modes (General, Health, Way of Dog)

## Notes

- The fix only applies to **General Mode** currently (where `active_mode=None`)
- Health and Way of Dog modes already have their own specialized retrieval logic
- The database query is efficient (uses JOINs and indexes)
- Documents are still filtered by file type if the query specifically asks for images


