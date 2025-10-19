# Book Reader Application - Backend

## Features

### Knowledge Search

The application includes a semantic search feature that allows users to search through their book notes, highlights, and comments. This feature uses Pinecone vector database and OpenAI embeddings to provide relevant search results based on meaning, not just keywords.

See [knowledge_search.md](./knowledge_search.md) for detailed setup instructions and usage information.

### Knowledge-Aware Chat

The application features a knowledge-aware chatbot that can access and reference a user's personal notes and comments when answering questions. This provides personalized responses that incorporate the user's own insights.

See [knowledge_chat.md](./knowledge_chat.md) for details about this feature.

To set up the knowledge search feature:

1. Install dependencies: `pip install -r requirements.txt`
2. Set environment variables in `.env`:
   ```
   OPENAI_API_KEY=your_openai_api_key
   PINECONE_API_KEY=your_pinecone_api_key
   PINECONE_ENVIRONMENT=your_pinecone_environment
   ```
3. Run the setup script: `python backend/scripts/setup_knowledge_base.py`
4. Backfill existing notes: `python backend/scripts/setup_knowledge_base.py --user=1`

## API Endpoints

### User Book Routes

- `GET /api/user-books/copy` - Get authenticated user's book copy
- `GET /api/user-books/progress/<book_copy_id>` - Get reading progress
- `PUT /api/user-books/progress/<book_copy_id>` - Update reading progress
- `GET /api/user-books/notes/<book_copy_id>` - Get notes for a book
- `POST /api/user-books/notes` - Create a note
- `DELETE /api/user-books/notes/<note_id>` - Delete a note
- `POST /api/user-books/search` - Search user's knowledge base
- `POST /api/user-books/backfill-knowledge-base` - Backfill notes to knowledge base 

### Book Routes

- `GET /api/book/info` - Get book information
- `POST /api/book/chat` - Chat about book content
- `POST /api/book/knowledge-chat` - Chat with awareness of user's personal notes
- `POST /api/book/search` - Search book content