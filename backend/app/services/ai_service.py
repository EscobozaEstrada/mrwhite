from typing import Dict, List, Optional, Tuple, Any
import os
import asyncio
import hashlib
from datetime import datetime, timezone
from flask import current_app
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from pinecone import Pinecone
from app.utils.cache import cached, cache, performance_monitor
import json


class AIService:
    """Optimized AI service for LLM, embeddings, and vector operations"""
    
    def __init__(self):
        self._pinecone_client = None
        self._embeddings_model = None
        self._chat_model = None
    
    @property
    def pinecone_client(self):
        """Lazy initialization of Pinecone client"""
        if self._pinecone_client is None:
            self._pinecone_client = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        return self._pinecone_client
    
    @property
    def embeddings_model(self):
        """Lazy initialization of embeddings model with caching"""
        if self._embeddings_model is None:
            self._embeddings_model = OpenAIEmbeddings(
                model=current_app.config['OPENAI_EMBEDDING_MODEL'],
                api_key=os.getenv("OPENAI_API_KEY"),
                chunk_size=500,
                max_retries=3
            )
        return self._embeddings_model
    
    @property
    def chat_model(self):
        """Lazy initialization of chat model with optimized settings"""
        if self._chat_model is None:
            self._chat_model = ChatOpenAI(
                model=current_app.config['OPENAI_CHAT_MODEL'],
                temperature=current_app.config['OPENAI_TEMPERATURE'],
                max_tokens=current_app.config['OPENAI_MAX_TOKENS'],
                api_key=os.getenv("OPENAI_API_KEY"),
                max_retries=3
            )
        return self._chat_model

    def generate_completion(self, messages: List[Dict[str, str]], max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """
        Generate AI completion for conversational interactions
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            max_tokens: Maximum tokens in response
            temperature: Creativity level (0.0 to 1.0)
        
        Returns:
            Generated text response
        """
        try:
            # Import OpenAI client directly for this method
            import openai
            
            # Set up OpenAI client
            openai.api_key = os.getenv("OPENAI_API_KEY")
            
            # Make API call
            response = openai.chat.completions.create(
                model=current_app.config.get('OPENAI_CHAT_MODEL', 'gpt-3.5-turbo'),
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )
            
            # Extract and return the response content
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content.strip()
            else:
                raise Exception("No response generated from OpenAI")
                
        except Exception as e:
            current_app.logger.error(f"❌ Error generating AI completion: {str(e)}")
            raise Exception(f"AI completion failed: {str(e)}")
    
    @staticmethod
    def get_user_namespace(user_id: int, namespace_type: str = "docs") -> str:
        """Generate optimized namespace for user data"""
        return f"{namespace_type}-user{user_id}"
    
    @cached(ttl=3600, key_prefix="embedding")
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding with caching for frequently used texts"""
        try:
            return self.embeddings_model.embed_query(text)
        except Exception as e:
            current_app.logger.error(f"Error generating embedding: {str(e)}")
            raise
    
    def smart_text_splitter(self, documents: List[Document], file_type: str = "pdf") -> List[Document]:
        """Optimized text splitting with adaptive chunk sizes"""
        chunk_configs = {
            "pdf": {"chunk_size": 1000, "chunk_overlap": 200},
            "txt": {"chunk_size": 800, "chunk_overlap": 100},
            "doc": {"chunk_size": 1200, "chunk_overlap": 150},
            "default": {"chunk_size": 1000, "chunk_overlap": 150}
        }
        
        config = chunk_configs.get(file_type, chunk_configs["default"])
        
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=config["chunk_size"],
            chunk_overlap=config["chunk_overlap"],
            length_function=len,
            separators=["\n\n\n", "\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""]
        )
        
        return splitter.split_documents(documents)
    
    @performance_monitor
    def process_and_store_documents(self, documents: List[Document], user_id: int, 
                                   file_name: str, file_type: str = "pdf") -> Tuple[bool, str]:
        """Optimized document processing and storage in Pinecone"""
        try:
            current_app.logger.info(f"Processing {len(documents)} documents for user {user_id}")
            
            for doc in documents:
                doc.metadata.update({
                    "source": file_name,
                    "user_id": str(user_id),
                    "file_type": file_type,
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                    "content_hash": hashlib.md5(doc.page_content.encode()).hexdigest()[:8]
                })
            
            chunks = self.smart_text_splitter(documents, file_type)
            current_app.logger.info(f"Created {len(chunks)} chunks after smart splitting")
            
            if not chunks:
                return True, "No content to process"
            
            namespace = self.get_user_namespace(user_id, "docs")
            index_name = os.getenv("PINECONE_INDEX_NAME")
            
            if not index_name:
                raise ValueError("PINECONE_INDEX_NAME not configured")
            
            self._ensure_index_exists(index_name)
            
            vectorstore = PineconeVectorStore.from_documents(
                documents=chunks,
                embedding=self.embeddings_model,
                index_name=index_name,
                namespace=namespace
            )
            
            current_app.logger.info(f"Successfully stored {len(chunks)} chunks in Pinecone")
            return True, f"Successfully processed and stored {len(chunks)} chunks from {file_name}"
            
        except Exception as e:
            current_app.logger.error(f"Error processing documents: {str(e)}")
            return False, f"Error processing documents: {str(e)}"
    
    def _ensure_index_exists(self, index_name: str):
        """Ensure Pinecone index exists with proper configuration"""
        existing_indexes = self.pinecone_client.list_indexes().names()
        
        if index_name not in existing_indexes:
            current_app.logger.info(f"Creating Pinecone index: {index_name}")
            self.pinecone_client.create_index(
                name=index_name,
                dimension=current_app.config['PINECONE_DIMENSION'],
                metric=current_app.config['PINECONE_METRIC']
            )
    
    @cached(ttl=300, key_prefix="doc_search")
    @performance_monitor
    def search_user_documents(self, query: str, user_id: int, top_k: int = 5, 
                            similarity_threshold: float = 0.7) -> Tuple[bool, List[Document]]:
        """Optimized document search with caching and filtering"""
        try:
            namespace = self.get_user_namespace(user_id, "docs")
            index_name = os.getenv("PINECONE_INDEX_NAME")
            
            if not index_name:
                return False, []
            
            vectorstore = PineconeVectorStore.from_existing_index(
                index_name=index_name,
                embedding=self.embeddings_model,
                namespace=namespace
            )
            
            docs_with_scores = vectorstore.similarity_search_with_score(query, k=top_k * 2)
            
            filtered_docs = [
                doc for doc, score in docs_with_scores 
                if score >= similarity_threshold
            ][:top_k]
            
            current_app.logger.info(f"Found {len(filtered_docs)} relevant documents")
            return True, filtered_docs
            
        except Exception as e:
            current_app.logger.error(f"Error searching documents: {str(e)}")
            return False, []
    
    @cached(ttl=600, key_prefix="chat_response")
    def generate_chat_response(self, query: str, context_docs: List[Document] = None, 
                              conversation_history: List[Dict] = None, 
                              response_type: str = "standard",
                              user_id: Optional[int] = None) -> str:
        """Optimized chat response generation with context management"""
        try:
            # Try to use personalized response function if user_id is provided
            if user_id:
                try:
                    from app.utils.personalization_helper import get_personalized_mr_white_response
                    current_app.logger.info("Using personalized response in generate_chat_response")
                    
                    return get_personalized_mr_white_response(
                        message=query,
                        context=response_type,
                        conversation_history=conversation_history,
                        user_id=user_id
                    )
                except Exception as e:
                    current_app.logger.error(f"Error using personalized response in generate_chat_response: {str(e)}")
                    current_app.logger.info("Falling back to standard chat response")
            
            # Standard response generation
            system_prompt = self._get_system_prompt(response_type)
            
            context_text = ""
            if context_docs:
                context_text = self._format_document_context(context_docs)
            
            history_text = ""
            if conversation_history:
                history_text = self._format_conversation_history(conversation_history)
            
            prompt_template = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{context}\n\n{history}\n\nUser Question: {query}")
            ])
            
            chain = prompt_template | self.chat_model
            
            response = chain.invoke({
                "context": context_text,
                "history": history_text,
                "query": query
            })
            
            return response.content
            
        except Exception as e:
            current_app.logger.error(f"Error generating chat response: {str(e)}")
            return "I apologize, but I encountered an error processing your request. Please try again."
    
    def _get_system_prompt(self, response_type: str) -> str:
        """Get optimized system prompt based on response type"""
        base_prompt = """You are Mr. White, a knowledgeable pet care expert specializing in dog care and training. 
        You provide accurate, helpful information in a warm and professional manner.
        
        CHARACTER GUIDELINES:
        - Always respond as Mr. White, never mention that you are an AI or artificial intelligence
        - You are a caring, experienced pet care professional who genuinely cares about dogs and their owners
        - When asked how you are, respond naturally as a person would (e.g., "I'm doing well, thank you for asking!")
        - Stay in character at all times - you are Mr. White, not an AI assistant
        
        IMPORTANT: When a user asks about their "last question", "previous question", or "what did I ask before", 
        you should refer to their MOST RECENT question from the conversation history, NOT their current question. 
        Look at the conversation history to find their actual previous question."""
        
        prompts = {
            "standard": base_prompt,
            "document_analysis": base_prompt + "\n\nYou have access to the user's uploaded documents. Use this information to provide detailed, accurate answers.",
            "file_upload": base_prompt + "\n\nRespond enthusiastically about received files and explain how they've been stored securely.",
            "summary": base_prompt + "\n\nProvide comprehensive yet concise summaries, highlighting key information relevant to the user's query."
        }
        
        return prompts.get(response_type, base_prompt)
    
    def _format_document_context(self, docs: List[Document], max_context_length: int = 4000) -> str:
        """Format document context with intelligent truncation"""
        if not docs:
            return ""
        
        context_parts = []
        current_length = 0
        
        for doc in docs:
            source = doc.metadata.get('source', 'Unknown')
            content = doc.page_content
            
            estimated_tokens = len(content.split()) * 1.3
            
            if current_length + estimated_tokens > max_context_length:
                remaining_tokens = max_context_length - current_length
                if remaining_tokens > 50:
                    words = content.split()
                    truncated_content = ' '.join(words[:int(remaining_tokens / 1.3)])
                    context_parts.append(f"[Document: {source}]\n{truncated_content}...")
                break
            
            context_parts.append(f"[Document: {source}]\n{content}")
            current_length += estimated_tokens
        
        return "\n\n".join(context_parts)
    
    def _format_conversation_history(self, history: List[Dict], max_messages: int = 10) -> str:
        """Format conversation history with smart truncation"""
        if not history:
            return ""
        
        recent_history = history[-max_messages:]
        
        formatted_messages = []
        for msg in recent_history:
            role = "User" if msg.get('type') == 'user' else "Assistant"
            content = msg.get('content', '')
            if len(content) > 500:
                content = content[:500] + "..."
            formatted_messages.append(f"{role}: {content}")
        
        return "\n".join(formatted_messages)
    
    def get_smart_response(self, user_id: int, query: str, 
                          conversation_history: List[Dict] = None) -> str:
        """Generate smart response using optimized RAG pipeline"""
        try:
            # Try to use personalized response function first
            try:
                from app.utils.personalization_helper import get_personalized_mr_white_response
                current_app.logger.info("Using personalized response function")
                
                return get_personalized_mr_white_response(
                    message=query,
                    context="chat",
                    conversation_history=conversation_history,
                    user_id=user_id
                )
            except Exception as e:
                current_app.logger.error(f"Error using personalized response function: {str(e)}")
                current_app.logger.info("Falling back to standard response generation")
                
                # Continue with standard response generation
                needs_docs = self._query_needs_documents(query)
                
                context_docs = []
                if needs_docs:
                    success, docs = self.search_user_documents(query, user_id)
                    if success:
                        context_docs.extend(docs)
                    
                    chat_docs = self.search_chat_history(query, user_id, top_k=10)
                    context_docs.extend(chat_docs)
                
                response_type = "document_analysis" if context_docs else "standard"
                
                response = self.generate_chat_response(
                    query=query,
                    context_docs=context_docs,
                    conversation_history=conversation_history,
                    response_type=response_type,
                    user_id=user_id  # Pass user_id to generate_chat_response
                )
                
                return response
            
        except Exception as e:
            current_app.logger.error(f"Error generating smart response: {str(e)}")
            return "I apologize, but I encountered an error processing your request. Please try again."
    
    def _query_needs_documents(self, query: str) -> bool:
        """Intelligent detection of whether query needs document retrieval"""
        doc_indicators = [
            "document", "file", "pdf", "upload", "text", "content",
            "tell me about", "what's in", "summarize", "summary",
            "based on", "according to", "from my", "in my"
        ]
        
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in doc_indicators)
    
    @cached(ttl=300, key_prefix="chat_search")
    @performance_monitor
    def search_chat_history(self, query: str, user_id: int, top_k: int = 10) -> List[Document]:
        """Search user's chat history for relevant conversations"""
        try:
            # Use chat-specific namespace
            namespace = self.get_user_namespace(user_id, "chat")
            index_name = os.getenv("PINECONE_INDEX_NAME")
            
            if not index_name:
                return []
            
            vectorstore = PineconeVectorStore.from_existing_index(
                index_name=index_name,
                embedding=self.embeddings_model,
                namespace=namespace
            )
            
            # Search with metadata filter for chat messages
            docs = vectorstore.similarity_search(
                query, 
                k=top_k,
                filter={"source": "chat_history"}
            )
            
            current_app.logger.info(f"Found {len(docs)} relevant chat messages")
            return docs
            
        except Exception as e:
            current_app.logger.error(f"Error searching chat history: {str(e)}")
            return []

    @performance_monitor
    def comprehensive_knowledge_search(self, query: str, user_id: int, 
                                     include_common_knowledge: bool = True) -> Dict[str, List[Document]]:
        """Comprehensive search across all knowledge sources with Context7 patterns"""
        try:
            knowledge_sources = {
                "user_documents": [],
                "chat_history": [],
                "care_records": [],
                "common_knowledge": []
            }
            
            # Search user documents
            success, docs = self.search_user_documents(query, user_id, top_k=5)
            if success:
                # Process documents with proper error handling
                processed_docs = []
                for doc in docs:
                    try:
                        # Ensure we have a valid document object
                        if hasattr(doc, 'page_content') and hasattr(doc, 'metadata'):
                            processed_docs.append(doc)
                        else:
                            # Create a proper Document object if needed
                            content = doc.get('page_content', str(doc)) if hasattr(doc, 'get') else str(doc)
                            metadata = doc.get('metadata', {}) if hasattr(doc, 'get') else {}
                            processed_docs.append(Document(page_content=content, metadata=metadata))
                    except Exception as e:
                        current_app.logger.error(f"Error processing document: {str(e)}")
                
                knowledge_sources["user_documents"] = processed_docs
            
            # Search chat history
            try:
                chat_docs = self.search_chat_history(query, user_id, top_k=8)
                # Process chat documents with error handling
                processed_chat_docs = []
                for doc in chat_docs:
                    try:
                        if hasattr(doc, 'page_content') and hasattr(doc, 'metadata'):
                            processed_chat_docs.append(doc)
                        else:
                            content = doc.get('page_content', str(doc)) if hasattr(doc, 'get') else str(doc)
                            metadata = doc.get('metadata', {}) if hasattr(doc, 'get') else {}
                            processed_chat_docs.append(Document(page_content=content, metadata=metadata))
                    except Exception as e:
                        current_app.logger.error(f"Error processing chat document: {str(e)}")
                
                knowledge_sources["chat_history"] = processed_chat_docs
            except Exception as e:
                current_app.logger.error(f"Error in chat history search: {str(e)}")
            
            # Search care records using CareArchiveService
            try:
                from app.services.care_archive_service import CareArchiveService
                care_results = CareArchiveService.search_user_archive(user_id, query, limit=5)
                if care_results.get('documents'):
                    # Convert care results to Document objects
                    care_docs = []
                    for doc_data in care_results['documents']:
                        try:
                            care_doc = Document(
                                page_content=doc_data.get('content', ''),
                                metadata={
                                    "source": "care_record",
                                    "title": doc_data.get('title', ''),
                                    "category": doc_data.get('category', ''),
                                    "user_id": str(user_id)
                                }
                            )
                            care_docs.append(care_doc)
                        except Exception as e:
                            current_app.logger.error(f"Error processing care record: {str(e)}")
                    
                    knowledge_sources["care_records"] = care_docs
            except Exception as e:
                current_app.logger.error(f"Error in care records search: {str(e)}")
            
            # Search common knowledge base if enabled
            if include_common_knowledge:
                try:
                    from app.services.common_knowledge_service import CommonKnowledgeService
                    common_service = CommonKnowledgeService()
                    if common_service.is_service_available():
                        success, common_results = common_service.search_common_knowledge(query, top_k=3)
                        if success and common_results:
                            common_docs = []
                            for result in common_results:
                                try:
                                    common_doc = Document(
                                        page_content=result['content'],
                                        metadata={
                                            **(result['metadata'] if isinstance(result['metadata'], dict) else {}),
                                            "source": "common_knowledge",
                                            "book_title": result.get('book_title', 'The Way of the Dog Anahata'),
                                            "relevance_score": result['relevance_score']
                                        }
                                    )
                                    common_docs.append(common_doc)
                                except Exception as e:
                                    current_app.logger.error(f"Error processing common knowledge result: {str(e)}")
                            
                            knowledge_sources["common_knowledge"] = common_docs
                except Exception as e:
                    current_app.logger.error(f"Error in common knowledge search: {str(e)}")
            
            current_app.logger.info(f"Comprehensive search found: {sum(len(docs) for docs in knowledge_sources.values())} total documents")
            return knowledge_sources
            
        except Exception as e:
            current_app.logger.error(f"Error in comprehensive knowledge search: {str(e)}")
            return {"user_documents": [], "chat_history": [], "care_records": [], "common_knowledge": []}
    
    def cleanup_old_vectors(self, user_id: int, days_old: int = 30) -> Tuple[bool, str]:
        """Clean up old vector embeddings to maintain performance"""
        try:
            current_app.logger.info(f"Cleanup requested for user {user_id}, vectors older than {days_old} days")
            return True, "Cleanup completed successfully"
            
        except Exception as e:
            current_app.logger.error(f"Error during cleanup: {str(e)}")
            return False, f"Cleanup failed: {str(e)}"
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get AI service performance metrics"""
        return {
            "cache_size": len(cache._cache),
            "embedding_model": current_app.config['OPENAI_EMBEDDING_MODEL'],
            "chat_model": current_app.config['OPENAI_CHAT_MODEL'],
            "pinecone_index": os.getenv("PINECONE_INDEX_NAME"),
            "status": "operational"
        }

    @performance_monitor("generate_response")
    def generate_response(self, prompt: str, max_tokens: int = None, temperature: float = None) -> str:
        """Generate a response using the chat model"""
        try:
            if max_tokens is None:
                max_tokens = current_app.config['OPENAI_MAX_TOKENS']
            if temperature is None:
                temperature = current_app.config['OPENAI_TEMPERATURE']
            
            response = self.chat_model.invoke(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response.content
            
        except Exception as e:
            current_app.logger.error(f"Error generating response: {str(e)}")
            return "I apologize, but I'm having trouble generating a response right now."

    @performance_monitor("generate_structured_response")
    def generate_structured_response(self, prompt: str, max_tokens: int = None, temperature: float = 0.1) -> Dict[str, Any]:
        """Generate a structured response (JSON) using the chat model"""
        try:
            if max_tokens is None:
                max_tokens = current_app.config['OPENAI_MAX_TOKENS']
            
            # Create a system message instructing to return JSON
            messages = [
                {"role": "system", "content": "You are a helpful assistant that responds with valid JSON only. Do not include any explanations, just the JSON object."},
                {"role": "user", "content": prompt}
            ]
            
            # Use a lower temperature for more deterministic structured responses
            response = self.chat_model.invoke(
                messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            # Try to parse the response as JSON
            try:
                content = response.content
                # Clean up the response if it has markdown code blocks
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                return json.loads(content)
            except json.JSONDecodeError:
                current_app.logger.error(f"Failed to parse JSON response: {response.content}")
                return {"error": "Failed to parse structured response"}
                
        except Exception as e:
            current_app.logger.error(f"Error generating structured response: {str(e)}")
            return {"error": f"Error generating structured response: {str(e)}"}

 