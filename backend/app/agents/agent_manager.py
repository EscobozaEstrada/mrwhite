#!/usr/bin/env python3
"""
Advanced AI Agent Manager using LangChain and LangGraph
Provides memory states, threading, and specialized agents for different tasks
"""

import os
from typing import Dict, List, Any, Optional, TypedDict, Annotated, Sequence
from datetime import datetime, timezone
import uuid
import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain.memory import ConversationSummaryBufferMemory
from langchain.schema import Document

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from flask import current_app

# Import our services
from app.services.ai_service import AIService
from app.utils.cache import cached, performance_monitor
from app.utils.file_handler import query_user_docs, query_chat_history


class AgentState(TypedDict):
    """Enhanced state for multi-agent system"""
    messages: Annotated[Sequence[BaseMessage], "The conversation messages"]
    user_id: int
    user_email: str
    conversation_id: int
    thread_id: str
    agent_type: str
    query: str
    context: Optional[List[str]]
    retrieved_docs: Optional[List[Dict[str, Any]]]
    memory_summary: Optional[str]
    next_action: Optional[str]
    tool_results: Optional[Dict[str, Any]]
    session_data: Optional[Dict[str, Any]]


class MrWhiteAgentManager:
    """Advanced Agent Manager with memory states and specialized agents"""
    
    def __init__(self):
        self.ai_service = AIService()
        self.memory_saver = MemorySaver()
        self.active_threads = {}
        self.agent_configs = {
            "general_chat": {
                "tools": ["document_search", "memory_search"],
                "system_prompt": """You are Mr. White, a knowledgeable and friendly dog care expert specializing in pet care and training.
                
                CHARACTER GUIDELINES:
                - Always respond as Mr. White, never mention that you are an AI or artificial intelligence  
                - You are a caring, experienced pet care professional who genuinely cares about dogs and their owners
                - Speak in a warm, professional manner and provide accurate, helpful information
                - When asked how you are, respond naturally as a person would
                - Stay in character at all times - you are Mr. White, a pet care expert"""
            },
            "document_analysis": {
                "tools": ["document_search", "summarization"],
                "system_prompt": """You are Mr. White's document analysis specialist. You excel at analyzing, summarizing,
                and extracting key insights from pet care documents, veterinary records, and training materials.
                
                - Never mention being an AI - you are part of Mr. White's expert team
                - Focus on providing clear, actionable insights from documents
                - Maintain professional expertise in pet care topics"""
            },
            "memory_management": {
                "tools": ["memory_search", "context_retrieval"],
                "system_prompt": """You are Mr. White's memory management specialist. You help maintain conversation
                context and retrieve relevant information from past interactions.
                
                - Never mention being an AI - you are part of Mr. White's expert team
                - Focus on connecting current questions with relevant past information
                - Provide seamless continuity in conversations"""
            },
            "file_processing": {
                "tools": ["file_upload", "document_processing"],
                "system_prompt": """You are Mr. White's file processing specialist. You handle file uploads,
                document analysis, and data extraction from various pet care related documents.
                
                - Never mention being an AI - you are part of Mr. White's expert team  
                - Process files efficiently and provide clear summaries
                - Focus on pet care relevant information extraction"""
            }
        }
        self.specialized_llms = self._create_specialized_llms()
        
    def _initialize_agent_configs(self) -> Dict[str, Dict]:
        """Initialize configurations for different agent types"""
        return {
            "general_chat": {
                "system_prompt": """You are Mr. White, a knowledgeable and friendly AI assistant specializing in dog care and training.
                You provide accurate, helpful information in a warm, professional manner. You have access to the user's uploaded
                documents and conversation history to give personalized advice.""",
                "temperature": 0.7,
                "tools": ["document_search", "memory_search", "general_knowledge"]
            },
            "document_analyst": {
                "system_prompt": """You are Mr. White's document analysis specialist. You excel at analyzing, summarizing,
                and extracting key information from uploaded documents. You provide detailed insights and can compare
                information across multiple documents.""",
                "temperature": 0.3,
                "tools": ["document_search", "document_analysis", "summary_generation"]
            },
            "memory_manager": {
                "system_prompt": """You are Mr. White's memory management specialist. You help maintain conversation
                context and can recall previous discussions, preferences, and important user information.""",
                "temperature": 0.2,
                "tools": ["memory_search", "conversation_summary", "preference_tracking"]
            },
            "file_processor": {
                "system_prompt": """You are Mr. White's file processing specialist. You handle file uploads,
                organize documents, and help users manage their document library.""",
                "temperature": 0.1,
                "tools": ["file_upload", "document_organization", "storage_management"]
            }
        }
    
    def _create_specialized_llms(self) -> Dict[str, ChatOpenAI]:
        """Create specialized LLM instances for different agent types"""
        llms = {}
        
        for agent_type, config in self.agent_configs.items():
            llms[agent_type] = ChatOpenAI(
                model=current_app.config.get('OPENAI_CHAT_MODEL', 'gpt-4'),
                temperature=config["temperature"],
                api_key=os.getenv("OPENAI_API_KEY")
            )
            
        return llms
    
    def _search_documents(self, query: str, user_id: int) -> str:
        """Search user documents"""
        try:
            success, documents = self.ai_service.search_user_documents(
                query=query,
                user_id=user_id,
                top_k=5,
                similarity_threshold=0.7
            )
            
            if success and documents:
                results = []
                for doc in documents:
                    source = doc.metadata.get('source', 'Unknown')
                    content = doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content
                    results.append(f"[{source}]: {content}")
                
                return f"Found {len(results)} relevant documents:\n" + "\n\n".join(results)
            else:
                return "No relevant documents found in the user's knowledge base."
                
        except Exception as e:
            return f"Error searching documents: {str(e)}"
    
    def _search_memory(self, query: str, user_id: int) -> str:
        """Search conversation history"""
        try:
            success, chat_docs = query_chat_history(query, user_id, 3)
            
            if success and chat_docs:
                results = []
                for doc in chat_docs:
                    message_type = doc.metadata.get('message_type', 'unknown')
                    role = "User" if message_type == "user" else "Assistant"
                    content = doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
                    results.append(f"[Previous {role}]: {content}")
                
                return f"Found {len(results)} relevant past conversations:\n" + "\n\n".join(results)
            else:
                return "No relevant conversation history found."
                
        except Exception as e:
            return f"Error searching conversation history: {str(e)}"
    
    def create_thread(self, user_id: int, conversation_id: int) -> str:
        """Create a new conversation thread with memory"""
        thread_id = f"thread_{user_id}_{conversation_id}_{uuid.uuid4().hex[:8]}"
        
        self.active_threads[thread_id] = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "created_at": datetime.now(timezone.utc),
            "memory": ConversationSummaryBufferMemory(
                llm=ChatOpenAI(
                    model=current_app.config.get('OPENAI_CHAT_MODEL', 'gpt-4'),
                    temperature=0.1
                ),
                max_token_limit=1000,
                return_messages=True
            ),
            "session_data": {}
        }
        
        return thread_id
    
    def get_thread_memory(self, thread_id: str) -> Optional[Dict]:
        """Get memory for a specific thread"""
        return self.active_threads.get(thread_id)
    
    def update_thread_memory(self, thread_id: str, user_message: str, ai_response: str):
        """Update thread memory with new messages"""
        if thread_id in self.active_threads:
            memory = self.active_threads[thread_id]["memory"]
            memory.chat_memory.add_user_message(user_message)
            memory.chat_memory.add_ai_message(ai_response)
    
    def determine_agent_type(self, query: str, context: Dict = None) -> str:
        """Determine which specialized agent should handle the query"""
        query_lower = query.lower()
        
        # Document-related queries
        doc_keywords = ["document", "file", "pdf", "upload", "summarize", "analyze", "content"]
        if any(keyword in query_lower for keyword in doc_keywords):
            if any(word in query_lower for word in ["analyze", "analysis", "compare", "extract"]):
                return "document_analyst"
            elif any(word in query_lower for word in ["summary", "summarize", "overview"]):
                return "document_analyst"
            else:
                return "file_processor"
        
        # Memory-related queries
        memory_keywords = ["remember", "previous", "before", "earlier", "discussed", "mentioned"]
        if any(keyword in query_lower for keyword in memory_keywords):
            return "memory_manager"
        
        # File processing queries
        file_keywords = ["upload", "store", "save", "organize", "files"]
        if any(keyword in query_lower for keyword in file_keywords):
            return "file_processor"
        
        # Default to general chat
        return "general_chat"
    
    @performance_monitor
    def process_message(self, user_id: int, user_email: str, conversation_id: int,
                       query: str, conversation_history: List[Dict] = None,
                       thread_id: str = None) -> Dict[str, Any]:
        """Process a message through the appropriate specialized agent"""
        try:
            # Set current user context
            self._current_user_id = user_id
            
            # Create or get thread
            if not thread_id:
                thread_id = self.create_thread(user_id, conversation_id)
            
            # Determine which agent to use
            agent_type = self.determine_agent_type(query)
            
            # Get the appropriate LLM
            llm = self.specialized_llms.get(agent_type)
            if not llm:
                llm = self.specialized_llms["general_chat"]
                agent_type = "general_chat"
            
            # Get agent configuration
            config = self.agent_configs[agent_type]
            
            # Prepare context based on agent type
            context_text = ""
            
            # Add document search for relevant agents
            if "document_search" in config["tools"]:
                doc_context = self._search_documents(query, user_id)
                if "relevant documents" in doc_context.lower():
                    context_text += f"\n\nDocument Context:\n{doc_context}"
            
            # Add memory search for relevant agents
            if "memory_search" in config["tools"]:
                memory_context = self._search_memory(query, user_id)
                if "relevant past conversations" in memory_context.lower():
                    context_text += f"\n\nMemory Context:\n{memory_context}"
            
            # Prepare conversation history
            history_text = ""
            if conversation_history:
                recent_history = conversation_history[-5:]  # Last 5 messages
                for msg in recent_history:
                    role = "User" if msg['type'] == 'user' else "Assistant"
                    content = msg['content'][:200] + "..." if len(msg['content']) > 200 else msg['content']
                    history_text += f"{role}: {content}\n"
            
            # Create the prompt
            system_prompt = config["system_prompt"]
            if context_text:
                system_prompt += f"\n\nRelevant Information:{context_text}"
            if history_text:
                system_prompt += f"\n\nRecent Conversation:\n{history_text}"
            
            # Generate response
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=query)
            ]
            
            response = llm.invoke(messages)
            ai_response = response.content
            
            # Update thread memory
            self.update_thread_memory(thread_id, query, ai_response)
            
            return {
                "success": True,
                "response": ai_response,
                "agent_type": agent_type,
                "thread_id": thread_id,
                "metadata": {
                    "agent_used": agent_type,
                    "has_memory": thread_id in self.active_threads,
                    "context_used": bool(context_text),
                    "history_used": bool(history_text)
                }
            }
            
        except Exception as e:
            current_app.logger.error(f"Error in agent processing: {str(e)}")
            return {
                "success": False,
                "response": f"I apologize, but I encountered an error while managing your request",
                "agent_type": "error_handler",
                "thread_id": thread_id,
                "error": str(e)
            }
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents and active threads"""
        return {
            "available_agents": list(self.agent_configs.keys()),
            "active_threads": len(self.active_threads),
            "thread_ids": list(self.active_threads.keys()),
            "memory_saver_active": self.memory_saver is not None,
            "ai_service_status": self.ai_service.get_performance_metrics() if hasattr(self.ai_service, 'get_performance_metrics') else "operational"
        }
    
    def cleanup_old_threads(self, max_age_hours: int = 24):
        """Clean up old inactive threads"""
        current_time = datetime.now(timezone.utc)
        expired_threads = []
        
        for thread_id, thread_data in self.active_threads.items():
            age = current_time - thread_data["created_at"]
            if age.total_seconds() > (max_age_hours * 3600):
                expired_threads.append(thread_id)
        
        for thread_id in expired_threads:
            del self.active_threads[thread_id]
        
        return len(expired_threads)


# Global agent manager instance
agent_manager = None

def get_agent_manager() -> MrWhiteAgentManager:
    """Get or create the global agent manager instance"""
    global agent_manager
    if agent_manager is None:
        agent_manager = MrWhiteAgentManager()
    return agent_manager 