# Pinecone Configuration for Intelligent Chat System

## Overview
The Intelligent Chat system uses Pinecone for semantic search and memory retrieval across multiple content types.

## Namespace Strategy

### Production Namespaces:
```
intelligent-chat-documents-prod
intelligent-chat-vet-reports-prod
intelligent-chat-conversations-prod
intelligent-chat-book-comments-prod
```

### Development Namespaces:
```
intelligent-chat-documents-dev
intelligent-chat-vet-reports-dev
intelligent-chat-conversations-dev
intelligent-chat-book-comments-dev
```

## Index Configuration

### Index Name: `intelligent-chat`

**Specifications:**
- **Dimension**: 1536 (for OpenAI text-embedding-3-small) or 1024 (for Amazon Titan embeddings)
- **Metric**: cosine
- **Pod Type**: s1 or p1 (production)
- **Replicas**: 1 (can scale up)

### Metadata Schema

#### 1. Documents Namespace (`intelligent-chat-documents-{env}`)
```json
{
  "type": "document",
  "user_id": 123,
  "document_id": 456,
  "conversation_id": 789,
  "message_id": 1011,
  "filename": "dog_training_guide.pdf",
  "file_type": "pdf",
  "s3_url": "https://s3...",
  "chunk_index": 0,
  "total_chunks": 5,
  "page_number": 1,
  "uploaded_at": "2025-01-15T10:30:00Z",
  "content_type": "text",
  "language": "en"
}
```

#### 2. Vet Reports Namespace (`intelligent-chat-vet-reports-{env}`)
```json
{
  "type": "vet_report",
  "user_id": 123,
  "dog_profile_id": 45,
  "report_id": 67,
  "dog_name": "Max",
  "dog_breed": "Golden Retriever",
  "report_date": "2025-01-10",
  "report_name": "Annual Checkup 2025",
  "s3_url": "https://s3...",
  "chunk_index": 0,
  "key_findings": ["healthy", "vaccination_due"],
  "uploaded_at": "2025-01-15T10:30:00Z"
}
```

#### 3. Conversations Namespace (`intelligent-chat-conversations-{env}`)
```json
{
  "type": "conversation",
  "user_id": 123,
  "conversation_id": 789,
  "message_id": 1011,
  "role": "user",
  "date": "2025-01-15",
  "active_mode": "health",
  "dog_profile_id": 45,
  "has_documents": false,
  "created_at": "2025-01-15T10:30:00Z"
}
```

#### 4. Book Comments Namespace (`intelligent-chat-book-comments-{env}`)
```json
{
  "type": "book_comment",
  "user_id": 123,
  "book_note_id": 456,
  "user_book_copy_id": 789,
  "chapter_name": "Chapter 3: Training Basics",
  "page_number": 42,
  "note_type": "note",
  "selected_text": "...",
  "created_at": "2025-01-15T10:30:00Z"
}
```

## Chunking Strategy

### Text Documents (PDFs, DOCX, TXT):
- **Max Chunk Size**: 1000 tokens (~750 words)
- **Overlap**: 200 tokens (~150 words)
- **Separator**: Paragraphs, then sentences
- **Include**: Page numbers, headers, context

### Images:
- **Description**: Full image analysis from Claude Vision
- **No Chunking**: Single vector per image
- **Metadata**: Include analysis results

### Vet Reports:
- **Max Chunk Size**: 800 tokens (smaller for medical precision)
- **Overlap**: 150 tokens
- **Preserve**: Medical terminology, dates, measurements
- **Extract**: Key findings as separate metadata

### Conversations:
- **Window Size**: 5 messages grouped together
- **Sliding Window**: Overlap of 2 messages
- **Include**: Mode context, dog profile info

### Book Comments:
- **Include**: Comment + selected text + context before/after
- **Single Vector**: Per comment
- **Rich Context**: Chapter, page, tags

## Contextual Retrieval Implementation

### Strategy (per Anthropic's recommendations):

1. **Add Context to Chunks**:
   ```python
   # For each chunk, prepend document context
   context = f"Document: {filename}, Type: {file_type}, Page: {page_number}"
   enriched_chunk = f"{context}\n\n{chunk_text}"
   ```

2. **Generate Contextual Embeddings**:
   - Embed both the chunk AND its context
   - Store original chunk in metadata
   - Use enriched version for semantic search

3. **Use BM25 + Semantic Hybrid**:
   - Combine keyword matching with semantic search
   - Re-rank results using both scores

4. **Re-ranking**:
   - Retrieve top 20 results
   - Re-rank to top 5 using:
     - Relevance score
     - Recency (time decay)
     - User preference patterns

## Query Strategies

### 1. Simple Query (No Mode Active):
```python
# Search conversations + documents
namespaces = ['conversations', 'documents']
top_k = 10
```

### 2. Health Mode Query:
```python
# Priority: Vet reports > Conversations > Documents
namespaces = ['vet-reports', 'conversations', 'documents']
filters = {"dog_profile_id": selected_dog_id}
top_k = 15
```

### 3. Way of Dog Mode Query:
```python
# Only book comments
namespaces = ['book-comments']
top_k = 8
```

### 4. Reminder Mode Query:
```python
# Conversations for context
namespaces = ['conversations']
filters = {"active_mode": "reminders"}
top_k = 5
```

## Embedding Model Configuration

### Primary: Amazon Titan Text Embeddings
```python
model_id = "amazon.titan-embed-text-v2:0"
dimensions = 1024
```

### Fallback: OpenAI text-embedding-3-small
```python
model = "text-embedding-3-small"
dimensions = 1536
```

## Usage Limits & Scaling

### Free Tier (if applicable):
- 1 index
- 100K vectors
- 1 pod

### Production Recommendations:
- **Vectors per user**: ~500-1000 (conversations + documents)
- **For 10,000 users**: ~10M vectors
- **Index size**: p1.x2 or s1.x4

### Cost Optimization:
1. Delete old conversation vectors after 90 days
2. Keep documents/vet reports forever
3. Compress older conversations

## Setup Script

```python
import pinecone
from pinecone import ServerlessSpec

# Initialize
pinecone.init(api_key="YOUR_API_KEY", environment="YOUR_ENV")

# Create index
index_name = "intelligent-chat"
if index_name not in pinecone.list_indexes():
    pinecone.create_index(
        name=index_name,
        dimension=1024,  # or 1536 for OpenAI
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )

print(f"✅ Index '{index_name}' created successfully!")
```

## Monitoring & Maintenance

### Metrics to Track:
- Query latency (<100ms target)
- Recall rate (>95% target)
- Index size growth
- Credit usage per query

### Regular Maintenance:
- Weekly: Check for orphaned vectors
- Monthly: Analyze query patterns
- Quarterly: Re-evaluate chunking strategy
- Yearly: Consider re-embedding with better models

## Security

### Access Control:
- User ID filtering on ALL queries
- Never expose other users' data
- Validate user_id matches session

### Data Privacy:
- Encrypt vectors at rest
- Secure API keys in environment variables
- Audit logs for all operations






