import uuid
import os
from typing import Dict, List, Optional, Tuple, Any, Literal
from typing_extensions import Annotated, TypedDict
from datetime import datetime, timezone

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore
from langgraph.store.base import BaseStore
from langchain_core.tools import tool

from flask import current_app
from app import db
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.care_record import CareRecord, Document, KnowledgeBase
from app.services.care_archive_service import CareArchiveService
from app.utils.file_handler import query_user_docs

# Initialize models
chat_model = ChatOpenAI(
    model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4"),
    temperature=0.7,
    max_tokens=1500
)

class IntentState(TypedDict):
    """State for intent analysis"""
    message: str
    intent: str
    confidence: float
    requires_context: bool
    context_types: List[str]

class EnhancedChatState(MessagesState):
    """Enhanced state with user context and intent"""
    user_id: int
    thread_id: str
    intent_analysis: Optional[IntentState]
    user_context: Dict[str, Any]
    sources_used: List[Dict[str, Any]]
    response_metadata: Dict[str, Any]

class LangGraphChatService:
    """Advanced LangGraph-based chat service with AI agents"""
    
    def __init__(self):
        self.care_service = CareArchiveService()
        self.checkpointer = None
        self.store = None
        self.graph = None
        self._initialize_graph()
    
    def _initialize_graph(self):
        """Initialize LangGraph with memory storage to avoid connection issues"""
        try:
            # Force use of memory storage to avoid PostgreSQL connection issues
            # PostgreSQL connections are causing timeouts and connection closure issues
            try:
                current_app.logger.info("Initializing LangGraph with memory storage for stability")
            except RuntimeError:
                # No Flask application context available during import
                print("[INFO] Initializing LangGraph with memory storage for stability")
            
            # Use memory checkpointer for reliable operation
            from langgraph.checkpoint.memory import MemorySaver
            self.checkpointer = MemorySaver()
            try:
                current_app.logger.info("Memory checkpointer initialized successfully")
            except RuntimeError:
                print("[INFO] Memory checkpointer initialized successfully")
            
            # Use memory store for user memories and context  
            from langgraph.store.memory import InMemoryStore
            self.store = InMemoryStore()
            try:
                current_app.logger.info("Memory store initialized successfully")
            except RuntimeError:
                print("[INFO] Memory store initialized successfully")
            
            # Build the graph
            self._build_graph()
            
            try:
                current_app.logger.info("LangGraph chat service initialized successfully with memory storage")
            except RuntimeError:
                # No Flask application context available
                print("[INFO] LangGraph chat service initialized successfully with memory storage")
            
        except Exception as e:
            try:
                current_app.logger.error(f"Error initializing LangGraph chat service: {str(e)}")
            except RuntimeError:
                # No Flask application context available
                print(f"[ERROR] Error initializing LangGraph chat service: {str(e)}")
            raise
    
    def _build_graph(self):
        """Build the LangGraph state graph with AI agents"""
        
        builder = StateGraph(EnhancedChatState)
        
        # Add nodes (agents)
        builder.add_node("intent_analyzer", self._intent_analyzer_agent)
        builder.add_node("context_builder", self._context_builder_agent)
        builder.add_node("response_generator", self._response_generator_agent)
        builder.add_node("memory_manager", self._memory_manager_agent)
        
        # Define the flow
        builder.add_edge(START, "intent_analyzer")
        builder.add_edge("intent_analyzer", "context_builder")
        builder.add_edge("context_builder", "response_generator")
        builder.add_edge("response_generator", "memory_manager")
        builder.add_edge("memory_manager", END)
        
        # Compile the graph
        self.graph = builder.compile(
            checkpointer=self.checkpointer,
            store=self.store,
        )
    
    @tool
    def get_care_records(user_id: int, query: str) -> List[Dict]:
        """Tool to search user's care records"""
        try:
            service = CareArchiveService()
            results = service.search_user_archive(user_id, query, limit=5)
            return results.get('care_records', [])
        except Exception as e:
            return []
    
    @tool 
    def get_documents(user_id: int, query: str) -> List[Dict]:
        """Tool to search user's documents"""
        try:
            success, docs = query_user_docs(query, user_id, top_k=10)
            if success and docs:
                return [
                    {
                        'filename': doc.metadata.get('source', 'Unknown'),
                        'content': doc.page_content,
                        'url': doc.metadata.get('url', ''),
                        'score': 1.0
                    }
                    for doc in docs
                ]
            return []
        except Exception as e:
            return []
    
    @tool
    def get_upcoming_reminders(user_id: int) -> List[Dict]:
        """Tool to get upcoming care reminders"""
        try:
            service = CareArchiveService()
            reminders = service.get_upcoming_reminders(user_id, days_ahead=30)
            return [r.to_dict() for r in reminders]
        except Exception as e:
            return []
    
    @tool
    def create_health_reminder(user_id: int, title: str, description: str, 
                              due_date: str, reminder_type: str = "custom") -> Dict[str, Any]:
        """
        Create a new health reminder that will appear in the user's reminders dashboard.
        
        Args:
            user_id: User ID
            title: Reminder title (e.g., "Give Max his heartworm medication")
            description: Detailed description
            due_date: Due date in YYYY-MM-DD format
            reminder_type: Type of reminder (vaccination, vet_appointment, medication, grooming, checkup, custom)
        
        Returns:
            Dictionary with creation result
        """
        try:
            from app.services.health_service import HealthService
            from app.utils.database import get_db_session
            from datetime import datetime
            
            # Get database session
            db_session = get_db_session()
            health_service = HealthService(db_session)
            
            # Parse due date
            try:
                due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
            except ValueError:
                return {"success": False, "error": "Invalid date format. Use YYYY-MM-DD"}
            
            # Validate reminder type
            valid_types = ["vaccination", "vet_appointment", "medication", "grooming", "checkup", "custom"]
            if reminder_type not in valid_types:
                reminder_type = "custom"
            
            # Create reminder data
            reminder_data = {
                "reminder_type": reminder_type,
                "title": title,
                "description": description,
                "due_date": due_date_obj,
                "send_email": True,
                "send_push": True,
                "days_before_reminder": 7
            }
            
            # Create the reminder
            reminder = health_service.create_reminder(user_id, reminder_data)
            
            return {
                "success": True,
                "reminder_id": reminder.id,
                "message": f"✅ Health reminder '{title}' created successfully for {due_date}",
                "reminder": {
                    "id": reminder.id,
                    "title": reminder.title,
                    "type": reminder.reminder_type.value,
                    "due_date": reminder.due_date.isoformat(),
                    "status": reminder.status.value
                }
            }
            
        except Exception as e:
            current_app.logger.error(f"Error creating health reminder: {str(e)}")
            return {"success": False, "error": f"Failed to create reminder: {str(e)}"}
    
    def _intent_analyzer_agent(
        self, 
        state: EnhancedChatState, 
        config: RunnableConfig,
        *, 
        store: BaseStore
    ) -> EnhancedChatState:
        """AI agent to analyze user intent"""
        
        user_message = state["messages"][-1].content if state["messages"] else ""
        user_id = state.get("user_id")
        
        # AI-powered intent analysis
        intent_prompt = f"""
        You are an expert AI intent classifier for a pet care management system.
        
        Analyze this user message and determine:
        1. Primary intent (one of: care_history, medical_records, reminders, document_search, general_question, care_planning)
        2. Confidence level (0.0 to 1.0)
        3. Whether it requires user's specific context (true/false)
        4. What types of context needed (documents, care_records, reminders, chat_history)
        
        User message: "{user_message}"
        
        Respond in this exact JSON format:
        {{
            "intent": "primary_intent_here",
            "confidence": 0.85,
            "requires_context": true,
            "context_types": ["documents", "care_records"]
        }}
        """
        
        try:
            response = chat_model.invoke([HumanMessage(content=intent_prompt)])
            
            # Parse AI response (simplified - in production, use structured output)
            import json
            intent_data = json.loads(response.content.strip())
            
            intent_analysis = IntentState(
                message=user_message,
                intent=intent_data.get("intent", "general_question"),
                confidence=intent_data.get("confidence", 0.5),
                requires_context=intent_data.get("requires_context", False),
                context_types=intent_data.get("context_types", [])
            )
            
            current_app.logger.info(f"Intent analysis: {intent_analysis}")
            
        except Exception as e:
            current_app.logger.error(f"Intent analysis failed: {str(e)}")
            # Re-raise exception so enhanced chat service can handle fallback
            raise Exception(f"Intent analysis failed: {str(e)}")
        
        return {
            **state,
            "intent_analysis": intent_analysis
        }
    
    def _context_builder_agent(
        self, 
        state: EnhancedChatState, 
        config: RunnableConfig,
        *, 
        store: BaseStore
    ) -> EnhancedChatState:
        """Agent to build comprehensive user context"""
        
        user_id = state.get("user_id")
        intent_analysis = state.get("intent_analysis", {})
        user_message = state["messages"][-1].content if state["messages"] else ""
        
        user_context = {
            "user_id": user_id,
            "current_message": user_message,
            "intent": intent_analysis,
            "sources": [],
            "care_records": [],
            "documents": [],
            "reminders": [],
            "user_memories": [],
            "chat_summary": ""
        }
        
        try:
            # Get user memories from store
            namespace = ("user_context", str(user_id))
            memories = store.search(namespace, query=user_message, limit=10)
            user_context["user_memories"] = [m.value for m in memories]
            
            # Build context based on intent
            if intent_analysis.get("requires_context"):
                context_types = intent_analysis.get("context_types", [])
                
                if "care_records" in context_types:
                    care_results = self.care_service.search_user_archive(user_id, user_message, limit=5)
                    care_records = care_results.get('care_records', [])
                    user_context["care_records"] = care_records
                    user_context["sources"].extend([
                        {
                            "type": "care_record",
                            "title": record.get("title", ""),
                            "date": record.get("date_occurred", ""),
                            "category": record.get("category", "")
                        }
                        for record in care_records
                    ])
                
                if "documents" in context_types:
                    success, doc_results = query_user_docs(user_message, user_id, top_k=10)
                    if success and doc_results:
                        documents = [
                            {
                                'filename': doc.metadata.get('source', 'Unknown'),
                                'content': doc.page_content,
                                'url': doc.metadata.get('url', ''),
                                'score': 1.0
                            }
                            for doc in doc_results
                        ]
                    user_context["documents"] = documents
                    user_context["sources"].extend([
                        {
                            "type": "document",
                            "title": doc.get("filename", ""),
                            "content_preview": doc.get("content", "")[:200],
                            "relevance_score": doc.get("score", 0)
                        }
                        for doc in documents
                    ])
                
                if "reminders" in context_types:
                    reminders = self.care_service.get_upcoming_reminders(user_id, days_ahead=30)
                    reminder_dicts = [r.to_dict() for r in reminders]
                    user_context["reminders"] = reminder_dicts
                    user_context["sources"].extend([
                        {
                            "type": "reminder",
                            "title": reminder.get("title", ""),
                            "date": reminder.get("reminder_date", ""),
                            "category": reminder.get("category", "")
                        }
                        for reminder in reminder_dicts
                    ])
            
            # Get chat summary from previous messages
            if len(state["messages"]) > 1:
                recent_messages = state["messages"][-10:]  # Last 10 messages
                chat_summary = self._summarize_chat_history(recent_messages)
                user_context["chat_summary"] = chat_summary
            
            current_app.logger.info(f"Built context with {len(user_context['sources'])} sources")
            
        except Exception as e:
            current_app.logger.error(f"Context building failed: {str(e)}")
        
        return {
            **state,
            "user_context": user_context
        }
    
    def _response_generator_agent(
        self, 
        state: EnhancedChatState, 
        config: RunnableConfig,
        *, 
        store: BaseStore
    ) -> EnhancedChatState:
        """Agent to generate responses based on context and intent"""
        
        user_context = state.get("user_context", {})
        intent_analysis = state.get("intent_analysis", {})
        user_message = state["messages"][-1].content if state["messages"] else ""
        user_id = state.get("user_id")
        
        # Get username for personalization
        username = None
        dog_name = None
        try:
            from app.models.user import User
            user = User.query.get(user_id)
            if user:
                username = user.username
                if hasattr(user, 'dog_name') and user.dog_name:
                    dog_name = user.dog_name
        except Exception as e:
            current_app.logger.error(f"Error getting user info for personalization: {str(e)}")
        
        # Check if this is a reminder creation request
        reminder_keywords = ["remind", "reminder", "schedule", "set reminder", "create reminder", "don't forget"]
        is_reminder_request = any(keyword in user_message.lower() for keyword in reminder_keywords)
        
        try:
            if is_reminder_request:
                # Extract reminder details from user message
                title, due_date, reminder_type = self._extract_reminder_details(user_message)
                
                if title and due_date:
                    # Create the health reminder using the tool
                    result = self.create_health_reminder(
                        user_id=user_id,
                        title=title,
                        description=user_message,
                        due_date=due_date,
                        reminder_type=reminder_type
                    )
                    
                    if result.get("success"):
                        response_content = f"{result['message']}\n\nYou can view and manage all your reminders at /reminders"
                        
                        # Update state with tool result
                        tool_results = state.get("tool_results", [])
                        tool_results.append({
                            "tool": "create_health_reminder",
                            "result": result,
                            "success": True
                        })
                        
                        response = AIMessage(content=response_content)
                    else:
                        response = AIMessage(content=f"I tried to create the reminder but encountered an issue: {result.get('error', 'Unknown error')}. You can also create reminders manually at /reminders")
                else:
                    response = AIMessage(content="I'd be happy to help you create a reminder! However, I need more specific details like what the reminder is for and when it's due. You can also create reminders manually at /reminders")
            else:
                # Regular response generation
                system_prompt = f"""
                You are Mr. White, an AI assistant specialized in pet care and health management.
                
                User Query: "{user_message}"
                Intent: {intent_analysis.get("intent", "general")}
                
                Available Context:
                - Care Records: {len(user_context.get('care_records', []))} records
                - Documents: {len(user_context.get('documents', []))} documents  
                - Reminders: {len(user_context.get('reminders', []))} reminders
                - User Memories: {len(user_context.get('user_memories', []))} memories
                
                Context Sources:
                {chr(10).join([f"- {source.get('type', '')}: {source.get('title', '')}" 
                              for source in user_context.get('sources', [])[:5]])}
                """
                
                # Add personalization if username is available
                if username:
                    system_prompt += f"""
                
                PERSONALIZATION:
                - You are talking to {username}. Address them by name occasionally in a natural, conversational way.
                - Use their name especially when greeting them or providing important advice.
                - Don't overuse their name - once or twice in a response is sufficient.
                """
                
                # Add dog name if available
                if dog_name:
                    system_prompt += f"""
                - When discussing their dog, refer to {dog_name} by name rather than saying "your dog".
                - Incorporate {dog_name}'s name naturally in your responses about their pet.
                """
                
                system_prompt += """
                
                Provide a helpful, accurate response based on the available context.
                If you reference specific information, mention where it came from.
                Be conversational but professional.
                """
                
                # Include relevant context in the prompt
                if user_context.get('care_records'):
                    system_prompt += f"\n\nRelevant Care Records:\n"
                    for record in user_context.get('care_records', [])[:3]:
                        system_prompt += f"- {record.get('title', '')} ({record.get('date_occurred', '')})\n"
                
                if user_context.get('reminders'):
                    system_prompt += f"\n\nUpcoming Reminders:\n"
                    for reminder in user_context.get('reminders', [])[:3]:
                        system_prompt += f"- {reminder.get('title', '')} (due: {reminder.get('due_date', '')})\n"
                
                response = chat_model.invoke([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_message)
                ])
            
            response_metadata = {
                "context_used": len(user_context.get('sources', [])),
                "intent": intent_analysis.get("intent", "unknown"),
                "tools_used": state.get("tool_results", []),
                "confidence": 0.85
            }
            
        except Exception as e:
            current_app.logger.error(f"Error in response generation: {str(e)}")
            response = AIMessage(content="I encountered an issue processing your request. Please try again or contact support if the problem persists.")
            response_metadata = {"error": str(e), "confidence": 0.3}
        
        # Add AI response to messages
        new_messages = state["messages"] + [response]
        
        return {
            **state,
            "messages": new_messages,
            "sources_used": user_context.get('sources', []),
            "response_metadata": response_metadata
        }
    
    def _memory_manager_agent(
        self, 
        state: EnhancedChatState, 
        config: RunnableConfig,
        *, 
        store: BaseStore
    ) -> EnhancedChatState:
        """Agent to manage user memories and long-term context"""
        
        user_id = state.get("user_id")
        user_message = state["messages"][-2].content if len(state["messages"]) >= 2 else ""
        ai_response = state["messages"][-1].content if state["messages"] else ""
        
        try:
            namespace = ("user_context", str(user_id))
            
            # Store important information for future reference
            if any(keyword in user_message.lower() for keyword in ["remember", "my pet", "important", "note"]):
                memory_id = str(uuid.uuid4())
                memory_data = {
                    "data": f"User mentioned: {user_message}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "context": "user_preference"
                }
                store.put(namespace, memory_id, memory_data)
            
            # Store conversation patterns for better future responses
            conversation_summary = f"User asked about: {user_message[:100]}... AI responded with context from {len(state.get('sources_used', []))} sources"
            memory_id = str(uuid.uuid4())
            conversation_memory = {
                "data": conversation_summary,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "context": "conversation_pattern",
                "intent": state.get("intent_analysis", {}).get("intent", "unknown")
            }
            store.put(namespace, memory_id, conversation_memory)
            
            current_app.logger.info(f"Stored memories for user {user_id}")
            
        except Exception as e:
            current_app.logger.error(f"Memory management failed: {str(e)}")
        
        return state
    
    def _extract_reminder_details(self, user_message: str) -> Tuple[str, str, str]:
        """
        Extract reminder details from user message
        
        Returns:
            Tuple of (title, due_date, reminder_type)
        """
        import re
        from datetime import datetime, timedelta
        
        # Default values
        title = ""
        due_date = ""
        reminder_type = "custom"
        
        # Extract title - look for patterns like "remind me to [action]"
        title_patterns = [
            r"remind me to (.+?)(?:\s+(?:on|by|next|tomorrow|friday|monday|tuesday|wednesday|thursday|saturday|sunday))",
            r"remind me to (.+?)(?:\s+(?:in|at|around))",
            r"remind me to (.+)",
            r"set a reminder (?:to|for) (.+?)(?:\s+(?:on|by|next|tomorrow|friday))",
            r"create a reminder (?:to|for) (.+?)(?:\s+(?:on|by|next|tomorrow|friday))",
            r"schedule (.+?)(?:\s+(?:on|by|next|tomorrow|friday))",
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, user_message.lower())
            if match:
                title = match.group(1).strip()
                break
        
        # If no specific pattern found, use a more general approach
        if not title:
            # Look for key action words
            action_words = ["give", "medication", "vaccine", "vaccination", "checkup", "grooming", "appointment"]
            for word in action_words:
                if word in user_message.lower():
                    # Extract around the action word
                    words = user_message.split()
                    for i, w in enumerate(words):
                        if word in w.lower():
                            # Take some context around the action word
                            start = max(0, i-2)
                            end = min(len(words), i+4)
                            title = " ".join(words[start:end])
                            break
                    break
        
        # Extract reminder type based on keywords
        type_keywords = {
            "medication": ["medication", "medicine", "pill", "dose", "heartworm", "flea", "tick"],
            "vaccination": ["vaccination", "vaccine", "shot", "rabies", "dhpp", "bordetella"],
            "vet_appointment": ["vet", "veterinarian", "appointment", "checkup", "visit", "doctor"],
            "grooming": ["grooming", "groom", "bath", "nail", "trim", "haircut", "shampoo"],
            "checkup": ["checkup", "check-up", "examination", "exam", "health check"]
        }
        
        for rtype, keywords in type_keywords.items():
            if any(keyword in user_message.lower() for keyword in keywords):
                reminder_type = rtype
                break
        
        # Extract due date
        due_date = self._extract_due_date(user_message)
        
        return title, due_date, reminder_type
    
    def _extract_due_date(self, user_message: str) -> str:
        """Extract due date from user message and return in YYYY-MM-DD format"""
        import re
        from datetime import datetime, timedelta
        
        message_lower = user_message.lower()
        today = datetime.now()
        
        # Check for relative dates
        if "tomorrow" in message_lower:
            target_date = today + timedelta(days=1)
            return target_date.strftime('%Y-%m-%d')
        
        if "next week" in message_lower:
            target_date = today + timedelta(days=7)
            return target_date.strftime('%Y-%m-%d')
        
        if "next month" in message_lower:
            target_date = today + timedelta(days=30)
            return target_date.strftime('%Y-%m-%d')
        
        # Check for specific days of the week
        days_of_week = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        for day_name, day_num in days_of_week.items():
            if f"next {day_name}" in message_lower or f"{day_name}" in message_lower:
                days_ahead = (day_num - today.weekday()) % 7
                if days_ahead == 0:  # If it's the same day, assume next week
                    days_ahead = 7
                target_date = today + timedelta(days=days_ahead)
                return target_date.strftime('%Y-%m-%d')
        
        # Check for specific date patterns (MM/DD, MM-DD, etc.)
        date_patterns = [
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',  # MM/DD/YYYY or MM-DD-YYYY
            r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',  # YYYY/MM/DD or YYYY-MM-DD
            r'(\d{1,2})[/-](\d{1,2})',             # MM/DD or MM-DD (current year)
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, user_message)
            if match:
                try:
                    if len(match.groups()) == 3:
                        if len(match.group(1)) == 4:  # YYYY-MM-DD format
                            year, month, day = map(int, match.groups())
                        else:  # MM/DD/YYYY format
                            month, day, year = map(int, match.groups())
                    else:  # MM/DD format (current year)
                        month, day = map(int, match.groups())
                        year = today.year
                    
                    target_date = datetime(year, month, day)
                    return target_date.strftime('%Y-%m-%d')
                except ValueError:
                    continue
        
        # Default to one week from now if no date found
        default_date = today + timedelta(days=7)
        return default_date.strftime('%Y-%m-%d')
    
    def _summarize_chat_history(self, messages: List[BaseMessage]) -> str:
        """Summarize recent chat history"""
        try:
            if len(messages) < 2:
                return "No previous conversation"
            
            # Create a summary of the last few exchanges
            summary_prompt = f"""
            Summarize this recent conversation in 2-3 sentences, focusing on:
            1. What the user has been asking about
            2. Key information that was discussed
            3. Any ongoing topics or concerns
            
            Conversation:
            {chr(10).join([f"{msg.type}: {msg.content}" for msg in messages[-6:]])}
            """
            
            response = chat_model.invoke([HumanMessage(content=summary_prompt)])
            return response.content
            
        except Exception as e:
            current_app.logger.error(f"Chat summarization failed: {str(e)}")
            return "Previous conversation available"
    
    def process_message(
        self, 
        user_id: int, 
        message: str, 
        thread_id: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """Process a user message through the LangGraph agents"""
        
        if not thread_id:
            thread_id = str(uuid.uuid4())
        
        config = {
            "configurable": {
                "thread_id": thread_id,
                "user_id": str(user_id),
            }
        }
        
        initial_state = {
            "messages": [HumanMessage(content=message)],
            "user_id": user_id,
            "thread_id": thread_id,
        }
        
        try:
            # Check if graph is initialized
            if not self.graph:
                current_app.logger.error("Graph not initialized, reinitializing...")
                self._initialize_graph()
            
            # Run the graph with connection retry logic
            final_state = None
            max_retries = 2
            
            for attempt in range(max_retries):
                try:
                    for chunk in self.graph.stream(initial_state, config, stream_mode="values"):
                        final_state = chunk
                    break  # Success, exit retry loop
                    
                except Exception as stream_error:
                    if "connection is closed" in str(stream_error).lower() and attempt < max_retries - 1:
                        current_app.logger.warning(f"Connection issue detected (attempt {attempt + 1}), reinitializing graph...")
                        # Reinitialize the graph on connection errors
                        self._initialize_graph()
                        continue
                    else:
                        # Re-raise if it's not a connection error or we've exhausted retries
                        raise stream_error
            
            if final_state and final_state["messages"]:
                ai_response = final_state["messages"][-1].content
                
                # Prepare context info for frontend
                context_info = {
                    "thread_id": thread_id,
                    "sources": final_state.get("sources_used", []),
                    "intent_analysis": final_state.get("intent_analysis", {}),
                    "response_metadata": final_state.get("response_metadata", {}),
                    "documents_referenced": len([s for s in final_state.get("sources_used", []) if s.get("type") == "document"]),
                    "care_records_referenced": len([s for s in final_state.get("sources_used", []) if s.get("type") == "care_record"])
                }
                
                return ai_response, context_info
            else:
                return "I apologize, but I couldn't process your message. Please try again.", {}
                
        except Exception as e:
            try:
                current_app.logger.error(f"LangGraph processing failed: {str(e)}")
            except RuntimeError:
                print(f"[ERROR] LangGraph processing failed: {str(e)}")
            
            # Instead of returning error message, raise exception so fallback is triggered
            raise Exception(f"LangGraph processing failed: {str(e)}")
        
        # If we got here, there was an unexpected issue
        raise Exception("LangGraph processing completed but no response was generated")
    
    def cleanup_connections(self):
        """Cleanup database connections"""
        try:
            if hasattr(self.checkpointer, 'close'):
                self.checkpointer.close()
            if hasattr(self.store, 'close'):
                self.store.close()
            current_app.logger.info("LangGraph connections cleaned up")
        except Exception as e:
            current_app.logger.error(f"Error cleaning up connections: {str(e)}")
    
    def __del__(self):
        """Destructor to cleanup connections"""
        try:
            self.cleanup_connections()
        except:
            pass  # Ignore errors during cleanup
    
    def get_conversation_history(self, thread_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a thread"""
        try:
            config = {"configurable": {"thread_id": thread_id}}
            state = self.graph.get_state(config)
            
            if state and state.values.get("messages"):
                return [
                    {
                        "type": "user" if isinstance(msg, HumanMessage) else "ai",
                        "content": msg.content,
                        "timestamp": getattr(msg, 'timestamp', datetime.now(timezone.utc).isoformat())
                    }
                    for msg in state.values["messages"]
                ]
            return []
            
        except Exception as e:
            current_app.logger.error(f"Error getting conversation history: {str(e)}")
            return [] 