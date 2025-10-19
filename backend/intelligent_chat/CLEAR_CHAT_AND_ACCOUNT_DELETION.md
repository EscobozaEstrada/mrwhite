# Clear Chat & Account Deletion Implementation

## Overview
This document explains how clearing chat and account deletion work in the Intelligent Chat system, specifically addressing Pinecone namespace management and data cleanup.

---

## 1. **Clear Chat Functionality**

### Two Options:

#### **Option A: Clear Chat Only**
- **What happens:**
  - ✅ Deletes all messages from `ic_messages` table
  - ✅ Clears messages from UI
  - ❌ Does NOT touch Pinecone (memories remain)
  
- **Use case:** User wants fresh conversation but keep AI's learned context
  
- **Backend behavior:**
  ```python
  # Soft delete messages
  await db.execute(
      delete(Message).where(Message.conversation_id == conversation_id)
  )
  ```

#### **Option B: Clear Chat + Memory**
- **What happens:**
  - ✅ Deletes all messages from `ic_messages` table
  - ✅ Clears messages from UI
  - ✅ Deletes user's vectors from ALL Pinecone namespaces
  
- **Use case:** User wants complete reset (fresh start)

---

## 2. **Pinecone Namespace Architecture**

### **Shared Namespaces** (Multi-user, filtered by `user_id`):
```
intelligent-chat-conversations-development     # All users' conversations
intelligent-chat-documents-development         # All users' documents  
intelligent-chat-vet-reports-development       # All users' vet reports
book-content-development                       # Shared book content (NO user_id filter!)
```

### **User-Specific Namespaces** (Isolated per user):
```
user_248_docs          # User 248's documents
user_248_book_notes    # User 248's book comments
user_349_docs          # User 349's documents  
user_349_book_notes    # User 349's book comments
```

---

## 3. **How Pinecone Deletion Works**

### **For Shared Namespaces:**
❌ **Cannot delete the entire namespace** (would affect all users!)

✅ **Use metadata filtering to delete specific user's data:**
```python
# Delete user 248's data from shared namespace
await pinecone.delete_by_filter(
    filter={"user_id": 248},
    namespace="intelligent-chat-conversations-development"
)
```

**This deletes ONLY vectors where `metadata.user_id == 248`**

### **For User-Specific Namespaces:**
✅ **Can delete entire namespace** (only contains that user's data):
```python
# Delete user's entire namespace
await pinecone.index.delete(
    delete_all=True,
    namespace="user_248_book_notes"
)
```

---

## 4. **Complete Implementation for Clear Memory**

### Current Implementation (Partial):
```python
# From memory_service.py - lines 658-704
async def clear_user_memories(self, user_id: int, namespace: Optional[str] = None):
    """Clear all memories for a user"""
    filter_dict = {"user_id": user_id}
    
    if namespace:
        # Clear specific namespace
        await self.pinecone.delete_by_filter(
            filter=filter_dict,
            namespace=namespace
        )
    else:
        # Clear all namespaces
        namespaces = [
            self.pinecone.namespace_conversations,
            self.pinecone.namespace_documents,
            self.pinecone.namespace_vet_reports,
            self.pinecone.namespace_book_comments
        ]
        
        for ns in namespaces:
            await self.pinecone.delete_by_filter(
                filter=filter_dict,
                namespace=ns
            )
```

### ⚠️ **Missing Functionality:**
1. **User-specific namespaces not cleared** (`user_{user_id}_docs`, `user_{user_id}_book_notes`)
2. **Book content namespace cannot be filtered by user** (it's shared content)
3. **No cleanup of `ic_conversation_context`, `ic_message_feedback`, etc.**

---

## 5. **Enhanced Clear Memory Implementation**

### What needs to be cleared:

#### **Database Tables:**
```sql
-- Messages
DELETE FROM ic_messages WHERE conversation_id = ?

-- Conversation context
DELETE FROM ic_conversation_context WHERE conversation_id = ?

-- Message feedback
DELETE FROM ic_message_feedback WHERE message_id IN (
    SELECT id FROM ic_messages WHERE conversation_id = ?
)

-- User corrections
DELETE FROM ic_user_corrections WHERE conversation_id = ?

-- Credit usage tracking
DELETE FROM ic_credit_usage WHERE conversation_id = ?
```

#### **Pinecone Namespaces:**

**Shared namespaces (filter by user_id):**
- `intelligent-chat-conversations-{env}`
- `intelligent-chat-documents-{env}`
- `intelligent-chat-vet-reports-{env}`
- `intelligent-chat-book-comments-{env}` (if used)

**User-specific namespaces (delete entirely):**
- `user_{user_id}_docs`
- `user_{user_id}_book_notes`

**DO NOT DELETE:**
- `book-content-{env}` - Shared content, no user ownership

---

## 6. **Account Deletion Flow**

### When user deletes account from settings:

#### **Step 1: Delete from `ic_*` tables**
```sql
-- Order matters due to foreign key constraints!

-- 1. Delete message-related data first
DELETE FROM ic_message_feedback WHERE message_id IN (
    SELECT id FROM ic_messages WHERE user_id = ?
);

DELETE FROM ic_user_corrections WHERE user_id = ?;

DELETE FROM ic_message_document WHERE message_id IN (
    SELECT id FROM ic_messages WHERE user_id = ?
);

-- 2. Delete messages
DELETE FROM ic_messages WHERE user_id = ?;

-- 3. Delete conversation-related data
DELETE FROM ic_conversation_context WHERE user_id = ?;
DELETE FROM ic_conversations WHERE user_id = ?;

-- 4. Delete documents and dog profiles
DELETE FROM ic_documents WHERE user_id = ?;
DELETE FROM ic_vet_reports WHERE user_id = ?;
DELETE FROM ic_dog_profiles WHERE user_id = ?;

-- 5. Delete preferences and access logs
DELETE FROM ic_user_preferences WHERE user_id = ?;
DELETE FROM ic_book_comments_access WHERE user_id = ?;

-- 6. Delete credit tracking
DELETE FROM ic_credit_usage WHERE user_id = ?;
```

#### **Step 2: Delete from Pinecone**
```python
# Shared namespaces (filter by user_id)
shared_namespaces = [
    "intelligent-chat-conversations-development",
    "intelligent-chat-documents-development",
    "intelligent-chat-vet-reports-development",
]

for ns in shared_namespaces:
    await pinecone.delete_by_filter(
        filter={"user_id": user_id},
        namespace=ns
    )

# User-specific namespaces (delete entirely)
user_namespaces = [
    f"user_{user_id}_docs",
    f"user_{user_id}_book_notes",
]

for ns in user_namespaces:
    try:
        await pinecone.index.delete(
            delete_all=True,
            namespace=ns
        )
    except Exception as e:
        # Namespace might not exist, that's okay
        logger.warning(f"Could not delete namespace {ns}: {e}")
```

#### **Step 3: Delete from S3**
```python
# Delete user's uploaded files
s3_prefix = f"intelligent-chat/user_{user_id}/"

# List and delete all objects under this prefix
objects = s3.list_objects_v2(Bucket=bucket_name, Prefix=s3_prefix)
if 'Contents' in objects:
    for obj in objects['Contents']:
        s3.delete_object(Bucket=bucket_name, Key=obj['Key'])
```

#### **Step 4: Delete from main `users` table**
```python
# Finally delete the user record
DELETE FROM users WHERE id = ?;
```

---

## 7. **Updated Clear Memory Service**

```python
# Enhanced version to be implemented
async def clear_user_memories_complete(
    self, 
    user_id: int, 
    clear_user_namespaces: bool = True
) -> bool:
    """
    Completely clear all memories for a user from Pinecone
    
    Args:
        user_id: User ID
        clear_user_namespaces: Also delete user-specific namespaces
    
    Returns:
        True if successful
    """
    try:
        filter_dict = {"user_id": user_id}
        
        # 1. Clear shared namespaces (filter by user_id)
        shared_namespaces = [
            self.pinecone.namespace_conversations,
            self.pinecone.namespace_documents,
            self.pinecone.namespace_vet_reports,
        ]
        
        for ns in shared_namespaces:
            try:
                await self.pinecone.delete_by_filter(
                    filter=filter_dict,
                    namespace=ns
                )
                logger.info(f"✅ Cleared user {user_id} from shared namespace: {ns}")
            except Exception as e:
                logger.error(f"❌ Failed to clear {ns}: {e}")
        
        # 2. Clear user-specific namespaces (delete entirely)
        if clear_user_namespaces:
            user_namespaces = [
                f"user_{user_id}_docs",
                f"user_{user_id}_book_notes",
            ]
            
            for ns in user_namespaces:
                try:
                    # Delete all vectors in user-specific namespace
                    await self.pinecone.index.delete(
                        delete_all=True,
                        namespace=ns
                    )
                    logger.info(f"✅ Deleted user namespace: {ns}")
                except Exception as e:
                    # Namespace might not exist - that's okay
                    logger.warning(f"⚠️ Could not delete namespace {ns}: {e}")
        
        logger.info(f"✅ Completely cleared all memories for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to clear memories: {str(e)}")
        return False
```

---

## 8. **Frontend Clear Button Implementation**

### Updated `ChatHeader.tsx`:
```typescript
const handleClearChat = async () => {
  // Show custom dialog
  const choice = await showClearDialog(); // "chat" | "memory" | "cancel"
  
  if (choice === "cancel") return;
  
  const clearMemory = choice === "memory";
  
  try {
    await apiClearChat(conversationId, clearMemory);
    
    // Clear UI
    setMessages([]);
    
    // Show success message
    if (clearMemory) {
      toast.success("Chat and memories cleared!");
    } else {
      toast.success("Chat cleared! Memories preserved.");
    }
  } catch (error) {
    toast.error("Failed to clear chat");
  }
};
```

---

## 9. **Database Cascade Deletion Setup**

### Ensure proper CASCADE constraints:

```sql
-- Example for ic_messages
ALTER TABLE ic_messages 
ADD CONSTRAINT fk_ic_messages_user 
FOREIGN KEY (user_id) REFERENCES users(id) 
ON DELETE CASCADE;

-- Example for ic_dog_profiles
ALTER TABLE ic_dog_profiles 
ADD CONSTRAINT fk_ic_dog_profiles_user 
FOREIGN KEY (user_id) REFERENCES users(id) 
ON DELETE CASCADE;
```

**All `ic_*` tables should have `ON DELETE CASCADE` on `user_id` foreign keys.**

---

## 10. **Testing Checklist**

### Clear Chat (Chat Only):
- [ ] Messages deleted from database
- [ ] UI cleared
- [ ] Pinecone vectors remain
- [ ] Can see previous context if starting new chat

### Clear Chat (Chat + Memory):
- [ ] Messages deleted from database
- [ ] UI cleared
- [ ] Pinecone vectors deleted (shared namespaces)
- [ ] User-specific namespaces deleted
- [ ] Fresh start with no context

### Account Deletion:
- [ ] All `ic_*` table records deleted
- [ ] Pinecone vectors deleted (all namespaces)
- [ ] S3 files deleted
- [ ] User record deleted from `users` table
- [ ] No orphaned data in any table
- [ ] Shared book content remains for other users

---

## 11. **Summary**

### Clear Chat Only:
- Database: ✅ Cleared
- Pinecone: ❌ Preserved
- S3: ❌ Preserved

### Clear Chat + Memory:
- Database: ✅ Cleared
- Pinecone: ✅ Cleared (user's data only)
- S3: ❌ Preserved

### Account Deletion:
- Database: ✅ Completely deleted (all `ic_*` + `users`)
- Pinecone: ✅ Completely deleted (all namespaces)
- S3: ✅ Completely deleted (user's folder)

**Key Insight:** Shared namespaces use metadata filtering, user-specific namespaces can be deleted entirely.


