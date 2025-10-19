import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
from dataclasses import dataclass
from enum import Enum

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import PydanticOutputParser
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.care_record import CareRecord, Document, KnowledgeBase
from app.services.ai_service import AIService
from app import db

logger = logging.getLogger(__name__)

class HealthCategory(Enum):
    VACCINATION = "vaccination"
    MEDICATION = "medication" 
    VET_VISITS = "vet_visits"
    SYMPTOMS = "symptoms"
    NUTRITION = "nutrition"
    BEHAVIOR = "behavior"
    EMERGENCY = "emergency"
    GENERAL_CARE = "general_care"

class HealthQueryType(Enum):
    RETRIEVE_RECORDS = "retrieve_records"
    ANALYZE_TRENDS = "analyze_trends"
    GET_RECOMMENDATIONS = "get_recommendations"
    EMERGENCY_ASSESSMENT = "emergency_assessment"
    SCHEDULE_REMINDER = "schedule_reminder"

@dataclass
class HealthContext:
    user_id: int
    pet_name: Optional[str]
    health_records: List[Dict]
    recent_conversations: List[Dict]
    relevant_documents: List[Dict]
    health_summary: Optional[str]

class HealthQuery(BaseModel):
    query_text: str = Field(description="The user's health-related query")
    category: HealthCategory = Field(description="Primary health category")
    query_type: HealthQueryType = Field(description="Type of query operation")
    urgency_level: int = Field(description="Urgency level 1-5 (5 being emergency)", ge=1, le=5)
    pet_name: Optional[str] = Field(description="Specific pet name if mentioned")
    confidence: float = Field(description="Confidence in query classification", ge=0.0, le=1.0)

class HealthInsight(BaseModel):
    category: HealthCategory
    insight: str = Field(description="Health insight or recommendation")
    supporting_data: List[str] = Field(description="Supporting evidence from records")
    confidence: float = Field(description="Confidence in the insight")
    urgency: int = Field(description="Urgency level 1-5")
    next_actions: List[str] = Field(description="Recommended next actions")

class HealthIntelligenceState(BaseModel):
    user_id: int
    query: str
    parsed_query: Optional[HealthQuery] = None
    health_context: Optional[HealthContext] = None
    insights: List[HealthInsight] = []
    response: Optional[str] = None
    sources: List[str] = []
    error: Optional[str] = None

class HealthIntelligenceService:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
        self.ai_service = AIService()
        self.graph = self._build_health_graph()
        
    def _build_health_graph(self) -> StateGraph:
        """Build the LangGraph for health intelligence processing"""
        workflow = StateGraph(HealthIntelligenceState)
        
        # Add nodes
        workflow.add_node("query_analyzer", self._analyze_health_query)
        workflow.add_node("context_builder", self._build_health_context)
        workflow.add_node("health_specialist", self._health_specialist_agent)
        workflow.add_node("emergency_agent", self._emergency_assessment_agent)
        workflow.add_node("trend_analyzer", self._trend_analysis_agent)
        workflow.add_node("recommendation_engine", self._recommendation_agent)
        workflow.add_node("response_synthesizer", self._synthesize_response)
        
        # Add conditional edges
        workflow.add_edge("query_analyzer", "context_builder")
        workflow.add_conditional_edges(
            "context_builder",
            self._route_by_urgency,
            {
                "emergency": "emergency_agent",
                "analysis": "trend_analyzer", 
                "general": "health_specialist",
                "recommendation": "recommendation_engine"
            }
        )
        
        # All paths lead to response synthesis
        workflow.add_edge("emergency_agent", "response_synthesizer")
        workflow.add_edge("trend_analyzer", "response_synthesizer")
        workflow.add_edge("health_specialist", "response_synthesizer")
        workflow.add_edge("recommendation_engine", "response_synthesizer")
        workflow.add_edge("response_synthesizer", END)
        
        # Set entry point
        workflow.set_entry_point("query_analyzer")
        
        return workflow.compile()
    
    async def process_health_query(self, user_id: int, query: str, thread_id: str = None) -> Dict[str, Any]:
        """Process a health-related query using the LangGraph agent"""
        try:
            initial_state = HealthIntelligenceState(
                user_id=user_id,
                query=query
            )
            
            config = {"configurable": {"thread_id": thread_id or f"health_{user_id}_{datetime.now().isoformat()}"}}
            
            # Run the graph
            result = await self.graph.ainvoke(initial_state.dict(), config=config)
            
            # Convert Pydantic model to dict if needed
            if hasattr(result, 'dict') and callable(getattr(result, 'dict')):
                result = result.dict()
            
            # Extract parsed_query safely
            parsed_query = result.get("parsed_query")
            urgency = 1
            category = None
            
            if parsed_query:
                if isinstance(parsed_query, dict):
                    urgency = parsed_query.get("urgency_level", 1)
                    category = parsed_query.get("category")
                else:
                    # Handle if parsed_query is still a Pydantic model
                    urgency = getattr(parsed_query, "urgency_level", 1)
                    category = getattr(parsed_query, "category", None)
            
            return {
                "response": result.get("response"),
                "insights": result.get("insights", []),
                "sources": result.get("sources", []),
                "urgency": urgency,
                "category": category,
                "thread_id": config["configurable"]["thread_id"]
            }
            
        except Exception as e:
            logger.error(f"Error in health query processing: {str(e)}")
            return {
                "response": "I apologize, but I encountered an error processing your health query. Please try again.",
                "error": str(e)
            }
    
    def _analyze_health_query(self, state: HealthIntelligenceState) -> HealthIntelligenceState:
        """Analyze and classify the health query"""
        try:
            parser = PydanticOutputParser(pydantic_object=HealthQuery)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a veterinary AI specialist. Analyze the user's query about their pet's health.
                
                Classify the query into appropriate categories and determine the urgency level:
                - Level 1-2: General information, routine care
                - Level 3: Concerning symptoms, needs attention
                - Level 4: Urgent symptoms, see vet soon
                - Level 5: Emergency, immediate veterinary care needed
                
                {format_instructions}"""),
                ("human", "Query: {query}")
            ])
            
            chain = prompt | self.llm | parser
            
            parsed_query = chain.invoke({
                "query": state.query,
                "format_instructions": parser.get_format_instructions()
            })
            
            state.parsed_query = parsed_query
            return state
            
        except Exception as e:
            logger.error(f"Error in query analysis: {str(e)}")
            state.error = f"Query analysis failed: {str(e)}"
            return state
    
    def _build_health_context(self, state: HealthIntelligenceState) -> HealthIntelligenceState:
        """Build comprehensive health context from existing data"""
        try:
            user_id = state.user_id
            pet_name = state.parsed_query.pet_name if state.parsed_query else None
            
            # 1. Get health-related chat history from existing conversations
            health_conversations = self._get_health_conversations(user_id, limit=20)
            
            # 2. Get care records from database
            health_records = self._get_health_records(user_id, pet_name)
            
            # 3. Get relevant documents from existing knowledge base
            relevant_docs = self._get_relevant_health_documents(user_id, state.query)
            
            # 4. Generate health summary using AI
            health_summary = self._generate_health_summary(health_records, health_conversations)
            
            state.health_context = HealthContext(
                user_id=user_id,
                pet_name=pet_name,
                health_records=health_records,
                recent_conversations=health_conversations,
                relevant_documents=relevant_docs,
                health_summary=health_summary
            )
            
            return state
            
        except Exception as e:
            logger.error(f"Error building health context: {str(e)}")
            state.error = f"Context building failed: {str(e)}"
            return state
    
    def _get_health_conversations(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Extract health-related conversations from existing chat data"""
        try:
            # Query existing conversations and messages for health-related content
            health_keywords = [
                'vaccination', 'vaccine', 'vet', 'veterinarian', 'sick', 'illness', 'symptom',
                'medication', 'medicine', 'health', 'pain', 'injury', 'behavior', 'eating',
                'drinking', 'weight', 'temperature', 'vomiting', 'diarrhea', 'lethargy',
                'appetite', 'breathing', 'cough', 'limping', 'seizure', 'emergency'
            ]
            
            # Use text search on messages
            health_conversations = []
            
            # Get recent conversations
            conversations = db.session.query(Conversation)\
                .filter_by(user_id=user_id)\
                .order_by(Conversation.created_at.desc())\
                .limit(50).all()
            
            for conv in conversations:
                messages = db.session.query(Message)\
                    .filter_by(conversation_id=conv.id)\
                    .order_by(Message.created_at).all()
                
                # Check if conversation contains health-related content
                conv_text = " ".join([msg.content.lower() for msg in messages])
                if any(keyword in conv_text for keyword in health_keywords):
                    health_conversations.append({
                        'conversation_id': conv.id,
                        'messages': [{
                            'role': msg.type,  # Fixed: use 'type' instead of 'role'
                            'content': msg.content,
                            'timestamp': msg.created_at.isoformat()
                        } for msg in messages],
                        'created_at': conv.created_at.isoformat()
                    })
                    
                if len(health_conversations) >= limit:
                    break
            
            return health_conversations
            
        except Exception as e:
            logger.error(f"Error getting health conversations: {str(e)}")
            return []
    
    def _get_health_records(self, user_id: int, pet_name: Optional[str] = None) -> List[Dict]:
        """Get existing care records from database"""
        try:
            query = db.session.query(CareRecord).filter_by(user_id=user_id)
            
            if pet_name:
                # Note: CareRecord doesn't have pet_name field, this might need adjustment
                # For now, we'll search in metadata or description
                pass
            
            records = query.order_by(CareRecord.date_occurred.desc()).all()
            
            return [{
                'id': record.id,
                'title': record.title,
                'category': record.category,
                'description': record.description,
                'meta_data': record.meta_data,
                'date_occurred': record.date_occurred.isoformat() if record.date_occurred else None,
                'created_at': record.created_at.isoformat()
            } for record in records]
            
        except Exception as e:
            logger.error(f"Error getting health records: {str(e)}")
            return []
    
    def _get_relevant_health_documents(self, user_id: int, query: str) -> List[Dict]:
        """Get relevant documents from existing Pinecone knowledge base"""
        try:
            # Use AI service to search for health-related documents
            health_query = f"health pet care veterinary {query}"
            
            # Search in existing knowledge base using AI service
            success, docs = self.ai_service.search_user_documents(
                health_query,
                user_id,
                top_k=10
            )
            
            if not success:
                return []
            
            relevant_docs = []
            for doc in docs:
                metadata = doc.metadata
                relevant_docs.append({
                    'id': metadata.get('source', 'unknown'),
                    'content': doc.page_content,
                    'source': metadata.get('source', ''),
                    'score': 1.0,  # Default score since we don't get it from search_user_documents
                    'category': metadata.get('category', ''),
                    'timestamp': metadata.get('processed_at', '')
                })
            
            return relevant_docs
            
        except Exception as e:
            logger.error(f"Error getting relevant documents: {str(e)}")
            return []
    
    def _generate_health_summary(self, health_records: List[Dict], conversations: List[Dict]) -> str:
        """Generate AI-powered health summary"""
        try:
            if not health_records and not conversations:
                return "No health data available for this pet."
            
            # Combine data for summary
            records_text = "\n".join([
                f"- {record['title']}: {record['description']} ({record['date_occurred']})"
                for record in health_records[:10]  # Limit to recent records
            ])
            
            recent_health_chats = []
            for conv in conversations[:5]:  # Recent conversations
                for msg in conv['messages']:
                    if msg['role'] == 'user':  # This is correct - we're accessing the dict we just created above
                        recent_health_chats.append(msg['content'])
            
            chats_text = "\n".join(recent_health_chats[:10])
            
            prompt = f"""
            Based on the following health records and recent conversations, provide a comprehensive health summary:
            
            Health Records:
            {records_text}
            
            Recent Health Discussions:
            {chats_text}
            
            Provide a concise summary of the pet's health status, patterns, and any notable concerns.
            """
            
            response = self.llm.invoke([HumanMessage(content=prompt)])
            return response.content
            
        except Exception as e:
            logger.error(f"Error generating health summary: {str(e)}")
            return "Unable to generate health summary at this time."
    
    def _route_by_urgency(self, state: HealthIntelligenceState) -> str:
        """Route to appropriate agent based on query urgency and type"""
        if not state.parsed_query:
            return "general"
        
        urgency = state.parsed_query.urgency_level
        query_type = state.parsed_query.query_type
        
        if urgency >= 4:
            return "emergency"
        elif query_type == HealthQueryType.ANALYZE_TRENDS:
            return "analysis"
        elif query_type == HealthQueryType.GET_RECOMMENDATIONS:
            return "recommendation"
        else:
            return "general"
    
    def _health_specialist_agent(self, state: HealthIntelligenceState) -> HealthIntelligenceState:
        """General health specialist agent"""
        try:
            context = state.health_context
            query = state.parsed_query
            
            prompt = f"""
            You are a veterinary health specialist AI. Answer the user's health query based on their pet's history.
            
            Query: {state.query}
            Category: {query.category.value if query else 'general'}
            
            Pet Health Context:
            {context.health_summary if context else 'No context available'}
            
            Health Records Available: {len(context.health_records) if context else 0}
            Recent Conversations: {len(context.recent_conversations) if context else 0}
            
            Provide a helpful, accurate response based on the available information.
            If the query requires immediate veterinary attention, clearly state this.
            """
            
            response = self.llm.invoke([HumanMessage(content=prompt)])
            state.response = response.content
            
            # Add sources
            if context:
                state.sources = [
                    f"Health records: {len(context.health_records)} entries",
                    f"Chat history: {len(context.recent_conversations)} conversations",
                    f"Documents: {len(context.relevant_documents)} relevant documents"
                ]
            
            return state
            
        except Exception as e:
            logger.error(f"Error in health specialist agent: {str(e)}")
            state.error = f"Health specialist processing failed: {str(e)}"
            return state
    
    def _emergency_assessment_agent(self, state: HealthIntelligenceState) -> HealthIntelligenceState:
        """Emergency assessment agent for urgent health queries"""
        try:
            prompt = f"""
            URGENT HEALTH ASSESSMENT REQUIRED
            
            Query: {state.query}
            
            You are an emergency veterinary triage AI. Assess the urgency of this situation.
            
            Provide:
            1. Immediate actions the pet owner should take
            2. Whether immediate veterinary care is needed
            3. Warning signs to watch for
            4. Timeline for seeking care
            
            Be clear, direct, and prioritize the pet's safety.
            """
            
            response = self.llm.invoke([HumanMessage(content=prompt)])
            
            # Prepend emergency warning
            emergency_response = f"""
            🚨 URGENT HEALTH CONCERN DETECTED 🚨
            
            {response.content}
            
            ⚠️ This appears to be a high-priority health situation. Please contact your veterinarian immediately or visit an emergency animal hospital if symptoms worsen.
            """
            
            state.response = emergency_response
            state.sources = ["Emergency assessment protocol", "Veterinary triage guidelines"]
            
            return state
            
        except Exception as e:
            logger.error(f"Error in emergency agent: {str(e)}")
            state.error = f"Emergency assessment failed: {str(e)}"
            return state
    
    def _trend_analysis_agent(self, state: HealthIntelligenceState) -> HealthIntelligenceState:
        """Analyze health trends from historical data"""
        try:
            context = state.health_context
            if not context or not context.health_records:
                state.response = "Insufficient health data for trend analysis."
                return state
            
            # Analyze trends in health records
            records_by_type = {}
            for record in context.health_records:
                record_type = record['category']
                if record_type not in records_by_type:
                    records_by_type[record_type] = []
                records_by_type[record_type].append(record)
            
            trend_analysis = []
            for record_type, records in records_by_type.items():
                trend_analysis.append(f"{record_type}: {len(records)} entries")
            
            prompt = f"""
            Analyze the health trends for this pet based on their records:
            
            Query: {state.query}
            
            Health Record Types and Counts:
            {chr(10).join(trend_analysis)}
            
            Recent Health Summary:
            {context.health_summary}
            
            Provide insights on:
            1. Health patterns and trends
            2. Areas of concern or improvement
            3. Preventive care recommendations
            4. Notable changes over time
            """
            
            response = self.llm.invoke([HumanMessage(content=prompt)])
            state.response = response.content
            state.sources = [f"Analyzed {len(context.health_records)} health records"]
            
            return state
            
        except Exception as e:
            logger.error(f"Error in trend analysis: {str(e)}")
            state.error = f"Trend analysis failed: {str(e)}"
            return state
    
    def _recommendation_agent(self, state: HealthIntelligenceState) -> HealthIntelligenceState:
        """Generate health recommendations based on context"""
        try:
            context = state.health_context
            
            prompt = f"""
            Based on this pet's health history, provide personalized recommendations:
            
            Query: {state.query}
            Health Summary: {context.health_summary if context else 'No data available'}
            
            Provide specific, actionable recommendations for:
            1. Preventive care
            2. Lifestyle improvements
            3. Monitoring recommendations
            4. When to schedule vet checkups
            5. Warning signs to watch for
            
            Make recommendations practical and specific to this pet's history.
            """
            
            response = self.llm.invoke([HumanMessage(content=prompt)])
            state.response = response.content
            
            if context:
                state.sources = [
                    "Pet health history analysis",
                    f"Based on {len(context.health_records)} health records",
                    "Veterinary best practices"
                ]
            
            return state
            
        except Exception as e:
            logger.error(f"Error in recommendation agent: {str(e)}")
            state.error = f"Recommendation generation failed: {str(e)}"
            return state
    
    def _synthesize_response(self, state: HealthIntelligenceState) -> HealthIntelligenceState:
        """Final response synthesis and formatting"""
        try:
            if state.error:
                state.response = f"I apologize, but I encountered an error: {state.error}"
                return state
            
            if not state.response:
                state.response = "I'm unable to provide a specific response to your health query at this time."
                return state
            
            # Add metadata to response
            if state.parsed_query:
                urgency_note = ""
                if state.parsed_query.urgency_level >= 4:
                    urgency_note = "\n\n⚠️ HIGH PRIORITY: Please consult with a veterinarian promptly."
                elif state.parsed_query.urgency_level >= 3:
                    urgency_note = "\n\n💡 RECOMMENDED: Consider scheduling a vet checkup if symptoms persist."
                
                state.response += urgency_note
            
            # Add source attribution
            if state.sources:
                sources_text = "\n\n📋 **Sources**: " + ", ".join(state.sources[:3])
                state.response += sources_text
            
            return state
            
        except Exception as e:
            logger.error(f"Error in response synthesis: {str(e)}")
            state.response = "I apologize, but I encountered an error preparing your response."
            return state
    
    def get_health_dashboard_data(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive health dashboard data for the user"""
        try:
            # Get health records
            health_records = self._get_health_records(user_id)
            
            # Get health conversations 
            health_conversations = self._get_health_conversations(user_id, limit=10)
            
            # Generate summary statistics
            stats = self._generate_health_stats(health_records, health_conversations)
            
            # Get recent health insights
            recent_insights = self._get_recent_health_insights(user_id)
            
            return {
                "health_records": health_records,
                "health_conversations": health_conversations[:5],  # Recent conversations
                "stats": stats,
                "insights": recent_insights,
                "summary": self._generate_health_summary(health_records, health_conversations)
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard data: {str(e)}")
            return {
                "error": str(e),
                "health_records": [],
                "health_conversations": [],
                "stats": {},
                "insights": [],
                "summary": "Unable to load health data."
            }
    
    def _generate_health_stats(self, health_records: List[Dict], conversations: List[Dict]) -> Dict[str, Any]:
        """Generate health statistics for dashboard"""
        try:
            total_records = len(health_records)
            
            # Count by type
            record_types = {}
            for record in health_records:
                record_type = record['category']
                record_types[record_type] = record_types.get(record_type, 0) + 1
            
            # Recent activity (last 30 days)
            recent_cutoff = datetime.now() - timedelta(days=30)
            recent_records = [
                r for r in health_records 
                if r['date_occurred'] and datetime.fromisoformat(r['date_occurred'].replace('Z', '+00:00')) > recent_cutoff
            ]
            
            return {
                "total_records": total_records,
                "record_types": record_types,
                "recent_activity": len(recent_records),
                "health_conversations": len(conversations),
                "most_common_type": max(record_types.items(), key=lambda x: x[1])[0] if record_types else None
            }
            
        except Exception as e:
            logger.error(f"Error generating health stats: {str(e)}")
            return {}
    
    def _get_recent_health_insights(self, user_id: int) -> List[Dict]:
        """Get recent AI-generated health insights"""
        try:
            # This would typically be stored in database
            # For now, return empty list - can be enhanced later
            return []
            
        except Exception as e:
            logger.error(f"Error getting recent insights: {str(e)}")
            return [] 