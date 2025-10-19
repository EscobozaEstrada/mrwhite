# Knowledge-Aware Chat

This feature enables the chatbot to access and reference a user's personal notes and comments when answering questions.

## Overview

The knowledge-aware chat integrates the user's personal knowledge base (comments and highlights) with the book chatbot, allowing for personalized responses that reference the user's own notes and insights.

## How It Works

1. When a user asks a question, the system:
   - Searches the book's common knowledge base (general content)
   - Searches the user's personal knowledge base (their comments and highlights)
   - Combines both sources to generate a comprehensive response

2. The chatbot will explicitly acknowledge when it's referencing the user's personal notes, making it clear which information comes from the book and which comes from the user's own comments.

## API Endpoints

### Regular Book Chat

```
POST /api/book/chat
```

This is the standard book chat endpoint that primarily uses the book's content to answer questions.

### Knowledge-Aware Chat

```
POST /api/book/knowledge-chat
```

This enhanced endpoint incorporates the user's personal notes and comments when generating responses.

**Request Body:**
```json
{
  "query": "What are the key principles mentioned in chapter 3?",
  "conversation_history": [
    { "role": "user", "content": "Tell me about chapter 3" },
    { "role": "assistant", "content": "Chapter 3 covers..." }
  ],
  "book_id": "123",
  "book_copy_id": 456
}
```

**Response:**
```json
{
  "success": true,
  "response": "Based on the book content and your own notes, the key principles in chapter 3 are...",
  "operation": "knowledge_chat",
  "chat_info": {
    "query": "What are the key principles mentioned in chapter 3?",
    "context_used": {
      "relevant_content_length": 1500,
      "context_used": 3,
      "user_knowledge_used": true
    },
    "conversation_length": 2,
    "user_knowledge_used": true
  },
  "tools_used": ["book_chat", "knowledge_search", "user_knowledge_search"]
}
```

## Frontend Components

### KnowledgeChatPanel

A dedicated React component (`KnowledgeChatPanel.tsx`) provides the UI for interacting with the knowledge-aware chatbot. This component:

- Displays chat messages between the user and the AI
- Shows when the AI has used the user's personal notes
- Sends queries to the knowledge-aware chat endpoint
- Maintains conversation history

### Integration

The knowledge chat is integrated into the PDF reader as a new tab alongside Comments and Knowledge Search, allowing users to easily access this functionality while reading.

## Technical Implementation

1. **User Knowledge Service**: A dedicated service (`UserKnowledgeService`) bridges between the user's personal comments in Pinecone and the chatbot.

2. **Book Chat Agent**: The `_book_chat_agent` method in `BookManagementService` has been enhanced to search for and incorporate relevant user comments.

3. **Namespaces**: User comments are stored in user-specific namespaces (`book_notes_user_{user_id}`) in Pinecone, keeping them separate from the common knowledge base.

## Usage Tips

- The more detailed comments and highlights a user adds, the more personalized the chatbot's responses will be.
- Ask questions that might relate to your notes for the most personalized experience.
- Look for the "Used your notes" indicator to see when the chatbot is referencing your personal insights. 