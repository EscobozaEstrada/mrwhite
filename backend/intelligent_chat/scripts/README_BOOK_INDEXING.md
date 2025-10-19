# Index "The Way of the Dog" Book to Pinecone

## Overview

This script processes and indexes "The Way of the Dog" by Anahata Graceland into Pinecone for use in **Way of Dog Mode** in the Intelligent Chat system.

## Script Location

```
/home/ubuntu/Mr-White-Project/backend/intelligent_chat/scripts/index_book.py
```

## What It Does

1. **Extracts text** from the PDF page by page
2. **Detects chapters** automatically
3. **Detects topics** (training, health, nutrition, psychology, etc.)
4. **Chunks text** intelligently (500-2000 characters per chunk)
5. **Generates embeddings** using AWS Bedrock (with contextual retrieval)
6. **Uploads to Pinecone** in the `book-content-{environment}` namespace

## Prerequisites

### 1. PDF File Location

The PDF should be at:
```
/home/ubuntu/Mr-White-Project/frontend/public/books/the-way-of-the-dog-anahata.pdf
```

Or specify a custom path with `--pdf` flag.

### 2. Environment Variables

Ensure these are set in `.env` or `.env.local`:

```bash
# AWS Bedrock (for embeddings)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Pinecone
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_pinecone_env
PINECONE_INDEX_NAME=dog-project  # or your index name

# Environment
ENVIRONMENT=production  # or development
```

### 3. Python Dependencies

The script requires:
- `PyPDF2` - PDF text extraction
- `boto3` - AWS Bedrock embeddings
- `pinecone-client` - Pinecone vector storage

These should already be in `requirements.txt`.

## Usage

### Basic Usage (Production)

```bash
cd /home/ubuntu/Mr-White-Project/backend/intelligent_chat

# Activate venv
source venv/bin/activate  # or your venv path

# Run with default settings (production namespace)
python scripts/index_book.py
```

This will:
- Use PDF from default location
- Create namespace: `book-content-production`
- Process all pages and upload to Pinecone

### Custom PDF Path

```bash
python scripts/index_book.py --pdf /path/to/your/book.pdf
```

### Custom Namespace

```bash
# For development environment
python scripts/index_book.py --namespace book-content-development

# For production
python scripts/index_book.py --namespace book-content-production

# For testing
python scripts/index_book.py --namespace book-content-test
```

### Dry Run (Test Without Uploading)

```bash
# Process book but don't upload to Pinecone
python scripts/index_book.py --dry-run
```

This is useful for:
- Testing PDF extraction
- Checking chunk count
- Verifying chapter detection
- Testing without consuming Pinecone quota

## Output

### Console Output

```
==================================================
📚 BOOK INDEXING PIPELINE
==================================================
Book: The Way of the Dog by Anahata Graceland
PDF: /path/to/book.pdf
Namespace: book-content-production
==================================================

📖 Reading PDF: /path/to/book.pdf
📄 Total pages: 250
  Processed 10/250 pages...
  Processed 20/250 pages...
  ...
✅ Extracted text from 248 pages

✂️ Chunking text...
  📑 Found chapter: Introduction (page 1)
  📑 Found chapter: Understanding Your Dog (page 12)
  📑 Found chapter: Training Fundamentals (page 45)
  ...
✅ Created 312 chunks
📚 Detected 18 chapters
🏷️ Topic distribution:
   - training: 89 chunks
   - behavior: 76 chunks
   - psychology: 54 chunks
   - health: 43 chunks
   - bonding: 38 chunks
   ...

🧠 Generating embeddings and uploading to Pinecone...
📍 Namespace: book-content-production
  ✅ Uploaded 100/312 chunks (32%)
  ✅ Uploaded 200/312 chunks (64%)
  ✅ Uploaded 312/312 chunks (100%)
✅ Successfully indexed 312 chunks to Pinecone!

==================================================
✅ INDEXING COMPLETE!
==================================================
📄 Total pages processed: 248
✂️ Total chunks created: 312
⏱️ Time taken: 185.43 seconds
📍 Pinecone namespace: book-content-production
==================================================
📝 Summary saved to: book_index_summary.json
```

### Summary File

A JSON summary is saved to `scripts/book_index_summary.json`:

```json
{
  "total_pages": 248,
  "total_chunks": 312,
  "namespace": "book-content-production",
  "duration_seconds": 185.43,
  "indexed_at": "2025-10-13T08:00:00.000000"
}
```

## Chunk Structure

Each chunk stored in Pinecone contains:

### Vector Metadata
```python
{
    "text": "First 1000 chars of chunk...",
    "page": 45,
    "chapter": "Training Fundamentals",
    "topics": ["training", "behavior", "bonding"],
    "source": "The Way of the Dog",
    "author": "Anahata Graceland",
    "content_type": "book",
    "chunk_index": 123,
    "indexed_at": "2025-10-13T08:00:00.000000"
}
```

### Contextual Embedding

Each chunk's embedding is generated with context:
```
Book: The Way of the Dog by Anahata Graceland
Chapter: Training Fundamentals
Page: 45
Topics: training, behavior, bonding
```

This improves retrieval accuracy in RAG.

## Verification

After indexing, verify in Pinecone:

```python
# Python verification
from pinecone import Pinecone

pc = Pinecone(api_key="your_key")
index = pc.Index("dog-project")

# Check stats
stats = index.describe_index_stats()
print(stats.namespaces.get('book-content-production'))
# Should show vector count matching total chunks

# Test query
results = index.query(
    vector=[0.1] * 1024,  # dummy vector
    namespace="book-content-production",
    top_k=5,
    include_metadata=True
)
print(results)
```

## Common Issues

### Issue: "PDF not found"
**Solution:** 
- Check PDF path: `/home/ubuntu/Mr-White-Project/frontend/public/books/the-way-of-the-dog-anahata.pdf`
- Or specify custom path with `--pdf` flag

### Issue: "AWS credentials not found"
**Solution:**
```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
```

### Issue: "Pinecone index not found"
**Solution:**
- Verify `PINECONE_INDEX_NAME` in `.env`
- Ensure index exists in Pinecone dashboard
- Create index if needed (dimension: 1024 for Bedrock Titan)

### Issue: "Out of memory"
**Solution:**
- The script processes in batches of 100
- If still issues, reduce batch size in code (line 237)

### Issue: "Embeddings taking too long"
**Solution:**
- Normal time: ~3 minutes for 300 chunks
- AWS Bedrock has rate limits
- The script auto-handles batching

## Re-indexing

To re-index the book (e.g., after book updates):

```bash
# This will overwrite existing vectors with same IDs
python scripts/index_book.py --namespace book-content-production
```

The script uses chunk IDs like `book_page_45_chunk_3`, so re-running will update existing chunks.

## Namespace Strategy

- **Development:** `book-content-development` - For testing
- **Staging:** `book-content-staging` - Pre-production
- **Production:** `book-content-production` - Live users

## Performance

Typical metrics:
- **Pages:** 200-300
- **Chunks:** 300-400
- **Time:** 3-5 minutes
- **Vectors:** 1 per chunk
- **Storage:** ~400 vectors × 1024 dimensions

## Integration with Intelligent Chat

After indexing, the book content is automatically available in:
- **Way of Dog Mode** (`wayofdog_chat_service.py`)
- Retrieved via `memory_service.retrieve_memories()`
- Namespace: `book-content-{environment}`

The system will:
1. Embed user query
2. Search book namespace
3. Re-rank results
4. Return top 3-5 most relevant chunks
5. Include in AI context

## Maintenance

### When to Re-index

- ✅ Book content updated
- ✅ Chunking strategy improved
- ✅ New PDF version available
- ❌ Not needed for code changes (embeddings are data)

### Monitoring

Check Pinecone dashboard for:
- Vector count in `book-content-production`
- Query performance
- Storage usage

## Support

For issues:
1. Check script logs
2. Verify environment variables
3. Test with `--dry-run`
4. Check Pinecone dashboard
5. Review `book_index_summary.json`

---

**Script:** `backend/intelligent_chat/scripts/index_book.py`  
**Created:** 2025-10-13  
**Purpose:** Index "The Way of the Dog" for intelligent chat RAG

