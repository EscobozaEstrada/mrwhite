from typing import Dict, List, Optional, Tuple, Any
import json
import uuid
from datetime import datetime, timezone, timedelta, time
from flask import current_app

from app import db
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.care_record import CareRecord, Document, KnowledgeBase
from app.services.ai_service import AIService
from app.services.care_archive_service import CareArchiveService
from app.services.langgraph_chat_service import LangGraphChatService
from app.services.common_knowledge_service import get_common_knowledge_service
from app.utils.file_handler import query_user_docs, query_chat_history


class EnhancedChatService:
    """Enhanced chat service with knowledge base integration and context awareness"""
    
    def __init__(self):
        self.ai_service = AIService()
        self.care_service = None
        self.common_knowledge_service = None
        self._init_services()
    
    def _init_services(self):
        """Initialize dependent services"""
        try:
            from app.services.care_archive_service import CareArchiveService
            from app.services.common_knowledge_service import CommonKnowledgeService
            
            self.care_service = CareArchiveService()
            self.common_knowledge_service = CommonKnowledgeService()
        except Exception as e:
            current_app.logger.warning(f"Failed to initialize some services: {str(e)}")
    
    def generate_contextual_response(self, user_id: int, message: str, 
                                   conversation_id: int = None, thread_id: str = None) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Generate AI-powered contextual responses with enhanced reminder support
        """
        try:
            # 🎯 CONTEXT7 ENHANCEMENT: Fetch user context including timezone for reminder processing
            user_context = self._get_user_timezone_context(user_id)
            
            current_app.logger.info(f"🌍 User timezone context: {user_context.get('timezone', 'UTC')} ({user_context.get('timezone_abbreviation', 'UTC')})")
            
            # Check if this is a reminder request using AI
            if self._is_reminder_request(message):
                current_app.logger.info("🤖 AI Agent detected reminder request - Processing...")
                
                # 🎯 CONTEXT7 ENHANCEMENT: Check for recurring patterns first
                from app.services.recurring_reminder_service import get_recurring_reminder_service
                recurring_service = get_recurring_reminder_service()
                
                recurring_pattern = recurring_service.detect_recurring_pattern(message, user_context)
                
                if recurring_pattern.get("is_recurring", False) and recurring_pattern.get("confidence", 0) > 0.6:
                    current_app.logger.info(f"🔄 Detected recurring pattern: {recurring_pattern}")
                    
                    # Generate clarification questions if needed
                    clarification = recurring_service.generate_clarification_questions(recurring_pattern, message)
                    
                    if clarification.get("needs_clarification", False):
                        current_app.logger.info("❓ Recurring reminder needs clarification")
                        
                        # Return clarification response
                        clarification_response = clarification.get("response", "")
                        
                        context_info = {
                            'conversation_id': conversation_id,
                            'thread_id': thread_id,
                            'sources': [],
                            'intent_analysis': {'primary_intent': 'recurring_reminder_clarification'},
                            'response_metadata': {
                                'ai_agent_action': 'recurring_clarification', 
                                'recurring_pattern': recurring_pattern,
                                'questions': clarification.get("questions", [])
                            },
                            'care_records_referenced': 0,
                            'documents_referenced': 0,
                            'fallback_used': False,
                            'needs_clarification': True,
                            'clarification_questions': clarification.get("questions", [])
                        }
                        
                        current_app.logger.info(f"❓ Returning clarification request for recurring reminder")
                        return True, clarification_response, context_info
                    
                    else:
                        # We have enough info to create recurring reminders
                        current_app.logger.info("🔄 Creating recurring reminders series...")
                        
                        # Extract base reminder details with timezone context
                        base_reminder_details = self._extract_reminder_details_ai_with_timezone(message, user_id, user_context)
                        
                        if base_reminder_details.get("is_reminder_request", False):
                            # Create the recurring reminder series
                            recurring_result = recurring_service.create_recurring_reminders(
                                user_id=user_id,
                                base_reminder_data=base_reminder_details,
                                recurring_config=recurring_pattern,
                                user_context=user_context
                            )
                            
                            if recurring_result.get("success", False):
                                # Generate confirmation response for recurring series
                                series_response = self._generate_recurring_series_confirmation(
                                    recurring_result, base_reminder_details, message, user_context
                                )
                                
                                context_info = {
                                    'conversation_id': conversation_id,
                                    'thread_id': thread_id,
                                    'sources': [],
                                    'intent_analysis': {'primary_intent': 'recurring_reminder_created'},
                                    'response_metadata': {
                                        'ai_agent_action': 'recurring_series_created', 
                                        'series_id': recurring_result.get('series_id'),
                                        'total_reminders': recurring_result.get('total_created'),
                                        'user_timezone': user_context.get('timezone', 'UTC')
                                    },
                                    'care_records_referenced': 0,
                                    'documents_referenced': 0,
                                    'fallback_used': False,
                                    'recurring_series_created': True,
                                    'recurring_info': recurring_result
                                }
                                
                                current_app.logger.info(f"✅ Created recurring series with {recurring_result.get('total_created')} reminders")
                                return True, series_response, context_info
                            
                            else:
                                # Failed to create recurring series
                                error_msg = recurring_result.get('error', 'Unknown error')
                                fallback_response = f"I detected you want recurring reminders for '{base_reminder_details.get('title', 'that task')}', but I had trouble creating the series: {error_msg}. You can create individual reminders manually in your Reminders page."
                                
                                context_info = {
                                    'conversation_id': conversation_id,
                                    'thread_id': thread_id,
                                    'sources': [],
                                    'intent_analysis': {'primary_intent': 'recurring_reminder_failed'},
                                    'response_metadata': {'ai_agent_action': 'recurring_series_failed', 'error': error_msg},
                                    'care_records_referenced': 0,
                                    'documents_referenced': 0,
                                    'fallback_used': True,
                                    'recurring_failed': True,
                                    'error_message': error_msg
                                }
                                
                                current_app.logger.warning(f"❌ Failed to create recurring series: {error_msg}")
                                return True, fallback_response, context_info
                
                # Not a recurring reminder, proceed with single reminder creation
                current_app.logger.info("📅 Processing single reminder creation...")
                
                # Extract reminder details using AI with timezone context
                reminder_details = self._extract_reminder_details_ai_with_timezone(message, user_id, user_context)
                
                if reminder_details.get("is_reminder_request", False) and reminder_details.get("confidence", 0) > 0.3:
                    current_app.logger.info(f"🎯 AI Agent extracted reminder: {reminder_details}")
                    
                    # Create the reminder with timezone-aware processing
                    success, create_message, reminder_info = self._create_health_reminder_with_timezone(user_id, reminder_details, user_context)
                    
                    if success:
                        # Generate a personalized confirmation response
                        confirmation_response = self._generate_reminder_confirmation_response(
                            reminder_details, reminder_info, message, user_context
                        )
                        
                        # Try to save the conversation message for this reminder creation
                        try:
                            if conversation_id:
                                conversation = Conversation.query.filter_by(id=conversation_id, user_id=user_id).first()
                            else:
                                # Create new conversation for this reminder
                                thread_id = thread_id or str(uuid.uuid4())
                                conversation = self._create_new_conversation(user_id, message, thread_id)
                                conversation_id = conversation.id
                            
                            if conversation:
                                # Save the user message and AI response
                                user_msg = Message(conversation_id=conversation.id, content=message, type='user')
                                ai_msg = Message(conversation_id=conversation.id, content=confirmation_response, type='ai')
                                db.session.add(user_msg)
                                db.session.add(ai_msg)
                                conversation.updated_at = datetime.now(timezone.utc)
                                db.session.commit()
                                current_app.logger.info(f"💾 Saved reminder conversation to database")
                        except Exception as save_error:
                            current_app.logger.warning(f"Failed to save reminder conversation: {str(save_error)}")
                            db.session.rollback()
                        
                        context_info = {
                            'conversation_id': conversation_id,
                            'thread_id': thread_id,
                            'sources': [],
                            'intent_analysis': {'primary_intent': 'reminder_creation'},
                            'response_metadata': {
                                'ai_agent_action': 'reminder_created', 
                                'reminder_type': reminder_details.get('reminder_type'),
                                'user_timezone': user_context.get('timezone', 'UTC'),
                                'local_time_used': True
                            },
                            'care_records_referenced': 0,
                            'documents_referenced': 0,
                            'fallback_used': False,
                            'reminder_created': True,
                            'reminder_info': reminder_info
                        }
                        
                        current_app.logger.info(f"✅ AI Agent successfully created reminder {reminder_info.get('reminder_id')}")
                        return True, confirmation_response, context_info
                    else:
                        # Failed to create reminder, but still respond helpfully
                        fallback_response = f"I understand you'd like me to remind you about {reminder_details.get('title', 'that task')}. I had a small issue setting up the reminder automatically, but I can still help you with pet care advice! You can also create reminders manually in your Reminders page."
                        
                        context_info = {
                            'conversation_id': conversation_id,
                            'thread_id': thread_id,
                            'sources': [],
                            'intent_analysis': {'primary_intent': 'reminder_creation_failed'},
                            'response_metadata': {'ai_agent_action': 'reminder_failed', 'error': create_message},
                            'care_records_referenced': 0,
                            'documents_referenced': 0,
                            'fallback_used': True,
                            'reminder_failed': True,
                            'error_message': create_message
                        }
                        
                        current_app.logger.warning(f"❌ AI Agent failed to create reminder: {create_message}")
                        return True, fallback_response, context_info
            
            # Get or create conversation with timeout handling
            if conversation_id:
                try:
                    current_app.logger.info(f"Looking up conversation {conversation_id}")
                    conversation = Conversation.query.filter_by(id=conversation_id, user_id=user_id).first()
                    if not conversation:
                        current_app.logger.warning(f"Conversation {conversation_id} not found, creating new one")
                        conversation_id = None
                    else:
                        current_app.logger.info(f"Found existing conversation {conversation_id}: '{conversation.title}'")
                except Exception as db_error:
                    current_app.logger.warning(f"Database timeout during conversation lookup: {str(db_error)}, proceeding without existing conversation")
                    conversation_id = None
            else:
                current_app.logger.info("No conversation_id provided - will create new conversation")
            
            # Create new conversation if needed
            if not conversation:
                try:
                    current_app.logger.info("Creating new conversation")
                    thread_id = thread_id or str(uuid.uuid4())
                    conversation = self._create_new_conversation(user_id, message, thread_id)
                    current_app.logger.info(f"Created conversation with ID {conversation.id}")
                except Exception as create_error:
                    current_app.logger.warning(f"Failed to create conversation: {str(create_error)}, proceeding with temporary conversation")
                    conversation = type('TempConversation', (), {
                        'id': conversation_id or 0,
                        'user_id': user_id,
                        'title': 'Temporary Conversation',
                        'thread_id': thread_id or str(uuid.uuid4()),
                        'to_dict': lambda: {'id': conversation_id or 0, 'title': 'Temporary Conversation'}
                    })()
            
            # Set thread_id
            if not thread_id:
                thread_id = getattr(conversation, 'thread_id', None) or str(uuid.uuid4())
                if hasattr(conversation, 'thread_id') and not conversation.thread_id:
                    conversation.thread_id = thread_id
            
            current_app.logger.info(f"Using thread_id: {thread_id}")
            
            # Build context for health-focused AI response
            current_app.logger.info("Building context for health AI")
            current_app.logger.info(f"Conversation ID being used: {getattr(conversation, 'id', None)}")
            context = self._build_user_context_with_conversation(user_id, message, getattr(conversation, 'id', None))
            current_app.logger.info(f"Built context with {len(context.get('sources', []))} sources")
            current_app.logger.info(f"Conversation history messages: {len(context.get('conversation_history', []))}")
            
            # Log first few conversation history messages for debugging
            if context.get('conversation_history'):
                current_app.logger.info("Sample conversation history:")
                for i, msg in enumerate(context['conversation_history'][-5:]):
                    current_app.logger.info(f"  {i+1}. {msg['type']}: {msg['content'][:100]}...")
            else:
                current_app.logger.warning("No conversation history found!")
            
            # Generate health-focused AI response
            current_app.logger.info("Generating health-focused AI response")
            ai_response = self._generate_health_response(message, context, user_id)
            current_app.logger.info(f"Generated response: {ai_response[:100]}...")
            
            # Create context info
            context_info = {
                'sources': context.get('sources', []),
                'fallback_used': False,  # This is now the primary method
                'care_records_referenced': context.get('care_records_count', 0),
                'documents_referenced': context.get('documents_count', 0),
                'health_ai_used': True
            }
            
            current_app.logger.info(f"Final AI response: {ai_response[:100]}...")
            
            # Try to save messages to database
            try:
                current_app.logger.info("Attempting to save messages to database")
                if hasattr(conversation, 'id') and conversation.id:
                    current_app.logger.info(f"Saving messages to conversation ID: {conversation.id}")
                    
                    user_msg = Message(
                        conversation_id=conversation.id,
                        content=message,
                        type='user'
                    )
                    db.session.add(user_msg)
                    current_app.logger.info(f"Added user message: {message[:50]}...")
                    
                    ai_msg = Message(
                        conversation_id=conversation.id,
                        content=ai_response,
                        type='ai'
                    )
                    db.session.add(ai_msg)
                    current_app.logger.info(f"Added AI message: {ai_response[:50]}...")
                    
                    # Update conversation
                    if hasattr(conversation, 'updated_at'):
                        conversation.updated_at = datetime.now(timezone.utc)
                        current_app.logger.info("Updated conversation timestamp")
                    if hasattr(conversation, 'title') and (not conversation.title or conversation.title == "New Conversation"):
                        new_title = self._generate_conversation_title(message)
                        conversation.title = new_title
                        current_app.logger.info(f"Updated conversation title to: {new_title}")
                    
                    db.session.commit()
                    current_app.logger.info("Successfully committed messages to database")
                    
                    # Verify messages were saved
                    saved_messages = Message.query.filter_by(conversation_id=conversation.id).count()
                    current_app.logger.info(f"Total messages in conversation {conversation.id}: {saved_messages}")
                else:
                    current_app.logger.warning(f"Cannot save messages - invalid conversation: {conversation}")
            except Exception as db_save_error:
                db.session.rollback()
                current_app.logger.warning(f"Failed to save messages to database: {str(db_save_error)}, but response generated successfully")
            
            # Enhanced context info with conversation details
            enhanced_context_info = {
                'conversation_id': getattr(conversation, 'id', conversation_id),
                'thread_id': thread_id,
                'sources': context_info.get('sources', []),
                'intent_analysis': {},
                'response_metadata': {'health_ai_used': True},
                'care_records_referenced': context_info.get('care_records_referenced', 0),
                'documents_referenced': context_info.get('documents_referenced', 0),
                'fallback_used': False
            }
            
            current_app.logger.info(f"Returning successful response with {len(enhanced_context_info.get('sources', []))} sources")
            return True, ai_response, enhanced_context_info
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error generating contextual response: {str(e)}")
            current_app.logger.error(f"Full error details: {repr(e)}")
            
            # Return a helpful response even if something fails
            fallback_response = self._generate_simple_response(message)
            return True, fallback_response, {
                'conversation_id': getattr(conversation, 'id', conversation_id) if conversation else None,
                'thread_id': thread_id,
                'sources': [],
                'intent_analysis': {},
                'response_metadata': {'health_ai_used': True, 'error_handled': True},
                'care_records_referenced': 0,
                'documents_referenced': 0,
                'fallback_used': True
            }
    
    def _build_user_context_with_conversation(self, user_id: int, current_message: str, conversation_id: int = None) -> Dict[str, Any]:
        """Build user context including current conversation messages"""
        context = {
            'current_message': current_message,
            'sources': [],
            'care_records_count': 0,
            'documents_count': 0,
            'relevant_care_records': [],
            'relevant_documents': [],
            'conversation_history': []
        }
        
        try:
            # Get conversation history including current conversation
            try:
                current_app.logger.info(f"Building context for user {user_id}, conversation {conversation_id}")
                conversation_history = []
                
                # First, get messages from current conversation if available
                if conversation_id:
                    current_app.logger.info(f"Retrieving messages from current conversation {conversation_id}")
                    current_messages = (Message.query
                                      .filter_by(conversation_id=conversation_id)
                                      .order_by(Message.created_at.asc())
                                      .all())
                    
                    current_app.logger.info(f"Found {len(current_messages)} messages in current conversation")
                    
                    for msg in current_messages:
                        conversation_history.append({
                            'type': msg.type,
                            'content': msg.content,
                            'timestamp': msg.created_at.isoformat(),
                            'conversation_id': conversation_id,
                            'is_current_conversation': True
                        })
                        current_app.logger.debug(f"Added message: {msg.type} - {msg.content[:50]}...")
                else:
                    current_app.logger.info("No conversation_id provided, skipping current conversation messages")
                
                # Then get recent messages from other conversations
                current_app.logger.info("Retrieving messages from other recent conversations")
                recent_conversations = (Conversation.query
                                      .filter_by(user_id=user_id)
                                      .filter(Conversation.id != conversation_id if conversation_id else True)
                                      .order_by(Conversation.updated_at.desc())
                                      .limit(2)
                                      .all())
                
                current_app.logger.info(f"Found {len(recent_conversations)} other recent conversations")
                
                for conv in recent_conversations:
                    messages = (Message.query
                              .filter_by(conversation_id=conv.id)
                              .order_by(Message.created_at.desc())
                              .limit(5)
                              .all())
                    
                    current_app.logger.info(f"Adding {len(messages)} messages from conversation {conv.id}")
                    
                    for msg in reversed(messages):
                        conversation_history.append({
                            'type': msg.type,
                            'content': msg.content,
                            'timestamp': msg.created_at.isoformat(),
                            'conversation_id': conv.id,
                            'is_current_conversation': False
                        })
                
                # Sort by timestamp and keep most recent 25 messages
                conversation_history.sort(key=lambda x: x['timestamp'])
                context['conversation_history'] = conversation_history[-25:]
                current_app.logger.info(f"Final conversation history: {len(context['conversation_history'])} messages")
                
            except Exception as e:
                current_app.logger.error(f"Error retrieving conversation history: {str(e)}")
                current_app.logger.error(f"Exception details: {repr(e)}")
                import traceback
                current_app.logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Search relevant care records
            try:
                care_results = self.care_service.search_user_archive(user_id, current_message, limit=3)
                context['relevant_care_records'] = care_results.get('care_records', [])
                context['care_records_count'] = len(context['relevant_care_records'])
                
                # Add care record sources
                for record in context['relevant_care_records']:
                    context['sources'].append({
                        'type': 'care_record',
                        'title': record.get('title', 'Care Record'),
                        'category': record.get('category', ''),
                        'date': record.get('date_occurred', '')
                    })
            except Exception as e:
                current_app.logger.warning(f"Error searching care records: {str(e)}")
            
            # Search relevant documents
            try:
                success, doc_results = query_user_docs(current_message, user_id, top_k=10)
                if success and doc_results:
                    context['relevant_documents'] = [
                        {
                            'filename': doc.metadata.get('source', 'Unknown'),
                            'content': doc.page_content,
                            'url': doc.metadata.get('url', ''),
                            'score': 1.0  # Default score
                        }
                        for doc in doc_results
                    ]
                    context['documents_count'] = len(context['relevant_documents'])
                    
                    # Add document sources
                    for doc_info in context['relevant_documents']:
                        context['sources'].append({
                            'type': 'document',
                            'title': doc_info.get('filename', 'Unknown Document'),
                            'content_preview': doc_info.get('content', '')[:100]
                        })
                else:
                    context['relevant_documents'] = []
                    context['documents_count'] = 0
            except Exception as e:
                current_app.logger.warning(f"Error querying documents: {str(e)}")
                context['relevant_documents'] = []
                context['documents_count'] = 0
            
        except Exception as e:
            current_app.logger.error(f"Error building user context with conversation: {str(e)}")
        
        return context
    
    def _build_user_context_simple(self, user_id: int, current_message: str) -> Dict[str, Any]:
        """Build simple user context without requiring conversation_id"""
        context = {
            'current_message': current_message,
            'sources': [],
            'care_records_count': 0,
            'documents_count': 0,
            'relevant_care_records': [],
            'relevant_documents': [],
            'conversation_history': []
        }
        
        try:
            # Get recent conversation history for this user
            try:
                recent_conversations = (Conversation.query
                                      .filter_by(user_id=user_id)
                                      .order_by(Conversation.updated_at.desc())
                                      .limit(3)
                                      .all())
                
                conversation_history = []
                for conv in recent_conversations:
                    messages = (Message.query
                              .filter_by(conversation_id=conv.id)
                              .order_by(Message.created_at.desc())
                              .limit(10)
                              .all())
                    
                    for msg in reversed(messages):  # Reverse to get chronological order
                        conversation_history.append({
                            'type': msg.type,
                            'content': msg.content,
                            'timestamp': msg.created_at.isoformat(),
                            'conversation_id': conv.id
                        })
                
                # Keep only the most recent 20 messages across all conversations
                context['conversation_history'] = conversation_history[-20:]
                current_app.logger.info(f"Retrieved {len(context['conversation_history'])} conversation history messages")
                
            except Exception as e:
                current_app.logger.warning(f"Error retrieving conversation history: {str(e)}")
            
            # Search relevant care records (simplified)
            try:
                care_results = self.care_service.search_user_archive(user_id, current_message, limit=3)
                context['relevant_care_records'] = care_results.get('care_records', [])
                context['care_records_count'] = len(context['relevant_care_records'])
                
                # Add care record sources
                for record in context['relevant_care_records']:
                    context['sources'].append({
                        'type': 'care_record',
                        'title': record.get('title', 'Care Record'),
                        'category': record.get('category', ''),
                        'date': record.get('date_occurred', '')
                    })
            except Exception as e:
                current_app.logger.warning(f"Error searching care records: {str(e)}")
            
            # Search relevant documents (simplified)
            try:
                from app.utils.file_handler import query_user_docs
                success, doc_results = query_user_docs(current_message, user_id, top_k=10)
                if success and doc_results:
                    context['relevant_documents'] = [
                        {
                            'filename': doc.metadata.get('source', 'Unknown'),
                            'content': doc.page_content,
                            'url': doc.metadata.get('url', ''),
                            'score': 1.0  # Default score
                        }
                        for doc in doc_results
                    ]
                    context['documents_count'] = len(context['relevant_documents'])
                    
                    # Add document sources
                    for doc_info in context['relevant_documents']:
                        context['sources'].append({
                            'type': 'document',
                            'title': doc_info.get('filename', 'Unknown Document'),
                            'content_preview': doc_info.get('content', '')[:100]
                        })
                else:
                    context['relevant_documents'] = []
                    context['documents_count'] = 0
            except Exception as e:
                current_app.logger.warning(f"Error querying documents: {str(e)}")
                context['relevant_documents'] = []
                context['documents_count'] = 0
            
        except Exception as e:
            current_app.logger.error(f"Error building simple user context: {str(e)}")
        
        return context
    
    def _create_new_conversation(self, user_id: int, message: str, thread_id: str) -> 'Conversation':
        """Create a new conversation with timeout handling"""
        try:
            title = self._generate_conversation_title(message)
            conversation = Conversation(
                user_id=user_id, 
                title=title,
                thread_id=thread_id
            )
            db.session.add(conversation)
            db.session.commit()
            return conversation
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating new conversation: {str(e)}")
            raise
    
    def _generate_conversation_title(self, message: str) -> str:
        """Generate a conversation title based on the first message"""
        try:
            # Use AI to generate a concise title
            prompt = f"""
            Generate a short, descriptive title (max 50 characters) for a conversation that starts with:
            "{message[:200]}..."
            
            Focus on the main topic or question. Return only the title, no quotes or extra text.
            """
            
            title = self.ai_service.generate_response(prompt, max_tokens=50)
            
            # Clean and validate the title
            title = title.strip().strip('"\'')
            if len(title) > 50:
                title = title[:47] + "..."
            
            return title if title else "New Conversation"
            
        except Exception as e:
            current_app.logger.error(f"Error generating conversation title: {str(e)}")
            return "New Conversation"
    
    def get_conversation_with_context(self, user_id: int, conversation_id: int) -> Dict[str, Any]:
        """Get conversation with enhanced context and metadata"""
        try:
            conversation = Conversation.query.filter_by(id=conversation_id, user_id=user_id).first()
            
            if not conversation:
                return {}
            
            # Get messages
            messages = (Message.query
                       .filter_by(conversation_id=conversation_id)
                       .order_by(Message.created_at)
                       .all())
            
            # Build context for the conversation
            latest_message = messages[-1].content if messages else ""
            context = self._build_user_context(user_id, latest_message, conversation_id)
            
            return {
                'conversation': conversation.to_dict(),
                'messages': [msg.to_dict() for msg in messages],
                'context': {
                    'total_sources': len(context.get('sources', [])),
                    'documents_available': context.get('documents_count', 0),
                    'care_records_available': context.get('care_records_count', 0),
                    'user_stats': context.get('user_stats', {})
                },
                'upcoming_reminders': context.get('upcoming_reminders', [])
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting conversation with context: {str(e)}")
            return {}
    
    def analyze_user_query_intent(self, message: str) -> Dict[str, Any]:
        """Analyze user query to determine intent and required context"""
        intents = {
            'care_history': any(word in message.lower() for word in 
                              ['history', 'past', 'previous', 'before', 'last time']),
            'medical_records': any(word in message.lower() for word in 
                                 ['vaccination', 'vet', 'medical', 'doctor', 'medicine', 'prescription']),
            'reminders': any(word in message.lower() for word in 
                           ['remind', 'upcoming', 'schedule', 'next', 'appointment']),
            'document_search': any(word in message.lower() for word in 
                                 ['document', 'file', 'record', 'report', 'show me']),
            'general_question': True  # Default intent
        }
        
        # Determine primary intent
        primary_intent = 'general_question'
        for intent, is_present in intents.items():
            if is_present and intent != 'general_question':
                primary_intent = intent
                break
        
        return {
            'primary_intent': primary_intent,
            'intents': intents,
            'requires_context': primary_intent != 'general_question'
        }
    
    def get_user_care_summary(self, user_id: int) -> Dict[str, Any]:
        """Get a comprehensive summary of user's care data"""
        try:
            stats = self.care_service.get_knowledge_base_stats(user_id)
            timeline = self.care_service.get_user_care_timeline(user_id, limit=10)
            reminders = self.care_service.get_upcoming_reminders(user_id, days_ahead=30)
            
            # Get recent conversations
            recent_conversations = (Conversation.query
                                  .filter_by(user_id=user_id)
                                  .order_by(Conversation.updated_at.desc())
                                  .limit(5)
                                  .all())
            
            return {
                'knowledge_base_stats': stats,
                'recent_timeline': timeline,
                'upcoming_reminders': [r.to_dict() for r in reminders],
                'recent_conversations': [c.to_dict() for c in recent_conversations],
                'summary_generated_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting user care summary: {str(e)}")
            return {}
    
    def suggest_follow_up_questions(self, user_id: int, conversation_id: int) -> List[str]:
        """Suggest relevant follow-up questions based on conversation and user data"""
        try:
            # Get conversation context
            conversation_data = self.get_conversation_with_context(user_id, conversation_id)
            
            if not conversation_data:
                return []
            
            messages = conversation_data.get('messages', [])
            context = conversation_data.get('context', {})
            
            suggestions = []
            
            # Based on available data, suggest relevant questions
            if context.get('documents_available', 0) > 0:
                suggestions.append("Can you show me what's in my uploaded documents?")
            
            if context.get('care_records_available', 0) > 0:
                suggestions.append("What vaccination records do I have?")
                suggestions.append("When was my pet's last vet visit?")
            
            if context.get('user_stats', {}).get('total_care_records', 0) > 0:
                suggestions.append("Show me my pet's care timeline")
                suggestions.append("What reminders do I have coming up?")
            
            # Add general helpful suggestions
            suggestions.extend([
                "How can I organize my pet's medical records better?",
                "What should I track for my pet's health?",
                "Can you help me prepare for my next vet visit?"
            ])
            
            return suggestions[:5]  # Return top 5 suggestions
            
        except Exception as e:
            current_app.logger.error(f"Error generating follow-up suggestions: {str(e)}")
            return []
    
    def _generate_health_response(self, message: str, context: Dict[str, Any], user_id: int) -> str:
        """Generate a health-focused AI response with common knowledge base integration"""
        try:
            # Step 1: Search common knowledge base for relevant information
            common_knowledge_context = self._get_common_knowledge_context(message, context)
            
            # Check if this is a health-related query that needs specialized handling
            if self._is_health_query(message):
                current_app.logger.info("Detected health query - using Health Intelligence Service")
                return self._generate_health_intelligence_response_with_common_knowledge(
                    message, context, user_id, common_knowledge_context
                )
            
            # Build conversation history summary - more focused approach
            conversation_summary = ""
            if context.get('conversation_history'):
                current_conv_messages = [msg for msg in context['conversation_history'] if msg.get('is_current_conversation', False)]
                
                if current_conv_messages:
                    # Create a focused summary of key information
                    key_facts = []
                    for msg in current_conv_messages:
                        if msg['type'] == 'user':
                            content = msg['content']
                            # Look for key health information
                            if any(keyword in content.lower() for keyword in [
                                'vaccination', 'vaccine', 'vet', 'medication', 'treatment', 
                                'appointment', 'visit', 'medicine', 'dose', 'allergic', 'sick'
                            ]):
                                key_facts.append(content)
                    
                    if key_facts:
                        conversation_summary = f"""
IMPORTANT: The user has told you the following information in this conversation:
{chr(10).join([f"- {fact}" for fact in key_facts[-5:]])}

You must use this information when answering questions. If they ask about something they just told you, reference what they said.
"""
                    else:
                        # Include recent conversation for context
                        recent_exchange = []
                        for msg in current_conv_messages[-6:]:
                            role = "User" if msg['type'] == 'user' else "Mr. White"
                            recent_exchange.append(f"{role}: {msg['content']}")
                        
                        conversation_summary = f"""
Recent conversation:
{chr(10).join(recent_exchange)}

Remember what was discussed above when answering the current question.
"""
            
            # Build enhanced prompt with common knowledge
            common_knowledge_section = ""
            if common_knowledge_context.get('context'):
                common_knowledge_section = f"""

Additional Context from 'The Way of the Dog Anahata':
{common_knowledge_context['context']}

Please incorporate relevant information from this book context when appropriate. When you reference insights from the book, you can mention "As discussed in 'The Way of the Dog Anahata'" to provide attribution.
"""
            
            # Enhanced prompt with common knowledge integration
            prompt = f"""You are Mr. White, a caring pet care expert. You help pet owners with their questions and remember what they tell you.

{conversation_summary}

Current question: {message}
{common_knowledge_section}

Instructions:
1. If the user asks about something they told you earlier in the conversation, use that information
2. Be helpful and caring
3. If you have relevant information from 'The Way of the Dog Anahata', incorporate it naturally
4. If you don't have specific information, provide general pet care advice
5. Always remember what the user has told you in this conversation
6. When referencing the book, you can mention "As discussed in 'The Way of the Dog Anahata'" when relevant

Answer as Mr. White:"""
            
            current_app.logger.info("=== ENHANCED AI PROMPT WITH COMMON KNOWLEDGE ===")
            current_app.logger.info(f"Common knowledge context length: {len(common_knowledge_context.get('context', ''))}")
            current_app.logger.info("=== END ENHANCED PROMPT ===")
            
            response = self.ai_service.generate_response(prompt, max_tokens=400)
            
            # Add common knowledge sources to context for tracking
            if common_knowledge_context.get('sources'):
                context.setdefault('sources', []).extend([
                    {
                        'type': 'common_knowledge',
                        'source': source.get('source', 'The Way of the Dog Anahata'),
                        'relevance_score': source.get('relevance_score', 0.0)
                    }
                    for source in common_knowledge_context['sources']
                ])
            
            # Validate response
            if not response or len(response.strip()) < 10:
                raise Exception("AI service returned empty or invalid response")
                
            return response
            
        except Exception as e:
            current_app.logger.error(f"Health response generation failed: {str(e)}")
            # Return a simple but helpful response with fallback common knowledge
            return self._generate_simple_response_with_common_knowledge(message)

    def _get_common_knowledge_context(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get relevant context from the common knowledge base"""
        try:
            common_knowledge_service = get_common_knowledge_service()
            
            if not common_knowledge_service.is_service_available():
                current_app.logger.info("Common knowledge base not available")
                return {'context': '', 'sources': [], 'enhanced': False}
            
            current_app.logger.info("Searching common knowledge base for relevant information")
            
            # Enhanced search with query augmentation
            enhanced_query_info = common_knowledge_service.enhance_query_with_common_knowledge(
                message, max_context_length=800
            )
            
            if enhanced_query_info.get('enhancement_applied'):
                return {
                    'context': enhanced_query_info['common_knowledge_context'],
                    'sources': enhanced_query_info['sources_used'],
                    'enhanced': True
                }
            else:
                # Direct search if enhancement didn't work
                success, results = common_knowledge_service.search_common_knowledge(message, top_k=3)
                if success and results:
                    context_snippets = [result['content'][:300] for result in results]
                    return {
                        'context': '\n\n'.join(context_snippets),
                        'sources': [{'source': result['source'], 'relevance_score': result['relevance_score']} for result in results],
                        'enhanced': False
                    }
            
            return {'context': '', 'sources': [], 'enhanced': False}
            
        except Exception as e:
            current_app.logger.error(f"Error getting common knowledge context: {str(e)}")
            return {'context': '', 'sources': [], 'enhanced': False}

    def _generate_health_intelligence_response_with_common_knowledge(self, message: str, context: Dict[str, Any], user_id: int, common_knowledge_context: Dict[str, Any]) -> str:
        """Generate response using Health Intelligence Service enhanced with common knowledge"""
        try:
            import asyncio
            current_app.logger.info("Using Health Intelligence Service with common knowledge enhancement")
            
            # Create or get event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Enhance the query with common knowledge if available
            enhanced_message = message
            if common_knowledge_context.get('context'):
                enhanced_message = f"""
Original Query: {message}

Additional Context from 'The Way of the Dog Anahata':
{common_knowledge_context['context']}

Please provide a comprehensive response that considers both the specific query and the relevant context from the book.
"""
            
            # Process health query with enhanced context
            result = loop.run_until_complete(
                self.health_intelligence_service.process_health_query(
                    user_id=user_id,
                    query=enhanced_message,
                    thread_id=None  # Could be passed from context if available
                )
            )
            
            # Extract response
            response = result.get('response')
            if response:
                current_app.logger.info(f"Enhanced Health Intelligence response generated: {response[:100]}...")
                
                # Add common knowledge attribution if used
                if common_knowledge_context.get('sources'):
                    response += f"\n\n*Additional insights from 'The Way of the Dog Anahata' were incorporated into this response.*"
                
                return response
            else:
                current_app.logger.warning("Health Intelligence Service returned empty response")
                return self._generate_simple_response_with_common_knowledge(message, common_knowledge_context)
                
        except Exception as e:
            current_app.logger.error(f"Error using enhanced Health Intelligence Service: {str(e)}")
            # Fallback to simple response with common knowledge
            current_app.logger.info("Falling back to simple health response with common knowledge")
            return self._generate_simple_health_response_with_common_knowledge(message, common_knowledge_context)

    def _generate_simple_response_with_common_knowledge(self, message: str, common_knowledge_context: Dict[str, Any] = None) -> str:
        """Generate a simple response with common knowledge integration for fallback scenarios"""
        try:
            if common_knowledge_context is None:
                common_knowledge_context = self._get_common_knowledge_context(message, {})
            
            # Get base response
            base_response = self._generate_simple_response(message)
            
            # Add common knowledge context if available and relevant
            if common_knowledge_context.get('context'):
                # Check if the common knowledge is relevant to the query
                context_lower = common_knowledge_context['context'].lower()
                query_terms = message.lower().split()
                
                # Simple relevance check
                relevance_score = sum(1 for term in query_terms if len(term) > 3 and term in context_lower) / max(len(query_terms), 1)
                
                if relevance_score > 0.2:  # If context seems relevant
                    additional_context = f"""

**Additional Insight from 'The Way of the Dog Anahata':**
{common_knowledge_context['context'][:300]}{"..." if len(common_knowledge_context['context']) > 300 else ""}

This information from the book may provide additional perspective on your question."""
                    
                    return base_response + additional_context
            
            return base_response
            
        except Exception as e:
            current_app.logger.error(f"Error in simple response with common knowledge: {str(e)}")
            return self._generate_simple_response(message)

    def _generate_simple_health_response_with_common_knowledge(self, message: str, common_knowledge_context: Dict[str, Any]) -> str:
        """Generate a simple health-focused response with common knowledge integration"""
        try:
            # Get base response
            base_response = self._generate_simple_health_response(message)
            
            # Add common knowledge context if available and relevant
            if common_knowledge_context.get('context'):
                # Check if the common knowledge is relevant to the query
                context_lower = common_knowledge_context['context'].lower()
                query_terms = message.lower().split()
                
                # Simple relevance check
                relevance_score = sum(1 for term in query_terms if len(term) > 3 and term in context_lower) / max(len(query_terms), 1)
                
                if relevance_score > 0.2:  # If context seems relevant
                    additional_context = f"""

**Additional Insight from 'The Way of the Dog Anahata':**
{common_knowledge_context['context'][:300]}{"..." if len(common_knowledge_context['context']) > 300 else ""}

This information from the book may provide additional perspective on your health question."""
                    
                    return base_response + additional_context
            
            return base_response
            
        except Exception as e:
            current_app.logger.error(f"Error in simple health response with common knowledge: {str(e)}")
            return self._generate_simple_health_response(message)

    def _is_health_query(self, message: str) -> bool:
        """Detect if the message is health-related and should use Health Intelligence Service"""
        health_keywords = [
            # Medical/Veterinary
            'vaccination', 'vaccine', 'vet', 'veterinarian', 'doctor', 'medical', 'medicine',
            'medication', 'prescription', 'dose', 'treatment', 'therapy', 'surgery', 'operation',
            'diagnosis', 'symptom', 'condition', 'disease', 'illness', 'infection',
            
            # Health conditions/symptoms
            'sick', 'pain', 'hurt', 'injury', 'wound', 'bleeding', 'vomiting', 'diarrhea',
            'fever', 'temperature', 'cough', 'sneeze', 'limping', 'seizure', 'paralysis',
            'swelling', 'rash', 'itching', 'scratching', 'lethargy', 'weakness', 'tired',
            'appetite', 'eating', 'drinking', 'weight', 'breathing', 'panting', 'drooling',
            
            # Body parts/systems
            'eye', 'ear', 'nose', 'mouth', 'teeth', 'gums', 'skin', 'coat', 'fur',
            'paw', 'leg', 'tail', 'stomach', 'kidney', 'liver', 'heart', 'lung',
            
            # Behavioral health
            'aggressive', 'anxious', 'stressed', 'depressed', 'hyperactive', 'restless',
            'behavior', 'behavioral', 'change', 'unusual', 'strange', 'different',
            
            # Emergency indicators
            'emergency', 'urgent', 'help', 'worried', 'concerned', 'scared', 'afraid',
            'suddenly', 'immediately', 'right now', 'can\'t', 'unable', 'won\'t',
            
            # Health maintenance
            'checkup', 'exam', 'test', 'blood work', 'x-ray', 'ultrasound', 'biopsy',
            'health', 'healthy', 'wellness', 'preventive', 'prevention', 'care'
        ]
        
        message_lower = message.lower()
        
        # Check for health keywords
        keyword_found = any(keyword in message_lower for keyword in health_keywords)
        
        # Check for question patterns that suggest health concern
        health_patterns = [
            'what should i do', 'is this normal', 'should i be worried', 'is it serious',
            'what does it mean', 'what could cause', 'why is my dog', 'my dog is',
            'my dog has', 'my dog seems', 'help with', 'advice', 'recommend'
        ]
        
        pattern_found = any(pattern in message_lower for pattern in health_patterns)
        
        return keyword_found or pattern_found
    
    def _generate_health_intelligence_response(self, message: str, context: Dict[str, Any], user_id: int) -> str:
        """Generate response using Health Intelligence Service for health-related queries"""
        try:
            import asyncio
            current_app.logger.info("Using Health Intelligence Service for health query")
            
            # Create or get event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Process health query
            result = loop.run_until_complete(
                self.health_intelligence_service.process_health_query(
                    user_id=user_id,
                    query=message,
                    thread_id=None  # Could be passed from context if available
                )
            )
            
            # Extract response
            response = result.get('response')
            if response:
                current_app.logger.info(f"Health Intelligence response generated: {response[:100]}...")
                return response
            else:
                current_app.logger.warning("Health Intelligence Service returned empty response")
                return self._generate_simple_response(message)
                
        except Exception as e:
            current_app.logger.error(f"Error using Health Intelligence Service: {str(e)}")
            # Fallback to simple response
            current_app.logger.info("Falling back to simple health response")
            return self._generate_simple_health_response(message)
    
    def _generate_simple_health_response(self, message: str) -> str:
        """Generate a simple health-focused response when Health Intelligence Service fails"""
        message_lower = message.lower()
        
        # Emergency indicators
        emergency_keywords = ['emergency', 'urgent', 'help', 'bleeding', 'seizure', 'can\'t breathe', 'unconscious', 'collapse']
        if any(keyword in message_lower for keyword in emergency_keywords):
            return """🚨 URGENT: If this is a medical emergency, please contact your veterinarian or emergency animal hospital immediately.

For immediate help:
- Call your vet's emergency line
- Go to the nearest animal emergency clinic
- Don't wait if your pet is in distress

I'm here to help with general pet care questions, but emergency situations require immediate professional veterinary attention."""

        # Specific health topics
        if any(word in message_lower for word in ['vaccination', 'vaccine', 'shot']):
            return """I understand you're asking about vaccinations. Keeping your pet's vaccinations up to date is crucial for their health and protection against serious diseases.

Key points about vaccinations:
- Core vaccines are essential for all dogs (rabies, DHPP)
- Non-core vaccines depend on lifestyle and risk factors
- Puppies need a series of vaccines starting at 6-8 weeks
- Adult dogs need regular boosters

I'd recommend discussing your pet's specific vaccination needs with your veterinarian, as they can create a personalized schedule based on your dog's age, health status, and lifestyle."""

        elif any(word in message_lower for word in ['vet', 'veterinarian', 'appointment', 'checkup']):
            return """Regular veterinary care is essential for your pet's health and wellbeing.

For routine care:
- Annual wellness exams for adult dogs
- Bi-annual exams for senior dogs (7+ years)
- More frequent visits for puppies or dogs with health conditions

Before your vet visit:
- Write down any questions or concerns
- Note any changes in behavior, appetite, or habits
- Bring vaccination records and current medications
- Consider bringing a stool sample if requested

If you have specific health concerns, don't hesitate to call your vet's office - they can advise whether you need an immediate appointment or if it can wait."""

        elif any(word in message_lower for word in ['sick', 'symptoms', 'not feeling well', 'lethargic', 'tired']):
            return """I understand you're concerned about your pet not feeling well. Changes in your dog's behavior or energy level can be concerning.

Watch for these signs that warrant veterinary attention:
- Loss of appetite for more than 24 hours
- Vomiting or diarrhea (especially if persistent)
- Lethargy or unusual tiredness
- Changes in drinking or urination
- Difficulty breathing
- Unusual behavior or hiding

For mild symptoms:
- Monitor closely for 24 hours
- Ensure access to fresh water
- Offer small amounts of bland food
- Keep them comfortable and quiet

If symptoms persist, worsen, or you're concerned, contact your veterinarian. Trust your instincts - you know your pet best."""

        else:
            return """Thank you for your health-related question. I want to make sure you get the best care information for your pet.

For specific health concerns, I always recommend consulting with your veterinarian, as they can:
- Perform a physical examination
- Consider your pet's complete medical history
- Provide personalized advice and treatment

General health tips:
- Monitor your pet's eating, drinking, and behavior daily
- Keep up with regular vet checkups and vaccinations
- Maintain a healthy diet and exercise routine
- Don't hesitate to call your vet if you notice changes

Is there a specific aspect of your pet's health you'd like to discuss? I'm here to help with general information and guidance."""
    
    def _generate_simple_response(self, message: str) -> str:
        """Generate a simple response when all AI services fail"""
        # Check for common pet care topics and provide basic responses
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['vaccination', 'vaccine', 'shot']):
            return "I understand you're asking about vaccinations. It's important to keep your pet's vaccinations up to date. I recommend consulting with your veterinarian about the right vaccination schedule for your pet based on their age, health, and lifestyle."
        
        elif any(word in message_lower for word in ['appointment', 'vet', 'veterinarian']):
            return "Regarding veterinary appointments, it's great that you're staying proactive about your pet's health. Regular check-ups help catch any issues early. If you have an upcoming appointment, make sure to bring any questions or concerns you have about your pet."
        
        elif any(word in message_lower for word in ['medication', 'medicine', 'drug']):
            return "When it comes to pet medications, always follow your veterinarian's instructions carefully. Make sure to give the full course of any prescribed medication, even if your pet seems better. Never give human medications to pets without veterinary approval."
        
        elif any(word in message_lower for word in ['diet', 'food', 'eating', 'nutrition']):
            return "Pet nutrition is crucial for their health and wellbeing. A balanced diet appropriate for your pet's age, size, and activity level is important. If you have concerns about your pet's diet, your veterinarian can recommend the best food options."
        
        elif any(word in message_lower for word in ['behavior', 'training', 'aggressive', 'anxious']):
            return "Pet behavior can be influenced by many factors including health, environment, and training. Consistent, positive reinforcement training works best. If you're seeing concerning behavioral changes, it's worth discussing with your vet as medical issues can sometimes affect behavior."
        
        else:
            return "Thank you for your question about your pet's care. While I'm experiencing some technical difficulties accessing your specific records right now, I'm here to help with any pet care concerns you may have. Could you provide a bit more detail about what you'd like to know?"

    def _is_reminder_request(self, message: str) -> bool:
        """Detect if the message is a reminder/scheduling request"""
        reminder_keywords = [
            'remind me', 'reminder', 'schedule', 'set reminder', 'create reminder', 
            'don\'t forget', 'help me remember', 'make sure i', 'set up a reminder',
            'appointment', 'due date', 'next friday', 'next week', 'tomorrow'
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in reminder_keywords)

    def _check_missing_reminder_info(self, reminder_details: Dict[str, Any], original_message: str) -> List[str]:
        """
        Check if any important reminder information is missing and needs clarification
        """
        missing_info = []
        
        try:
            # Check if time is missing for time-sensitive reminders
            if not reminder_details.get("due_time") and not reminder_details.get("reminder_time"):
                # Check if this is a time-sensitive reminder type
                reminder_type = reminder_details.get("reminder_type", "")
                time_sensitive_types = ["medication", "vet_appointment"]
                
                if (reminder_type in time_sensitive_types or 
                    any(keyword in original_message.lower() for keyword in 
                        ["appointment", "medication", "medicine", "pill", "dose", "visit"])):
                    missing_info.append("specific_time")
            
            # Check if title is too generic
            title = reminder_details.get("title", "")
            if len(title) < 10 or title.lower() in ["reminder", "don't forget", "remember"]:
                missing_info.append("specific_details")
            
            # Check if recurring reminder needs more details
            recurrence_type = reminder_details.get("recurrence_type", "none")
            if recurrence_type != "none" and not reminder_details.get("recurrence_interval"):
                missing_info.append("recurrence_details")
            
            return missing_info
            
        except Exception as e:
            current_app.logger.error(f"Error checking missing reminder info: {str(e)}")
            return []
    
    def _generate_clarification_request(self, reminder_details: Dict[str, Any], 
                                      missing_info: List[str], original_message: str) -> str:
        """
        Generate a clarification request for missing reminder information
        """
        try:
            title = reminder_details.get("title", "your reminder")
            due_date = reminder_details.get("due_date", "")
            reminder_type = reminder_details.get("reminder_type", "custom")
            
            # Format due date nicely
            if due_date:
                from datetime import datetime, time
                try:
                    date_obj = datetime.strptime(due_date, '%Y-%m-%d')
                    formatted_date = date_obj.strftime('%B %d, %Y')
                    day_name = date_obj.strftime('%A')
                except:
                    formatted_date = due_date
                    day_name = ""
            else:
                formatted_date = "the scheduled date"
                day_name = ""
            
            # Create type-specific emoji
            type_emojis = {
                "medication": "💊",
                "vaccination": "💉", 
                "vet_appointment": "🏥",
                "grooming": "✂️",
                "checkup": "🔍",
                "custom": "📝"
            }
            emoji = type_emojis.get(reminder_type, "📝")
            
            response = f"Great! I'd love to help you set up a {reminder_type.replace('_', ' ')} reminder {emoji}\n\n"
            response += f"I understand you want to remember: **{title}**\n"
            if formatted_date != "the scheduled date":
                response += f"Due: **{formatted_date}** ({day_name})\n\n"
            
            # Ask for specific missing information
            if "specific_time" in missing_info:
                response += "⏰ **What time should this reminder be for?**\n"
                response += "For example: '9:00 AM', '2:30 PM', or '10:00'\n\n"
                
                if reminder_type == "medication":
                    response += "💡 *This helps ensure you don't miss medication doses at the right time.*\n\n"
                elif reminder_type == "vet_appointment":
                    response += "💡 *This ensures you arrive on time for your appointment.*\n\n"
            
            if "specific_details" in missing_info:
                response += "📝 **Could you provide more specific details?**\n"
                if reminder_type == "medication":
                    response += "For example: 'Give Max his heartworm medication' or 'Luna's anxiety medication dose'\n\n"
                elif reminder_type == "vet_appointment":
                    response += "For example: 'Annual checkup for Buddy at VetCare Clinic' or 'Vaccination appointment for Luna'\n\n"
                else:
                    response += "For example: What exactly should you be reminded to do?\n\n"
            
            if "recurrence_details" in missing_info:
                response += "🔄 **How often should this repeat?**\n"
                response += "For example: 'Every day', 'Every week', 'Every month', or 'Every 3 months'\n\n"
            
            response += "Just reply with the missing information, and I'll create your perfect reminder! 🐾"
            
            return response
            
        except Exception as e:
            current_app.logger.error(f"Error generating clarification request: {str(e)}")
            return f"I'd like to create a reminder for you, but I need a bit more information. Could you please provide more specific details about what time this reminder should be for? For example, '9:00 AM' or '2:30 PM'?"
    
    def _extract_reminder_details_ai(self, message: str, user_id: int) -> Dict[str, Any]:
        """
        Enhanced AI extraction of reminder details with time support
        """
        try:
            from app.utils.openai_helper import get_openai_response
            
            # Enhanced prompt for time-based and recurring reminders
            extraction_prompt = f"""
You are an expert AI assistant for pet care reminder extraction. Analyze this message and extract reminder details.

User message: "{message}"

Extract the following information in JSON format:
{{
    "is_reminder_request": boolean,
    "confidence": float (0.0-1.0),
    "title": "specific reminder title",
    "description": "detailed description",
    "due_date": "YYYY-MM-DD",
    "due_time": "HH:MM" or null,
    "reminder_type": "vaccination|vet_appointment|medication|grooming|checkup|custom",
    "recurrence_type": "none|daily|weekly|monthly|yearly",
    "recurrence_interval": number or null,
    "extracted_info": {{
        "pet_name": "extracted pet name or null",
        "specific_activity": "what exactly to do",
        "urgency": "low|medium|high|critical",
        "time_mentioned": boolean,
        "recurring_mentioned": boolean
    }}
}}

Guidelines:
- Only mark as reminder request if user wants to be reminded of something in the future
- Extract specific times if mentioned (e.g., "9 AM", "2:30 PM", "10:00")
- Identify recurring patterns (daily medication, weekly grooming, monthly checkups)
- For medications: default to daily recurrence unless specified
- For vet appointments: default to none/one-time
- Set confidence based on clarity of intent and information completeness
- Extract pet names if mentioned
- Determine urgency based on reminder type and timing

Return ONLY the JSON object.
"""
            
            result = get_openai_response(extraction_prompt, max_tokens=500, temperature=0.3)
            
            if result and result.get("response"):
                try:
                    extracted_data = json.loads(result["response"])
                    current_app.logger.info(f"AI extracted reminder data: {extracted_data}")
                    
                    # Validate and enhance the extracted data
                    enhanced_data = self._validate_and_enhance_reminder_data(extracted_data, message)
                    return enhanced_data
                    
                except json.JSONDecodeError as e:
                    current_app.logger.warning(f"Failed to parse AI response JSON: {str(e)}")
                    return self._extract_reminder_details_manual(message)
            
            return self._extract_reminder_details_manual(message)
            
        except Exception as e:
            current_app.logger.error(f"Error in AI reminder extraction: {str(e)}")
            return self._extract_reminder_details_manual(message)
    
    def _validate_and_enhance_reminder_data(self, extracted_data: Dict[str, Any], original_message: str) -> Dict[str, Any]:
        """
        Validate and enhance the AI-extracted reminder data
        """
        try:
            from datetime import datetime, timedelta, time
            
            # Ensure all required fields exist
            enhanced_data = {
                "is_reminder_request": extracted_data.get("is_reminder_request", False),
                "confidence": extracted_data.get("confidence", 0.5),
                "title": extracted_data.get("title", ""),
                "description": extracted_data.get("description", original_message),
                "due_date": "",
                "due_time": extracted_data.get("due_time"),
                "reminder_type": extracted_data.get("reminder_type", "custom"),
                "recurrence_type": extracted_data.get("recurrence_type", "none"),
                "recurrence_interval": extracted_data.get("recurrence_interval", 1),
                "extracted_info": extracted_data.get("extracted_info", {})
            }
            
            # Validate and fix due_date
            due_date = extracted_data.get("due_date")
            if due_date:
                try:
                    # Validate date format
                    datetime.strptime(due_date, '%Y-%m-%d')
                    enhanced_data["due_date"] = due_date
                except ValueError:
                    # Try to parse and reformat
                    enhanced_data["due_date"] = self._parse_and_format_date(due_date, original_message)
            else:
                # Auto-generate due date based on message context
                enhanced_data["due_date"] = self._auto_generate_due_date(original_message)
            
            # Validate and normalize time format
            due_time = extracted_data.get("due_time")
            if due_time:
                enhanced_data["due_time"] = self._normalize_time_format(due_time)
            
            # Set default recurrence for medications
            if enhanced_data["reminder_type"] == "medication" and enhanced_data["recurrence_type"] == "none":
                if any(keyword in original_message.lower() for keyword in ["daily", "every day", "each day"]):
                    enhanced_data["recurrence_type"] = "daily"
                elif any(keyword in original_message.lower() for keyword in ["weekly", "every week"]):
                    enhanced_data["recurrence_type"] = "weekly"
            
            # Enhance title if too generic
            if len(enhanced_data["title"]) < 5:
                enhanced_data["title"] = self._generate_better_title(enhanced_data, original_message)
            
            return enhanced_data
            
        except Exception as e:
            current_app.logger.error(f"Error validating reminder data: {str(e)}")
            return extracted_data
    
    def _parse_and_format_date(self, date_str: str, original_message: str) -> str:
        """
        Parse various date formats and return YYYY-MM-DD
        """
        try:
            from datetime import datetime, timedelta
            import re
            
            today = datetime.now()
            
            # Handle relative dates
            if "today" in original_message.lower():
                return today.strftime('%Y-%m-%d')
            elif "tomorrow" in original_message.lower():
                return (today + timedelta(days=1)).strftime('%Y-%m-%d')
            elif "next week" in original_message.lower():
                return (today + timedelta(days=7)).strftime('%Y-%m-%d')
            elif "next month" in original_message.lower():
                return (today + timedelta(days=30)).strftime('%Y-%m-%d')
            
            # Handle specific day mentions
            days_map = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                'friday': 4, 'saturday': 5, 'sunday': 6
            }
            
            for day_name, day_num in days_map.items():
                if day_name in original_message.lower():
                    days_ahead = (day_num - today.weekday()) % 7
                    if days_ahead == 0:  # If it's today, assume next week
                        days_ahead = 7
                    return (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
            
            # Default to today instead of 7 days from now
            return today.strftime('%Y-%m-%d')
            
        except Exception as e:
            current_app.logger.error(f"Error parsing date: {str(e)}")
            from datetime import datetime, timedelta
            return datetime.now().strftime('%Y-%m-%d')
    
    def _auto_generate_due_date(self, message: str) -> str:
        """
        Auto-generate a due date based on message context
        """
        return self._parse_and_format_date("", message)
    
    def _normalize_time_format(self, time_str: str) -> str:
        """
        Normalize time format to HH:MM (24-hour format)
        """
        try:
            import re
            from datetime import datetime, time
            
            if not time_str:
                return None
            
            # Handle various time formats
            time_str = time_str.lower().strip()
            
            # Remove spaces and common variations
            time_str = re.sub(r'\s+', '', time_str)
            
            # Handle AM/PM format
            if 'am' in time_str or 'pm' in time_str:
                # Extract hour and minute
                time_match = re.search(r'(\d{1,2})(?::(\d{2}))?(?:\s*)?(am|pm)', time_str)
                if time_match:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2)) if time_match.group(2) else 0
                    period = time_match.group(3)
                    
                    # Convert to 24-hour format
                    if period == 'pm' and hour != 12:
                        hour += 12
                    elif period == 'am' and hour == 12:
                        hour = 0
                    
                    return f"{hour:02d}:{minute:02d}"
            
            # Handle 24-hour format
            time_match = re.search(r'(\d{1,2}):(\d{2})', time_str)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    return f"{hour:02d}:{minute:02d}"
            
            # Handle hour only
            time_match = re.search(r'^(\d{1,2})$', time_str)
            if time_match:
                hour = int(time_match.group(1))
                if 0 <= hour <= 23:
                    return f"{hour:02d}:00"
                elif 1 <= hour <= 12:  # Assume PM for afternoon hours
                    if hour != 12:
                        hour += 12
                    return f"{hour:02d}:00"
            
            return None
            
        except Exception as e:
            current_app.logger.error(f"Error normalizing time format: {str(e)}")
            return None
    
    def _generate_better_title(self, reminder_data: Dict[str, Any], original_message: str) -> str:
        """
        Generate a better title for the reminder based on type and message
        """
        try:
            reminder_type = reminder_data.get("reminder_type", "custom")
            pet_name = reminder_data.get("extracted_info", {}).get("pet_name", "your pet")
            
            # Type-specific title templates
            if reminder_type == "medication":
                return f"Give {pet_name} medication"
            elif reminder_type == "vaccination":
                return f"{pet_name}'s vaccination appointment"
            elif reminder_type == "vet_appointment":
                return f"Vet appointment for {pet_name}"
            elif reminder_type == "grooming":
                return f"{pet_name}'s grooming appointment"
            elif reminder_type == "checkup":
                return f"{pet_name}'s health checkup"
            else:
                # Extract key action words from message
                action_words = ["give", "take", "schedule", "book", "feed", "walk", "train"]
                for word in action_words:
                    if word in original_message.lower():
                        return f"{word.capitalize()} {pet_name}"
                
                return f"Reminder for {pet_name}"
                
        except Exception as e:
            current_app.logger.error(f"Error generating better title: {str(e)}")
            return "Pet care reminder"

    def _extract_reminder_details_manual(self, message: str) -> Dict[str, Any]:
        """Manual fallback for reminder extraction with enhanced time parsing"""
        import re
        from datetime import datetime, timedelta
        
        # Default values
        extracted = {
            "is_reminder_request": True,
            "title": "",
            "description": message,
            "due_date": "",
            "due_time": "09:00",  # Default time
            "reminder_type": "custom",
            "confidence": 0.6,
            "extracted_info": {"specific_time_mentioned": False}
        }
        
        # Extract time first
        time_patterns = [
            r"(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)",  # 10:45 PM
            r"(\d{1,2}):(\d{2})",  # 22:45 (24-hour)
            r"(\d{1,2})\s*(AM|PM|am|pm)",  # 10 PM
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, message)
            if match:
                groups = match.groups()
                if len(groups) == 3:  # 12-hour format with AM/PM
                    hour = int(groups[0])
                    minute = int(groups[1])
                    ampm = groups[2].upper()
                    
                    if ampm == "PM" and hour != 12:
                        hour += 12
                    elif ampm == "AM" and hour == 12:
                        hour = 0
                    
                    extracted["due_time"] = f"{hour:02d}:{minute:02d}"
                    extracted["extracted_info"]["specific_time_mentioned"] = True
                elif len(groups) == 2 and groups[1] in ["AM", "PM", "am", "pm"]:  # Hour only with AM/PM
                    hour = int(groups[0])
                    ampm = groups[1].upper()
                    
                    if ampm == "PM" and hour != 12:
                        hour += 12
                    elif ampm == "AM" and hour == 12:
                        hour = 0
                    
                    extracted["due_time"] = f"{hour:02d}:00"
                    extracted["extracted_info"]["specific_time_mentioned"] = True
                elif len(groups) == 2:  # 24-hour format
                    hour = int(groups[0])
                    minute = int(groups[1])
                    extracted["due_time"] = f"{hour:02d}:{minute:02d}"
                    extracted["extracted_info"]["specific_time_mentioned"] = True
                break
        
        # Extract title
        if "feed" in message.lower() or "food" in message.lower():
            extracted["title"] = "Dog Food Feeding"
        else:
            extracted["title"] = f"Reminder: {message[:50]}..."
        
        # Extract due date
        today = datetime.now()
        message_lower = message.lower()
        
        if "today" in message_lower:
            extracted["due_date"] = today.strftime("%Y-%m-%d")
        elif "tomorrow" in message_lower:
            extracted["due_date"] = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            extracted["due_date"] = today.strftime("%Y-%m-%d")
        
        return extracted

    def _create_health_reminder(self, user_id: int, reminder_details: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """Create a health reminder that will appear in the reminders dashboard"""
        try:
            from app.services.health_service import HealthService
            from app import db
            from datetime import datetime, time
            
            # Get database session
            health_service = HealthService(db.session)
            
            # Prepare reminder data
            # Parse due_time if provided
            due_time_obj = None
            if "due_time" in reminder_details and reminder_details["due_time"]:
                time_str = reminder_details["due_time"]
                try:
                    time_parts = time_str.split(":")
                    due_time_obj = time(int(time_parts[0]), int(time_parts[1]))
                    current_app.logger.info(f"🕐 Parsed due_time '{time_str}' as {due_time_obj} (user local time)")
                except (ValueError, IndexError) as e:
                    current_app.logger.warning(f"Error parsing due_time '{time_str}': {e}")
                    due_time_obj = time(9, 0)  # Default to 9 AM
            else:
                due_time_obj = time(9, 0)  # Default to 9 AM
            
            # 🎯 FIX: Determine days_before_reminder based on reminder context
            # For immediate reminders (same day), use 0 days
            days_before_reminder = 0  # Default for immediate reminders
            
            # Check if this is a future appointment/event that needs advance notice
            due_date_obj = datetime.strptime(reminder_details["due_date"], '%Y-%m-%d').date()
            today = datetime.now().date()
            
            reminder_type = reminder_details.get("reminder_type", "custom")
            
            if due_date_obj > today:
                # Future event - check if it's a medical appointment that needs advance notice
                if reminder_type in ["vet_appointment", "vaccination", "checkup"]:
                    days_before_reminder = 1  # 1 day advance notice for appointments
                else:
                    days_before_reminder = 0  # Immediate for other future reminders
            
            current_app.logger.info(f"🗓️  Setting days_before_reminder={days_before_reminder} for {reminder_type} reminder")
            current_app.logger.info(f"🌍 User local time to be stored: {due_date_obj} {due_time_obj}")
            
            reminder_data = {
                "reminder_type": reminder_details.get("reminder_type", "custom"),
                "title": reminder_details.get("title", "Reminder"),
                "description": reminder_details.get("description", ""),
                "due_date": due_date_obj,
                "send_email": True,
                "send_push": True,
                "due_time": due_time_obj,  # This is user's local time
                "days_before_reminder": days_before_reminder,  # 🎯 FIXED: Now dynamic based on context
                "hours_before_reminder": 0,  # 🎯 ADDED: Explicit hours_before_reminder
                "_user_local_time": True  # 🎯 ADDED: Flag to indicate this is user local time
            }
            
            # Create the reminder
            reminder = health_service.create_reminder(user_id, reminder_data)
            
            current_app.logger.info(f"✅ Created health reminder {reminder.id} for user {user_id}: {reminder.title}")
            current_app.logger.info(f"📅 Stored due_time as: {reminder.due_time} (user local timezone)")
            
            return True, "Reminder created successfully", {
                "reminder_id": reminder.id,
                "title": reminder.title,
                "due_date": reminder.due_date.isoformat(),
                "type": reminder.reminder_type.value,
                "status": reminder.status.value
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Error creating health reminder: {str(e)}")
            return False, f"Failed to create reminder: {str(e)}", {}

    def _generate_reminder_confirmation_response(self, reminder_details: Dict[str, Any], 
                                               reminder_info: Dict[str, Any], 
                                               original_message: str, 
                                               user_context: Dict[str, Any] = None) -> str:
        """Generate a personalized confirmation response for created reminders with timezone awareness"""
        try:
            title = reminder_details.get("title", "your reminder")
            due_date = reminder_details.get("due_date", "")
            due_time = reminder_details.get("due_time", "")
            reminder_type = reminder_details.get("reminder_type", "custom")
            pet_name = reminder_details.get("extracted_info", {}).get("pet_name", "your pet")
            
            # Get timezone context for better formatting
            user_timezone = user_context.get('timezone', 'UTC') if user_context else 'UTC'
            timezone_abbr = user_context.get('timezone_abbreviation', 'UTC') if user_context else 'UTC'
            time_format_24h = user_context.get('time_format_24h', False) if user_context else False
            
            # Format the due date and time nicely
            if due_date:
                try:
                    date_obj = datetime.strptime(due_date, '%Y-%m-%d')
                    formatted_date = date_obj.strftime('%B %d, %Y')  # e.g., "January 15, 2024"
                    day_name = date_obj.strftime('%A')  # e.g., "Friday"
                except:
                    formatted_date = due_date
                    day_name = ""
            else:
                formatted_date = "the scheduled date"
                day_name = ""
            
            # Format time according to user preference
            if due_time:
                try:
                    time_obj = datetime.strptime(due_time, '%H:%M').time()
                    if time_format_24h:
                        formatted_time = time_obj.strftime('%H:%M')
                    else:
                        formatted_time = time_obj.strftime('%I:%M %p')
                except:
                    formatted_time = due_time
            else:
                formatted_time = ""
            
            # Create personalized responses based on reminder type
            type_responses = {
                "medication": f"Perfect! I've set up a medication reminder for {pet_name} on {formatted_date} ({day_name}){f' at {formatted_time}' if formatted_time else ''} ({timezone_abbr}). 💊",
                "vaccination": f"Got it! I've scheduled a vaccination reminder for {pet_name} on {formatted_date} ({day_name}){f' at {formatted_time}' if formatted_time else ''} ({timezone_abbr}). 💉",
                "vet_appointment": f"All set! I've created a vet appointment reminder for {pet_name} on {formatted_date} ({day_name}){f' at {formatted_time}' if formatted_time else ''} ({timezone_abbr}). 🏥",
                "grooming": f"Noted! I've set up a grooming reminder for {pet_name} on {formatted_date} ({day_name}){f' at {formatted_time}' if formatted_time else ''} ({timezone_abbr}). ✂️",
                "checkup": f"Perfect! I've scheduled a checkup reminder for {pet_name} on {formatted_date} ({day_name}){f' at {formatted_time}' if formatted_time else ''} ({timezone_abbr}). 🔍",
                "custom": f"All done! I've created your reminder for {formatted_date} ({day_name}){f' at {formatted_time}' if formatted_time else ''} ({timezone_abbr}). 📝"
            }
            
            main_response = type_responses.get(reminder_type, type_responses["custom"])
            
            # Add timezone-aware additional information
            additional_info = f"""

I'll make sure to notify you ahead of time so you don't forget! The reminder is set according to your timezone ({user_timezone}), and you can view and manage all your reminders in the Reminders section of your dashboard.

**Reminder Details:**
• **What:** {title}
• **When:** {formatted_date}{f' ({day_name})' if day_name else ''}{f' at {formatted_time}' if formatted_time else ''}
• **Timezone:** {timezone_abbr}
• **Type:** {reminder_type.replace('_', ' ').title()}

Is there anything else I can help you with regarding {pet_name}'s care?
"""
            
            return main_response + additional_info
            
        except Exception as e:
            current_app.logger.error(f"Error generating timezone-aware reminder confirmation: {str(e)}")
            return f"✅ Great! I've successfully created your reminder and it will appear in your Reminders dashboard. You'll be notified when it's time!" 

    def _get_user_timezone_context(self, user_id: int) -> Dict[str, Any]:
        """
        Get comprehensive user timezone context for reminder processing
        """
        try:
            from app.models.user import User
            from app.services.ai_time_manager import get_ai_time_manager
            import pytz
            
            user = User.query.get(user_id)
            if not user:
                current_app.logger.warning(f"User {user_id} not found, using UTC timezone")
                return {
                    'timezone': 'UTC',
                    'timezone_abbreviation': 'UTC',
                    'current_local_time': datetime.now(timezone.utc),
                    'user_preferences': {},
                    'time_format_24h': False
                }
            
            # Get user's timezone or default to UTC
            user_timezone = user.timezone or 'UTC'
            
            try:
                user_tz = pytz.timezone(user_timezone)
                current_local_time = datetime.now(user_tz)
                timezone_abbreviation = current_local_time.strftime('%Z')
            except Exception as tz_error:
                current_app.logger.warning(f"Invalid user timezone {user_timezone}, using UTC: {tz_error}")
                user_tz = pytz.UTC
                current_local_time = datetime.now(pytz.UTC)
                timezone_abbreviation = 'UTC'
                user_timezone = 'UTC'
            
            ai_time_manager = get_ai_time_manager()
            
            context = {
                'timezone': user_timezone,
                'timezone_obj': user_tz,
                'timezone_abbreviation': timezone_abbreviation,
                'current_local_time': current_local_time,
                'user_preferences': user.preferred_reminder_times or {},
                'time_format_24h': user.time_format_24h or False,
                'location_city': user.location_city,
                'location_country': user.location_country,
                'user_id': user_id
            }
            
            current_app.logger.info(f"🌍 Retrieved timezone context for user {user_id}: {user_timezone} ({timezone_abbreviation})")
            return context
            
        except Exception as e:
            current_app.logger.error(f"Error getting user timezone context: {str(e)}")
            return {
                'timezone': 'UTC',
                'timezone_abbreviation': 'UTC',
                'current_local_time': datetime.now(timezone.utc),
                'user_preferences': {},
                'time_format_24h': False
            }

    def _extract_reminder_details_ai_with_timezone(self, message: str, user_id: int, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced AI extraction of reminder details with timezone context
        """
        try:
            from app.utils.openai_helper import get_openai_response
            
            # Get timezone information for AI prompt
            user_timezone = user_context.get('timezone', 'UTC')
            current_local_time = user_context.get('current_local_time')
            timezone_abbr = user_context.get('timezone_abbreviation', 'UTC')
            time_format_24h = user_context.get('time_format_24h', False)
            
            # Format current time for AI context
            if current_local_time:
                current_time_str = current_local_time.strftime('%Y-%m-%d %H:%M:%S %Z')
                current_date_str = current_local_time.strftime('%A, %B %d, %Y')
                current_time_only_str = current_local_time.strftime('%H:%M' if time_format_24h else '%I:%M %p')
            else:
                current_time_str = "Unknown"
                current_date_str = "Unknown"
                current_time_only_str = "Unknown"
            
            # Enhanced prompt for timezone-aware time extraction
            extraction_prompt = f"""
You are an expert AI assistant for pet care reminder extraction with advanced timezone awareness.

TIMEZONE CONTEXT:
- User's timezone: {user_timezone} ({timezone_abbr})
- Current user local time: {current_time_str}
- Current date: {current_date_str}
- User prefers: {'24-hour' if time_format_24h else '12-hour'} time format

User message: "{message}"

Extract reminder details considering the user's timezone context. When the user mentions times like "9 AM" or "tomorrow at 2 PM", these refer to their LOCAL timezone ({timezone_abbr}).

Extract the following information in JSON format:
{{
    "is_reminder_request": boolean,
    "confidence": float (0.0-1.0),
    "title": "specific reminder title",
    "description": "detailed description",
    "due_date": "YYYY-MM-DD (in user's timezone)",
    "due_time": "HH:MM (in user's timezone, 24-hour format)",
    "reminder_type": "vaccination|vet_appointment|medication|grooming|checkup|custom",
    "recurrence_type": "none|daily|weekly|monthly|yearly",
    "recurrence_interval": number or null,
    "timezone_aware": true,
    "extracted_info": {{
        "pet_name": "extracted pet name or null",
        "specific_activity": "what exactly to do",
        "urgency": "low|medium|high|critical",
        "time_mentioned": boolean,
        "recurring_mentioned": boolean,
        "relative_time_used": boolean,
        "timezone_context": "{timezone_abbr}"
    }}
}}

IMPORTANT TIMEZONE RULES:
1. All times should be interpreted in the user's timezone ({timezone_abbr})
2. Convert relative times (today, tomorrow, next week) based on current local time: {current_date_str}
3. If no specific time is mentioned, suggest optimal times based on reminder type
4. For "today" appointments, ensure the time hasn't already passed (current time: {current_time_only_str})
5. Always set "timezone_aware": true to indicate proper timezone processing

Guidelines:
- Only mark as reminder request if user wants to be reminded of something in the future
- Extract specific times if mentioned (e.g., "9 AM", "2:30 PM", "14:00")
- Identify recurring patterns (daily medication, weekly grooming, monthly checkups)
- For medications: default to daily recurrence unless specified
- For vet appointments: default to none/one-time
- Set confidence based on clarity of intent and information completeness
- Extract pet names if mentioned
- Determine urgency based on reminder type and timing
- If time has passed today, automatically move to next appropriate day

Return ONLY the JSON object.
"""
            
            result = get_openai_response(extraction_prompt, max_tokens=600, temperature=0.2)
            
            if result and result.get("response"):
                try:
                    extracted_data = json.loads(result["response"])
                    current_app.logger.info(f"🤖 AI extracted timezone-aware reminder data: {extracted_data}")
                    
                    # Validate and enhance the extracted data with timezone context
                    enhanced_data = self._validate_and_enhance_reminder_data_with_timezone(extracted_data, message, user_context)
                    return enhanced_data
                    
                except json.JSONDecodeError as e:
                    current_app.logger.warning(f"Failed to parse AI response JSON: {str(e)}")
                    return self._extract_reminder_details_manual_with_timezone(message, user_context)
            
            return self._extract_reminder_details_manual_with_timezone(message, user_context)
            
        except Exception as e:
            current_app.logger.error(f"Error in AI reminder extraction: {str(e)}")
            return self._extract_reminder_details_manual_with_timezone(message, user_context)

    def _validate_and_enhance_reminder_data_with_timezone(self, extracted_data: Dict[str, Any], original_message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and enhance the AI-extracted reminder data with timezone context
        """
        try:
            from datetime import datetime, timedelta, time
            import pytz
            
            user_timezone = user_context.get('timezone', 'UTC')
            current_local_time = user_context.get('current_local_time')
            timezone_obj = user_context.get('timezone_obj', pytz.UTC)
            
            # Ensure all required fields exist
            enhanced_data = {
                "is_reminder_request": extracted_data.get("is_reminder_request", False),
                "confidence": extracted_data.get("confidence", 0.5),
                "title": extracted_data.get("title", ""),
                "description": extracted_data.get("description", original_message),
                "due_date": "",
                "due_time": extracted_data.get("due_time"),
                "reminder_type": extracted_data.get("reminder_type", "custom"),
                "recurrence_type": extracted_data.get("recurrence_type", "none"),
                "recurrence_interval": extracted_data.get("recurrence_interval", 1),
                "timezone_aware": True,
                "user_timezone": user_timezone,
                "extracted_info": extracted_data.get("extracted_info", {})
            }
            
            # Validate and fix due_date with timezone awareness
            due_date = extracted_data.get("due_date")
            if due_date:
                try:
                    # Validate date format
                    parsed_date = datetime.strptime(due_date, '%Y-%m-%d').date()
                    enhanced_data["due_date"] = parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    # Try to parse and reformat with timezone context
                    enhanced_data["due_date"] = self._parse_and_format_date_with_timezone(due_date, original_message, user_context)
            else:
                # Auto-generate due date based on message context with timezone
                enhanced_data["due_date"] = self._auto_generate_due_date_with_timezone(original_message, user_context)
            
            # Validate and normalize time format with timezone context
            due_time = extracted_data.get("due_time")
            if due_time:
                enhanced_data["due_time"] = self._normalize_time_format(due_time)
            else:
                # Use AI to suggest optimal time based on reminder type
                enhanced_data["due_time"] = self._suggest_optimal_time_for_type(
                    enhanced_data["reminder_type"], 
                    user_context
                )
            
            # Validate that the time hasn't already passed today
            if enhanced_data["due_date"] and enhanced_data["due_time"] and current_local_time:
                due_date_obj = datetime.strptime(enhanced_data["due_date"], '%Y-%m-%d').date()
                due_time_obj = datetime.strptime(enhanced_data["due_time"], '%H:%M').time()
                
                if due_date_obj == current_local_time.date():
                    # Check if time has already passed today
                    if due_time_obj <= current_local_time.time():
                        current_app.logger.info(f"⏰ Time {due_time_obj} has passed today, moving to tomorrow")
                        due_date_obj = due_date_obj + timedelta(days=1)
                        enhanced_data["due_date"] = due_date_obj.strftime('%Y-%m-%d')
            
            # Set default recurrence for medications with timezone awareness
            if enhanced_data["reminder_type"] == "medication" and enhanced_data["recurrence_type"] == "none":
                if any(keyword in original_message.lower() for keyword in ["daily", "every day", "each day"]):
                    enhanced_data["recurrence_type"] = "daily"
                elif any(keyword in original_message.lower() for keyword in ["weekly", "every week"]):
                    enhanced_data["recurrence_type"] = "weekly"
                else:
                    enhanced_data["recurrence_type"] = "daily"  # Default for medications
            
            # Enhance title if too generic
            if len(enhanced_data["title"]) < 5:
                enhanced_data["title"] = self._generate_better_title(enhanced_data, original_message)
            
            # Add timezone metadata
            enhanced_data["timezone_metadata"] = {
                "user_timezone": user_timezone,
                "timezone_abbreviation": user_context.get('timezone_abbreviation', 'UTC'),
                "local_time_extracted": True,
                "extraction_timestamp": current_local_time.isoformat() if current_local_time else None
            }
            
            current_app.logger.info(f"✅ Enhanced reminder data with timezone: {enhanced_data}")
            return enhanced_data
            
        except Exception as e:
            current_app.logger.error(f"Error validating reminder data with timezone: {str(e)}")
            return extracted_data

    def _extract_reminder_details_manual_with_timezone(self, message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Manual fallback for reminder extraction with enhanced timezone-aware time parsing"""
        import re
        from datetime import datetime, timedelta, time
        
        user_timezone = user_context.get('timezone', 'UTC')
        current_local_time = user_context.get('current_local_time')
        
        # Default values
        extracted = {
            "is_reminder_request": True,
            "title": "",
            "description": message,
            "due_date": "",
            "due_time": "09:00",  # Default time
            "reminder_type": "custom",
            "confidence": 0.6,
            "timezone_aware": True,
            "user_timezone": user_timezone,
            "extracted_info": {
                "specific_time_mentioned": False,
                "timezone_context": user_context.get('timezone_abbreviation', 'UTC')
            }
        }
        
        # Extract time with timezone awareness
        time_patterns = [
            r"(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)",  # 10:45 PM
            r"(\d{1,2}):(\d{2})",  # 22:45 (24-hour)
            r"(\d{1,2})\s*(AM|PM|am|pm)",  # 10 PM
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, message)
            if match:
                groups = match.groups()
                if len(groups) == 3:  # 12-hour format with AM/PM
                    hour = int(groups[0])
                    minute = int(groups[1])
                    ampm = groups[2].upper()
                    
                    if ampm == "PM" and hour != 12:
                        hour += 12
                    elif ampm == "AM" and hour == 12:
                        hour = 0
                    
                    extracted["due_time"] = f"{hour:02d}:{minute:02d}"
                    extracted["extracted_info"]["specific_time_mentioned"] = True
                elif len(groups) == 2 and groups[1] in ["AM", "PM", "am", "pm"]:  # Hour only with AM/PM
                    hour = int(groups[0])
                    ampm = groups[1].upper()
                    
                    if ampm == "PM" and hour != 12:
                        hour += 12
                    elif ampm == "AM" and hour == 12:
                        hour = 0
                    
                    extracted["due_time"] = f"{hour:02d}:00"
                    extracted["extracted_info"]["specific_time_mentioned"] = True
                elif len(groups) == 2:  # 24-hour format
                    hour = int(groups[0])
                    minute = int(groups[1])
                    extracted["due_time"] = f"{hour:02d}:{minute:02d}"
                    extracted["extracted_info"]["specific_time_mentioned"] = True
                break
        
        # If no time mentioned, use optimal time for reminder type
        if not extracted["extracted_info"]["specific_time_mentioned"]:
            extracted["due_time"] = self._suggest_optimal_time_for_type(
                extracted["reminder_type"], 
                user_context
            )
        
        # Extract title with better logic
        if "feed" in message.lower() or "food" in message.lower():
            extracted["title"] = "Pet Feeding Reminder"
        elif "medication" in message.lower() or "medicine" in message.lower():
            extracted["title"] = "Medication Reminder"
        elif "vet" in message.lower() or "appointment" in message.lower():
            extracted["title"] = "Vet Appointment"
        else:
            extracted["title"] = f"Pet Care Reminder: {message[:30]}..."
        
        # Extract due date with timezone awareness
        extracted["due_date"] = self._parse_relative_date_with_timezone(message, user_context)
        
        # Validate that the time hasn't already passed today
        if extracted["due_date"] and extracted["due_time"] and current_local_time:
            due_date_obj = datetime.strptime(extracted["due_date"], '%Y-%m-%d').date()
            due_time_obj = datetime.strptime(extracted["due_time"], '%H:%M').time()
            
            if due_date_obj == current_local_time.date():
                # Check if time has already passed today
                if due_time_obj <= current_local_time.time():
                    current_app.logger.info(f"⏰ Manual extraction: Time {due_time_obj} has passed today, moving to tomorrow")
                    due_date_obj = due_date_obj + timedelta(days=1)
                    extracted["due_date"] = due_date_obj.strftime('%Y-%m-%d')
        
        return extracted

    def _suggest_optimal_time_for_type(self, reminder_type: str, user_context: Dict[str, Any]) -> str:
        """Suggest optimal time for reminder type based on user context"""
        try:
            from app.services.ai_time_manager import get_ai_time_manager
            
            ai_time_manager = get_ai_time_manager()
            user_timezone = user_context.get('timezone', 'UTC')
            user_preferences = user_context.get('user_preferences', {})
            
            time_insight = ai_time_manager.suggest_optimal_reminder_time(
                reminder_type=reminder_type,
                user_timezone=user_timezone,
                user_preferences=user_preferences
            )
            
            return time_insight.optimal_time.strftime('%H:%M')
            
        except Exception as e:
            current_app.logger.warning(f"Error suggesting optimal time: {str(e)}")
            # Fallback to default times
            default_times = {
                'vaccination': '09:00',
                'vet_appointment': '08:30',
                'medication': '20:00',
                'grooming': '10:00',
                'checkup': '09:30',
                'custom': '12:00'
            }
            return default_times.get(reminder_type, '09:00')

    def _parse_relative_date_with_timezone(self, message: str, user_context: Dict[str, Any]) -> str:
        """Parse relative dates with timezone awareness"""
        try:
            current_local_time = user_context.get('current_local_time')
            if not current_local_time:
                return datetime.now().strftime('%Y-%m-%d')
            
            message_lower = message.lower()
            
            if "today" in message_lower:
                return current_local_time.strftime('%Y-%m-%d')
            elif "tomorrow" in message_lower:
                tomorrow = current_local_time + timedelta(days=1)
                return tomorrow.strftime('%Y-%m-%d')
            elif "next week" in message_lower:
                next_week = current_local_time + timedelta(days=7)
                return next_week.strftime('%Y-%m-%d')
            elif "next month" in message_lower:
                next_month = current_local_time + timedelta(days=30)
                return next_month.strftime('%Y-%m-%d')
            else:
                # Check for specific day names
                days_map = {
                    'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                    'friday': 4, 'saturday': 5, 'sunday': 6
                }
                
                for day_name, day_num in days_map.items():
                    if day_name in message_lower:
                        days_ahead = (day_num - current_local_time.weekday()) % 7
                        if days_ahead == 0:  # If it's today, assume next week
                            days_ahead = 7
                        target_date = current_local_time + timedelta(days=days_ahead)
                        return target_date.strftime('%Y-%m-%d')
                
                # Default to today
                return current_local_time.strftime('%Y-%m-%d')
                
        except Exception as e:
            current_app.logger.error(f"Error parsing relative date: {str(e)}")
            return datetime.now().strftime('%Y-%m-%d')

    def _parse_and_format_date_with_timezone(self, date_str: str, original_message: str, user_context: Dict[str, Any]) -> str:
        """Parse various date formats and return YYYY-MM-DD with timezone awareness"""
        try:
            current_local_time = user_context.get('current_local_time')
            if not current_local_time:
                return datetime.now().strftime('%Y-%m-%d')
            
            # Try standard date formats first
            date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y']
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            
            # Fall back to relative date parsing
            return self._parse_relative_date_with_timezone(original_message, user_context)
            
        except Exception as e:
            current_app.logger.error(f"Error parsing date with timezone: {str(e)}")
            return datetime.now().strftime('%Y-%m-%d')

    def _auto_generate_due_date_with_timezone(self, message: str, user_context: Dict[str, Any]) -> str:
        """Auto-generate a due date based on message context with timezone awareness"""
        return self._parse_relative_date_with_timezone(message, user_context)

    def _create_health_reminder_with_timezone(self, user_id: int, reminder_details: Dict[str, Any], user_context: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """Create a health reminder with proper timezone handling"""
        try:
            from app.services.health_service import HealthService
            from app import db
            from datetime import datetime, time
            import pytz
            from flask import current_app
            
            # Get database session
            health_service = HealthService(db.session)
            
            # Get timezone context
            user_timezone = user_context.get('timezone', 'UTC')
            timezone_obj = user_context.get('timezone_obj', pytz.UTC)
            
            current_app.logger.info(f"🌍 Creating reminder with timezone context: {user_timezone}")
            
            # Parse due_time if provided (this is in user's local time)
            due_time_obj = None
            if "due_time" in reminder_details and reminder_details["due_time"]:
                time_str = reminder_details["due_time"]
                try:
                    time_parts = time_str.split(":")
                    due_time_obj = time(int(time_parts[0]), int(time_parts[1]))
                    current_app.logger.info(f"🕐 Parsed due_time '{time_str}' as {due_time_obj} (user local time in {user_timezone})")
                except (ValueError, IndexError) as e:
                    current_app.logger.warning(f"Error parsing due_time '{time_str}': {e}")
                    due_time_obj = time(9, 0)  # Default to 9 AM
            else:
                due_time_obj = time(9, 0)  # Default to 9 AM
            
            # Parse due_date (this is in user's local timezone)
            due_date_obj = datetime.strptime(reminder_details["due_date"], '%Y-%m-%d').date()
            
            # Create timezone-aware due datetime in user's local time
            due_datetime_local = datetime.combine(due_date_obj, due_time_obj)
            due_datetime_local = timezone_obj.localize(due_datetime_local)
            
            # Convert to UTC for storage
            due_datetime_utc = due_datetime_local.astimezone(pytz.UTC)
            
            current_app.logger.info(f"📅 Due datetime in user's timezone ({user_timezone}): {due_datetime_local}")
            current_app.logger.info(f"📅 Due datetime in UTC (for storage): {due_datetime_utc}")
            
            # Determine days_before_reminder based on reminder context
            days_before_reminder = 0  # Default for immediate reminders
            today_local = user_context.get('current_local_time', datetime.now(timezone_obj)).date()
            reminder_type = reminder_details.get("reminder_type", "custom")
            
            if due_date_obj > today_local:
                # Future event - check if it's a medical appointment that needs advance notice
                if reminder_type in ["vet_appointment", "vaccination", "checkup"]:
                    days_before_reminder = 1  # 1 day advance notice for appointments
                else:
                    days_before_reminder = 0  # Immediate for other future reminders
            
            current_app.logger.info(f"🗓️  Setting days_before_reminder={days_before_reminder} for {reminder_type} reminder")
            
            # Prepare reminder data with timezone-aware storage
            reminder_data = {
                "reminder_type": reminder_details.get("reminder_type", "custom"),
                "title": reminder_details.get("title", "Reminder"),
                "description": reminder_details.get("description", ""),
                "due_date": due_datetime_utc,  # Store as UTC datetime
                "send_email": True,
                "send_push": True,
                "days_before_reminder": days_before_reminder,
                "hours_before_reminder": 0,
                "recurrence_type": reminder_details.get("recurrence_type", "none"),
                "recurrence_interval": reminder_details.get("recurrence_interval", 1),
                "_timezone_metadata": {
                    "user_timezone": user_timezone,
                    "original_local_time": due_datetime_local.isoformat(),
                    "storage_utc_time": due_datetime_utc.isoformat(),
                    "timezone_aware_creation": True
                }
            }
            
            # Create the reminder
            reminder = health_service.create_reminder(user_id, reminder_data)
            
            current_app.logger.info(f"✅ Created timezone-aware health reminder {reminder.id} for user {user_id}: {reminder.title}")
            current_app.logger.info(f"📅 Stored due_date as UTC: {reminder.due_date} (original local: {due_datetime_local})")
            
            return True, "Reminder created successfully", {
                "reminder_id": reminder.id,
                "title": reminder.title,
                "due_date": reminder.due_date.isoformat() if hasattr(reminder.due_date, 'isoformat') else str(reminder.due_date),
                "type": reminder.reminder_type.value,
                "status": reminder.status.value,
                "user_timezone": user_timezone,
                "local_due_time": due_datetime_local.isoformat(),
                "timezone_aware": True
            }
            
        except Exception as e:
            # Use print as fallback if current_app isn't available
            try:
                from flask import current_app
                current_app.logger.error(f"❌ Error creating timezone-aware health reminder: {str(e)}")
                import traceback
                current_app.logger.error(f"Traceback: {traceback.format_exc()}")
            except:
                print(f"❌ Error creating timezone-aware health reminder: {str(e)}")
            return False, f"Failed to create reminder: {str(e)}", {}

    def _generate_recurring_series_confirmation(self, recurring_result: Dict[str, Any], 
                                             base_reminder_details: Dict[str, Any], 
                                             original_message: str, 
                                             user_context: Dict[str, Any]) -> str:
        """
        🎯 CONTEXT7: Generate confirmation response for created recurring reminder series
        """
        try:
            series_id = recurring_result.get('series_id', '')
            total_created = recurring_result.get('total_created', 0)
            schedule_summary = recurring_result.get('schedule_summary', {})
            pattern = recurring_result.get('pattern', {})
            
            title = base_reminder_details.get('title', 'Reminder')
            user_timezone = user_context.get('timezone', 'UTC')
            timezone_abbr = user_context.get('timezone_abbreviation', 'UTC')
            
            # Format frequency description
            interval = pattern.get('interval', 1)
            interval_unit = pattern.get('interval_unit', '')
            
            if interval == 1:
                frequency_desc = f"{pattern.get('pattern', 'recurring')}"
            else:
                frequency_desc = f"every {interval} {interval_unit}"
            
            # Format date range
            start_date = schedule_summary.get('start_date', '')
            end_date = schedule_summary.get('end_date', '')
            
            try:
                if start_date:
                    start_formatted = datetime.strptime(start_date, '%Y-%m-%d').strftime('%B %d, %Y')
                else:
                    start_formatted = "today"
                
                if end_date and end_date != start_date:
                    end_formatted = datetime.strptime(end_date, '%Y-%m-%d').strftime('%B %d, %Y')
                    date_range = f"from {start_formatted} to {end_formatted}"
                else:
                    date_range = f"starting {start_formatted}"
            except:
                date_range = "starting soon"
            
            # Main confirmation message
            main_response = f"Perfect! I've created a series of {total_created} {frequency_desc} reminders for '{title}' {date_range} ({timezone_abbr}). 🎯"
            
            # Add details
            details_section = f"""

**📋 Recurring Series Details:**
• **Frequency:** {schedule_summary.get('frequency', frequency_desc)}
• **Total Reminders:** {total_created}
• **Period:** {date_range}
• **Timezone:** {user_timezone} ({timezone_abbr})
• **Series ID:** {series_id[:8]}...

Each reminder will include follow-up notifications every 30 minutes for 5 times if not marked as completed. You can mark any reminder as completed from your dashboard or directly from the email notifications.

**📱 Managing Your Series:**
• View all reminders in your Reminders dashboard
• Mark individual reminders as completed
• Stop follow-up notifications for specific reminders
• Each reminder can be managed independently

Is there anything else you'd like me to help you with regarding your pet care reminders?
"""
            
            return main_response + details_section
            
        except Exception as e:
            current_app.logger.error(f"Error generating recurring series confirmation: {str(e)}")
            return f"✅ Great! I've successfully created {recurring_result.get('total_created', 'multiple')} recurring reminders for you. You can view and manage them in your Reminders dashboard!"