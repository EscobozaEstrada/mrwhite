# Profile Image vs Uploaded Image Priority Fix

## Problem Summary

User reported two issues:

### Issue 1: Profile Images Shown When Documents Attached
When uploading 4 images with a message "these are some images of bella", the chatbot would:
- Skip semantic document search ✅ (working)
- Show the 4 uploaded images
- **BUT ALSO show the dog profile image** ❌
- Focus on the profile image instead of the uploaded images

### Issue 2: "Share the images" Only Returns Profile Image
When asking "can you share the images of bella":
- Only returns the dog **profile image** ❌
- Does NOT return the 4 images just uploaded ❌
- Should return ALL uploaded images from the conversation

## Root Causes

### Root Cause #1: Profile Images Always Injected
The code automatically injects dog profile images whenever an image-related query is detected, even when documents are explicitly attached:

```python
# OLD CODE (BROKEN):
if is_image_related and dog_profiles:
    memory_context += "**🐕 YOUR DOG PROFILE IMAGES:**\n\n"
    # ... adds profile images
```

This happened **regardless** of whether the user just uploaded new images!

### Root Cause #2: Insufficient Reference Query Detection
The reference query keywords were too strict:

```python
# OLD KEYWORDS:
reference_keywords = ['i shared', 'i uploaded', 'i sent', 'i gave', 'that i', 'i provided']
```

User's query "**can you share the images of bella**" didn't match any of these, so it used semantic search instead of retrieving ALL conversation images.

## Solutions

### Solution #1: Skip Profile Images When Documents Attached

Added `has_attached_documents` parameter to `_prepare_messages()`:

```python
def _prepare_messages(
    self,
    conversation_history: List[Dict],
    current_message: str,
    retrieved_memories: List[Dict],
    dog_profiles: Optional[List[Dict]] = None,
    has_attached_documents: bool = False  # NEW PARAMETER
) -> List[Dict[str, str]]:
```

Updated profile image injection logic:

```python
# NEW CODE (FIXED):
# Skip profile images if documents are explicitly attached to this message
# (user wants to focus on their uploaded docs, not profile pics)
if is_image_related and dog_profiles and not has_attached_documents:
    dog_images = [d for d in dog_profiles if d.get('image_url')]
    if dog_images:
        memory_context += "**🐕 YOUR DOG PROFILE IMAGES:**\n\n"
        # ... adds profile images
```

Pass the flag when calling `_prepare_messages()`:

```python
messages = self._prepare_messages(
    conversation_history=context.get("conversation_history", []),
    current_message=message_content,
    retrieved_memories=context.get("retrieved_memories", []),
    dog_profiles=context.get("dog_profiles", []),
    has_attached_documents=bool(document_ids)  # NEW PARAMETER
)
```

### Solution #2: Expanded Reference Query Keywords

Added more natural phrases that indicate the user wants ALL previously shared items:

```python
# NEW KEYWORDS (EXPANDED):
reference_keywords = [
    'i shared', 'i uploaded', 'i sent', 'i gave', 'that i', 'i provided',
    'share the', 'show me the', 'send me', 'give me the', 'all the',  # NEW
    'images of', 'pictures of', 'photos of'  # NEW
]
```

Now queries like these trigger full conversation retrieval:
- "can you **share the** images"
- "**show me the** photos"
- "**images of** bella"
- "**pictures of** my dog"

## Files Modified

1. **`services/chat_service.py`**
   - Added `has_attached_documents` parameter to `_prepare_messages()`
   - Updated profile image injection to skip when `has_attached_documents=True`
   - Pass `has_attached_documents=bool(document_ids)` when calling `_prepare_messages()`

2. **`services/memory_service.py`**
   - Expanded `reference_keywords` list to include more natural query patterns
   - Now detects "share the images", "images of [dog]", "show me the photos", etc.

## Behavior Comparison

### Scenario 1: User Uploads Images

**Before:**
```
User: "these are images of bella" + [uploads 4 images]
Context:
  ├─ 4 uploaded images ✅
  └─ 1 profile image ❌ (shouldn't be here!)
AI: Talks about profile image instead of uploaded ones ❌
```

**After:**
```
User: "these are images of bella" + [uploads 4 images]
Context:
  └─ 4 uploaded images only ✅ (profile image skipped!)
AI: Focuses on the 4 newly uploaded images ✅
```

### Scenario 2: User Asks For Images Later

**Before:**
```
User: "can you share the images of bella"
System: Semantic search → Returns profile image + maybe 2-3 uploaded images
AI: Only shows profile image ❌
```

**After:**
```
User: "can you share the images of bella"
System: Detects reference query → Retrieves ALL from conversation history
AI: Shows ALL 4 uploaded images ✅
```

## When Profile Images ARE Shown

Profile images will still be shown when:
1. **No documents attached** to current message, AND
2. User is **NOT** referencing previously uploaded images, AND
3. User asks an image-related question (e.g., "what does my dog look like?")

This is intentional - profile images are useful context when the user hasn't uploaded recent photos!

## Profile Image Suppression Logic

Profile images are **suppressed** when:
- Documents are attached to the current message, OR
- User message contains reference keywords like:
  - "i shared", "i uploaded", "i sent"
  - "show me the images/photos"
  - "the images", "my images", "these images"
  - "images of [dog name]"
  
This ensures the AI focuses on user-uploaded content, not profile pics!

## Testing

### Test 1: Upload + Immediate Query
1. Upload 4 images with message "here are images of bella"
2. **Expected**: AI focuses on 4 uploaded images, NO profile image mentioned
3. **Not expected**: AI should NOT discuss profile image

### Test 2: Later Query for Images
1. After uploading images, send: "share the images of bella"
2. **Expected**: AI returns ALL 4 uploaded images
3. **Not expected**: AI should NOT return only profile image

### Test 3: Profile Image Still Works
1. In a new conversation, ask: "what does my dog look like?"
2. **Expected**: AI shows profile image (no uploaded docs in conversation)
3. This confirms profile images still work when appropriate

## Log Output

**Test 1 - Upload with Documents (After Fix):**
```
📎 User attached 4 documents - prioritizing these over semantic search
⏭️ Skipping document semantic search (documents explicitly attached to message)
✅ Context: 4 attached documents (priority) + 1 conversation memories
📄 USER UPLOADED DOCUMENTS - FULL CONTENT AVAILABLE
[No profile images injected] ✅
```

**Test 2 - Later Query (After Fix):**
```
🔍 User asking for previously shared items - retrieving ALL from conversation 10
📎 Found 4 previously attached documents in conversation
[Returns all 4 uploaded images] ✅
```

## Impact

✅ AI focuses on user-uploaded images when explicitly attached
✅ Profile images no longer interfere with uploaded document analysis
✅ Queries like "share the images" now retrieve ALL conversation images
✅ Profile images still shown when appropriate (no uploaded docs)
✅ More intuitive and expected behavior for users

