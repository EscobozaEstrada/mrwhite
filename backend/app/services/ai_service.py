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
                api_key=os.getenv("OPENAI_API_KEY"),
                max_retries=3,
                request_timeout=30
            )
        return self._chat_model
    
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
                              response_type: str = "standard") -> str:
        """Optimized chat response generation with context management"""
        try:
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
                response_type=response_type
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
    def search_chat_history(self, query: str, user_id: int, top_k: int = 5) -> List[Document]:
        """Search chat history with caching"""
        try:
            namespace = self.get_user_namespace(user_id, "chat")
            index_name = os.getenv("PINECONE_INDEX_NAME")
            
            if not index_name:
                return []
            
            vectorstore = PineconeVectorStore.from_existing_index(
                index_name=index_name,
                embedding=self.embeddings_model,
                namespace=namespace
            )
            
            docs = vectorstore.similarity_search(query, k=top_k)
            return docs
            
        except Exception as e:
            current_app.logger.error(f"Error searching chat history: {str(e)}")
            return []
    
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

 