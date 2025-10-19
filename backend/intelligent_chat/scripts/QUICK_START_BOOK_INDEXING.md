# Quick Start: Index "The Way of the Dog" to Pinecone (Production)

## 🚀 Fast Track (Production)

```bash
# 1. Navigate to directory
cd /home/ubuntu/Mr-White-Project/backend/intelligent_chat

# 2. Activate virtual environment
source venv/bin/activate

# 3. Run the script
python scripts/index_book.py --namespace book-content-production
```

**Done! ✅** The book will be indexed in ~3-5 minutes.

---

## ✅ Prerequisites Checklist

Before running, ensure:

- [ ] PDF exists at: `frontend/public/books/the-way-of-the-dog-anahata.pdf`
- [ ] `.env` or `.env.local` has:
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `PINECONE_API_KEY`
  - `PINECONE_INDEX_NAME=dog-project`
- [ ] Virtual environment is activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)

---

## 📋 Command Options

### Production (Live Users)
```bash
python scripts/index_book.py --namespace book-content-production
```

### Development (Testing)
```bash
python scripts/index_book.py --namespace book-content-development
```

### Dry Run (Test Without Uploading)
```bash
python scripts/index_book.py --dry-run
```

### Custom PDF Path
```bash
python scripts/index_book.py --pdf /path/to/your/book.pdf --namespace book-content-production
```

---

## 📊 Expected Output

```
==================================================
📚 BOOK INDEXING PIPELINE
==================================================
✅ Extracted text from 248 pages
✅ Created 312 chunks
📚 Detected 18 chapters
✅ Successfully indexed 312 chunks to Pinecone!
⏱️ Time taken: 185.43 seconds
==================================================
```

---

## 🔍 Verify Success

### Check Pinecone Dashboard
1. Log in to Pinecone
2. Select index: `dog-project`
3. Check namespace: `book-content-production`
4. Should see ~300-400 vectors

### Or Query in Python
```python
from pinecone import Pinecone
pc = Pinecone(api_key="your_key")
index = pc.Index("dog-project")
stats = index.describe_index_stats()
print(stats.namespaces.get('book-content-production'))
# Output: {"vector_count": 312}
```

---

## ⚠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| PDF not found | Check path: `frontend/public/books/the-way-of-the-dog-anahata.pdf` |
| AWS credentials error | Export `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` |
| Pinecone error | Check `PINECONE_API_KEY` and `PINECONE_INDEX_NAME` |
| Takes too long | Normal: 3-5 minutes for ~300 chunks |
| Import errors | Run `pip install -r requirements.txt` |

---

## 📁 Files

- **Script:** `backend/intelligent_chat/scripts/index_book.py`
- **README:** `backend/intelligent_chat/scripts/README_BOOK_INDEXING.md`
- **Summary:** `backend/intelligent_chat/scripts/book_index_summary.json` (created after run)

---

## 🎯 What Happens Next?

After indexing:
1. ✅ Book content is in Pinecone
2. ✅ Way of Dog Mode will use it automatically
3. ✅ Users can ask questions about the book
4. ✅ AI retrieves relevant chapters/passages

**No code changes needed** - the system is already configured to use the book content!

---

## 🔄 Re-indexing

To update the book (e.g., new PDF version):

```bash
# Just run again - it will overwrite
python scripts/index_book.py --namespace book-content-production
```

---

**Need help?** Check `README_BOOK_INDEXING.md` for detailed docs.

