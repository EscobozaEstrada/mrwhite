import os
import uuid
import json
import logging
from typing import Dict, List, Optional, Tuple, Any, Literal
from datetime import datetime, timezone

# LangGraph and LangChain imports
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from typing_extensions import TypedDict

# Flask and internal imports
from flask import current_app
from app import db
from app.models.care_record import Document, KnowledgeBase
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.utils.file_handler import query_user_docs, store_enhanced_chat_message
from app.utils.s3_handler import upload_file_to_s3, get_s3_url

# Enhanced state for document chat with Context7 patterns
class DocumentChatState(MessagesState):
    """Enhanced state for document chat workflow following Context7 best practices"""
    user_id: int
    query: str
    conversation_id: Optional[int]
    thread_id: Optional[str]
    
    # Intent and routing
    intent: str
    intent_confidence: float
    routing_decision: str
    
    # Document search and retrieval
    search_query: str
    documents_found: List[Dict[str, Any]]
    selected_document: Optional[Dict[str, Any]]
    document_content: str
    
    # Document retrieval by name
    document_name_query: str
    name_search_results: List[Dict[str, Any]]
    exact_document_match: Optional[Dict[str, Any]]
    
    # Response generation
    response_content: str
    response_type: str
    confidence_score: float
    
    # Context and memory
    chat_context: Dict[str, Any]
    conversation_history: List[Dict[str, Any]]
    
    # Agent communication
    agent_notes: Dict[str, Any]
    tools_used: List[str]
    workflow_trace: List[str]
    
    # Follow-up and suggestions
    follow_up_suggestions: List[str]
    related_documents: List[Dict[str, Any]]
    
    # Error handling
    error_message: Optional[str]
    processing_status: str


class EnhancedDocumentChatAgents:
    """Enhanced document chat agents with Context7 LangGraph patterns"""
    
    def __init__(self):
        self.chat_model = ChatOpenAI(
            model="gpt-4",
            temperature=0.3,
            max_tokens=2000
        )
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

        self.checkpointer = MemorySaver()
        self.graph = None
        self._initialize_chat_graph()
    
    def _initialize_chat_graph(self):
        """Initialize the document chat LangGraph workflow"""
        try:
            self._build_chat_graph()
            # Use Flask logger if available, otherwise use Python logging
            try:
                current_app.logger.info("✅ Enhanced document chat graph initialized successfully")
            except RuntimeError:
                logging.info("✅ Enhanced document chat graph initialized successfully")
        except Exception as e:
            # Use Flask logger if available, otherwise use Python logging
            try:
                current_app.logger.error(f"❌ Error initializing enhanced document chat graph: {str(e)}")
            except RuntimeError:
                logging.error(f"❌ Error initializing enhanced document chat graph: {str(e)}")
            raise
    
    def _build_chat_graph(self):
        """Build the enhanced LangGraph state graph for document chat"""
        
        builder = StateGraph(DocumentChatState)
        
        # Add specialized chat agents
        builder.add_node("intent_analyzer", self._intent_analyzer_agent)
        builder.add_node("document_searcher", self._document_searcher_agent)
        builder.add_node("name_retriever", self._name_retriever_agent)
        builder.add_node("document_analyzer", self._document_analyzer_agent)
        builder.add_node("content_synthesizer", self._content_synthesizer_agent)
        builder.add_node("response_generator", self._response_generator_agent)
        builder.add_node("context_manager", self._context_manager_agent)
        builder.add_node("suggestion_generator", self._suggestion_generator_agent)
        
        # Define conditional routing based on intent
        builder.add_edge(START, "intent_analyzer")
        builder.add_conditional_edges(
            "intent_analyzer",
            self._route_by_intent,
            {
                "document_search": "document_searcher",
                "document_retrieval": "name_retriever",
                "general_chat": "content_synthesizer"
            }
        )
        
        # Document search flow
        builder.add_edge("document_searcher", "document_analyzer")
        builder.add_edge("document_analyzer", "content_synthesizer")
        
        # Name retrieval flow
        builder.add_edge("name_retriever", "document_analyzer")
        
        # Common flow to response generation
        builder.add_edge("content_synthesizer", "response_generator")
        builder.add_edge("response_generator", "context_manager")
        builder.add_edge("context_manager", "suggestion_generator")
        builder.add_edge("suggestion_generator", END)
        
        # Compile the graph
        self.graph = builder.compile(checkpointer=self.checkpointer)
    
    def _route_by_intent(self, state: DocumentChatState) -> str:
        """Route based on user intent analysis"""
        intent = state.get('intent', 'general_chat')
        confidence = state.get('intent_confidence', 0.0)
        
        if intent == 'document_retrieval' and confidence > 0.7:
            return "document_retrieval"
        elif intent == 'document_search' and confidence > 0.6:
            return "document_search"
        else:
            return "general_chat"
    
    def _intent_analyzer_agent(self, state: DocumentChatState) -> DocumentChatState:
        """Agent to analyze user intent and determine appropriate routing"""
        
        try:
            current_app.logger.info("🎯 Intent Analyzer Agent processing")
            
            query = state['query']
            
            # Intent analysis with Context7 patterns
            intent_prompt = f"""
            You are an expert intent analyzer for a document chat system specializing in pet care.
            
            Analyze the user's query and determine their intent:
            
            User Query: "{query}"
            
            Intent Categories:
            1. "document_retrieval" - User wants to find a specific document by name (e.g., "show me the vet report", "find Max's vaccination record")
            2. "document_search" - User wants to search for information across documents (e.g., "what medications is my dog taking?", "show me health records")
            3. "general_chat" - User wants to chat about document content or ask general questions
            
            Provide your analysis in JSON format:
            {{
                "intent": "document_retrieval|document_search|general_chat",
                "confidence": 0.95,
                "reasoning": "Why you chose this intent",
                "key_phrases": ["phrase1", "phrase2"],
                "document_indicators": ["document name", "document type"],
                "search_terms": ["search term1", "search term2"]
            }}
            """
            
            response = self.chat_model.invoke([
                SystemMessage(content="You are an intent analysis expert. Always respond with valid JSON."),
                HumanMessage(content=intent_prompt)
            ])
            
            try:
                intent_analysis = json.loads(response.content)
            except json.JSONDecodeError:
                intent_analysis = {
                    "intent": "general_chat",
                    "confidence": 0.5,
                    "reasoning": "Failed to parse intent",
                    "key_phrases": [],
                    "document_indicators": [],
                    "search_terms": []
                }
            
            # Extract specific queries for different intents
            search_query = query
            document_name_query = query
            
            if intent_analysis['intent'] == 'document_retrieval':
                # Extract document name from query
                document_name_query = self._extract_document_name(query, intent_analysis)
            elif intent_analysis['intent'] == 'document_search':
                # Extract search terms
                search_query = self._extract_search_terms(query, intent_analysis)
            
            workflow_trace = state.get('workflow_trace', [])
            workflow_trace.append(f"✅ Intent Analyzer: {intent_analysis['intent']} ({intent_analysis['confidence']:.2f})")
            
            current_app.logger.info(f"✅ Intent analyzed: {intent_analysis['intent']} ({intent_analysis['confidence']:.2f})")
            
            return {
                **state,
                "intent": intent_analysis['intent'],
                "intent_confidence": intent_analysis['confidence'],
                "search_query": search_query,
                "document_name_query": document_name_query,
                "processing_status": "intent_analyzed",
                "agent_notes": {
                    **state.get('agent_notes', {}),
                    "intent_analysis": intent_analysis
                },
                "workflow_trace": workflow_trace
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Intent analysis failed: {str(e)}")
            return {
                **state,
                "intent": "general_chat",
                "intent_confidence": 0.0,
                "processing_status": "intent_failed",
                "error_message": str(e)
            }
    
    def _document_searcher_agent(self, state: DocumentChatState) -> DocumentChatState:
        """Agent to search for documents based on content similarity"""
        
        try:
            current_app.logger.info("🔍 Document Searcher Agent processing")
            
            user_id = state['user_id']
            search_query = state['search_query']
            
            # Search for relevant documents using enhanced vector search
            search_results = self._enhanced_vector_search(user_id, search_query)
            
            # Process and rank results
            processed_results = []
            for result in search_results:
                processed_results.append({
                    "document_id": result.get('document_id'),
                    "filename": result.get('filename'),
                    "content": result.get('content', ''),
                    "relevance_score": result.get('score', 0.0),
                    "metadata": result.get('metadata', {}),
                    "document_type": result.get('metadata', {}).get('document_type', 'unknown')
                })
            
            # Sort by relevance score
            processed_results.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            workflow_trace = state.get('workflow_trace', [])
            workflow_trace.append(f"✅ Document Searcher: Found {len(processed_results)} relevant documents")
            
            current_app.logger.info(f"✅ Document search completed: {len(processed_results)} documents found")
            
            return {
                **state,
                "documents_found": processed_results,
                "processing_status": "documents_searched",
                "tools_used": state.get('tools_used', []) + ["vector_search"],
                "workflow_trace": workflow_trace
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Document search failed: {str(e)}")
            return {
                **state,
                "documents_found": [],
                "processing_status": "search_failed",
                "error_message": str(e)
            }
    
    def _name_retriever_agent(self, state: DocumentChatState) -> DocumentChatState:
        """Agent to retrieve specific documents by name"""
        
        try:
            current_app.logger.info("📋 Name Retriever Agent processing")
            
            user_id = state['user_id']
            document_name_query = state['document_name_query']
            
            # Search for documents by name in database
            name_search_results = self._search_documents_by_name(user_id, document_name_query)
            
            # Find the best match
            exact_match = None
            if name_search_results:
                # Score matches based on name similarity
                scored_results = []
                for doc in name_search_results:
                    similarity_score = self._calculate_name_similarity(document_name_query, doc['original_filename'])
                    scored_results.append({
                        **doc,
                        "name_similarity": similarity_score
                    })
                
                # Sort by similarity and get the best match
                scored_results.sort(key=lambda x: x['name_similarity'], reverse=True)
                exact_match = scored_results[0] if scored_results and scored_results[0]['name_similarity'] > 0.5 else None
            
            workflow_trace = state.get('workflow_trace', [])
            workflow_trace.append(f"✅ Name Retriever: Found {len(name_search_results)} name matches")
            
            current_app.logger.info(f"✅ Name retrieval completed: {len(name_search_results)} matches found")
            
            return {
                **state,
                "name_search_results": name_search_results,
                "exact_document_match": exact_match,
                "processing_status": "name_retrieved",
                "tools_used": state.get('tools_used', []) + ["name_search"],
                "workflow_trace": workflow_trace
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Name retrieval failed: {str(e)}")
            return {
                **state,
                "name_search_results": [],
                "exact_document_match": None,
                "processing_status": "name_retrieval_failed",
                "error_message": str(e)
            }
    
    def _document_analyzer_agent(self, state: DocumentChatState) -> DocumentChatState:
        """Agent to analyze and select the most relevant document"""
        
        try:
            current_app.logger.info("📊 Document Analyzer Agent processing")
            
            intent = state['intent']
            query = state['query']
            
            # Check if we already have document content in the state
            document_content = state.get('document_content', '')
            selected_document = state.get('selected_document')
            
            # If we already have document content but no selected document, create one
            if document_content and not selected_document:
                selected_document = {
                    "filename": "uploaded_document.pdf",
                    "user_id": state['user_id'],
                    "content": document_content[:100] + "..." # Just store a preview
                }
                current_app.logger.info(f"✅ Created document object for existing content ({len(document_content)} chars)")
            
            # If we have a selected document but no content, get the content
            if selected_document and not document_content:
                document_content = self._get_document_content(selected_document)
                current_app.logger.info(f"✅ Retrieved document content: {len(document_content)} characters")
                
                # If still no content, try a direct search
                if not document_content or len(document_content) < 100:
                    filename = selected_document.get('filename', '')
                    if filename:
                        try:
                            success, docs = query_user_docs(filename, state['user_id'], top_k=1)
                            if success and docs and len(docs) > 0:
                                doc = docs[0]
                                if hasattr(doc, 'page_content') and doc.page_content:
                                    document_content = doc.page_content
                                    current_app.logger.info(f"✅ Retrieved document content from search: {len(document_content)} characters")
                        except Exception as e:
                            current_app.logger.error(f"❌ Search fallback failed: {str(e)}")
            
            # If we still don't have a selected document, try to find one
            if not selected_document:
                if intent == 'document_retrieval':
                    # Use exact match from name retrieval
                    exact_match = state.get('exact_document_match')
                    if exact_match:
                        selected_document = exact_match
                        if not document_content:
                            document_content = self._get_document_content(exact_match)
                    
                elif intent == 'document_search':
                    # Select best document from search results
                    documents_found = state.get('documents_found', [])
                    if documents_found:
                        # Use AI to select the most relevant document
                        selected_document = self._ai_select_document(query, documents_found)
                        if selected_document and not document_content:
                            document_content = self._get_document_content(selected_document)
            
            workflow_trace = state.get('workflow_trace', [])
            workflow_trace.append(f"✅ Document Analyzer: Selected {selected_document['filename'] if selected_document else 'no document'}")
            
            current_app.logger.info(f"✅ Document analysis completed: {selected_document['filename'] if selected_document else 'no document'}")
            
            return {
                **state,
                "selected_document": selected_document,
                "document_content": document_content,
                "processing_status": "document_analyzed",
                "workflow_trace": workflow_trace
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Document analysis failed: {str(e)}")
            return {
                **state,
                "selected_document": None,
                "document_content": "",
                "processing_status": "analysis_failed",
                "error_message": str(e)
            }
    
    def _content_synthesizer_agent(self, state: DocumentChatState) -> DocumentChatState:
        """Agent to synthesize content from documents based on user query"""
        
        try:
            current_app.logger.info("🔄 Content Synthesizer Agent processing")
            
            query = state['query']
            document_content = state.get('document_content', '')
            selected_document = state.get('selected_document')
            chat_context = state.get('chat_context', {})
            
            # Log document content length for debugging
            content_length = len(document_content) if document_content else 0
            current_app.logger.info(f"📝 Document content length: {content_length} characters")
            
            # If we have a selected document but no content, try to get content directly
            if selected_document and not document_content:
                current_app.logger.info(f"🔄 No document content, attempting direct retrieval")
                document_content = self._get_document_content(selected_document)
                content_length = len(document_content) if document_content else 0
                current_app.logger.info(f"📝 After direct retrieval, document content length: {content_length} characters")
                
                # If still no content, try a direct search as fallback
                if not document_content or content_length < 100:
                    filename = selected_document.get('filename', '')
                    if filename:
                        current_app.logger.info(f"⚠️ Document content still too short, trying search fallback")
                        try:
                            success, docs = query_user_docs(filename, state['user_id'], top_k=1)
                            if success and docs and len(docs) > 0:
                                doc = docs[0]
                                if hasattr(doc, 'page_content') and doc.page_content:
                                    document_content = doc.page_content
                                    content_length = len(document_content)
                                    current_app.logger.info(f"✅ Retrieved document content from search: {content_length} characters")
                        except Exception as e:
                            current_app.logger.error(f"❌ Search fallback failed: {str(e)}")
            
            # IMPROVED: Always use document-focused response for document queries
            # Synthesize content based on available information
            if document_content:
                document_name = selected_document.get('filename', 'the document') if selected_document else 'the document'
                
                synthesis_prompt = f"""
                You are a document analysis expert.
                
                User Query: "{query}"
                
                Document Name: {document_name}
                
                Document Content: {document_content[:8000]}
                
                Document Information: {json.dumps(selected_document, indent=2) if selected_document else "No specific document selected"}
                
                The user is asking about this document. Please provide:
                1. A comprehensive response that directly addresses their query
                2. If they're asking for a summary, provide a detailed summary of the document
                3. Key points and insights from the document relevant to their query
                4. Any relevant information that would be useful to the user
                
                Format your response as a well-structured answer with sections and bullet points where appropriate.
                Focus ONLY on the document content - do NOT add any information about pet care unless it's explicitly in the document.
                Do NOT include any disclaimers about being a pet care expert or AI assistant.
                
                Response format:
                {{
                    "response": "Your comprehensive response here",
                    "document_referenced": true,
                    "confidence": 0.95,
                    "key_points": ["Point 1", "Point 2"],
                    "source_document": "{document_name}"
                }}
                """
            else:
                # No document content available
                current_app.logger.warning("⚠️ No document content available for synthesis")
                
                # Try one more time to get the document content if we have a selected document
                if selected_document:
                    current_app.logger.info("🔄 Final attempt to retrieve document content")
                    document_content = self._get_document_content(selected_document)
                    content_length = len(document_content) if document_content else 0
                    current_app.logger.info(f"📝 Final retrieval attempt result: {content_length} characters")
                    
                    if document_content:
                        # We got content on the final try, use it
                        document_name = selected_document.get('filename', 'the document') if selected_document else 'the document'
                        synthesis_prompt = f"""
                        You are a document analysis expert.
                        
                        User Query: "{query}"
                        
                        Document Name: {document_name}
                        
                        Document Content: {document_content[:8000]}
                        
                        Document Information: {json.dumps(selected_document, indent=2) if selected_document else "No specific document selected"}
                        
                        The user is asking about this document. Please provide:
                        1. A comprehensive response that directly addresses their query
                        2. If they're asking for a summary, provide a detailed summary of the document
                        3. Key points and insights from the document relevant to their query
                        4. Any relevant information that would be useful to the user
                        
                        Format your response as a well-structured answer with sections and bullet points where appropriate.
                        Focus ONLY on the document content - do NOT add any information about pet care unless it's explicitly in the document.
                        Do NOT include any disclaimers about being a pet care expert or AI assistant.
                        
                        Response format:
                        {{
                            "response": "Your comprehensive response here",
                            "document_referenced": true,
                            "confidence": 0.95,
                            "key_points": ["Point 1", "Point 2"],
                            "source_document": "{document_name}"
                        }}
                        """
                
                # Fallback response if no document content
                if not document_content:
                    document_name = selected_document.get('filename', 'the requested document') if selected_document else 'the requested document'
                    
                    fallback_prompt = f"""
                    You are a document analysis expert.
                    
                    User Query: "{query}"
                    
                    Unfortunately, I was unable to retrieve the content of {document_name}. The document might be:
                    1. In a format that couldn't be processed
                    2. Empty or corrupted
                    3. Not properly uploaded or stored
                    
                    Please provide a helpful response that:
                    1. Acknowledges the issue with retrieving the document content
                    2. Suggests possible solutions (re-uploading, trying a different format)
                    3. Offers alternative ways to help the user
                    
                    Do NOT include any disclaimers about being a pet care expert or AI assistant.
                    
                    Response format:
                    {{
                        "response": "Your helpful response here",
                        "document_referenced": true,
                        "confidence": 0.5,
                        "key_points": ["Point 1", "Point 2"],
                        "source_document": "{document_name}"
                    }}
                    """
                    
                    synthesis_prompt = fallback_prompt
            
            response = self.chat_model.invoke([
                SystemMessage(content="You are a document analysis expert. Always respond with valid JSON."),
                HumanMessage(content=synthesis_prompt)
            ])
            
            try:
                synthesis_result = json.loads(response.content)
            except json.JSONDecodeError:
                synthesis_result = {
                    "response": "I can help you with your pet care question. Please provide more details.",
                    "document_referenced": False,
                    "confidence": 0.5,
                    "key_points": [],
                    "source_document": ""
                }
            
            workflow_trace = state.get('workflow_trace', [])
            workflow_trace.append(f"✅ Content Synthesizer: Generated response ({synthesis_result['confidence']:.2f})")
            
            current_app.logger.info(f"✅ Content synthesis completed: {synthesis_result['confidence']:.2f} confidence")
            
            return {
                **state,
                "response_content": synthesis_result['response'],
                "confidence_score": synthesis_result['confidence'],
                "processing_status": "content_synthesized",
                "agent_notes": {
                    **state.get('agent_notes', {}),
                    "synthesis": synthesis_result
                },
                "workflow_trace": workflow_trace
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Content synthesis failed: {str(e)}")
            return {
                **state,
                "response_content": "I apologize, but I'm having trouble processing your request. Please try again.",
                "confidence_score": 0.0,
                "processing_status": "synthesis_failed",
                "error_message": str(e)
            }
    
    def _response_generator_agent(self, state: DocumentChatState) -> DocumentChatState:
        """Agent to generate the final response"""
        
        try:
            current_app.logger.info("💬 Response Generator Agent processing")
            
            response_content = state.get('response_content', '')
            selected_document = state.get('selected_document')
            intent = state.get('intent', 'general_chat')
            
            # Enhance response based on intent
            if intent == 'document_retrieval' and selected_document:
                response_type = "document_retrieval"
                # Add document download/view options
                enhanced_response = f"{response_content}\n\n📄 **Document Found**: {selected_document['filename']}\n"
                if selected_document.get('s3_url'):
                    enhanced_response += f"📎 [View Document]({selected_document['s3_url']})\n"
                
            elif intent == 'document_search' and selected_document:
                response_type = "document_search"
                enhanced_response = f"{response_content}\n\n📄 **Source**: {selected_document['filename']}"
                
            else:
                response_type = "general_chat"
                enhanced_response = response_content
            
            workflow_trace = state.get('workflow_trace', [])
            workflow_trace.append(f"✅ Response Generator: Generated {response_type} response")
            
            current_app.logger.info(f"✅ Response generation completed: {response_type}")
            
            return {
                **state,
                "response_content": enhanced_response,
                "response_type": response_type,
                "processing_status": "response_generated",
                "workflow_trace": workflow_trace
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Response generation failed: {str(e)}")
            return {
                **state,
                "response_content": "I apologize, but I'm having trouble generating a response. Please try again.",
                "response_type": "error",
                "processing_status": "response_failed",
                "error_message": str(e)
            }
    
    def _context_manager_agent(self, state: DocumentChatState) -> DocumentChatState:
        """Agent to manage conversation context and memory"""
        
        try:
            current_app.logger.info("🧠 Context Manager Agent processing")
            
            user_id = state['user_id']
            conversation_id = state.get('conversation_id')
            query = state['query']
            response_content = state.get('response_content', '')
            selected_document = state.get('selected_document')
            
            # Store the conversation in enhanced chat history
            if conversation_id:
                # Ensure document_name is never null
                document_name = selected_document['filename'] if selected_document else "unknown_document"
                
                success = store_enhanced_chat_message(
                    user_id=user_id,
                    message_content=f"Q: {query}\nA: {response_content}",
                    message_metadata={
                        "conversation_id": conversation_id,
                        "document_referenced": selected_document is not None,
                        "document_name": document_name,
                        "intent": state.get('intent', 'general_chat'),
                        "confidence": state.get('confidence_score', 0.0),
                        "tools_used": state.get('tools_used', [])
                    }
                )
                
                if success:
                    workflow_trace = state.get('workflow_trace', [])
                    workflow_trace.append("✅ Context Manager: Conversation saved")
                    
                    current_app.logger.info("✅ Context management completed: Conversation saved")
                    
                    return {
                        **state,
                        "processing_status": "context_managed",
                        "workflow_trace": workflow_trace
                    }
            
            # If no conversation_id, just update status
            workflow_trace = state.get('workflow_trace', [])
            workflow_trace.append("✅ Context Manager: No conversation to save")
            
            return {
                **state,
                "processing_status": "context_managed",
                "workflow_trace": workflow_trace
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Context management failed: {str(e)}")
            return {
                **state,
                "processing_status": "context_failed",
                "error_message": str(e)
            }
    
    def _suggestion_generator_agent(self, state: DocumentChatState) -> DocumentChatState:
        """Agent to generate follow-up suggestions and related documents"""
        
        try:
            current_app.logger.info("💡 Suggestion Generator Agent processing")
            
            query = state['query']
            intent = state.get('intent', 'general_chat')
            selected_document = state.get('selected_document')
            user_id = state['user_id']
            
            # Generate follow-up suggestions
            suggestions_prompt = f"""
            You are a document analysis expert generating follow-up suggestions.
            
            User Query: "{query}"
            Intent: {intent}
            Document Used: {selected_document['filename'] if selected_document else 'None'}
            
            Generate 3-5 helpful follow-up suggestions related to the document that would be valuable to the user:
            
            Format as JSON:
            {{
                "suggestions": [
                    "Follow-up suggestion 1",
                    "Follow-up suggestion 2",
                    "Follow-up suggestion 3"
                ],
                "related_topics": ["topic1", "topic2", "topic3"]
            }}
            """
            
            response = self.chat_model.invoke([
                SystemMessage(content="You are a document analysis expert. Always respond with valid JSON."),
                HumanMessage(content=suggestions_prompt)
            ])
            
            try:
                suggestions_result = json.loads(response.content)
            except json.JSONDecodeError:
                suggestions_result = {
                    "suggestions": [
                        "Would you like to know more about this topic?",
                        "Do you have other questions about your pet's care?",
                        "Would you like to see related documents?"
                    ],
                    "related_topics": []
                }
            
            # Find related documents
            related_documents = []
            if suggestions_result.get('related_topics'):
                for topic in suggestions_result['related_topics'][:3]:  # Limit to 3 topics
                    try:
                        success, docs = query_user_docs(topic, user_id, top_k=2)
                        if success and docs:
                            # Process each document properly
                            for doc in docs:
                                try:
                                    # Handle Document objects from langchain
                                    if hasattr(doc, 'page_content') and hasattr(doc, 'metadata'):
                                        related_documents.append({
                                            "document_id": doc.metadata.get('id', ''),
                                            "filename": doc.metadata.get('source', '').split('/')[-1],
                                            "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                                            "score": 0.8,  # Default score
                                            "metadata": doc.metadata
                                        })
                                except Exception as e:
                                    current_app.logger.error(f"Error processing document in suggestion generator: {str(e)}")
                    except Exception as e:
                        current_app.logger.error(f"Error in suggestion search: {str(e)}")
            
            workflow_trace = state.get('workflow_trace', [])
            workflow_trace.append(f"✅ Suggestion Generator: Generated {len(suggestions_result['suggestions'])} suggestions")
            
            current_app.logger.info(f"✅ Suggestion generation completed: {len(suggestions_result['suggestions'])} suggestions")
            
            return {
                **state,
                "follow_up_suggestions": suggestions_result['suggestions'],
                "related_documents": related_documents,
                "processing_status": "suggestions_generated",
                "workflow_trace": workflow_trace
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Suggestion generation failed: {str(e)}")
            return {
                **state,
                "follow_up_suggestions": [],
                "related_documents": [],
                "processing_status": "suggestions_failed",
                "error_message": str(e)
            }
    
    # Helper methods
    def _enhanced_vector_search(self, user_id: int, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Enhanced vector search with better scoring"""
        try:
            # Use existing vector search function
            success, results = query_user_docs(query, user_id, top_k=limit)
            
            if not success:
                current_app.logger.warning(f"⚠️ Vector search failed for query: {query}")
                return []
                
            # Enhanced processing of results
            enhanced_results = []
            for result in results:
                enhanced_results.append({
                    "document_id": result.get('document_id'),
                    "filename": result.get('filename', ''),
                    "content": result.get('content', ''),
                    "score": result.get('score', 0.0),
                    "metadata": result.get('metadata', {})
                })
            
            return enhanced_results
            
        except Exception as e:
            current_app.logger.error(f"Enhanced vector search failed: {str(e)}")
            return []
    
    def _search_documents_by_name(self, user_id: int, name_query: str) -> List[Dict[str, Any]]:
        """Search for documents by name in database"""
        try:
            # Search in database for documents with similar names
            documents = Document.query.filter(
                Document.user_id == user_id,
                Document.original_filename.ilike(f"%{name_query}%")
            ).all()
            
            results = []
            for doc in documents:
                results.append({
                    "id": doc.id,
                    "filename": doc.filename,
                    "original_filename": doc.original_filename,
                    "file_type": doc.file_type,
                    "s3_url": doc.s3_url,
                    "s3_key": doc.s3_key,
                    "content_summary": doc.content_summary,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    "metadata": doc.meta_data or {}
                })
            
            return results
            
        except Exception as e:
            current_app.logger.error(f"Database document search failed: {str(e)}")
            return []
    
    def _calculate_name_similarity(self, query: str, filename: str) -> float:
        """Calculate similarity between query and filename"""
        try:
            # Simple similarity calculation
            query_lower = query.lower()
            filename_lower = filename.lower()
            
            # Check for exact match
            if query_lower in filename_lower:
                return 1.0
            
            # Check for partial matches
            query_words = query_lower.split()
            filename_words = filename_lower.split()
            
            matches = 0
            for word in query_words:
                for fname_word in filename_words:
                    if word in fname_word or fname_word in word:
                        matches += 1
                        break
            
            return matches / len(query_words) if query_words else 0.0
            
        except Exception as e:
            current_app.logger.error(f"Name similarity calculation failed: {str(e)}")
            return 0.0
    
    def _ai_select_document(self, query: str, documents: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Use AI to select the most relevant document"""
        try:
            if not documents:
                return None
            
            # If only one document, return it
            if len(documents) == 1:
                return documents[0]
            
            # Use AI to select the best document
            selection_prompt = f"""
            Select the most relevant document for the user's query.
            
            Query: "{query}"
            
            Available Documents:
            {json.dumps([{"filename": doc["filename"], "relevance_score": doc["relevance_score"], "document_type": doc["document_type"]} for doc in documents], indent=2)}
            
            Return the index (0-based) of the best document:
            {{"selected_index": 0, "reasoning": "Why this document is best"}}
            """
            
            response = self.chat_model.invoke([
                SystemMessage(content="You are a document selection expert. Always respond with valid JSON."),
                HumanMessage(content=selection_prompt)
            ])
            
            try:
                selection_result = json.loads(response.content)
                selected_index = selection_result.get('selected_index', 0)
                
                if 0 <= selected_index < len(documents):
                    return documents[selected_index]
                else:
                    return documents[0]  # Fallback to first document
                    
            except json.JSONDecodeError:
                return documents[0]  # Fallback to first document
                
        except Exception as e:
            current_app.logger.error(f"AI document selection failed: {str(e)}")
            return documents[0] if documents else None
    
    def _get_document_content(self, document: Dict[str, Any]) -> str:
        """Get full content of a document"""
        try:
            # Log document details for debugging
            current_app.logger.info(f"🔍 Getting content for document: {document.get('filename', 'unknown')}")
            current_app.logger.info(f"🔍 Document details: {json.dumps({k: v for k, v in document.items() if k != 'content'}, indent=2)}")
            
            # First, check if document is None
            if document is None:
                current_app.logger.error("❌ Document is None")
                
                # Try to get document from conversation context
                try:
                    from app.utils.conversation_context_manager import get_context_manager
                    from flask import g
                    
                    if hasattr(g, 'user_id') and hasattr(g, 'conversation_id'):
                        user_id = g.user_id
                        conversation_id = g.conversation_id
                        
                        context_manager = get_context_manager()
                        document_context = context_manager.get_document_context(user_id, conversation_id)
                        
                        if document_context and document_context.get("document_names"):
                            filename = document_context.get("document_names")[0]
                            current_app.logger.info(f"✅ Found document name from context: {filename}")
                            
                            # Create a document dict to work with
                            document = {
                                "filename": filename,
                                "user_id": user_id
                            }
                except Exception as e:
                    current_app.logger.error(f"❌ Failed to get document from context: {str(e)}")
                    return "Document content could not be retrieved."
            
            # Try to find the document in the uploads directory - make this a higher priority
            try:
                import os
                import glob
                
                # Get the filename from the document
                filename = document.get('filename')
                if filename:
                    current_app.logger.info(f"🔍 Searching for document in uploads directory: {filename}")
                    
                    # Define possible upload directories
                    uploads_dirs = [
                        os.path.join(os.getcwd(), 'app', 'uploads'),
                        os.path.join(os.getcwd(), 'backend', 'app', 'uploads'),
                        os.path.join(os.getcwd(), 'uploads')
                    ]
                    
                    # Try different filename variations
                    potential_paths = []
                    for uploads_dir in uploads_dirs:
                        if os.path.exists(uploads_dir):
                            # Try exact filename
                            potential_paths.append(os.path.join(uploads_dir, filename))
                            
                            # Try without UUID prefix if present
                            if '_' in filename:
                                clean_filename = filename.split('_', 1)[1]
                                potential_paths.append(os.path.join(uploads_dir, clean_filename))
                            
                            # Try glob pattern matching
                            pattern = os.path.join(uploads_dir, f"*{os.path.splitext(filename)[1]}")
                            potential_paths.extend(glob.glob(pattern))
                    
                    for path in potential_paths:
                        if os.path.exists(path):
                            current_app.logger.info(f"✅ Found document in uploads directory: {path}")
                            file_extension = os.path.splitext(path)[1].lower()
                            
                            if file_extension == '.pdf':
                                extracted_text = self._extract_pdf_text(path)
                                if extracted_text and len(extracted_text) > 100:
                                    current_app.logger.info(f"✅ Extracted {len(extracted_text)} characters from local PDF")
                                    return extracted_text
                            elif file_extension in ['.doc', '.docx']:
                                extracted_text = self._extract_word_text(path)
                                if extracted_text and len(extracted_text) > 100:
                                    current_app.logger.info(f"✅ Extracted {len(extracted_text)} characters from local Word doc")
                                    return extracted_text
                            elif file_extension in ['.txt', '.csv', '.json', '.md']:
                                # Read text file directly
                                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                                    extracted_text = f.read()
                                    if extracted_text and len(extracted_text) > 100:
                                        current_app.logger.info(f"✅ Extracted {len(extracted_text)} characters from text file")
                                        return extracted_text
            except Exception as e:
                current_app.logger.error(f"❌ Failed to check uploads directory: {str(e)}")
            
            # Try to get content from extracted text field
            if document.get('extracted_text') and len(document.get('extracted_text', '')) > 100:
                current_app.logger.info(f"✅ Using extracted_text field with {len(document.get('extracted_text', ''))} characters")
                return document['extracted_text']
            
            # Try to get from database by ID
            if isinstance(document, Document):
                # Try to get content from extracted text first
                if document.extracted_text:
                    return document.extracted_text
                
                # If no extracted text, try to get from database
                db_doc = Document.query.get(document.id)
                if db_doc and db_doc.extracted_text:
                    return db_doc.extracted_text
                
                # Fallback to content summary
                return document.content_summary or ""
            
            # If document is a dict, handle differently
            else:
                # Try to get content from extracted text first
                if document.get('extracted_text'):
                    return document['extracted_text']
                
                # If no extracted text, try to get from database
                doc_id = document.get('id')
                if doc_id:
                    db_doc = Document.query.get(doc_id)
                    if db_doc and db_doc.extracted_text:
                        return db_doc.extracted_text
                
                # Fallback to content summary
                return document.get('content_summary', '')
            
        except Exception as e:
            current_app.logger.error(f"Document content retrieval failed: {str(e)}")
            return ""
    
    def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF file using multiple methods"""
        try:
            current_app.logger.info(f"🔄 Extracting text from PDF: {file_path}")
            
            # Try PyMuPDF first (better formatting)
            try:
                import fitz
                doc = fitz.open(file_path)
                text = ""
                for page in doc:
                    text += page.get_text()
                doc.close()
                
                if text and len(text) > 100:
                    current_app.logger.info(f"✅ Successfully extracted {len(text)} characters with PyMuPDF")
                    return text
                else:
                    current_app.logger.warning(f"⚠️ PyMuPDF extraction returned only {len(text)} characters")
            except Exception as e:
                current_app.logger.error(f"❌ PyMuPDF extraction failed: {str(e)}")
            
            # Fallback to pdfplumber
            try:
                import pdfplumber
                text = ""
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        text += page.extract_text() or ""
                
                if text and len(text) > 100:
                    current_app.logger.info(f"✅ Successfully extracted {len(text)} characters with pdfplumber")
                    return text
                else:
                    current_app.logger.warning(f"⚠️ pdfplumber extraction returned only {len(text)} characters")
            except Exception as e:
                current_app.logger.error(f"❌ pdfplumber extraction failed: {str(e)}")
            
            # Last resort: try PyPDF2
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(file_path)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
                
                if text and len(text) > 100:
                    current_app.logger.info(f"✅ Successfully extracted {len(text)} characters with PyPDF2")
                    return text
                else:
                    current_app.logger.warning(f"⚠️ PyPDF2 extraction returned only {len(text)} characters")
            except Exception as e:
                current_app.logger.error(f"❌ PyPDF2 extraction failed: {str(e)}")
            
            current_app.logger.error("❌ All PDF extraction methods failed")
            return ""
            
        except Exception as e:
            current_app.logger.error(f"❌ PDF extraction error: {str(e)}")
            return ""
    
    def _extract_document_name(self, query: str, intent_analysis: Dict[str, Any]) -> str:
        """Extract document name from query"""
        try:
            # Use intent analysis to extract document name
            document_indicators = intent_analysis.get('document_indicators', [])
            
            if document_indicators:
                return ' '.join(document_indicators)
            
            # Fallback to original query
            return query
            
        except Exception as e:
            current_app.logger.error(f"Document name extraction failed: {str(e)}")
            return query
    
    def _extract_search_terms(self, query: str, intent_analysis: Dict[str, Any]) -> str:
        """Extract search terms from query"""
        try:
            # Use intent analysis to extract search terms
            search_terms = intent_analysis.get('search_terms', [])
            
            if search_terms:
                return ' '.join(search_terms)
            
            # Fallback to original query
            return query
            
        except Exception as e:
            current_app.logger.error(f"Search terms extraction failed: {str(e)}")
            return query
    
    # Main processing method
    def process_document_chat(self, user_id: int, query: str, 
                            conversation_id: Optional[int] = None,
                            thread_id: Optional[str] = None,
                            conversation_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Main method to process document chat through the enhanced LangGraph workflow"""
        
        try:
            current_app.logger.info(f"🚀 Starting enhanced document chat for user {user_id}: {query}")
            
            # Check for document context from conversation context manager
            document_content = ""
            selected_document = None
            
            try:
                from app.utils.conversation_context_manager import get_context_manager
                context_manager = get_context_manager()
                document_context = context_manager.get_document_context(user_id, conversation_id)
                
                if document_context and document_context.get("document_names"):
                    filename = document_context.get("document_names")[0]
                    current_app.logger.info(f"✅ Found document from context: {filename}")
                    
                    # Create a document dict
                    selected_document = {
                        "filename": filename,
                        "user_id": user_id
                    }
                    
                    # Try to get document content
                    document_content = self._get_document_content(selected_document)
                    current_app.logger.info(f"📝 Retrieved document content: {len(document_content)} characters")
                    
                    # If we have content, make sure we use it directly in the workflow
                    if document_content and len(document_content) > 100:
                        current_app.logger.info(f"✅ Successfully retrieved document content of {len(document_content)} characters")
                    else:
                        # Try a direct search as fallback
                        current_app.logger.info(f"⚠️ Document content too short or empty, trying search fallback")
                        success, docs = query_user_docs(filename, user_id, top_k=1)
                        if success and docs and len(docs) > 0:
                            doc = docs[0]
                            if hasattr(doc, 'page_content') and doc.page_content:
                                document_content = doc.page_content
                                current_app.logger.info(f"✅ Retrieved document content from search: {len(document_content)} characters")
            except Exception as e:
                current_app.logger.error(f"❌ Failed to get document from context: {str(e)}")
            
            # Initial state
            initial_state = {
                "messages": [HumanMessage(content=query)],
                "user_id": user_id,
                "query": query,
                "conversation_id": conversation_id,
                "thread_id": thread_id or str(uuid.uuid4()),
                "intent": "",
                "intent_confidence": 0.0,
                "routing_decision": "",
                "search_query": query,
                "documents_found": [],
                "selected_document": selected_document,
                "document_content": document_content,
                "document_name_query": query,
                "name_search_results": [],
                "exact_document_match": None,
                "response_content": "",
                "response_type": "general_chat",
                "confidence_score": 0.0,
                "chat_context": conversation_context or {},
                "conversation_history": [],
                "agent_notes": {},
                "tools_used": [],
                "workflow_trace": [],
                "follow_up_suggestions": [],
                "related_documents": [],
                "error_message": None,
                "processing_status": "started"
            }
            
            # If we have document content but no selected document in the initial state,
            # create a basic document object to ensure it's used
            if document_content and not selected_document:
                initial_state["selected_document"] = {
                    "filename": "uploaded_document.pdf",
                    "user_id": user_id
                }
            
            # Run the chat workflow
            config = {"thread_id": initial_state["thread_id"]}
            
            # Process through the enhanced graph
            final_state = None
            for state in self.graph.stream(initial_state, config):
                final_state = state
                current_app.logger.info(f"Chat processing step completed: {list(state.keys())}")
            
            if final_state:
                # Extract final results
                result = {
                    'success': final_state.get('processing_status', '').endswith('_generated') or final_state.get('processing_status') == 'suggestions_generated',
                    'response': final_state.get('response_content', ''),
                    'intent': final_state.get('intent', 'general_chat'),
                    'confidence_score': final_state.get('confidence_score', 0.0),
                    'documents_found': final_state.get('documents_found', []),
                    'selected_document': final_state.get('selected_document'),
                    'follow_up_suggestions': final_state.get('follow_up_suggestions', []),
                    'related_documents': final_state.get('related_documents', []),
                    'tools_used': final_state.get('tools_used', []),
                    'workflow_trace': final_state.get('workflow_trace', []),
                    'response_type': final_state.get('response_type', 'general_chat'),
                    'error_message': final_state.get('error_message'),
                    'processing_status': final_state.get('processing_status', 'completed')
                }
                
                current_app.logger.info(f"✅ Enhanced document chat completed: {result['success']}")
                
                # If we have document content but the response doesn't reference it,
                # generate a direct response using the content
                if document_content and len(document_content) > 100 and not result['success']:
                    current_app.logger.info("⚠️ Document chat failed but we have content, generating direct response")
                    try:
                        # Generate a direct response using the document content
                        document_name = selected_document.get('filename', 'the document') if selected_document else 'the document'
                        
                        direct_prompt = f"""
                        You are a document analysis expert.
                        
                        User Query: "{query}"
                        
                        Document Name: {document_name}
                        
                        Document Content: {document_content[:8000]}
                        
                        The user is asking about this document. Please provide:
                        1. A comprehensive response that directly addresses their query
                        2. If they're asking for a summary, provide a detailed summary of the document
                        3. Key points and insights from the document relevant to their query
                        4. Any relevant information that would be useful to the user
                        
                        Format your response as a well-structured answer with sections and bullet points where appropriate.
                        Focus ONLY on the document content. Do NOT include any disclaimers about being an AI assistant.
                        """
                        
                        response = self.chat_model.invoke([
                            SystemMessage(content="You are a document analysis expert."),
                            HumanMessage(content=direct_prompt)
                        ])
                        
                        result['response'] = response.content
                        result['success'] = True
                        result['confidence_score'] = 0.9
                        result['processing_status'] = "direct_response_generated"
                    except Exception as e:
                        current_app.logger.error(f"❌ Direct response generation failed: {str(e)}")
                
                return result
            
            else:
                raise Exception("No final state received from chat workflow")
                
        except Exception as e:
            current_app.logger.error(f"❌ Enhanced document chat failed: {str(e)}")
            return {
                'success': False,
                'response': 'I apologize, but I encountered an issue processing your request. Please try again.',
                'error_message': str(e),
                'processing_status': 'failed'
            } 