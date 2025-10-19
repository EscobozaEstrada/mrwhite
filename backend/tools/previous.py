from langchain.tools import tool
from flask import current_app, g
import os
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore
from langchain_openai.embeddings import OpenAIEmbeddings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

# The function name is "previous" but the agent might call it as "get_previous_message"
@tool("get_previous_message")
def previous(query: str) -> str:
    """Get relevant previous messages based on the user's query.
    
    Args:
        query: The query to search for in previous messages. Should be the user's actual question.
    """
    try:
        print(f"Previous tool called with query: '{query}'")
        
        # Handle case where only a simple word is passed
        if query.lower() in ["user", "1", "message", "previous"]:
            return "Error: You need to provide the full user query to find relevant messages. Just passing a single word like 'user' or '1' is not sufficient."
        
        # Check if we're in a Flask context (for configuration access)
        use_config = False
        try:
            current_app.config
            use_config = True
        except:
            # Not in Flask context, use environment variables directly
            pass
        
        # Get the user ID from the flask global context if available
        user_id = None
        
        # Try to get user_id from Flask's g object first
        try:
            if hasattr(g, 'user_id'):
                user_id = g.user_id
                print(f"Using user_id from Flask context: {user_id}")
        except:
            pass
            
        # If not available from context, try environment variable
        if not user_id:
            user_id = os.getenv("CURRENT_USER_ID")
            if user_id:
                print(f"Using user_id from environment variable: {user_id}")
        
        # If still not available, default to "1"
        if not user_id:
            user_id = "1"
            print(f"No user_id found, defaulting to: {user_id}")
        
        # Initialize embedding model
        embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
        if use_config:
            embedding_model = current_app.config.get('OPENAI_EMBEDDING_MODEL', embedding_model)
        
        embeddings = OpenAIEmbeddings(model=embedding_model)
        
        # Generate namespace for chat history
        namespace = f"chat-user{user_id}"
        print(f"Using namespace: {namespace} for query: '{query}'")
        
        # Get top_k from config or default
        top_k = 5
        if use_config:
            top_k = current_app.config.get('VECTOR_SEARCH_TOP_K', top_k)
        
        # Get Pinecone index name
        index_name = os.getenv("PINECONE_INDEX_NAME")
        if not index_name:
            return "Error: PINECONE_INDEX_NAME environment variable is not set!"
        
        # Verify index exists
        index_list = pc.list_indexes().names()
        if index_name not in index_list:
            return f"Error: Pinecone index '{index_name}' does not exist!"
        
        # Connect to existing index
        docsearch = PineconeVectorStore.from_existing_index(
            index_name=index_name,
            embedding=embeddings,
            namespace=namespace
        )
        
        # Search for relevant chat messages
        docs = docsearch.similarity_search(query, k=top_k)
        
        if not docs:
            return "No relevant previous messages found."
        
        # Format results
        result = "Relevant previous messages:\n\n"
        for i, doc in enumerate(docs):
            message_type = doc.metadata.get('message_type', 'Unknown')
            role = "User" if message_type == "user" else "Assistant"
            conversation_id = doc.metadata.get('conversation_id', 'Unknown')
            result += f"{i+1}. [{role}] (Conversation: {conversation_id}): {doc.page_content}\n\n"
        
        return result
    
    except Exception as e:
        import traceback
        traceback_str = traceback.format_exc()
        print(f"Error in previous tool: {str(e)}\n{traceback_str}")
        return f"Error retrieving previous messages: {str(e)}"