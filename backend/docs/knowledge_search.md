# Knowledge Search Feature

This document explains how to set up and use the knowledge search feature in the book reading application.

## Overview

The knowledge search feature allows users to search across all their book notes, highlights, and comments using semantic search. This means users can find relevant content based on meaning, not just exact keyword matches.

## Requirements

- Pinecone account (for vector database)
- OpenAI API key (for embeddings)

## Setup Instructions

### 1. Environment Variables

Add the following environment variables to your `.env` file:

```
OPENAI_API_KEY=your_openai_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_pinecone_environment
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Initialize Knowledge Base

Run the setup script to initialize the Pinecone index and backfill existing notes:

```bash
python backend/scripts/setup_knowledge_base.py
```

To backfill notes for a specific user:

```bash
python backend/scripts/setup_knowledge_base.py --user=1
```

### 4. API Endpoints

The following API endpoints are available for the knowledge search feature:

#### Search Knowledge Base

```
POST /api/user-books/search
```

Request body:
```json
{
  "query": "search query text",
  "top_k": 10
}
```

Response:
```json
{
  "success": true,
  "results": {
    "matches": [
      {
        "id": "user_1_note_123",
        "score": 0.92,
        "metadata": {
          "text": "Note content...",
          "book_title": "Book Title",
          "page_number": 42,
          "content_type": "book_note",
          "note_type": "comment",
          "color": "yellow"
        }
      }
    ]
  },
  "query": "search query text"
}
```

#### Backfill Knowledge Base

```
POST /api/user-books/backfill-knowledge-base
```

Response:
```json
{
  "success": true,
  "message": "Backfilled 15 notes to knowledge base",
  "stats": {
    "total": 15,
    "success": 15,
    "failed": 0
  }
}
```

## How It Works

1. **Note Creation**: When a user creates a note or comment, it's automatically added to their personal knowledge base in Pinecone.

2. **Embedding Generation**: The text content is converted to a vector embedding using OpenAI's embedding model.

3. **Vector Storage**: The embedding and metadata are stored in Pinecone under a namespace specific to that user.

4. **Search**: When a user searches, their query is converted to an embedding and semantically compared to all their stored notes.

5. **Result Display**: The most relevant results are displayed in the UI, sorted by relevance score.

## Namespaces

Each user's data is stored in a separate namespace in Pinecone to ensure data isolation:

```
book_notes_user_{user_id}
```

## Troubleshooting

### No Search Results

If you're not getting search results:

1. Check that notes have been successfully backfilled using the backfill endpoint
2. Verify that the Pinecone index exists and contains vectors
3. Check the API logs for any errors during search

### API Errors

Common error messages:

- "Failed to create embedding" - Check your OpenAI API key
- "Failed to connect to Pinecone" - Check your Pinecone API key and environment

## Future Enhancements

- Hybrid search (combining vector and keyword search)
- Filtering by book, date range, or note type
- Relevance feedback to improve search results 