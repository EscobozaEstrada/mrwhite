from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_pinecone import PineconeVectorStore
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from pinecone import Pinecone
from flask import current_app
import os
import tempfile
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from dotenv import load_dotenv
from .s3_handler import upload_file_to_s3, create_bucket_if_not_exists
from werkzeug.utils import secure_filename

# Make sure environment variables are loaded
load_dotenv()

# Initialize Pinecone with environment variables
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

# Ensure S3 bucket exists
create_bucket_if_not_exists()

# Set up file uploads directory
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

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

def store_document_vectors(user_id: int, documents: List[str], metadata: Dict[str, Any], filename: str) -> bool:
    """Store document text chunks as vectors in Pinecone with enhanced metadata"""
    try:
        current_app.logger.info(f"Storing {len(documents)} document chunks for user {user_id}")
        
        # Initialize embeddings
        embeddings = OpenAIEmbeddings(model=current_app.config['OPENAI_EMBEDDING_MODEL'])
        
        # Get user-specific namespace
        namespace = get_user_namespace(user_id)
        
        # Get the Pinecone index name
        index_name = os.getenv("PINECONE_INDEX_NAME")
        if not index_name:
            current_app.logger.error("PINECONE_INDEX_NAME environment variable is not set!")
            return False
        
        # Make sure the index exists
        index_list = pc.list_indexes().names()
        if index_name not in index_list:
            current_app.logger.info(f"Creating Pinecone index {index_name}")
            pc.create_index(
                name=index_name,
                dimension=current_app.config['PINECONE_DIMENSION'],
                metric=current_app.config['PINECONE_METRIC']
            )
        
        # Create Document objects with enhanced metadata
        docs = []
        for i, chunk in enumerate(documents):
            chunk_metadata = {
                **metadata,
                'chunk_index': i,
                'chunk_id': f"{metadata.get('document_id', 'unknown')}_{i}",
                'storage_timestamp': datetime.now(timezone.utc).isoformat(),
                'source': filename
            }
            docs.append(Document(page_content=chunk, metadata=chunk_metadata))
        
        # Store in Pinecone
        try:
            vectorstore = PineconeVectorStore.from_documents(
                documents=docs,
                embedding=embeddings,
                index_name=index_name,
                namespace=namespace
            )
            current_app.logger.info(f"Successfully stored {len(docs)} document chunks in Pinecone")
            return True
        except Exception as e:
            current_app.logger.error(f"Error storing document vectors: {str(e)}")
            return False
            
    except Exception as e:
        current_app.logger.error(f"Error in store_document_vectors: {str(e)}")
        return False

def search_document_vectors(user_id: int, query: str, top_k: int = 10, filter_metadata: Optional[Dict] = None) -> Tuple[bool, List[Document]]:
    """Search document vectors with optional metadata filtering"""
    try:
        current_app.logger.info(f"Searching document vectors for user {user_id}: {query}")
        
        # Initialize embeddings
        embeddings = OpenAIEmbeddings(model=current_app.config['OPENAI_EMBEDDING_MODEL'])
        
        # Get user-specific namespace
        namespace = get_user_namespace(user_id)
        
        # Connect to the existing index
        index_name = os.getenv("PINECONE_INDEX_NAME")
        if not index_name:
            current_app.logger.error("PINECONE_INDEX_NAME environment variable is not set!")
            return False, []
        
        # Make sure the index exists
        index_list = pc.list_indexes().names()
        if index_name not in index_list:
            current_app.logger.error(f"Pinecone index {index_name} does not exist!")
            return False, []
        
        try:
            # Connect to existing index
            docsearch = PineconeVectorStore.from_existing_index(
                index_name=index_name,
                embedding=embeddings,
                namespace=namespace
            )
            
            # Search for relevant documents
            if filter_metadata:
                # Use similarity search with metadata filter
                docs = docsearch.similarity_search(
                    query, 
                    k=top_k,
                    filter=filter_metadata
                )
            else:
                docs = docsearch.similarity_search(query, k=top_k)
            
            current_app.logger.info(f"Found {len(docs)} relevant documents")
            return True, docs
            
        except Exception as e:
            current_app.logger.error(f"Error in similarity search: {str(e)}")
            return False, []
            
    except Exception as e:
        current_app.logger.error(f"Error in search_document_vectors: {str(e)}")
        return False, []

def delete_document_vectors(user_id: int, document_id: int) -> bool:
    """Delete all vectors for a specific document"""
    try:
        current_app.logger.info(f"Deleting document vectors for user {user_id}, document {document_id}")
        
        # Get user-specific namespace
        namespace = get_user_namespace(user_id)
        
        # Get the Pinecone index
        index_name = os.getenv("PINECONE_INDEX_NAME")
        if not index_name:
            current_app.logger.error("PINECONE_INDEX_NAME environment variable is not set!")
            return False
        
        # Connect to the index
        index = pc.Index(index_name)
        
        # Delete vectors by metadata filter
        try:
            index.delete(
                filter={"document_id": document_id, "user_id": str(user_id)},
                namespace=namespace
            )
            current_app.logger.info(f"Successfully deleted vectors for document {document_id}")
            return True
        except Exception as e:
            current_app.logger.error(f"Error deleting document vectors: {str(e)}")
            return False
            
    except Exception as e:
        current_app.logger.error(f"Error in delete_document_vectors: {str(e)}")
        return False

def extract_and_store(file, user_id, conversation_id=None, message_id=None, user_description=None):
    """Extract text from files and store in vector database"""
    try:
        # Get file extension
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        print(f"🔍 extract_and_store: Processing {filename}, type: {file.content_type}, user_id: {user_id}")
        
        # Save file to disk
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        print(f"💾 extract_and_store: Saved file to {file_path}")
        
        # Initialize result
        result = {
            'filename': filename,
            'file_path': file_path,
            'file_type': file.content_type,
            'extracted_text': '',
            'success': False,
            'error': None
        }
        
        # Process based on file type
        if file.content_type.startswith('image/'):
            # Process image
            print(f"🖼️ extract_and_store: Processing image with user_description: {user_description}")
            result = process_image(file_path, result, user_description)
            
            # For images, add type explicitly
            result['type'] = 'image'
            
            # If this is an image, also try to use ImageService for proper gallery storage
            try:
                from flask import g
                from app.services.image_service import ImageService
                
                # Ensure user_id is set in Flask g object
                g.user_id = user_id
                print(f"🔑 extract_and_store: Setting g.user_id = {user_id} for ImageService")
                
                # Create ImageService instance
                image_service = ImageService()
                print(f"🔧 extract_and_store: Created ImageService instance")
                
                # Reopen the file for ImageService
                with open(file_path, 'rb') as img_file:
                    from werkzeug.datastructures import FileStorage
                    file_storage = FileStorage(
                        stream=img_file,
                        filename=filename,
                        content_type=file.content_type
                    )
                    
                    print(f"📤 extract_and_store: Calling ImageService.process_image_upload")
                    success, message, image_data = image_service.process_image_upload(
                        file=file_storage,
                        user_id=user_id,
                        conversation_id=conversation_id,
                        message_id=message_id,
                        user_description=user_description
                    )
                    
                    print(f"📥 extract_and_store: ImageService result: success={success}, message={message}")
                    
                    if success and image_data:
                        # Update result with ImageService data
                        result['success'] = True
                        result['url'] = image_data.get('url')
                        result['description'] = image_data.get('description')
                        result['name'] = image_data.get('original_filename') or filename
                        result['type'] = 'image'
                        print(f"✅ extract_and_store: Successfully processed image with ImageService: {result['url']}")
                    else:
                        print(f"⚠️ extract_and_store: ImageService failed, using basic result")
            except Exception as img_error:
                print(f"❌ extract_and_store: Error using ImageService: {str(img_error)}")
                import traceback
                print(f"❌ extract_and_store: ImageService error traceback: {traceback.format_exc()}")
                
        elif file.content_type.startswith('audio/'):
            # Process audio file
            print(f"🔊 extract_and_store: Processing audio file")
            result = process_audio(file_path, result, user_description)
            result['type'] = 'audio'
        elif file_ext in ['pdf', 'txt', 'doc', 'docx']:
            # Process document
            print(f"📄 extract_and_store: Processing document")
            result = process_document(file_path, result, file_ext, user_id)
            result['type'] = 'file'
        else:
            result['error'] = f"Unsupported file type: {file.content_type}"
            result['type'] = 'file'
            print(f"❌ extract_and_store: Unsupported file type: {file.content_type}")
            return result
        
        # Store in vector DB if text was extracted
        if result['extracted_text']:
            print(f"🧠 extract_and_store: Storing in vector DB")
            store_in_vector_db(result, user_id, conversation_id, message_id)
            result['success'] = True
        
        print(f"🏁 extract_and_store: Completed processing {filename}, result: {result}")
        return result
    
    except Exception as e:
        print(f"❌ extract_and_store: Error processing file {file.filename}: {str(e)}")
        import traceback
        print(f"❌ extract_and_store: Error traceback: {traceback.format_exc()}")
        return {
            'filename': file.filename,
            'success': False,
            'error': str(e),
            'type': 'file' if not file.content_type.startswith('image/') else 'image'
        }

def process_audio(file_path, result, user_description=None):
    """Process audio file - use description if available or note that it's an audio file"""
    try:
        # If we have a user description, use that as the extracted text
        if user_description:
            result['extracted_text'] = f"[Audio file description: {user_description}]"
        else:
            # Otherwise just note that it's an audio file
            result['extracted_text'] = f"[Audio file: {os.path.basename(file_path)}]"
        
        return result
    except Exception as e:
        current_app.logger.error(f"Error processing audio file: {str(e)}")
        result['error'] = f"Error processing audio: {str(e)}"
        return result

def process_document(file_path, result, file_ext, user_id):
    """Process document files (PDF, TXT, DOC, DOCX)"""
    try:
        # Choose the appropriate loader based on file type
        if file_ext == 'pdf':
            loader = PyPDFLoader(file_path)
        elif file_ext in ['txt', 'doc', 'docx']:
            loader = TextLoader(file_path)
        else:
            result['error'] = f"Unsupported document type: {file_ext}"
            return result
        
        # Load documents
        documents = loader.load()
        
        # Add metadata to each document
        for doc in documents:
            doc.metadata["source"] = result['filename']
            doc.metadata["user_id"] = str(user_id)
            doc.metadata["url"] = result['file_path']  # Add S3 URL to metadata
            doc.metadata["upload_timestamp"] = datetime.now(timezone.utc).isoformat()
        
        # Split documents into chunks

        chunk_size = current_app.config.get('CHUNK_SIZE', 1000)  # Default to 1000 if not set
        chunk_overlap = current_app.config.get('CHUNK_OVERLAP', 100)  # Default to 100 if not set
   
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        docs = text_splitter.split_documents(documents)
        
        # If no chunks were created, use the original documents as chunks
        if not docs and documents:
            docs = documents
        
        # Get user-specific namespace
        namespace = get_user_namespace(user_id)
        
        # Initialize embeddings
        embeddings = OpenAIEmbeddings(model=current_app.config['OPENAI_EMBEDDING_MODEL'])
        
        # Upsert to Pinecone with user-specific namespace
        index_name = os.getenv("PINECONE_INDEX_NAME")
        if not index_name:
            result['error'] = "PINECONE_INDEX_NAME environment variable is not set!"
            return result
        
        # Skip if no documents to upsert
        if not docs:
            result['extracted_text'] = "No document chunks to store"
            return result
            
        # Make sure the index exists
        index_list = pc.list_indexes().names()
        
        if index_name not in index_list:
            current_app.logger.info(f"ERROR: Pinecone index {index_name} does not exist!")
            current_app.logger.info(f"Creating index {index_name} with dimension 1536")
            # Create the index if it doesn't exist
            pc.create_index(
                name=index_name,
                dimension=current_app.config['PINECONE_DIMENSION'],
                metric=current_app.config['PINECONE_METRIC']
            )
            current_app.logger.info(f"Created index {index_name}")
        
        # Use langchain_pinecone's PineconeVectorStore instead
        try:
            # Use from_documents with langchain_pinecone
            vectorstore = PineconeVectorStore.from_documents(
                documents=docs,
                embedding=embeddings,
                index_name=index_name,
                namespace=namespace
            )
            result['extracted_text'] = f"Successfully processed and stored {result['filename']}"
        except Exception as e:
            result['error'] = f"Error upserting documents: {str(e)}"
            return result
        
        return result
    except Exception as e:
        current_app.logger.error(f"Error processing document {result['filename']}: {str(e)}")
        result['error'] = f"Error processing document: {str(e)}"
        return result

def process_image(file_path, result, user_description=None):
    """Process image files (JPEG, PNG, etc.)"""
    try:
        print(f"🖼️ process_image: Processing {file_path} with description: {user_description}")
        
        # If we have a user description, use that as the extracted text
        if user_description:
            result['extracted_text'] = f"[Image file description: {user_description}]"
            print(f"📝 process_image: Using user description: {user_description[:50]}...")
        else:
            # Otherwise just note that it's an image file
            result['extracted_text'] = f"[Image file: {os.path.basename(file_path)}]"
            print(f"📝 process_image: No description provided, using default")
        
        # Ensure type is set to image
        result['type'] = 'image'
        result['success'] = True
        
        print(f"✅ process_image: Successfully processed image: {result}")
        return result
    except Exception as e:
        print(f"❌ process_image: Error processing image file: {str(e)}")
        import traceback
        print(f"❌ process_image: Error traceback: {traceback.format_exc()}")
        result['error'] = f"Error processing image: {str(e)}"
        return result

def store_in_vector_db(result, user_id, conversation_id, message_id):
    """Store extracted text in Pinecone with enhanced metadata"""
    try:
        current_app.logger.info(f"Storing extracted text from {result['filename']} in Pinecone for user {user_id}")
        
        # Initialize embeddings
        embeddings = OpenAIEmbeddings(model=current_app.config['OPENAI_EMBEDDING_MODEL'])
        
        # Get user-specific namespace
        namespace = get_user_namespace(user_id)
        
        # Get the Pinecone index name
        index_name = os.getenv("PINECONE_INDEX_NAME")
        if not index_name:
            current_app.logger.error("PINECONE_INDEX_NAME environment variable is not set!")
            return False
        
        # Make sure the index exists
        index_list = pc.list_indexes().names()
        if index_name not in index_list:
            current_app.logger.info(f"Creating Pinecone index {index_name}")
            pc.create_index(
                name=index_name,
                dimension=current_app.config['PINECONE_DIMENSION'],
                metric=current_app.config['PINECONE_METRIC']
            )
        
        # Create enhanced metadata
        enhanced_metadata = {
            "user_id": str(user_id),
            "source": "document_upload",
            "document_id": result['filename'], # Assuming filename is the document ID
            "conversation_id": str(conversation_id) if conversation_id else "N/A",
            "message_id": str(message_id) if message_id else "N/A",
            "storage_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Create document
        doc = Document(page_content=result['extracted_text'], metadata=enhanced_metadata)
        
        # Store in Pinecone
        try:
            vectorstore = PineconeVectorStore.from_documents(
                documents=[doc],
                embedding=embeddings,
                index_name=index_name,
                namespace=namespace
            )
            current_app.logger.info("Successfully stored extracted text in Pinecone")
            return True
        except Exception as e:
            current_app.logger.error(f"Error storing extracted text: {str(e)}")
            return False
            
    except Exception as e:
        current_app.logger.error(f"Error in store_in_vector_db: {str(e)}")
        return False

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
                "source": "chat_history",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }]
        
        # Use langchain_pinecone's PineconeVectorStore
        try:
            # Create documents from the dict objects
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

def store_enhanced_chat_message(user_id: int, message_content: str, message_metadata: Dict[str, Any]) -> bool:
    """Enhanced chat message storage with additional metadata"""
    try:
        current_app.logger.info(f"Storing enhanced chat message for user {user_id}")
        
        # Initialize embeddings
        embeddings = OpenAIEmbeddings(model=current_app.config['OPENAI_EMBEDDING_MODEL'])
        
        # Get user-specific chat namespace
        namespace = get_chat_namespace(user_id)
        
        # Get the Pinecone index name
        index_name = os.getenv("PINECONE_INDEX_NAME")
        if not index_name:
            current_app.logger.error("PINECONE_INDEX_NAME environment variable is not set!")
            return False
        
        # Make sure the index exists
        index_list = pc.list_indexes().names()
        if index_name not in index_list:
            current_app.logger.info(f"Creating Pinecone index {index_name}")
            pc.create_index(
                name=index_name,
                dimension=current_app.config['PINECONE_DIMENSION'],
                metric=current_app.config['PINECONE_METRIC']
            )
        
        # Create enhanced metadata
        enhanced_metadata = {
            **message_metadata,
            "user_id": str(user_id),
            "source": "enhanced_chat",
            "storage_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Create document
        doc = Document(page_content=message_content, metadata=enhanced_metadata)
        
        # Store in Pinecone
        try:
            vectorstore = PineconeVectorStore.from_documents(
                documents=[doc],
                embedding=embeddings,
                index_name=index_name,
                namespace=namespace
            )
            current_app.logger.info("Successfully stored enhanced chat message")
            return True
        except Exception as e:
            current_app.logger.error(f"Error storing enhanced chat message: {str(e)}")
            return False
            
    except Exception as e:
        current_app.logger.error(f"Error in store_enhanced_chat_message: {str(e)}")
        return False

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

def get_user_document_stats(user_id: int) -> Dict[str, Any]:
    """Get statistics about user's stored documents"""
    try:
        # Get user-specific namespace
        namespace = get_user_namespace(user_id)
        
        # Get the Pinecone index
        index_name = os.getenv("PINECONE_INDEX_NAME")
        if not index_name:
            return {"error": "PINECONE_INDEX_NAME not set"}
        
        # Connect to the index
        index = pc.Index(index_name)
        
        # Get index stats for the namespace
        stats = index.describe_index_stats()
        namespace_stats = stats.get('namespaces', {}).get(namespace, {})
        
        return {
            "total_vectors": namespace_stats.get('vector_count', 0),
            "namespace": namespace,
            "index_name": index_name
        }
        
    except Exception as e:
        current_app.logger.error(f"Error getting user document stats: {str(e)}")
        return {"error": str(e)}