# Contextual Retrieval & Re-Ranking System - Complete Explanation

## 📚 Overview

Your intelligent_chat system uses **Anthropic's Contextual Retrieval** approach combined with **multi-signal re-ranking** to retrieve the most relevant information for the AI chatbot.

---

## 🎯 How Contextual Retrieval Works

### **Step 1: Adding Context During Chunking**

When documents are chunked and stored, context is **prepended** to each chunk before embedding:

#### **For Documents (PDFs, DOCX, Images):**
**File:** `services/document_service.py` + `utils/embeddings.py`

```python
# Context added during storage
context = f"Document: {filename}, Type: {file_type}"

# For embeddings (in embeddings.py line 104-118)
enriched_text = f"{context}\n\n{chunk_text}"
embedding = await generate_embedding(enriched_text)
```

**Example:**
```
STORED IN PINECONE:
[Context]
Document: Max_VetReport.pdf, Type: pdf

[Chunk Text]
Patient: Max, a 3-year-old Golden Retriever...
```

#### **For Book Content:**
**File:** `scripts/index_book.py` (lines 245-257)

```python
context = f"""
Book: The Way of the Dog by Anahata Graceland
Chapter: {chunk['chapter']}
Page: {chunk['page']}
Topics: {', '.join(chunk['topics'])}
""".strip()

# Generate contextual embedding
embedding = await self.embeddings.generate_contextual_embedding(
    chunk=chunk["text"],
    context=context
)
```

**Example:**
```
STORED IN PINECONE:
[Context]
Book: The Way of the Dog by Anahata Graceland
Chapter: Chapter 3: Training Basics
Page: 42
Topics: training, behavior, positive reinforcement

[Chunk Text]
Dogs respond best to positive reinforcement...
```

---

## 🔍 Retrieval Process (Before Re-Ranking)

### **Configuration (settings.py):**

```python
# How many chunks to retrieve BEFORE re-ranking
DEFAULT_TOP_K: int = 10          # General mode
HEALTH_MODE_TOP_K: int = 15      # Health mode
WAYOFDOG_MODE_TOP_K: int = 8     # Way of Dog mode

# How many chunks to keep AFTER re-ranking
RERANK_TOP_N: int = 5            # Final top results
```

---

### **Different Modes Retrieve Different Amounts:**

#### **1. Health Mode** (`_retrieve_health_memories`)
**File:** `memory_service.py` lines 70-173

**BEFORE RE-RANKING:**
- 🏥 **5 chunks** from `vet_reports` namespace (user's actual vet records)
- 📄 **5 chunks** from `user_{id}_docs` namespace (user documents)
- 📖 **5 chunks** from `book-content` namespace (health topics)
- **Total: ~15 chunks retrieved**

**Priority Boosts Applied:**
```python
vet_reports:   priority_boost = 2.0  # 2x weight
user_docs:     priority_boost = 1.5  # 1.5x weight
book_health:   priority_boost = 1.2  # 1.2x weight
```

**AFTER RE-RANKING:**
- **5 chunks** remain (top 5 based on rerank_score)

---

#### **2. Way of Dog Mode** (`_retrieve_book_memories`)
**File:** `memory_service.py` lines 175-260

**BEFORE RE-RANKING:**
- 📝 **Up to 15 chunks** from `user_{id}_book_notes` namespace (user's personal comments)
- 📖 **8 chunks** from `book-content` namespace (book passages)
- 💬 **3 chunks** from `conversations` namespace (past context)
- **Total: ~26 chunks retrieved**

**Priority Boosts Applied:**
```python
user_book_notes:  priority_boost = 3.0  # 3x weight (HIGHEST!)
book_content:     priority_boost = 2.0  # 2x weight
conversations:    priority_boost = 1.0  # 1x weight
```

**Special Feature:**
```python
# Lines 244-253: Force user notes to appear
if user_notes and not reranked_note_ids:
    logger.warning("User notes excluded by reranking! Forcing them.")
    reranked = reranked[:top_k - num_notes_to_add] + user_notes[:num_notes_to_add]
```

**AFTER RE-RANKING:**
- **8 chunks** remain (top 8 based on rerank_score)

---

#### **3. General Mode** (`_retrieve_general_memories`)
**File:** `memory_service.py` lines 287-397

**BEFORE RE-RANKING:**
- 💬 **5 chunks** from `conversations` namespace
- 📄 **5 chunks** from `user_{id}_docs` namespace
- 📖 **5 chunks** from `book-content` namespace (if dog-related query)
- **Total: ~15 chunks retrieved**

**Special Detection:**
```python
# Lines 300-301: Detect document queries
document_keywords = ['summarize', 'summary', 'read', 'story', 'document', ...]
is_document_query = any(keyword in query_lower for keyword in document_keywords)

if is_document_query:
    doc_top_k = 20  # Get MORE document chunks (20!)
    conv_top_k = 2  # Fewer conversation chunks
    rerank_limit = 15  # Keep more after re-ranking
```

**AFTER RE-RANKING:**
- **5 chunks** remain (or **15 chunks** for document queries)

---

## 🏆 Re-Ranking Algorithm

**File:** `memory_service.py` lines 399-461

### **How Re-Ranking Score is Calculated:**

```python
rerank_score = (
    base_score * 0.6 +          # Semantic similarity (60%)
    recency_score * 0.2 +       # Recency (20%)
    keyword_score * 0.2         # Keyword match (20%)
) * priority_boost              # Apply priority multiplier
```

### **Breakdown of Each Component:**

#### **1. Base Score (Semantic Similarity) - 60%**
- **Source:** Pinecone's cosine similarity score
- **Range:** 0.0 to 1.0
- **Higher = more semantically similar to the query**

#### **2. Recency Score - 20%**
```python
# Lines 436-441
created_at = datetime.fromisoformat(metadata["created_at"])
days_old = (current_time - created_at).days
recency_score = max(0, 1.0 - (days_old / 365))  # Decay over a year
```
- **Range:** 0.0 to 1.0
- **Decays linearly over 365 days**
- Recent memories get higher scores

#### **3. Keyword Score - 20%**
```python
# Lines 444-446
query_keywords = set(query.lower().split())
content_keywords = set(metadata["text"].lower().split())
matching_keywords = len(query_keywords.intersection(content_keywords))
keyword_score = min(1.0, matching_keywords / max(1, len(query_keywords)))
```
- **Range:** 0.0 to 1.0
- **Measures keyword overlap** between query and chunk
- Helps catch exact term matches

#### **4. Priority Boost (Multiplier)**
```python
# Lines 449-456
priority_boost = memory.get("priority_boost", 1.0)
```
- **Health Mode:**
  - Vet reports: 2.0x
  - User docs: 1.5x
  - Book health: 1.2x
  
- **Way of Dog Mode:**
  - User book notes: 3.0x (HIGHEST!)
  - Book content: 2.0x
  - Conversations: 1.0x

---

## 📊 Example Re-Ranking Calculation

### **Scenario: Health Mode Query**
**Query:** "What did the vet say about Max's knee?"

**Retrieved Memories (Before Re-Ranking):**

| Chunk | Source | Base Score | Recency | Keyword | Priority | **Rerank Score** |
|-------|--------|------------|---------|---------|----------|------------------|
| Chunk 1 | Vet Report | 0.85 | 0.95 | 0.70 | 2.0x | **(0.85×0.6 + 0.95×0.2 + 0.70×0.2) × 2.0 = 1.73** |
| Chunk 2 | Book | 0.90 | 0.30 | 0.60 | 1.2x | (0.90×0.6 + 0.30×0.2 + 0.60×0.2) × 1.2 = 0.86 |
| Chunk 3 | User Doc | 0.80 | 0.80 | 0.50 | 1.5x | (0.80×0.6 + 0.80×0.2 + 0.50×0.2) × 1.5 = 1.11 |
| Chunk 4 | Conversation | 0.75 | 0.90 | 0.80 | 1.0x | (0.75×0.6 + 0.90×0.2 + 0.80×0.2) × 1.0 = 0.79 |
| Chunk 5 | Book | 0.88 | 0.20 | 0.40 | 1.2x | (0.88×0.6 + 0.20×0.2 + 0.40×0.2) × 1.2 = 0.78 |

**After Re-Ranking (Top 5):**
1. ✅ Chunk 1 (Vet Report) - 1.73
2. ✅ Chunk 3 (User Doc) - 1.11
3. ✅ Chunk 2 (Book) - 0.86
4. ✅ Chunk 4 (Conversation) - 0.79
5. ✅ Chunk 5 (Book) - 0.78

**Result:** Vet report prioritized despite slightly lower semantic score!

---

## ❓ Why 0 Chunks After Re-Ranking?

### **Problem Scenario:**

This happened in Way of Dog mode when user asked about their book comments.

**Root Cause (Fixed in lines 244-253):**

1. **User notes retrieved** from Pinecone: ✅ 5 chunks
2. **Re-ranking applied**: Book content had higher semantic scores
3. **User notes pushed out** of top 8 results
4. **Result**: 0 user notes shown, AI said "I don't have access"

### **The Fix:**

```python
# CRITICAL FIX: Force user notes to appear
user_note_ids = {id(note) for note in user_notes}
reranked_note_ids = {id(mem) for mem in reranked if mem.get("source_type") == "user_book_note"}

if user_notes and not reranked_note_ids:
    logger.warning("⚠️ User notes were retrieved but excluded by reranking! Forcing them to appear.")
    num_notes_to_add = min(len(user_notes), 5)
    reranked = reranked[:top_k - num_notes_to_add] + user_notes[:num_notes_to_add]
```

**How It Works:**
- If user notes exist but aren't in top results...
- **Force** them into the final list
- Remove lowest-ranked items to make room
- Guarantees user notes always appear when they exist

---

## 🤔 Is the Number of Chunks Fine?

### **Current Configuration:**

| Mode | Before Re-Ranking | After Re-Ranking | Is It Fine? |
|------|-------------------|------------------|-------------|
| General | 10-15 chunks | 5 chunks | ✅ **Good** - Balanced |
| Health | 15 chunks | 5 chunks | ✅ **Good** - Prioritizes vet reports |
| Way of Dog | 26 chunks | 8 chunks | ✅ **Good** - More book context |
| Document Query | 25 chunks | 15 chunks | ✅ **Good** - Rich context |

### **Recommendations:**

#### **✅ Current Setup is Well-Tuned:**

1. **Health Mode (5 final chunks):**
   - Perfect for focused medical info
   - Vet reports get priority boost
   - Not overwhelming

2. **Way of Dog Mode (8 final chunks):**
   - Good balance for philosophical discussions
   - Allows multiple book passages + user notes
   - User notes FORCED to appear (critical fix)

3. **General Mode (5-15 chunks):**
   - Adaptive based on query type
   - Document queries get more chunks (15)
   - Regular queries stay focused (5)

#### **⚠️ Potential Improvements:**

1. **Consider Health Mode = 7 chunks** (instead of 5)
   - Medical queries often need more context
   - Could include more vet report chunks

2. **Add mode-specific keyword detection**
   - Auto-boost for certain medical terms in Health Mode
   - Spiritual/philosophical terms in Way of Dog Mode

3. **Implement BM25 hybrid search** (mentioned in docs but not implemented)
   - Combine keyword + semantic search
   - Better for exact term matches

---

## 📈 Chunk Flow Visualization

```
┌─────────────────────────────────────────────────────────────┐
│                    USER QUERY                                │
│            "What did the vet say about Max?"                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              GENERATE QUERY EMBEDDING                        │
│              (1024-dimensional vector)                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│         RETRIEVE FROM MULTIPLE NAMESPACES                    │
│                                                              │
│  📍 vet_reports:     5 chunks (score 0.7-0.9)              │
│  📍 user_docs:       5 chunks (score 0.6-0.8)              │
│  📍 book-content:    5 chunks (score 0.5-0.7)              │
│                                                              │
│  TOTAL: 15 chunks retrieved                                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              APPLY PRIORITY BOOSTS                           │
│                                                              │
│  Vet reports:   score × 2.0                                 │
│  User docs:     score × 1.5                                 │
│  Book health:   score × 1.2                                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                 CALCULATE RERANK SCORES                      │
│                                                              │
│  rerank_score = (                                           │
│      base_score × 0.6 +        (semantic)                   │
│      recency_score × 0.2 +     (time decay)                 │
│      keyword_score × 0.2       (keyword match)              │
│  ) × priority_boost                                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              SORT BY RERANK SCORE                            │
│                                                              │
│  Chunk 1: rerank_score = 1.73 (vet report)                 │
│  Chunk 2: rerank_score = 1.11 (user doc)                   │
│  Chunk 3: rerank_score = 0.86 (book)                       │
│  Chunk 4: rerank_score = 0.79 (conversation)               │
│  Chunk 5: rerank_score = 0.78 (book)                       │
│  ...                                                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              RETURN TOP 5 CHUNKS                             │
│              (or 8 for Way of Dog, 15 for document queries) │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│         FORMAT CONTEXT FOR AI CHATBOT                        │
│         (in base_chat_service.py)                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Key Takeaways

### **1. Contextual Embeddings Make Search Better**
- Context is prepended during chunking
- Embeddings capture both content + context
- More accurate retrieval

### **2. Multi-Stage Retrieval**
- **Stage 1:** Semantic search (Pinecone)
- **Stage 2:** Priority boosting (mode-specific)
- **Stage 3:** Re-ranking (3 signals)
- **Stage 4:** Force critical chunks (user notes)

### **3. Mode-Specific Tuning**
- Health Mode: Prioritizes real medical records
- Way of Dog: Prioritizes user's personal comments
- General Mode: Balanced approach

### **4. The "0 Chunks" Problem**
- Happened when user notes had low semantic scores
- **Fixed** by forcing user notes into results
- Guarantees user's data is always shown

### **5. Current Configuration is Solid**
- Well-balanced chunk counts
- Priority boosts work well
- Adaptive based on query type

---

## 🔧 Files Reference

| File | Purpose |
|------|---------|
| `memory_service.py` (lines 399-461) | Re-ranking algorithm |
| `embeddings.py` (lines 104-118) | Contextual embedding generation |
| `settings.py` (lines 72-75) | Retrieval configuration |
| `document_service.py` (lines 160-196) | Document chunking + storage |
| `scripts/index_book.py` (lines 232-277) | Book indexing with context |

---

## 💡 Potential Enhancements

1. **Implement BM25 Hybrid Search**
   - Combine keyword + semantic
   - Better for medical terms, exact names

2. **Dynamic Top-K Based on Query Complexity**
   - Simple queries: 3-5 chunks
   - Complex queries: 10-15 chunks

3. **User Feedback Loop**
   - Track which chunks users like/dislike
   - Adjust priority boosts over time

4. **Cross-Encoder Re-Ranking**
   - Use a re-ranking model (e.g., BGE reranker)
   - More accurate than simple scoring

---

**Your system is well-designed and the chunk retrieval numbers are appropriate for each mode!** 🎉




