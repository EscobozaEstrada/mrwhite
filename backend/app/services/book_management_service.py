import os
import uuid
import json
import logging
import tempfile
import requests
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime, timezone
from pathlib import Path

# Document processing libraries
import PyPDF2
import fitz  # PyMuPDF for better PDF handling
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LangchainDocument
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.document_loaders import PyPDFLoader

# LangGraph and LangChain imports
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from typing_extensions import TypedDict

# Flask and internal imports
from flask import current_app
from app import db
from app.models.care_record import KnowledgeBase
from app.models.user import User
from app.utils.s3_handler import get_s3_url
from app.services.common_knowledge_service import get_common_knowledge_service


# Book Management State Schema using Context7 patterns
class BookManagementState(MessagesState):
    """Enhanced state for book management workflow following Context7 best practices"""
    user_id: int
    operation: str  # 'read', 'chat', 'edit', 'download'
    book_title: str
    
    # Reading operations
    page_number: Optional[int]
    chapter_requested: Optional[str]
    reading_position: Dict[str, Any]
    
    # Chat operations
    query: str
    chat_context: Dict[str, Any]
    conversation_history: List[Dict[str, Any]]
    
    # Edit operations
    edit_instruction: str
    edit_type: str  # 'content', 'style', 'structure'
    original_content: str
    edited_content: str
    edit_summary: str
    
    # Download operations
    download_format: str  # 'pdf', 'epub', 'txt'
    download_url: str
    
    # Content and analysis
    book_content: str
    relevant_sections: List[Dict[str, Any]]
    insights: List[str]
    suggestions: List[str]
    
    # Agent communication
    agent_notes: Dict[str, Any]
    tools_used: List[str]
    workflow_trace: List[str]
    
    # Response generation
    response_content: str
    response_type: str
    confidence_score: float
    
    # Error handling
    error_message: Optional[str]
    processing_status: str


class BookManagementService:
    """Comprehensive book management service for 'The Way of the Dog Anahata' using LangGraph agents"""
    
    # Book configuration
    BOOK_TITLE = "The Way of the Dog Anahata"
    BOOK_S3_KEY = "public/books/the-way-of-the-dog-anahata.pdf"
    BOOK_S3_URL = "https://master-white-project.s3.us-east-1.amazonaws.com/public/books/the-way-of-the-dog-anahata.pdf"
    
    def __init__(self):
        self.chat_model = ChatOpenAI(
            model="gpt-4",
            temperature=0.3,
            max_tokens=2000
        )
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
        self.checkpointer = MemorySaver()
        self.graph = None
        self._initialize_book_graph()
    
    def _initialize_book_graph(self):
        """Initialize the book management LangGraph workflow"""
        try:
            self._build_book_graph()
            # Use Flask logger if available, otherwise use Python logging
            try:
                current_app.logger.info("✅ Book management graph initialized successfully")
            except RuntimeError:
                logging.info("✅ Book management graph initialized successfully")
        except Exception as e:
            # Use Flask logger if available, otherwise use Python logging
            try:
                current_app.logger.error(f"❌ Error initializing book management graph: {str(e)}")
            except RuntimeError:
                logging.error(f"❌ Error initializing book management graph: {str(e)}")
            raise
    
    def _build_book_graph(self):
        """Build the enhanced LangGraph state graph for book management"""
        
        builder = StateGraph(BookManagementState)
        
        # Add specialized book management agents
        builder.add_node("operation_router", self._operation_router_agent)
        builder.add_node("book_reader", self._book_reader_agent)
        builder.add_node("book_chat", self._book_chat_agent)
        builder.add_node("book_editor", self._book_editor_agent)
        builder.add_node("book_downloader", self._book_downloader_agent)
        builder.add_node("content_analyzer", self._content_analyzer_agent)
        builder.add_node("response_generator", self._response_generator_agent)
        
        # Define routing based on operation
        builder.add_edge(START, "operation_router")
        builder.add_conditional_edges(
            "operation_router",
            self._route_by_operation,
            {
                "read": "book_reader",
                "chat": "book_chat",
                "edit": "book_editor",
                "download": "book_downloader"
            }
        )
        
        # All operations go through content analysis
        builder.add_edge("book_reader", "content_analyzer")
        builder.add_edge("book_chat", "content_analyzer")
        builder.add_edge("book_editor", "content_analyzer")
        builder.add_edge("book_downloader", "response_generator")
        
        # Content analysis leads to response generation
        builder.add_edge("content_analyzer", "response_generator")
        builder.add_edge("response_generator", END)
        
        # Compile the graph
        self.graph = builder.compile(checkpointer=self.checkpointer)
    
    def _route_by_operation(self, state: BookManagementState) -> str:
        """Route to appropriate agent based on operation"""
        operation = state.get('operation', 'read')
        if operation in ['read', 'chat', 'edit', 'download']:
            return operation
        return 'read'  # Default fallback
    
    def _operation_router_agent(self, state: BookManagementState) -> Dict[str, Any]:
        """Route operations and initialize book content"""
        try:
            current_app.logger.info(f"🎯 Routing book operation: {state.get('operation', 'read')}")
            
            # Load book content if not already loaded
            book_content = state.get('book_content', '')
            if not book_content:
                book_content = self._load_book_content()
            
            workflow_trace = state.get('workflow_trace', [])
            workflow_trace.append("operation_router_completed")
            
            return {
                "book_content": book_content,
                "book_title": self.BOOK_TITLE,
                "processing_status": "routing_completed",
                "workflow_trace": workflow_trace,
                "agent_notes": {
                    **state.get('agent_notes', {}),
                    "router": {
                        "operation": state.get('operation', 'read'),
                        "book_loaded": bool(book_content),
                        "content_length": len(book_content)
                    }
                }
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Operation router failed: {str(e)}")
            return {
                "error_message": f"Operation routing failed: {str(e)}",
                "processing_status": "router_failed"
            }
    
    def _book_reader_agent(self, state: BookManagementState) -> Dict[str, Any]:
        """Handle book reading operations with chapter navigation"""
        try:
            current_app.logger.info("📖 Processing book reading request")
            current_app.logger.info(f"🔍 DEBUG: Book content length: {len(state.get('book_content', ''))}")
            current_app.logger.info(f"🔍 DEBUG: State keys: {list(state.keys())}")
            
            book_content = state.get('book_content', '')
            page_number = state.get('page_number')
            chapter_requested = state.get('chapter_requested')
            
            # Analyze reading request
            reading_prompt = f"""
            You are a book reading assistant for "{self.BOOK_TITLE}".
            
            User request: {state.get('query', 'Show me the book content')}
            Requested page: {page_number}
            Requested chapter: {chapter_requested}
            
            Based on the book content, provide:
            1. The most relevant section to show the user
            2. Chapter/section navigation options
            3. Reading progress tracking
            4. Key insights from the requested section
            
            Book content preview:
            {book_content[:2000]}...
            
            Provide a comprehensive reading experience.
            """
            
            response = self.chat_model.invoke([
                SystemMessage(content="You are an expert book reading assistant."),
                HumanMessage(content=reading_prompt)
            ])
            
            current_app.logger.info(f"🔍 DEBUG: AI response length: {len(response.content) if response.content else 0}")
            current_app.logger.info(f"🔍 DEBUG: AI response preview: {response.content[:200] if response.content else 'None'}")
            
            # Extract relevant sections
            relevant_sections = self._extract_relevant_sections(
                book_content, 
                state.get('query', ''),
                section_type='reading'
            )
            
            workflow_trace = state.get('workflow_trace', [])
            workflow_trace.append("book_reader_completed")
            
            return {
                "response_content": response.content,
                "response_type": "reading",
                "relevant_sections": relevant_sections,
                "reading_position": {
                    "current_page": page_number or 1,
                    "chapter": chapter_requested,
                    "progress_percentage": self._calculate_reading_progress(book_content, relevant_sections)
                },
                "confidence_score": 0.9,
                "processing_status": "reading_completed",
                "workflow_trace": workflow_trace,
                "tools_used": state.get('tools_used', []) + ["book_reader", "content_extractor"],
                "agent_notes": {
                    **state.get('agent_notes', {}),
                    "reader": {
                        "sections_found": len(relevant_sections),
                        "reading_mode": "structured",
                        "navigation_available": True
                    }
                }
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Book reader failed: {str(e)}")
            return {
                "error_message": f"Reading failed: {str(e)}",
                "processing_status": "reading_failed"
            }
    
    def _book_chat_agent(self, state: BookManagementState) -> Dict[str, Any]:
        """Handle interactive chat about the book content"""
        try:
            current_app.logger.info("💬 Processing book chat request")
            
            query = state.get('query', '')
            book_content = state.get('book_content', '')
            conversation_history = state.get('conversation_history', [])
            user_id = state.get('user_id', 1)
            
            # Search for relevant content using knowledge base
            relevant_content = self._search_book_knowledge(query, book_content)
            
            # Search for user's personal knowledge (comments and notes)
            from app.services.user_knowledge_service import get_user_knowledge_service
            user_knowledge_service = get_user_knowledge_service()
            user_knowledge = user_knowledge_service.get_user_knowledge_context(user_id, query)
            
            # Track if user knowledge was found
            has_user_knowledge = bool(user_knowledge)
            
            # Build chat context
            context_messages = []
            for msg in conversation_history[-5:]:  # Last 5 messages for context
                if msg.get('role') == 'user':
                    context_messages.append(HumanMessage(content=msg['content']))
                elif msg.get('role') == 'assistant':
                    context_messages.append(AIMessage(content=msg['content']))
            
            # Generate contextual response about the book
            chat_prompt = f"""
            You are Mr. White, an expert on "{self.BOOK_TITLE}" and dog training philosophy.
            
            User question: {query}
            
            Relevant book content:
            {relevant_content}
            """
            
            # Add user knowledge if available
            if has_user_knowledge:
                chat_prompt += f"""
                
                {user_knowledge}
                
                IMPORTANT: The user's personal notes and comments above are highly relevant to this query.
                Reference and acknowledge these personal notes in your response when appropriate.
                Make it clear when you're referencing the user's own notes vs. general book content.
                """
            
            chat_prompt += f"""
            
            Conversation history available: {len(conversation_history)} messages
            
            Provide a knowledgeable, friendly response that:
            1. Directly answers the user's question using book content
            2. References specific concepts from the book
            3. Offers practical insights and applications
            4. Suggests follow-up questions or related topics
            5. Maintains the wisdom and tone of the book
            
            Be conversational but authoritative, as if you're the author explaining your work.
            """
            
            response = self.chat_model.invoke([
                SystemMessage(content="You are Mr. White, expert dog trainer and author of 'The Way of the Dog Anahata'."),
                *context_messages,
                HumanMessage(content=chat_prompt)
            ])
            
            # Generate follow-up suggestions
            suggestions = self._generate_chat_suggestions(query, relevant_content)
            
            workflow_trace = state.get('workflow_trace', [])
            workflow_trace.append("book_chat_completed")
            
            # Update tools used to include user knowledge if it was used
            tools_used = state.get('tools_used', []) + ["book_chat", "knowledge_search"]
            if has_user_knowledge:
                tools_used.append("user_knowledge_search")
            
            return {
                "response_content": response.content,
                "response_type": "chat",
                "chat_context": {
                    "query": query,
                    "relevant_content_length": len(relevant_content),
                    "context_used": len(context_messages),
                    "user_knowledge_used": has_user_knowledge
                },
                "suggestions": suggestions,
                "confidence_score": 0.85,
                "processing_status": "chat_completed",
                "workflow_trace": workflow_trace,
                "tools_used": tools_used,
                "agent_notes": {
                    **state.get('agent_notes', {}),
                    "chat": {
                        "query_type": "book_discussion",
                        "knowledge_retrieved": bool(relevant_content),
                        "user_knowledge_retrieved": has_user_knowledge,
                        "conversation_length": len(conversation_history)
                    }
                }
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Book chat failed: {str(e)}")
            return {
                "error_message": f"Chat failed: {str(e)}",
                "processing_status": "chat_failed"
            }
    
    def _book_editor_agent(self, state: BookManagementState) -> Dict[str, Any]:
        """Handle AI-powered book editing operations"""
        try:
            current_app.logger.info("✏️ Processing book editing request")
            
            edit_instruction = state.get('edit_instruction', '')
            edit_type = state.get('edit_type', 'content')
            book_content = state.get('book_content', '')
            
            if not edit_instruction:
                return {
                    "error_message": "No edit instruction provided",
                    "processing_status": "edit_failed"
                }
            
            # Generate edited content based on instruction
            edit_prompt = f"""
            You are an expert editor for "{self.BOOK_TITLE}", a book about dog training philosophy.
            
            Edit type: {edit_type}
            Edit instruction: {edit_instruction}
            
            Original content (excerpt):
            {book_content[:3000]}...
            
            Please provide:
            1. Specific edits based on the instruction
            2. Explanation of changes made
            3. Improved version of the content
            4. Summary of editorial decisions
            
            Maintain the book's core philosophy and tone while implementing the requested changes.
            Focus on {edit_type} improvements.
            """
            
            response = self.chat_model.invoke([
                SystemMessage(content="You are a professional book editor specializing in dog training and philosophy books."),
                HumanMessage(content=edit_prompt)
            ])
            
            # Extract edited content and summary
            edited_response = response.content
            edit_summary = self._extract_edit_summary(edited_response)
            
            workflow_trace = state.get('workflow_trace', [])
            workflow_trace.append("book_editor_completed")
            
            return {
                "response_content": edited_response,
                "response_type": "edit",
                "edit_type": edit_type,
                "edited_content": edited_response,
                "edit_summary": edit_summary,
                "original_content": book_content[:3000],
                "confidence_score": 0.8,
                "processing_status": "edit_completed",
                "workflow_trace": workflow_trace,
                "tools_used": state.get('tools_used', []) + ["book_editor", "content_analyzer"],
                "agent_notes": {
                    **state.get('agent_notes', {}),
                    "editor": {
                        "edit_type": edit_type,
                        "instruction_length": len(edit_instruction),
                        "content_modified": True,
                        "editorial_approach": "philosophical_consistency"
                    }
                }
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Book editor failed: {str(e)}")
            return {
                "error_message": f"Editing failed: {str(e)}",
                "processing_status": "edit_failed"
            }
    
    def _book_downloader_agent(self, state: BookManagementState) -> Dict[str, Any]:
        """Handle book download operations in various formats"""
        try:
            current_app.logger.info("⬇️ Processing book download request")
            
            download_format = state.get('download_format', 'pdf')
            
            if download_format == 'pdf':
                download_url = self.BOOK_S3_URL
                response_content = f"""
                📚 **{self.BOOK_TITLE}** - PDF Download
                
                Your download is ready! Click the link below to download the book:
                
                🔗 [Download PDF]({download_url})
                
                **Book Information:**
                - Title: {self.BOOK_TITLE}
                - Format: PDF
                - Source: Original Master Copy
                - Access: Full public access for all users
                
                **Reading Tips:**
                - Use a PDF reader for best experience
                - Bookmark important sections
                - Take notes while reading
                - Come back to chat about what you've learned!
                
                Enjoy your reading journey! 🐕📖
                """
            else:
                # For other formats, provide conversion information
                response_content = f"""
                📚 **{self.BOOK_TITLE}** - Format Conversion
                
                The book is currently available in PDF format. 
                
                **Available:** PDF (Original)
                **Requested:** {download_format.upper()}
                
                🔗 [Download PDF]({self.BOOK_S3_URL})
                
                **Format Conversion Options:**
                - Use online PDF converters for EPUB/TXT
                - Many e-readers can open PDF files directly
                - PDF preserves original formatting and layout
                
                Would you like help with format conversion or reading recommendations?
                """
            
            workflow_trace = state.get('workflow_trace', [])
            workflow_trace.append("book_downloader_completed")
            
            return {
                "response_content": response_content,
                "response_type": "download",
                "download_format": download_format,
                "download_url": self.BOOK_S3_URL,
                "confidence_score": 1.0,
                "processing_status": "download_completed",
                "workflow_trace": workflow_trace,
                "tools_used": state.get('tools_used', []) + ["book_downloader", "s3_access"],
                "agent_notes": {
                    **state.get('agent_notes', {}),
                    "downloader": {
                        "format_requested": download_format,
                        "format_available": "pdf",
                        "download_ready": True,
                        "public_access": True
                    }
                }
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Book downloader failed: {str(e)}")
            return {
                "error_message": f"Download failed: {str(e)}",
                "processing_status": "download_failed"
            }
    
    def _content_analyzer_agent(self, state: BookManagementState) -> Dict[str, Any]:
        """Analyze book content and extract insights"""
        try:
            current_app.logger.info("🔍 Analyzing book content")
            
            book_content = state.get('book_content', '')
            response_content = state.get('response_content', '')
            operation = state.get('operation', 'read')
            
            # Generate insights based on the operation and content
            insights = self._generate_content_insights(book_content, operation, response_content)
            
            workflow_trace = state.get('workflow_trace', [])
            workflow_trace.append("content_analyzer_completed")
            
            return {
                "response_content": response_content,  # 🔥 CRITICAL: Preserve response from previous agent
                "response_type": state.get('response_type', operation),
                "confidence_score": state.get('confidence_score', 0.8),
                "relevant_sections": state.get('relevant_sections', []),
                "reading_position": state.get('reading_position', {}),
                "edit_summary": state.get('edit_summary'),
                "download_url": state.get('download_url'),
                "insights": insights,
                "processing_status": "analysis_completed",
                "workflow_trace": workflow_trace,
                "tools_used": state.get('tools_used', []) + ["content_analyzer"],
                "agent_notes": {
                    **state.get('agent_notes', {}),
                    "analyzer": {
                        "operation_analyzed": operation,
                        "insights_generated": len(insights),
                        "analysis_depth": "comprehensive"
                    }
                }
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Content analyzer failed: {str(e)}")
            return {
                "error_message": f"Analysis failed: {str(e)}",
                "processing_status": "analysis_failed"
            }
    
    def _response_generator_agent(self, state: BookManagementState) -> Dict[str, Any]:
        """Generate final response with suggestions and follow-ups"""
        try:
            current_app.logger.info("📝 Generating final response")
            
            response_content = state.get('response_content', '')
            operation = state.get('operation', 'read')
            insights = state.get('insights', [])
            
            # Generate follow-up suggestions based on operation
            suggestions = self._generate_operation_suggestions(operation, response_content)
            
            workflow_trace = state.get('workflow_trace', [])
            workflow_trace.append("response_generator_completed")
            
            return {
                "response_content": response_content,  # 🔥 CRITICAL: Preserve final response
                "response_type": state.get('response_type', operation),
                "confidence_score": state.get('confidence_score', 0.8),
                "relevant_sections": state.get('relevant_sections', []),
                "reading_position": state.get('reading_position', {}),
                "edit_summary": state.get('edit_summary'),
                "download_url": state.get('download_url'),
                "insights": state.get('insights', []),
                "suggestions": suggestions,
                "processing_status": "response_generated",
                "workflow_trace": workflow_trace,
                "tools_used": state.get('tools_used', []) + ["response_generator"],
                "agent_notes": {
                    **state.get('agent_notes', {}),
                    "response_generator": {
                        "suggestions_count": len(suggestions),
                        "operation_type": operation,
                        "response_ready": True
                    }
                }
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Response generator failed: {str(e)}")
            return {
                "error_message": f"Response generation failed: {str(e)}",
                "processing_status": "response_failed"
            }
    
    # Helper methods
    
    def _load_book_content(self) -> str:
        """Load book content from S3 or cache"""
        try:
            # Try to download and extract content from the PDF
            response = requests.get(self.BOOK_S3_URL, timeout=30)
            if response.status_code == 200:
                # Save temporarily and extract text
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                    temp_file.write(response.content)
                    temp_file_path = temp_file.name
                
                # Extract text using PyMuPDF
                doc = fitz.open(temp_file_path)
                content = ""
                for page in doc:
                    content += page.get_text()
                doc.close()
                
                # Clean up temp file
                os.unlink(temp_file_path)
                
                return content
            
            else:
                # Fallback content if download fails
                return f"The Way of the Dog Anahata - A comprehensive guide to understanding and training dogs through ancient wisdom and modern techniques."
                
        except Exception as e:
            current_app.logger.error(f"❌ Failed to load book content: {str(e)}")
            return f"The Way of the Dog Anahata - A comprehensive guide to understanding and training dogs through ancient wisdom and modern techniques."
    
    def _extract_relevant_sections(self, content: str, query: str, section_type: str = "general") -> List[Dict[str, Any]]:
        """Extract relevant sections from book content"""
        try:
            # Split content into sections
            sections = []
            if content:
                # Simple chunking for now - can be enhanced with chapter detection
                chunk_size = 1000
                chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
                
                for i, chunk in enumerate(chunks[:5]):  # Limit to first 5 sections
                    sections.append({
                        "section_id": f"section_{i+1}",
                        "title": f"Section {i+1}",
                        "content": chunk,
                        "relevance_score": 0.8,  # Placeholder scoring
                        "page_range": f"{i*3+1}-{(i+1)*3}"
                    })
            
            return sections
            
        except Exception as e:
            current_app.logger.error(f"❌ Failed to extract sections: {str(e)}")
            return []
    
    def _search_book_knowledge(self, query: str, book_content: str) -> str:
        """Search for relevant knowledge in the book using common knowledge base"""
        try:
            # Use common knowledge service
            knowledge_service = get_common_knowledge_service()
            
            if knowledge_service and knowledge_service.is_service_available():
                success, results = knowledge_service.search_common_knowledge(query, top_k=3)
                if success and results:
                    # Combine relevant content from knowledge base
                    relevant_content = []
                    for result in results:
                        content = result.get('content', '')
                        if content:
                            relevant_content.append(content)
                    
                    if relevant_content:
                        return '\n\n'.join(relevant_content)
            
            # Fallback to simple content search
            if query.lower() in book_content.lower():
                # Find relevant paragraphs
                paragraphs = book_content.split('\n\n')
                relevant = [p for p in paragraphs if query.lower() in p.lower()]
                return '\n\n'.join(relevant[:3])  # Return first 3 relevant paragraphs
            
            return book_content[:1500]  # Return beginning of book as fallback
            
        except Exception as e:
            current_app.logger.error(f"❌ Knowledge search failed: {str(e)}")
            return book_content[:1500]
    
    def _generate_chat_suggestions(self, query: str, content: str) -> List[str]:
        """Generate follow-up suggestions for chat"""
        base_suggestions = [
            "What are the key principles of dog training in this book?",
            "How does this book's approach differ from traditional training?",
            "Can you explain the concept of 'Anahata' in dog training?",
            "What practical exercises does the book recommend?",
            "How can I apply these teachings with my own dog?"
        ]
        
        return base_suggestions[:3]  # Return top 3 suggestions
    
    def _extract_edit_summary(self, edited_response: str) -> str:
        """Extract summary from edit response"""
        try:
            # Simple extraction - can be enhanced with structured parsing
            if "Summary:" in edited_response:
                summary_start = edited_response.find("Summary:")
                summary_section = edited_response[summary_start:summary_start+500]
                return summary_section
            return "Editing completed successfully with AI-powered improvements."
        except:
            return "Editing completed successfully."
    
    def _calculate_reading_progress(self, content: str, sections: List[Dict]) -> float:
        """Calculate reading progress percentage"""
        try:
            if not content or not sections:
                return 0.0
            
            total_length = len(content)
            sections_length = sum(len(section.get('content', '')) for section in sections)
            
            return min(100.0, (sections_length / total_length) * 100)
        except:
            return 0.0
    
    def _generate_content_insights(self, content: str, operation: str, response: str) -> List[str]:
        """Generate insights based on content and operation"""
        insights = []
        
        if operation == "read":
            insights = [
                "This book emphasizes the spiritual connection between humans and dogs",
                "Training techniques focus on understanding rather than control",
                "The 'Anahata' concept refers to heart-centered training approaches"
            ]
        elif operation == "chat":
            insights = [
                "User is exploring philosophical aspects of dog training",
                "Discussion centers on practical application of book concepts",
                "Knowledge sharing enhances understanding of training methods"
            ]
        elif operation == "edit":
            insights = [
                "AI editing improves clarity while preserving core message",
                "Editorial suggestions enhance readability and flow",
                "Content modifications align with book's philosophical foundation"
            ]
        elif operation == "download":
            insights = [
                "Book access facilitates deeper learning and reference",
                "PDF format preserves original layout and illustrations",
                "Download enables offline reading and note-taking"
            ]
        
        return insights
    
    def _generate_operation_suggestions(self, operation: str, response: str) -> List[str]:
        """Generate suggestions based on operation type"""
        suggestions = []
        
        if operation == "read":
            suggestions = [
                "Chat about specific concepts you found interesting",
                "Ask questions about training techniques mentioned",
                "Explore practical applications for your dog"
            ]
        elif operation == "chat":
            suggestions = [
                "Continue reading related chapters",
                "Ask about specific training scenarios",
                "Discuss implementation strategies"
            ]
        elif operation == "edit":
            suggestions = [
                "Review the original vs edited content",
                "Request additional editing perspectives",
                "Download the edited version for reference"
            ]
        elif operation == "download":
            suggestions = [
                "Start reading from the beginning",
                "Bookmark important sections",
                "Take notes as you read"
            ]
        
        return suggestions
    
    # Main processing method
    def process_book_operation(self, user_id: int, operation: str, **kwargs) -> Dict[str, Any]:
        """Main method to process book operations through the LangGraph workflow"""
        
        try:
            current_app.logger.info(f"🚀 Starting book operation: {operation} for user {user_id}")
            
            # Initial state
            initial_state = {
                "messages": [HumanMessage(content=f"Process book operation: {operation}")],
                "user_id": user_id,
                "operation": operation,
                "book_title": self.BOOK_TITLE,
                "processing_status": "started",
                "workflow_trace": [],
                "tools_used": [],
                "agent_notes": {},
                "confidence_score": 0.0,
                "error_message": None
            }
            
            # Add operation-specific parameters
            initial_state.update(kwargs)
            
            # Run the book workflow
            config = {"thread_id": str(uuid.uuid4())}
            
            # Process through the book graph
            final_state = None
            all_states = []
            
            for step_output in self.graph.stream(initial_state, config):
                all_states.append(step_output)
                current_app.logger.info(f"Book processing step: {list(step_output.keys())}")
                # LangGraph stream returns dict with node_name -> state
                for node_name, state in step_output.items():
                    final_state = state  # Keep updating to get the latest state
            
            current_app.logger.info(f"🔍 Final state keys: {list(final_state.keys()) if final_state else 'None'}")
            current_app.logger.info(f"🔍 Response content present: {bool(final_state.get('response_content') if final_state else False)}")
            
            if final_state:
                # Extract final results
                result = {
                    'success': final_state.get('processing_status', '').endswith('_completed') or final_state.get('processing_status') == 'response_generated',
                    'operation': operation,
                    'response': final_state.get('response_content', ''),
                    'response_type': final_state.get('response_type', operation),
                    'confidence_score': final_state.get('confidence_score', 0.0),
                    'insights': final_state.get('insights', []),
                    'suggestions': final_state.get('suggestions', []),
                    'relevant_sections': final_state.get('relevant_sections', []),
                    'reading_position': final_state.get('reading_position', {}),
                    'download_url': final_state.get('download_url'),
                    'edit_summary': final_state.get('edit_summary'),
                    'tools_used': final_state.get('tools_used', []),
                    'workflow_trace': final_state.get('workflow_trace', []),
                    'error_message': final_state.get('error_message'),
                    'processing_status': final_state.get('processing_status', 'completed')
                }
                
                current_app.logger.info(f"✅ Book operation completed: {result['success']}")
                
                return result
            
            else:
                raise Exception("No final state received from book workflow")
                
        except Exception as e:
            current_app.logger.error(f"❌ Book operation failed: {str(e)}")
            return {
                'success': False,
                'operation': operation,
                'response': 'I apologize, but I encountered an issue processing your book request. Please try again.',
                'error_message': str(e),
                'processing_status': 'failed'
            }

    # Public API methods
    
    def read_book(self, user_id: int, query: str = None, page_number: int = None, chapter: str = None) -> Dict[str, Any]:
        """Read book content with navigation"""
        return self.process_book_operation(
            user_id=user_id,
            operation="read",
            query=query or "Show me the book content",
            page_number=page_number,
            chapter_requested=chapter
        )
    
    def chat_about_book(self, user_id: int, query: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Chat about book content"""
        return self.process_book_operation(
            user_id=user_id,
            operation="chat",
            query=query,
            conversation_history=conversation_history or []
        )
    
    def edit_book_content(self, user_id: int, edit_instruction: str, edit_type: str = "content") -> Dict[str, Any]:
        """Edit book content with AI"""
        return self.process_book_operation(
            user_id=user_id,
            operation="edit",
            edit_instruction=edit_instruction,
            edit_type=edit_type
        )
    
    def download_book(self, user_id: int, format: str = "pdf") -> Dict[str, Any]:
        """Download book in specified format"""
        return self.process_book_operation(
            user_id=user_id,
            operation="download",
            download_format=format
        )
    
    def get_book_info(self) -> Dict[str, Any]:
        """Get book information"""
        return {
            "title": self.BOOK_TITLE,
            "s3_url": self.BOOK_S3_URL,
            "s3_key": self.BOOK_S3_KEY,
            "available_operations": ["read", "chat", "edit", "download"],
            "supported_formats": ["pdf"],
            "public_access": True,
            "description": "A comprehensive guide to understanding and training dogs through ancient wisdom and modern techniques."
        } 