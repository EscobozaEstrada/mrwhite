# Attached Document Priority Fix

## Problem

When users uploaded documents **with a message** (e.g., "here are some images of bella" + 3 images), the chatbot was:
1. Retrieving old documents from semantic search
2. Also fetching the newly attached documents
3. **Mixing them together** in the context
4. **Focusing on the OLD documents** instead of the newly attached ones

### Example from User Report

**User action:** Uploaded 3 new images (IDs: 54, 55, 56) with message "these are some images of bella"

**What happened:**
- Semantic search retrieved 3 OLD images from Pinecone
- System also fetched the 3 NEW attached images
- **Total context: 6 images** (3 old + 3 new)
- **Chatbot focused on the OLD images (dog profile images)** instead of the NEW ones the user just uploaded ❌

**What should happen:**
- When documents are explicitly attached, focus **ONLY** on those documents
- Don't confuse the AI with old semantic search results
- The user's intent is clear: "analyze THESE images I just uploaded"

## Root Cause

The code was always performing semantic document search, even when documents were explicitly attached to the current message. This created noise and confusion for the AI.

```python
# OLD LOGIC (BROKEN):
# 1. Always do semantic search (retrieve old documents)
retrieved_memories = semantic_search(query)  # Returns old docs

# 2. Then append attached docs
if attached_document_ids:
    attached_docs = fetch_attached_documents()
    retrieved_memories = attached_docs + retrieved_memories  # NEW + OLD mixed
```

## Solution

### 1. **Detect Attached Documents First**

When documents are attached to the current message, change the retrieval strategy:

```python
if attached_document_ids:
    # User explicitly attached documents - prioritize these!
    attached_docs = fetch_attached_documents()
    
    # Skip semantic document search to avoid confusion
    conversation_memories = retrieve_memories(skip_document_search=True)
    
    # Context = ONLY attached docs + conversation history
    context = attached_docs + conversation_memories
```

### 2. **Add `skip_document_search` Flag**

Added a new parameter to `MemoryService.retrieve_memories()`:

```python
async def retrieve_memories(
    self,
    query: str,
    user_id: int,
    skip_document_search: bool = False  # NEW FLAG
) -> List[Dict[str, Any]]:
    ...
```

### 3. **Skip Semantic Document Search When Flag is Set**

In `_retrieve_general_memories()`:

```python
documents = []
if not skip_document_search:
    # Normal: do semantic document search
    documents = await self.pinecone.query_vectors(...)
    logger.info(f"📄 Found {len(documents)} document chunks from semantic search")
else:
    # Documents explicitly attached: skip semantic search
    logger.info(f"⏭️ Skipping document semantic search (documents explicitly attached to message)")
```

## Files Modified

1. **`services/chat_service.py`**
   - Changed `_build_context()` to detect attached documents first
   - When documents are attached, skip semantic document search
   - Only retrieve conversation history (limit=2) to avoid noise

2. **`services/memory_service.py`**
   - Added `skip_document_search` parameter to `retrieve_memories()` and `_retrieve_general_memories()`
   - Skip Pinecone document search when flag is set

## Behavior Comparison

### Before Fix ❌

```
User: "here are some images of bella" + [uploads 3 new images]
System:
  ├─ Semantic search → 3 old images from profile
  ├─ Fetch attached → 3 new images
  └─ Total context: 6 images (3 old + 3 new)
  
AI: *focuses on old profile images instead of new uploads*
```

### After Fix ✅

```
User: "here are some images of bella" + [uploads 3 new images]
System:
  ├─ Detect: documents attached!
  ├─ Skip semantic document search ⏭️
  ├─ Fetch attached → 3 new images (PRIORITY)
  └─ Retrieve → 2 conversation memories only
  
Total context: 3 new images + 2 conversation memories

AI: *focuses on the 3 newly uploaded images* ✅
```

## When Semantic Search Still Runs

Semantic document search is **still enabled** when:
1. No documents are attached to the current message
2. User asks about documents later (e.g., "show me images I shared")
3. Normal conversation flow

## Benefits

✅ AI focuses on newly uploaded documents (user's clear intent)
✅ No confusion from mixing old and new documents
✅ Cleaner context for better AI responses
✅ Semantic search still works for non-attachment queries
✅ No performance impact (actually faster - skips one search!)

## Testing

To test this fix:

1. Upload 3-4 new images with a message like "these are some images of my dog"
2. **Expected**: AI should focus ONLY on the newly uploaded images
3. **Not expected**: AI should NOT mention old profile images or previously uploaded docs

Then test semantic search still works:

1. Send a message: "show me all the images I've uploaded"
2. **Expected**: AI should retrieve ALL images from conversation history via semantic search

## Log Output Changes

**Before:**
```
📎 Fetching 3 attached documents directly...
🔍 Searching documents in namespace: user_248_docs
📄 Found 3 document chunks from semantic search
✅ Added 3 attached documents to context
Memory breakdown: 6 documents, 2 conversations  ← 3 new + 3 old
```

**After:**
```
📎 User attached 3 documents - prioritizing these over semantic search
⏭️ Skipping document semantic search (documents explicitly attached to message)
✅ Context: 3 attached documents (priority) + 2 conversation memories  ← Only new docs!
```

## Impact

This fix ensures that when users explicitly upload documents, the AI's attention is **100% focused** on those documents, not distracted by semantically similar old documents. This matches user expectations and improves response quality significantly.


