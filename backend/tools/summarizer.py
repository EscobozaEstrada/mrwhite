from langchain.tools import tool
from flask import current_app, g
import os
from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

@tool("summarize_files")
def summarize(query: str) -> str:
    """Summarize the user's uploaded files based on the query.
    
    Args:
        query: The query to search for relevant information in the user's files.
    """
    try:
        print(f"Summarizer tool called with query: '{query}'")
        
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
        
        # Check if we're in a Flask context (for configuration access)
        use_config = False
        try:
            current_app.config
            use_config = True
        except:
            # Not in Flask context, use environment variables directly
            pass
        
        # Initialize embedding model
        embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
        if use_config:
            embedding_model = current_app.config.get('OPENAI_EMBEDDING_MODEL', embedding_model)
        
        embeddings = OpenAIEmbeddings(model=embedding_model)
        
        # Generate namespace for user documents
        namespace = f"docs-user{user_id}"
        print(f"Using namespace: {namespace} for query: '{query}'")
        
        # Get top_k from config or default
        top_k = 10  # Use a larger number for summarization
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
        try:
            docsearch = PineconeVectorStore.from_existing_index(
                index_name=index_name,
                embedding=embeddings,
                namespace=namespace
            )
            
            # Search for relevant documents
            docs = docsearch.similarity_search(query, k=top_k)
            
            if not docs:
                return "I couldn't find any relevant documents that you've uploaded. If you've recently uploaded files, they might still be processing."
            
            # Group documents by source file
            docs_by_source = {}
            for doc in docs:
                source = doc.metadata.get('source', 'Unknown')
                if source not in docs_by_source:
                    docs_by_source[source] = []
                docs_by_source[source].append(doc)
            
            # Initialize LLM for summarization
            llm_model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4")
            if use_config:
                llm_model = current_app.config.get('OPENAI_CHAT_MODEL', llm_model)
                
            llm = ChatOpenAI(model=llm_model, temperature=0)
            
            # Create summary for each file
            file_summaries = []
            
            # Summarization prompt
            summary_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert summarizer. Your task is to create a concise summary 
                 of the document chunks provided. Focus on addressing the user's query. 
                 Maintain factual accuracy and include only information present in the document."""),
                ("user", """
                User query: {query}
                
                Document chunks from file '{source}':
                {content}
                
                Create a concise summary focusing on information relevant to the user's query.
                """)
            ])
            
            for source, source_docs in docs_by_source.items():
                # Concatenate document chunks
                content = "\n\n".join([doc.page_content for doc in source_docs])
                
                # Create summary
                summary_chain = summary_prompt | llm
                summary = summary_chain.invoke({"query": query, "source": source, "content": content})
                
                file_summaries.append(f"**File: {source}**\n{summary.content}")
            
            # Combine all summaries
            if len(file_summaries) == 1:
                return file_summaries[0]
            else:
                full_summary = "Here's a summary of your files based on your query:\n\n" + "\n\n".join(file_summaries)
                return full_summary
                
        except Exception as e:
            import traceback
            traceback_str = traceback.format_exc()
            print(f"Error in document search: {str(e)}\n{traceback_str}")
            return f"Error retrieving documents: {str(e)}"
    
    except Exception as e:
        import traceback
        traceback_str = traceback.format_exc()
        print(f"Error in summarizer tool: {str(e)}\n{traceback_str}")
        return f"Error summarizing documents: {str(e)}"
