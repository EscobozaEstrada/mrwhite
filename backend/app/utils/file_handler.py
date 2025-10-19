from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_pinecone import PineconeVectorStore
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone
from flask import current_app
import os
import tempfile
from dotenv import load_dotenv
from .s3_handler import upload_file_to_s3, create_bucket_if_not_exists

# Make sure environment variables are loaded
load_dotenv()

# Initialize Pinecone with environment variables
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

# Ensure S3 bucket exists
create_bucket_if_not_exists()

def get_user_namespace(user_id):
    """Generate a namespace string for a specific user"""
    # Ensure user_id is converted to string
    user_id_str = str(user_id)
    return f"docs-user{user_id_str}"

def get_chat_namespace(user_id):
    """Generate a namespace string for a user's chat history"""
    # Ensure user_id is converted to string
    user_id_str = str(user_id)
    return f"chat-user{user_id_str}"

def extract_and_store(file, user_id):
    """Process and store a file's content in Pinecone with user-specific namespace"""
    print(f"Starting extraction and storage for file: {file.filename} for user_id: {user_id}")
    
    # Create a temporary file to save the uploaded file
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)
    file.save(temp_path)
    print(f"Saved file to temporary path: {temp_path}")
    
    # Upload file to S3
    content_type = file.content_type if hasattr(file, 'content_type') else None
    s3_success, s3_message, s3_url = upload_file_to_s3(temp_path, file.filename, content_type)
    if not s3_success:
        print(f"Warning: Failed to upload to S3: {s3_message}")
        # Continue with local processing but we'll return local URL
        s3_url = f"/uploads/{file.filename}"
    else:
        print(f"Successfully uploaded to S3: {s3_url}")
    
    # Choose the appropriate loader based on file type
    if file.filename.lower().endswith('.pdf'):
        print(f"Processing PDF file: {file.filename}")
        loader = PyPDFLoader(temp_path)
    elif file.filename.lower().endswith('.txt'):
        print(f"Processing TXT file: {file.filename}")
        loader = TextLoader(temp_path)
    else:
        # Clean up temporary file
        os.unlink(temp_path)
        os.rmdir(temp_dir)
        print(f"Unsupported file type: {file.filename}")
        return False, f"Unsupported file type: {file.filename}", None
    
    try:
        # Load documents
        print(f"Loading documents from {file.filename}")
        documents = loader.load()
        print(f"Loaded {len(documents)} document chunks")
        
        # Add metadata to each document
        for doc in documents:
            doc.metadata["source"] = file.filename
            doc.metadata["user_id"] = str(user_id)
            doc.metadata["url"] = s3_url  # Add S3 URL to metadata
        
        # Split documents into chunks
        print("Splitting documents into chunks")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=current_app.config['CHUNK_SIZE'],
            chunk_overlap=current_app.config['CHUNK_OVERLAP']
        )
        docs = text_splitter.split_documents(documents)
        print(f"Created {len(docs)} document chunks after splitting")
        
        # If no chunks were created, use the original documents as chunks
        if not docs and documents:
            print("No chunks created after splitting. Using original documents.")
            docs = documents
            print(f"Using {len(docs)} original document chunks")
        
        # Get user-specific namespace
        namespace = get_user_namespace(user_id)
        print(f"Using namespace: {namespace}")
        
        # Initialize embeddings
        print("Initializing OpenAI embeddings")
        embeddings = OpenAIEmbeddings(model=current_app.config['OPENAI_EMBEDDING_MODEL'])
        
        # Upsert to Pinecone with user-specific namespace
        index_name = os.getenv("PINECONE_INDEX_NAME")
        if not index_name:
            print("ERROR: PINECONE_INDEX_NAME environment variable is not set!")
            return False, "PINECONE_INDEX_NAME environment variable is not set", s3_url
        print(f"Using Pinecone index: {index_name}")
        
        # Skip if no documents to upsert
        if not docs:
            print("No document chunks to upsert. Skipping Pinecone upload.")
            return True, f"File {file.filename} processed but no content chunks to store", s3_url
            
        # Make sure the index exists
        index_list = pc.list_indexes().names()
        print(f"Available Pinecone indices: {index_list}")
        
        if index_name not in index_list:
            print(f"ERROR: Pinecone index {index_name} does not exist!")
            print(f"Creating index {index_name} with dimension 1536")
            # Create the index if it doesn't exist
            pc.create_index(
                name=index_name,
                dimension=current_app.config['PINECONE_DIMENSION'],
                metric=current_app.config['PINECONE_METRIC']
            )
            print(f"Created index {index_name}")
        
        # Use langchain_pinecone's PineconeVectorStore instead
        print(f"Upserting {len(docs)} documents to Pinecone index {index_name} with namespace {namespace}")
        try:
            # Use from_documents with langchain_pinecone
            vectorstore = PineconeVectorStore.from_documents(
                documents=docs,
                embedding=embeddings,
                index_name=index_name,
                namespace=namespace
            )
            print(f"Successfully upserted documents to Pinecone")
        except Exception as e:
            print(f"Error upserting documents: {str(e)}")
            raise e
        
        # Clean up temporary file
        os.unlink(temp_path)
        os.rmdir(temp_dir)
        
        return True, f"Successfully processed and stored {file.filename}", s3_url
    except Exception as e:
        # Clean up temporary file
        try:
            os.unlink(temp_path)
            os.rmdir(temp_dir)
        except:
            pass
        print(f"ERROR in extract_and_store: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, str(e), s3_url

def query_user_docs(query, user_id, top_k=None):
    """Query documents from a user's namespace in Pinecone"""
    try:
        # Validate input parameters
        if not query or not isinstance(query, str):
            print(f"ERROR: Invalid query parameter: {query}")
            return False, []
            
        if not user_id or not isinstance(user_id, (int, str)):
            print(f"ERROR: Invalid user_id parameter: {user_id}")
            return False, []
        
        # Convert user_id to string if it's an integer
        user_id_str = str(user_id)
        
        # Use default top_k from config if not provided
        if top_k is None:
            top_k = current_app.config['VECTOR_SEARCH_TOP_K']
            
        # Initialize embeddings
        print(f"Querying Pinecone for: '{query}' for user_id: {user_id_str}")
        embeddings = OpenAIEmbeddings(model=current_app.config['OPENAI_EMBEDDING_MODEL'])
        
        # Get user-specific namespace
        namespace = get_user_namespace(user_id_str)
        print(f"Using namespace: {namespace}")
        
        # Connect to the existing index
        index_name = os.getenv("PINECONE_INDEX_NAME")
        if not index_name:
            print("ERROR: PINECONE_INDEX_NAME environment variable is not set!")
            return False, []
        print(f"Using Pinecone index: {index_name}")
        
        # Make sure the index exists
        index_list = pc.list_indexes().names()
        if index_name not in index_list:
            print(f"ERROR: Pinecone index {index_name} does not exist!")
            return False, []
        
        try:
            # Connect to existing index using langchain_pinecone
            print(f"Connecting to existing Pinecone index: {index_name}")
            docsearch = PineconeVectorStore.from_existing_index(
                index_name=index_name,
                embedding=embeddings,
                namespace=namespace
            )
            
            # Search for relevant documents
            print(f"Searching for documents with query='{query}', top_k={top_k}")
            docs = docsearch.similarity_search(query, k=top_k)
            print(f"Found {len(docs)} relevant documents")
            
            if not docs:
                print("No documents found in the search results")
                return True, []
                
            # Log document content
            for i, doc in enumerate(docs):
                source = doc.metadata.get('source', 'Unknown')
                url = doc.metadata.get('url', None)
                content_preview = doc.page_content[:100] + "..." if len(doc.page_content) > 100 else doc.page_content
                print(f"Document {i+1}: Source={source}, URL={url}, Content preview: {content_preview}")
                
            return True, docs
        except Exception as e:
            print(f"ERROR in similarity search: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, []
    except Exception as e:
        print(f"ERROR in query_user_docs: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, []

def store_chat_message(user_id, message_content, message_id, message_type, conversation_id):
    """Store a chat message in Pinecone for future reference"""
    try:
        print(f"Storing {message_type} message in Pinecone for user_id: {user_id}")
        
        # Initialize embeddings
        embeddings = OpenAIEmbeddings(model=current_app.config['OPENAI_EMBEDDING_MODEL'])
        
        # Get user-specific chat namespace
        namespace = get_chat_namespace(user_id)
        print(f"Using chat namespace: {namespace}")
        
        # Get the Pinecone index name
        index_name = os.getenv("PINECONE_INDEX_NAME")
        if not index_name:
            print("ERROR: PINECONE_INDEX_NAME environment variable is not set!")
            return False, "PINECONE_INDEX_NAME environment variable is not set"
        
        # Make sure the index exists
        index_list = pc.list_indexes().names()
        if index_name not in index_list:
            print(f"ERROR: Pinecone index {index_name} does not exist!")
            print(f"Creating index {index_name} with dimension 1536")
            # Create the index if it doesn't exist
            pc.create_index(
                name=index_name,
                dimension=current_app.config['PINECONE_DIMENSION'],
                metric=current_app.config['PINECONE_METRIC']
            )
            print(f"Created index {index_name}")
        
        # Create a document from the message
        documents = [{
            "page_content": message_content,
            "metadata": {
                "message_id": str(message_id),
                "conversation_id": str(conversation_id),
                "message_type": message_type,
                "user_id": str(user_id),
                "source": "chat_history"
            }
        }]
        
        # Use langchain_pinecone's PineconeVectorStore
        try:
            # Create documents from the dict objects
            from langchain_core.documents import Document
            docs = [Document(page_content=doc["page_content"], metadata=doc["metadata"]) for doc in documents]
            
            # Use from_documents with langchain_pinecone
            vectorstore = PineconeVectorStore.from_documents(
                documents=docs,
                embedding=embeddings,
                index_name=index_name,
                namespace=namespace
            )
            print(f"Successfully stored message in Pinecone")
            return True, "Message stored successfully"
        except Exception as e:
            print(f"Error storing message: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, str(e)
    except Exception as e:
        print(f"Error in store_chat_message: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, str(e)

def query_chat_history(query, user_id, top_k=None):
    """Query chat history from a user's namespace in Pinecone"""
    try:
        # Use default top_k from config if not provided
        if top_k is None:
            top_k = current_app.config['VECTOR_SEARCH_TOP_K']
            
        # Initialize embeddings
        print(f"Querying Pinecone for chat history: '{query}' in namespace for user_id: {user_id}")
        embeddings = OpenAIEmbeddings(model=current_app.config['OPENAI_EMBEDDING_MODEL'])
        
        # Get user-specific chat namespace
        namespace = get_chat_namespace(user_id)
        print(f"Using chat namespace: {namespace}")
        
        # Connect to the existing index
        index_name = os.getenv("PINECONE_INDEX_NAME")
        if not index_name:
            print("ERROR: PINECONE_INDEX_NAME environment variable is not set!")
            return False, "PINECONE_INDEX_NAME environment variable is not set"
        
        # Make sure the index exists
        index_list = pc.list_indexes().names()
        if index_name not in index_list:
            print(f"ERROR: Pinecone index {index_name} does not exist!")
            return False, f"Pinecone index {index_name} does not exist"
        
        try:
            # Connect to existing index using langchain_pinecone
            print(f"Connecting to existing Pinecone index: {index_name}")
            docsearch = PineconeVectorStore.from_existing_index(
                index_name=index_name,
                embedding=embeddings,
                namespace=namespace
            )
            
            # Search for relevant messages
            print(f"Searching for chat messages with top_k={top_k}")
            docs = docsearch.similarity_search(query, k=top_k)
            print(f"Found {len(docs)} relevant chat messages")
            
            if not docs:
                print("No chat messages found in the search results")
                return True, []
                
            # Log message content
            for i, doc in enumerate(docs):
                message_id = doc.metadata.get('message_id', 'Unknown')
                message_type = doc.metadata.get('message_type', 'Unknown')
                conversation_id = doc.metadata.get('conversation_id', 'Unknown')
                content_preview = doc.page_content[:100] + "..." if len(doc.page_content) > 100 else doc.page_content
                print(f"Message {i+1}: ID={message_id}, Type={message_type}, Conversation={conversation_id}, Content preview: {content_preview}")
                
            return True, docs
        except Exception as e:
            print(f"ERROR in chat history search: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, f"Error querying chat history: {str(e)}"
    except Exception as e:
        print(f"ERROR in query_chat_history: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, str(e)