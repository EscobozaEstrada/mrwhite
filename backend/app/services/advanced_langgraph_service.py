import uuid
import os
import time
import json
import hashlib
from typing import Dict, List, Optional, Tuple, Any, Literal, Union, Callable, AsyncGenerator, Generator
from typing_extensions import Annotated, TypedDict
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
import aiofiles
import base64
from io import BytesIO

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool, BaseTool
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field, validator
from langchain_core.utils.function_calling import convert_to_openai_function

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

# Initialize embeddings for advanced memory
embeddings_model = OpenAIEmbeddings()

# 🛠️ Advanced Tool Integration Models
class ToolExecutionResult(BaseModel):
    """Result of tool execution with metadata"""
    tool_name: str
    result: Any
    execution_time: float
    success: bool
    error_message: Optional[str] = None
    cache_key: Optional[str] = None
    popularity_score: float = 0.0

class ToolUsageStats(BaseModel):
    """Tool usage statistics for optimization"""
    tool_name: str
    usage_count: int = 0
    success_rate: float = 1.0
    avg_execution_time: float = 0.0
    last_used: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    popularity_score: float = 0.0

# 🧠 Advanced Memory Models
class MemoryType(str, Enum):
    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"

class MemoryImportance(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class MemoryItem:
    """Advanced memory item with hierarchical classification"""
    id: str
    content: str
    memory_type: MemoryType
    importance: MemoryImportance
    timestamp: datetime
    user_id: int
    embeddings: Optional[List[float]] = None
    decay_factor: float = 1.0
    access_count: int = 0
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    related_memories: List[str] = field(default_factory=list)
    consolidated: bool = False
    source: str = "user_interaction"
    context_tags: List[str] = field(default_factory=list)

# 🔄 Advanced State Management Models
class StateLevel(str, Enum):
    CONVERSATION = "conversation"
    USER = "user"
    SESSION = "session"
    GLOBAL = "global"

@dataclass
class StateSnapshot:
    """State snapshot for versioning and rollback"""
    id: str
    level: StateLevel
    timestamp: datetime
    data: Dict[str, Any]
    version: int
    checksum: str
    compressed: bool = False

class PersonalizationProfile(BaseModel):
    """User personalization profile based on accumulated state"""
    user_id: int
    preferences: Dict[str, Any] = Field(default_factory=dict)
    interaction_patterns: Dict[str, float] = Field(default_factory=dict)
    response_preferences: Dict[str, float] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    adaptation_score: float = 0.0

# 🌊 Streaming & Real-time Models
class StreamingChunk(BaseModel):
    """Individual streaming response chunk"""
    content: str
    chunk_type: Literal["text", "source", "context", "intent", "metadata"] = "text"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_attribution: Optional[Dict[str, Any]] = None
    quality_score: Optional[float] = None

class StreamingProgress(BaseModel):
    """Progress tracking for streaming operations"""
    operation: str
    progress: float  # 0.0 to 1.0
    status: Literal["starting", "in_progress", "completed", "failed"] = "in_progress"
    details: Optional[str] = None
    sources_found: int = 0
    context_quality: float = 0.0

class AsyncTaskResult(BaseModel):
    """Result from asynchronous background processing"""
    task_id: str
    task_type: str
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

# 🤝 Multi-Agent Collaboration Models
class AgentExpertise(str, Enum):
    NUTRITION = "nutrition"
    MEDICAL = "medical"
    BEHAVIOR = "behavior"
    GROOMING = "grooming"
    TRAINING = "training"
    EMERGENCY = "emergency"
    GENERAL = "general"

class AgentCapability(BaseModel):
    """Individual agent capability definition"""
    name: str
    expertise_area: AgentExpertise
    skill_level: float  # 0.0 to 1.0
    specializations: List[str] = Field(default_factory=list)
    success_rate: float = 1.0
    average_response_time: float = 1.0

class AgentPerformance(BaseModel):
    """Agent performance tracking"""
    agent_id: str
    total_tasks: int = 0
    successful_tasks: int = 0
    average_quality_score: float = 0.0
    average_response_time: float = 0.0
    expertise_scores: Dict[AgentExpertise, float] = Field(default_factory=dict)
    last_active: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AgentMessage(BaseModel):
    """Inter-agent communication message"""
    sender_id: str
    receiver_id: str
    message_type: Literal["task_request", "task_response", "consultation", "validation", "conflict_resolution"]
    content: Dict[str, Any]
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    requires_response: bool = False

class AgentConsensus(BaseModel):
    """Agent consensus for important decisions"""
    decision_topic: str
    participating_agents: List[str]
    votes: Dict[str, Dict[str, Any]]  # agent_id -> vote_data
    consensus_reached: bool = False
    final_decision: Optional[Dict[str, Any]] = None
    confidence_score: float = 0.0

# 🔍 Advanced Search & Retrieval Models
class SearchModalityType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VOICE = "voice"
    DOCUMENT = "document"
    VIDEO = "video"

class MultiModalQuery(BaseModel):
    """Multi-modal search query"""
    text_query: Optional[str] = None
    image_data: Optional[str] = None  # base64 encoded
    audio_data: Optional[str] = None  # base64 encoded
    document_data: Optional[str] = None  # base64 encoded
    query_type: SearchModalityType = SearchModalityType.TEXT
    processing_options: Dict[str, Any] = Field(default_factory=dict)

class SearchResult(BaseModel):
    """Enhanced search result with multi-modal support"""
    content: str
    source: str
    relevance_score: float
    modality: SearchModalityType
    metadata: Dict[str, Any] = Field(default_factory=dict)
    extracted_features: Optional[Dict[str, Any]] = None
    semantic_embedding: Optional[List[float]] = None

class HybridSearchConfig(BaseModel):
    """Configuration for hybrid search systems"""
    vector_weight: float = 0.4
    lexical_weight: float = 0.3
    graph_weight: float = 0.3
    enable_query_expansion: bool = True
    personalization_factor: float = 0.2
    domain_specific_boost: float = 0.1

# 🎨 Response Generation Improvements Models
class ReasoningStep(BaseModel):
    """Individual step in chain-of-thought reasoning"""
    step_number: int
    description: str
    reasoning: str
    confidence: float
    evidence: List[str] = Field(default_factory=list)
    dependencies: List[int] = Field(default_factory=list)  # Steps this depends on

class ChainOfThoughtReasoning(BaseModel):
    """Complete chain-of-thought reasoning process"""
    query: str
    steps: List[ReasoningStep]
    final_conclusion: str
    overall_confidence: float
    reasoning_time: float
    validation_passed: bool = True

class UserPersonality(BaseModel):
    """User personality model for response personalization"""
    user_id: int
    communication_style: Literal["formal", "casual", "friendly", "professional"] = "friendly"
    complexity_preference: Literal["simple", "moderate", "detailed", "technical"] = "moderate"
    emotional_tone: Literal["neutral", "empathetic", "encouraging", "direct"] = "empathetic"
    response_length: Literal["brief", "moderate", "detailed", "comprehensive"] = "moderate"
    interaction_patterns: Dict[str, float] = Field(default_factory=dict)
    learning_rate: float = 0.1

class ResponseQuality(BaseModel):
    """Response quality assessment"""
    relevance_score: float  # 0.0 to 1.0
    accuracy_score: float   # 0.0 to 1.0
    factual_consistency: float  # 0.0 to 1.0
    bias_score: float      # 0.0 (no bias) to 1.0 (high bias)
    safety_score: float    # 0.0 to 1.0
    appropriateness_score: float  # 0.0 to 1.0
    source_support: float  # 0.0 to 1.0
    overall_quality: float # Computed average

# 📊 Evaluation & Feedback Models
class ConversationMetrics(BaseModel):
    """Conversation quality metrics"""
    conversation_id: str
    user_id: int
    total_exchanges: int
    avg_response_relevance: float
    avg_response_accuracy: float
    user_satisfaction_predicted: float
    success_rate: float
    source_utilization: float
    conversation_duration: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserFeedback(BaseModel):
    """User feedback on responses"""
    message_id: str
    user_id: int
    feedback_type: Literal["thumbs_up", "thumbs_down", "correction", "preference"]
    rating: Optional[int] = None  # 1-5 scale
    correction_text: Optional[str] = None
    feedback_text: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SystemImprovement(BaseModel):
    """System improvement tracking"""
    improvement_id: str
    improvement_type: Literal["pattern_identified", "strategy_updated", "model_retrained"]
    description: str
    confidence: float
    expected_impact: float
    implementation_status: Literal["proposed", "testing", "deployed", "reverted"]
    metrics_before: Dict[str, float] = Field(default_factory=dict)
    metrics_after: Dict[str, float] = Field(default_factory=dict)

# 🛡️ Reliability & Error Handling Models
class CircuitBreakerState(BaseModel):
    """Circuit breaker state for service calls"""
    service_name: str
    state: Literal["closed", "open", "half_open"] = "closed"
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    success_count: int = 0
    failure_threshold: int = 5
    timeout_duration: float = 60.0  # seconds

class SystemHealth(BaseModel):
    """System health monitoring"""
    component: str
    status: Literal["healthy", "degraded", "critical", "down"] = "healthy"
    response_time: float
    error_rate: float
    last_check: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    alerts_triggered: List[str] = Field(default_factory=list)

class DataQualityCheck(BaseModel):
    """Data quality validation result"""
    data_source: str
    quality_score: float
    freshness_score: float
    reliability_score: float
    validation_passed: bool
    issues_found: List[str] = Field(default_factory=list)
    last_checked: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# 🔮 Advanced AI Capabilities Models
class ConversationGoal(BaseModel):
    """Goal-oriented conversation planning"""
    goal_id: str
    user_id: int
    goal_description: str
    goal_type: Literal["information_gathering", "problem_solving", "care_planning", "monitoring"]
    sub_goals: List[str] = Field(default_factory=list)
    progress: float = 0.0  # 0.0 to 1.0
    status: Literal["active", "completed", "paused", "abandoned"] = "active"
    estimated_turns: int = 5
    actual_turns: int = 0

class ProactiveRecommendation(BaseModel):
    """Proactive assistance recommendation"""
    recommendation_id: str
    user_id: int
    recommendation_type: Literal["reminder", "suggestion", "insight", "warning"]
    content: str
    confidence: float
    urgency: Literal["low", "medium", "high", "critical"] = "medium"
    context: Dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None

class AgentDebate(BaseModel):
    """Multi-agent debate and reasoning"""
    debate_id: str
    topic: str
    participating_agents: List[str]
    arguments: Dict[str, List[str]] = Field(default_factory=dict)  # agent_id -> arguments
    counter_arguments: Dict[str, List[str]] = Field(default_factory=dict)
    consensus_reached: bool = False
    final_decision: Optional[str] = None
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    debate_rounds: int = 0

# 🎯 Advanced Intent Classification Models
class IntentType(str, Enum):
    CARE_HISTORY = "care_history"
    MEDICAL_RECORDS = "medical_records"
    REMINDERS = "reminders"
    DOCUMENT_SEARCH = "document_search"
    GENERAL_QUESTION = "general_question"
    CARE_PLANNING = "care_planning"
    NUTRITION = "nutrition"
    BEHAVIOR = "behavior"
    EMERGENCY = "emergency"
    SCHEDULING = "scheduling"

class SubIntentType(str, Enum):
    # Medical sub-intents
    VACCINATION = "vaccination"
    VET_VISIT = "vet_visit"
    MEDICATION = "medication"
    SYMPTOMS = "symptoms"
    
    # Care sub-intents
    GROOMING = "grooming"
    EXERCISE = "exercise"
    TRAINING = "training"
    
    # Document sub-intents
    SEARCH_SPECIFIC = "search_specific"
    SUMMARIZE = "summarize"
    EXTRACT_INFO = "extract_info"

class ContextRequirement(BaseModel):
    type: str = Field(description="Type of context needed")
    priority: float = Field(description="Priority score 0-1", ge=0, le=1)
    required: bool = Field(description="Whether this context is required")

class IntentAnalysis(BaseModel):
    """Advanced intent analysis with structured output"""
    primary_intent: IntentType = Field(description="Primary intent category")
    sub_intents: List[SubIntentType] = Field(description="Sub-intent categories", default=[])
    confidence: float = Field(description="Confidence score 0-1", ge=0, le=1)
    complexity: float = Field(description="Query complexity 0-1", ge=0, le=1)
    requires_context: bool = Field(description="Whether user context is needed")
    context_requirements: List[ContextRequirement] = Field(description="Specific context needs")
    urgency: float = Field(description="Urgency score 0-1", ge=0, le=1)
    ambiguity: float = Field(description="Ambiguity score 0-1", ge=0, le=1)
    
    @validator('confidence')
    def calibrate_confidence(cls, v):
        # Confidence calibration - adjust overconfident predictions
        if v > 0.95:
            return 0.95
        elif v < 0.3:
            return max(0.3, v * 1.2)  # Boost low confidence slightly
        return v

class MultiIntentAnalysis(BaseModel):
    """Multi-intent detection results"""
    intents: List[IntentAnalysis] = Field(description="List of detected intents")
    primary_intent_index: int = Field(description="Index of primary intent")
    requires_disambiguation: bool = Field(description="Whether disambiguation is needed")
    processing_strategy: Literal["sequential", "parallel", "hierarchical"] = Field(
        description="How to process multiple intents"
    )

class AdvancedChatState(MessagesState):
    """Enhanced state with advanced intent, tools, memory, and state management"""
    user_id: int
    thread_id: str
    intent_analysis: Optional[MultiIntentAnalysis]
    current_agent: Optional[str]
    user_context: Dict[str, Any]
    sources_used: List[Dict[str, Any]]
    response_metadata: Dict[str, Any]
    agent_results: Dict[str, Any]  # Results from specialized agents
    routing_history: List[str]  # Track which agents were used
    
    # 🛠️ Tool Integration State
    available_tools: List[str] = Field(default_factory=list)
    tool_results: List[ToolExecutionResult] = Field(default_factory=list)
    tool_execution_plan: Optional[Dict[str, Any]] = None
    
    # 🧠 Advanced Memory State
    active_memories: List[MemoryItem] = Field(default_factory=list)
    memory_context: Dict[str, Any] = Field(default_factory=dict)
    memory_consolidation_needed: bool = False
    
    # 🔄 State Management
    state_snapshots: List[StateSnapshot] = Field(default_factory=list)
    personalization_profile: Optional[PersonalizationProfile] = None
    state_version: int = 1
    
    # 📊 Performance Metrics
    processing_metrics: Dict[str, float] = Field(default_factory=dict)
    quality_scores: Dict[str, float] = Field(default_factory=dict)
    
    # 🌊 Streaming State
    streaming_chunks: List[StreamingChunk] = Field(default_factory=list)
    streaming_progress: Optional[StreamingProgress] = None
    async_tasks: Dict[str, AsyncTaskResult] = Field(default_factory=dict)
    
    # 🤝 Multi-Agent State
    active_agents: List[str] = Field(default_factory=list)
    agent_messages: List[AgentMessage] = Field(default_factory=list)
    agent_consensus: Optional[AgentConsensus] = None
    specialist_assignments: Dict[str, str] = Field(default_factory=dict)  # task_id -> agent_id
    
    # 🔍 Advanced Search State
    multi_modal_query: Optional[MultiModalQuery] = None
    search_results: List[SearchResult] = Field(default_factory=list)
    hybrid_search_config: HybridSearchConfig = Field(default_factory=HybridSearchConfig)
    search_personalization: Dict[str, float] = Field(default_factory=dict)
    
    # 🎨 Response Generation State
    chain_of_thought: Optional[ChainOfThoughtReasoning] = None
    user_personality: Optional[UserPersonality] = None
    response_quality: Optional[ResponseQuality] = None
    
    # 📊 Evaluation & Feedback State
    conversation_metrics: Optional[ConversationMetrics] = None
    user_feedback: List[UserFeedback] = Field(default_factory=list)
    system_improvements: List[SystemImprovement] = Field(default_factory=list)
    
    # 🛡️ Reliability State
    circuit_breakers: Dict[str, CircuitBreakerState] = Field(default_factory=dict)
    system_health: Dict[str, SystemHealth] = Field(default_factory=dict)
    data_quality: Dict[str, DataQualityCheck] = Field(default_factory=dict)
    
    # 🔮 Advanced AI State
    conversation_goals: List[ConversationGoal] = Field(default_factory=list)
    proactive_recommendations: List[ProactiveRecommendation] = Field(default_factory=list)
    agent_debates: List[AgentDebate] = Field(default_factory=list)

class AdvancedLangGraphService:
    """Advanced LangGraph service with sophisticated intent routing, tools, memory, and state management"""
    
    def __init__(self):
        self.care_service = CareArchiveService()
        self.checkpointer = None
        self.graph = None
        self.intent_parser = PydanticOutputParser(pydantic_object=MultiIntentAnalysis)
        
        # 🛠️ Tool Integration Systems
        self.tool_registry: Dict[str, BaseTool] = {}
        self.tool_cache: Dict[str, Any] = {}
        self.tool_stats: Dict[str, ToolUsageStats] = {}
        self.tool_executor = ThreadPoolExecutor(max_workers=5)
        
        # 🧠 Advanced Memory Systems
        self.hierarchical_memory: Dict[int, Dict[MemoryType, List[MemoryItem]]] = defaultdict(lambda: defaultdict(list))
        self.memory_graph: Dict[str, List[str]] = defaultdict(list)  # Memory relationships
        self.memory_consolidation_queue: deque = deque()
        
        # 🔄 State Management Systems
        self.state_snapshots: Dict[str, List[StateSnapshot]] = defaultdict(list)
        self.personalization_profiles: Dict[int, PersonalizationProfile] = {}
        self.state_compression_threshold = 1000  # Messages before compression
        
        # 🌊 Streaming & Real-time Systems
        self.streaming_sessions: Dict[str, Dict[str, Any]] = {}
        self.async_task_queue: asyncio.Queue = asyncio.Queue()
        self.background_tasks: Dict[str, asyncio.Task] = {}
        
        # 🤝 Multi-Agent Collaboration Systems
        self.agent_registry: Dict[str, AgentCapability] = {}
        self.agent_performance: Dict[str, AgentPerformance] = {}
        self.agent_message_queue: asyncio.Queue = asyncio.Queue()
        self.agent_workspace: Dict[str, Any] = {}
        self.supervisor_agents: List[str] = []
        
        # 🔍 Advanced Search & Retrieval Systems
        self.multi_modal_processors: Dict[SearchModalityType, Callable] = {}
        self.search_indices: Dict[str, Any] = {}
        self.domain_embeddings = None  # Will be initialized with domain-specific model
        self.search_cache: Dict[str, List[SearchResult]] = {}
        
        # 🎨 Response Generation Systems
        self.user_personalities: Dict[int, UserPersonality] = {}
        self.response_templates: Dict[str, str] = {}
        self.reasoning_cache: Dict[str, ChainOfThoughtReasoning] = {}
        
        # 📊 Evaluation & Feedback Systems
        self.conversation_metrics: Dict[str, ConversationMetrics] = {}
        self.feedback_history: Dict[int, List[UserFeedback]] = defaultdict(list)
        self.system_improvements: List[SystemImprovement] = []
        self.ab_test_strategies: Dict[str, Dict[str, Any]] = {}
        
        # 🛡️ Reliability & Error Handling Systems
        self.circuit_breakers: Dict[str, CircuitBreakerState] = {}
        self.system_health_monitors: Dict[str, SystemHealth] = {}
        self.data_quality_checks: Dict[str, DataQualityCheck] = {}
        self.retry_strategies: Dict[str, Dict[str, Any]] = {}
        
        # 🔮 Advanced AI Capabilities Systems
        self.conversation_goals: Dict[int, List[ConversationGoal]] = defaultdict(list)
        self.proactive_engine: Dict[str, Any] = {}
        self.agent_debates: Dict[str, AgentDebate] = {}
        self.predictive_models: Dict[str, Any] = {}
        
        # Initialize all systems
        self._initialize_tools()
        self._initialize_memory_system()
        self._initialize_state_management()
        self._initialize_streaming_system()
        self._initialize_multi_agent_system()
        self._initialize_advanced_search()
        self._initialize_response_generation()
        self._initialize_evaluation_feedback()
        self._initialize_reliability_systems()
        self._initialize_advanced_ai_capabilities()
        self._initialize_graph()
    
    def _initialize_tools(self):
        """Initialize advanced tool integration system"""
        try:
            # Register custom tools with @tool decorator
            self._register_pet_care_tools()
            current_app.logger.info(f"Initialized {len(self.tool_registry)} advanced tools")
        except Exception as e:
            current_app.logger.error(f"Tool initialization failed: {str(e)}")
    
    def _initialize_memory_system(self):
        """Initialize hierarchical memory system"""
        try:
            # Set up memory decay schedules
            self._setup_memory_decay()
            current_app.logger.info("Advanced memory system initialized")
        except Exception as e:
            current_app.logger.error(f"Memory system initialization failed: {str(e)}")
    
    def _initialize_state_management(self):
        """Initialize advanced state management"""
        try:
            # Set up state compression and versioning
            self._setup_state_versioning()
            current_app.logger.info("Advanced state management initialized")
        except Exception as e:
            current_app.logger.error(f"State management initialization failed: {str(e)}")
    
    def _initialize_streaming_system(self):
        """Initialize streaming and real-time systems"""
        try:
            # Set up streaming capabilities
            self._setup_streaming_handlers()
            current_app.logger.info("Streaming system initialized")
        except Exception as e:
            current_app.logger.error(f"Streaming system initialization failed: {str(e)}")
    
    def _initialize_multi_agent_system(self):
        """Initialize multi-agent collaboration system"""
        try:
            # Register specialist agents
            self._register_specialist_agents()
            # Set up agent communication
            self._setup_agent_communication()
            current_app.logger.info("Multi-agent system initialized")
        except Exception as e:
            current_app.logger.error(f"Multi-agent system initialization failed: {str(e)}")
    
    def _initialize_advanced_search(self):
        """Initialize advanced search and retrieval systems"""
        try:
            # Set up multi-modal processors
            self._setup_multi_modal_processors()
            # Initialize domain-specific embeddings
            self._setup_domain_embeddings()
            # Set up hybrid search
            self._setup_hybrid_search()
            current_app.logger.info("Advanced search system initialized")
        except Exception as e:
            current_app.logger.error(f"Advanced search initialization failed: {str(e)}")
    
    def _initialize_response_generation(self):
        """Initialize response generation improvements"""
        try:
            # Set up response templates
            self._setup_response_templates()
            # Initialize reasoning system
            self._setup_reasoning_system()
            current_app.logger.info("Response generation system initialized")
        except Exception as e:
            current_app.logger.error(f"Response generation initialization failed: {str(e)}")
    
    def _initialize_evaluation_feedback(self):
        """Initialize evaluation and feedback systems"""
        try:
            # Set up metrics tracking
            self._setup_metrics_tracking()
            # Initialize feedback processing
            self._setup_feedback_processing()
            current_app.logger.info("Evaluation & feedback system initialized")
        except Exception as e:
            current_app.logger.error(f"Evaluation & feedback initialization failed: {str(e)}")
    
    def _initialize_reliability_systems(self):
        """Initialize reliability and error handling systems"""
        try:
            # Set up circuit breakers
            self._setup_circuit_breakers()
            # Initialize health monitoring
            self._setup_health_monitoring()
            # Set up data quality checks
            self._setup_data_quality_checks()
            current_app.logger.info("Reliability systems initialized")
        except Exception as e:
            current_app.logger.error(f"Reliability systems initialization failed: {str(e)}")
    
    def _initialize_advanced_ai_capabilities(self):
        """Initialize advanced AI capabilities"""
        try:
            # Set up goal-oriented planning
            self._setup_goal_planning()
            # Initialize proactive assistance
            self._setup_proactive_assistance()
            # Set up multi-agent reasoning
            self._setup_multi_agent_reasoning()
            current_app.logger.info("Advanced AI capabilities initialized")
        except Exception as e:
            current_app.logger.error(f"Advanced AI capabilities initialization failed: {str(e)}")
    
    def _initialize_graph(self):
        """Initialize advanced LangGraph with conditional routing"""
        try:
            database_url = os.getenv('DATABASE_URL')
            
            # Try PostgreSQL checkpointer first, fallback to memory
            try:
                self.checkpointer = PostgresSaver.from_conn_string(database_url)
                self.checkpointer.setup()
                current_app.logger.info("Using PostgreSQL checkpointer")
            except Exception as e:
                current_app.logger.warning(f"PostgreSQL checkpointer failed, using memory: {str(e)}")
                self.checkpointer = MemorySaver()
            
            # For now, use simple in-memory storage for user context
            self.user_memories = {}
            
            self._build_advanced_graph()
            
            current_app.logger.info("Advanced LangGraph service initialized successfully")
            
        except Exception as e:
            current_app.logger.error(f"Error initializing advanced LangGraph service: {str(e)}")
            raise
    
    # 🌊 STREAMING & REAL-TIME FEATURES
    
    def _setup_streaming_handlers(self):
        """Set up streaming response handlers"""
        self.streaming_handlers = {
            "token_streaming": self._handle_token_streaming,
            "context_streaming": self._handle_context_streaming,
            "progress_streaming": self._handle_progress_streaming
        }
    
    async def stream_response_generation(self, 
                                       user_id: int, 
                                       message: str, 
                                       thread_id: Optional[str] = None) -> AsyncGenerator[StreamingChunk, None]:
        """Stream response generation with real-time feedback"""
        try:
            session_id = thread_id or str(uuid.uuid4())
            
            # Initialize streaming session
            self.streaming_sessions[session_id] = {
                "user_id": user_id,
                "start_time": datetime.now(timezone.utc),
                "chunks_sent": 0,
                "total_tokens": 0
            }
            
            # Stream intent analysis
            yield StreamingChunk(
                content="🤔 Analyzing your request...",
                chunk_type="intent",
                source_attribution={"component": "intent_analyzer"}
            )
            
            # Progressive context building
            async for progress_chunk in self._stream_context_building(user_id, message):
                yield progress_chunk
            
            # Stream response synthesis
            async for response_chunk in self._stream_response_synthesis(user_id, message, session_id):
                yield response_chunk
            
            # Final metadata chunk
            session = self.streaming_sessions[session_id]
            yield StreamingChunk(
                content="",
                chunk_type="metadata",
                source_attribution={
                    "session_stats": {
                        "chunks_sent": session["chunks_sent"],
                        "duration_ms": (datetime.now(timezone.utc) - session["start_time"]).total_seconds() * 1000
                    }
                }
            )
            
        except Exception as e:
            current_app.logger.error(f"Streaming response generation failed: {str(e)}")
            yield StreamingChunk(
                content=f"Error: {str(e)}",
                chunk_type="text",
                source_attribution={"error": True}
            )
        finally:
            # Clean up streaming session
            if session_id in self.streaming_sessions:
                del self.streaming_sessions[session_id]
    
    async def _stream_context_building(self, user_id: int, message: str) -> AsyncGenerator[StreamingChunk, None]:
        """Stream context building progress"""
        try:
            # Search memories
            yield StreamingChunk(
                content="🧠 Searching relevant memories...",
                chunk_type="context",
                source_attribution={"component": "memory_search"}
            )
            
            memories = self.search_memories_by_embedding(user_id, message, limit=5)
            
            yield StreamingChunk(
                content=f"Found {len(memories)} relevant memories",
                chunk_type="context",
                source_attribution={
                    "component": "memory_search",
                    "count": len(memories)
                }
            )
            
            # Search care records
            yield StreamingChunk(
                content="📋 Searching care records...",
                chunk_type="context",
                source_attribution={"component": "care_search"}
            )
            
            await asyncio.sleep(0.1)  # Simulate processing time
            
            # Search documents
            yield StreamingChunk(
                content="📄 Analyzing documents...",
                chunk_type="context",
                source_attribution={"component": "document_search"}
            )
            
            await asyncio.sleep(0.1)
            
        except Exception as e:
            current_app.logger.error(f"Context streaming failed: {str(e)}")
    
    async def _stream_response_synthesis(self, user_id: int, message: str, session_id: str) -> AsyncGenerator[StreamingChunk, None]:
        """Stream response synthesis with token-level streaming"""
        try:
            # Simulate token-level response generation
            response_parts = [
                "Based on your query, ",
                "I found relevant information ",
                "in your pet's care records. ",
                "Here's what I discovered..."
            ]
            
            for i, part in enumerate(response_parts):
                yield StreamingChunk(
                    content=part,
                    chunk_type="text",
                    source_attribution={
                        "token_index": i,
                        "total_tokens": len(response_parts)
                    },
                    quality_score=0.8 + (i * 0.05)  # Increasing quality as response builds
                )
                
                # Update session stats
                if session_id in self.streaming_sessions:
                    self.streaming_sessions[session_id]["chunks_sent"] += 1
                    self.streaming_sessions[session_id]["total_tokens"] += len(part.split())
                
                await asyncio.sleep(0.2)  # Simulate streaming delay
                
        except Exception as e:
            current_app.logger.error(f"Response synthesis streaming failed: {str(e)}")
    
    def _handle_token_streaming(self, tokens: List[str]) -> Generator[StreamingChunk, None, None]:
        """Handle token-level streaming"""
        for i, token in enumerate(tokens):
            yield StreamingChunk(
                content=token,
                chunk_type="text",
                source_attribution={"token_index": i}
            )
    
    def _handle_context_streaming(self, context_updates: List[Dict[str, Any]]) -> Generator[StreamingChunk, None, None]:
        """Handle context building streaming"""
        for update in context_updates:
            yield StreamingChunk(
                content=update.get("message", ""),
                chunk_type="context",
                source_attribution=update
            )
    
    def _handle_progress_streaming(self, progress: StreamingProgress) -> StreamingChunk:
        """Handle progress streaming"""
        return StreamingChunk(
            content=f"Progress: {progress.progress:.1%}",
            chunk_type="metadata",
            source_attribution={"progress": progress.dict()}
        )
    
    async def schedule_background_task(self, task_type: str, task_data: Dict[str, Any], user_id: int) -> str:
        """Schedule asynchronous background processing"""
        task_id = str(uuid.uuid4())
        
        task_result = AsyncTaskResult(
            task_id=task_id,
            task_type=task_type,
            status="pending"
        )
        
        # Create and schedule the background task
        if task_type == "memory_consolidation":
            task = asyncio.create_task(self._background_memory_consolidation(user_id, task_id))
        elif task_type == "document_processing":
            task = asyncio.create_task(self._background_document_processing(task_data, task_id))
        elif task_type == "reminder_processing":
            task = asyncio.create_task(self._background_reminder_processing(task_data, task_id))
        else:
            task_result.status = "failed"
            task_result.error = f"Unknown task type: {task_type}"
            return task_id
        
        self.background_tasks[task_id] = task
        
        current_app.logger.info(f"Scheduled background task {task_id} of type {task_type}")
        return task_id
    
    async def _background_memory_consolidation(self, user_id: int, task_id: str):
        """Background memory consolidation processing"""
        try:
            await asyncio.sleep(1)  # Simulate processing time
            results = self.consolidate_memories(user_id)
            
            # Update task result
            if task_id in self.background_tasks:
                # Store result somewhere accessible
                current_app.logger.info(f"Background memory consolidation completed for user {user_id}: {results}")
                
        except Exception as e:
            current_app.logger.error(f"Background memory consolidation failed: {str(e)}")
    
    async def _background_document_processing(self, task_data: Dict[str, Any], task_id: str):
        """Background document processing"""
        try:
            # Simulate document processing
            await asyncio.sleep(2)
            current_app.logger.info(f"Background document processing completed for task {task_id}")
        except Exception as e:
            current_app.logger.error(f"Background document processing failed: {str(e)}")
    
    async def _background_reminder_processing(self, task_data: Dict[str, Any], task_id: str):
        """Background reminder processing"""
        try:
            # Simulate reminder processing
            await asyncio.sleep(0.5)
            current_app.logger.info(f"Background reminder processing completed for task {task_id}")
        except Exception as e:
            current_app.logger.error(f"Background reminder processing failed: {str(e)}")
    
    # 🤝 MULTI-AGENT COLLABORATION
    
    def _register_specialist_agents(self):
        """Register specialist agents with their capabilities"""
        specialists = [
            {
                "name": "nutrition_specialist",
                "expertise": AgentExpertise.NUTRITION,
                "skill_level": 0.95,
                "specializations": ["diet_planning", "nutritional_analysis", "supplement_recommendations"]
            },
            {
                "name": "medical_specialist",
                "expertise": AgentExpertise.MEDICAL,
                "skill_level": 0.98,
                "specializations": ["diagnosis_support", "treatment_planning", "medication_management"]
            },
            {
                "name": "behavior_specialist",
                "expertise": AgentExpertise.BEHAVIOR,
                "skill_level": 0.92,
                "specializations": ["training_programs", "behavioral_analysis", "socialization"]
            },
            {
                "name": "grooming_specialist",
                "expertise": AgentExpertise.GROOMING,
                "skill_level": 0.88,
                "specializations": ["coat_care", "nail_trimming", "dental_hygiene"]
            },
            {
                "name": "emergency_specialist",
                "expertise": AgentExpertise.EMERGENCY,
                "skill_level": 0.99,
                "specializations": ["emergency_assessment", "first_aid", "urgent_care"]
            },
            {
                "name": "supervisor_agent",
                "expertise": AgentExpertise.GENERAL,
                "skill_level": 0.90,
                "specializations": ["task_coordination", "quality_control", "agent_management"]
            }
        ]
        
        for spec in specialists:
            capability = AgentCapability(
                name=spec["name"],
                expertise_area=spec["expertise"],
                skill_level=spec["skill_level"],
                specializations=spec["specializations"]
            )
            
            self.agent_registry[spec["name"]] = capability
            self.agent_performance[spec["name"]] = AgentPerformance(agent_id=spec["name"])
            
            if spec["name"] == "supervisor_agent":
                self.supervisor_agents.append(spec["name"])
    
    def _setup_agent_communication(self):
        """Set up inter-agent communication protocols"""
        self.agent_message_handlers = {
            "task_request": self._handle_agent_task_request,
            "task_response": self._handle_agent_task_response,
            "consultation": self._handle_agent_consultation,
            "validation": self._handle_agent_validation,
            "conflict_resolution": self._handle_agent_conflict_resolution
        }
    
    async def send_agent_message(self, sender: str, receiver: str, message_type: str, 
                                content: Dict[str, Any], requires_response: bool = False) -> str:
        """Send message between agents"""
        message = AgentMessage(
            sender_id=sender,
            receiver_id=receiver,
            message_type=message_type,
            content=content,
            requires_response=requires_response
        )
        
        # Add to message queue for processing
        await self.agent_message_queue.put(message)
        
        current_app.logger.info(f"Agent message sent from {sender} to {receiver}: {message_type}")
        return message.timestamp.isoformat()
    
    async def process_agent_messages(self):
        """Process pending agent messages"""
        try:
            while not self.agent_message_queue.empty():
                message = await self.agent_message_queue.get()
                handler = self.agent_message_handlers.get(message.message_type)
                
                if handler:
                    await handler(message)
                else:
                    current_app.logger.warning(f"No handler for message type: {message.message_type}")
                    
        except Exception as e:
            current_app.logger.error(f"Agent message processing failed: {str(e)}")
    
    async def _handle_agent_task_request(self, message: AgentMessage):
        """Handle agent task request"""
        try:
            # Find best agent for the task
            task_requirements = message.content.get("requirements", {})
            best_agent = self._select_best_agent(task_requirements)
            
            if best_agent:
                # Assign task to best agent
                response_content = {
                    "assigned_agent": best_agent,
                    "task_id": str(uuid.uuid4()),
                    "estimated_completion": datetime.now(timezone.utc) + timedelta(minutes=5)
                }
                
                await self.send_agent_message(
                    sender="system",
                    receiver=message.sender_id,
                    message_type="task_response",
                    content=response_content
                )
                
        except Exception as e:
            current_app.logger.error(f"Task request handling failed: {str(e)}")
    
    async def _handle_agent_task_response(self, message: AgentMessage):
        """Handle agent task response"""
        # Store task result in agent workspace
        task_id = message.content.get("task_id")
        if task_id:
            self.agent_workspace[task_id] = {
                "result": message.content,
                "agent": message.sender_id,
                "completed_at": datetime.now(timezone.utc)
            }
    
    async def _handle_agent_consultation(self, message: AgentMessage):
        """Handle agent consultation request"""
        # Route consultation to appropriate expert
        expertise_needed = message.content.get("expertise")
        if expertise_needed:
            expert_agent = self._find_expert_agent(expertise_needed)
            if expert_agent and expert_agent != message.sender_id:
                await self.send_agent_message(
                    sender="system",
                    receiver=expert_agent,
                    message_type="consultation",
                    content=message.content,
                    requires_response=True
                )
    
    async def _handle_agent_validation(self, message: AgentMessage):
        """Handle agent validation request"""
        # Implement peer review validation
        validators = self._select_validation_agents(message.sender_id)
        for validator in validators:
            await self.send_agent_message(
                sender="system",
                receiver=validator,
                message_type="validation",
                content=message.content
            )
    
    async def _handle_agent_conflict_resolution(self, message: AgentMessage):
        """Handle agent conflict resolution"""
        # Route to supervisor agent
        if self.supervisor_agents:
            supervisor = self.supervisor_agents[0]
            await self.send_agent_message(
                sender="system",
                receiver=supervisor,
                message_type="conflict_resolution",
                content=message.content
            )
    
    def _select_best_agent(self, requirements: Dict[str, Any]) -> Optional[str]:
        """Select best agent based on requirements"""
        expertise_needed = requirements.get("expertise")
        if not expertise_needed:
            return None
        
        # Find agents with matching expertise
        candidates = []
        for agent_id, capability in self.agent_registry.items():
            if capability.expertise_area.value == expertise_needed:
                performance = self.agent_performance.get(agent_id)
                if performance:
                    score = capability.skill_level * performance.average_quality_score * performance.success_rate
                    candidates.append((agent_id, score))
        
        # Return best candidate
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]
        
        return None
    
    def _find_expert_agent(self, expertise: str) -> Optional[str]:
        """Find expert agent for specific expertise"""
        for agent_id, capability in self.agent_registry.items():
            if capability.expertise_area.value == expertise:
                return agent_id
        return None
    
    def _select_validation_agents(self, exclude_agent: str) -> List[str]:
        """Select agents for validation (excluding the original agent)"""
        validators = []
        for agent_id, capability in self.agent_registry.items():
            if agent_id != exclude_agent and capability.skill_level > 0.8:
                validators.append(agent_id)
        return validators[:2]  # Return up to 2 validators
    
    async def create_agent_consensus(self, topic: str, participating_agents: List[str], 
                                   decision_data: Dict[str, Any]) -> AgentConsensus:
        """Create agent consensus for important decisions"""
        consensus = AgentConsensus(
            decision_topic=topic,
            participating_agents=participating_agents,
            votes={}
        )
        
        # Request votes from participating agents
        for agent in participating_agents:
            await self.send_agent_message(
                sender="system",
                receiver=agent,
                message_type="consultation",
                content={
                    "consensus_request": True,
                    "topic": topic,
                    "data": decision_data
                },
                requires_response=True
            )
        
        # For now, simulate consensus (in real implementation, would wait for responses)
        consensus.votes = {agent: {"vote": "approve", "confidence": 0.8} for agent in participating_agents}
        consensus.consensus_reached = len([v for v in consensus.votes.values() if v["vote"] == "approve"]) >= len(participating_agents) * 0.6
        consensus.confidence_score = sum(v["confidence"] for v in consensus.votes.values()) / len(consensus.votes)
        
        return consensus
    
    def update_agent_performance(self, agent_id: str, task_quality: float, response_time: float, success: bool):
        """Update agent performance metrics"""
        if agent_id not in self.agent_performance:
            self.agent_performance[agent_id] = AgentPerformance(agent_id=agent_id)
        
        performance = self.agent_performance[agent_id]
        performance.total_tasks += 1
        
        if success:
            performance.successful_tasks += 1
        
        # Update averages
        total_tasks = performance.total_tasks
        performance.average_quality_score = ((performance.average_quality_score * (total_tasks - 1)) + task_quality) / total_tasks
        performance.average_response_time = ((performance.average_response_time * (total_tasks - 1)) + response_time) / total_tasks
        performance.last_active = datetime.now(timezone.utc)
    
    # 🔍 ADVANCED SEARCH & RETRIEVAL
    
    def _setup_multi_modal_processors(self):
        """Set up multi-modal content processors"""
        self.multi_modal_processors = {
            SearchModalityType.TEXT: self._process_text_query,
            SearchModalityType.IMAGE: self._process_image_query,
            SearchModalityType.VOICE: self._process_voice_query,
            SearchModalityType.DOCUMENT: self._process_document_query,
            SearchModalityType.VIDEO: self._process_video_query
        }
    
    def _setup_domain_embeddings(self):
        """Initialize domain-specific embeddings for pet care"""
        try:
            # For now, use OpenAI embeddings (could be replaced with domain-specific model)
            self.domain_embeddings = embeddings_model
            current_app.logger.info("Domain-specific embeddings initialized")
        except Exception as e:
            current_app.logger.error(f"Domain embeddings setup failed: {str(e)}")
            self.domain_embeddings = embeddings_model  # Fallback to general embeddings
    
    def _setup_hybrid_search(self):
        """Set up hybrid search system combining multiple approaches"""
        self.hybrid_search_config = HybridSearchConfig()
        
        # Initialize search indices
        self.search_indices = {
            "vector_index": {},  # Semantic embeddings
            "lexical_index": {},  # Keyword search
            "graph_index": {}     # Relationship-based search
        }
    
    async def multi_modal_search(self, query: MultiModalQuery, user_id: int, limit: int = 10) -> List[SearchResult]:
        """Perform multi-modal search across different content types"""
        try:
            # Generate cache key
            cache_key = hashlib.md5(str(query.dict()).encode()).hexdigest()
            
            # Check cache first
            if cache_key in self.search_cache:
                cached_results = self.search_cache[cache_key]
                if len(cached_results) > 0:
                    return cached_results[:limit]
            
            # Process query based on modality
            processor = self.multi_modal_processors.get(query.query_type)
            if not processor:
                raise ValueError(f"No processor for modality: {query.query_type}")
            
            # Extract features from query
            query_features = await processor(query)
            
            # Perform hybrid search
            search_results = await self._hybrid_search(query_features, user_id, limit)
            
            # Apply personalization
            personalized_results = self._apply_search_personalization(search_results, user_id)
            
            # Cache results
            self.search_cache[cache_key] = personalized_results
            
            return personalized_results
            
        except Exception as e:
            current_app.logger.error(f"Multi-modal search failed: {str(e)}")
            return []
    
    async def _process_text_query(self, query: MultiModalQuery) -> Dict[str, Any]:
        """Process text query and extract features"""
        text_query = query.text_query or ""
        
        # Generate embeddings
        embeddings = self.domain_embeddings.embed_query(text_query)
        
        # Extract keywords
        keywords = text_query.lower().split()
        
        # Analyze intent
        pet_care_keywords = {
            "medical": ["vet", "doctor", "sick", "medicine", "vaccination", "surgery"],
            "nutrition": ["food", "diet", "nutrition", "feeding", "treat", "supplement"],
            "behavior": ["training", "behavior", "aggression", "anxiety", "socialization"],
            "grooming": ["groom", "bath", "brush", "nail", "dental", "hygiene"]
        }
        
        intent_scores = {}
        for category, category_keywords in pet_care_keywords.items():
            score = sum(1 for word in keywords if word in category_keywords)
            intent_scores[category] = score / len(keywords) if keywords else 0
        
        return {
            "text": text_query,
            "embeddings": embeddings,
            "keywords": keywords,
            "intent_scores": intent_scores,
            "modality": SearchModalityType.TEXT
        }
    
    async def _process_image_query(self, query: MultiModalQuery) -> Dict[str, Any]:
        """Process image query and extract visual features"""
        try:
            if not query.image_data:
                raise ValueError("No image data provided")
            
            # Decode base64 image
            image_bytes = base64.b64decode(query.image_data)
            
            # For now, simulate image processing (would use actual vision model)
            # In real implementation, would use OpenAI Vision API or specialized pet image recognition
            simulated_features = {
                "detected_objects": ["dog", "collar", "outdoor"],
                "colors": ["brown", "black", "green"],
                "scene_type": "outdoor",
                "estimated_breed": "unknown",
                "estimated_age": "adult",
                "health_indicators": []
            }
            
            # Generate text description for embedding
            description = f"Image showing {', '.join(simulated_features['detected_objects'])}"
            embeddings = self.domain_embeddings.embed_query(description)
            
            return {
                "image_features": simulated_features,
                "embeddings": embeddings,
                "description": description,
                "modality": SearchModalityType.IMAGE
            }
            
        except Exception as e:
            current_app.logger.error(f"Image processing failed: {str(e)}")
            return {"error": str(e), "modality": SearchModalityType.IMAGE}
    
    async def _process_voice_query(self, query: MultiModalQuery) -> Dict[str, Any]:
        """Process voice query and extract audio features"""
        try:
            if not query.audio_data:
                raise ValueError("No audio data provided")
            
            # For now, simulate voice processing (would use speech-to-text)
            simulated_transcript = "My dog seems to be limping"
            
            # Process as text query
            text_query = MultiModalQuery(text_query=simulated_transcript, query_type=SearchModalityType.TEXT)
            text_features = await self._process_text_query(text_query)
            
            # Add voice-specific features
            voice_features = {
                "transcript": simulated_transcript,
                "confidence": 0.85,
                "detected_emotion": "concern",
                "urgency_level": 0.7
            }
            
            text_features.update({
                "voice_features": voice_features,
                "modality": SearchModalityType.VOICE
            })
            
            return text_features
            
        except Exception as e:
            current_app.logger.error(f"Voice processing failed: {str(e)}")
            return {"error": str(e), "modality": SearchModalityType.VOICE}
    
    async def _process_document_query(self, query: MultiModalQuery) -> Dict[str, Any]:
        """Process document query with OCR and structured extraction"""
        try:
            if not query.document_data:
                raise ValueError("No document data provided")
            
            # Simulate OCR processing (would use actual OCR service)
            simulated_text = "Veterinary Report - Patient: Max, Date: 2024-01-15, Diagnosis: Healthy"
            
            # Extract structured data
            structured_data = {
                "document_type": "veterinary_report",
                "patient_name": "Max",
                "date": "2024-01-15",
                "diagnosis": "Healthy",
                "recommendations": []
            }
            
            # Process extracted text
            text_query = MultiModalQuery(text_query=simulated_text, query_type=SearchModalityType.TEXT)
            text_features = await self._process_text_query(text_query)
            
            text_features.update({
                "structured_data": structured_data,
                "extracted_text": simulated_text,
                "modality": SearchModalityType.DOCUMENT
            })
            
            return text_features
            
        except Exception as e:
            current_app.logger.error(f"Document processing failed: {str(e)}")
            return {"error": str(e), "modality": SearchModalityType.DOCUMENT}
    
    async def _process_video_query(self, query: MultiModalQuery) -> Dict[str, Any]:
        """Process video query and extract temporal features"""
        try:
            # Simulate video processing (would extract frames and analyze)
            simulated_features = {
                "duration_seconds": 30,
                "frame_analysis": [
                    {"timestamp": 0, "objects": ["dog", "walking"]},
                    {"timestamp": 15, "objects": ["dog", "limping"]},
                    {"timestamp": 30, "objects": ["dog", "sitting"]}
                ],
                "detected_behaviors": ["walking", "limping", "resting"],
                "health_concerns": ["possible_injury"]
            }
            
            # Generate description
            description = f"Video showing dog behavior: {', '.join(simulated_features['detected_behaviors'])}"
            embeddings = self.domain_embeddings.embed_query(description)
            
            return {
                "video_features": simulated_features,
                "embeddings": embeddings,
                "description": description,
                "modality": SearchModalityType.VIDEO
            }
            
        except Exception as e:
            current_app.logger.error(f"Video processing failed: {str(e)}")
            return {"error": str(e), "modality": SearchModalityType.VIDEO}
    
    async def _hybrid_search(self, query_features: Dict[str, Any], user_id: int, limit: int) -> List[SearchResult]:
        """Perform hybrid search combining vector, lexical, and graph-based approaches"""
        try:
            results = []
            config = self.hybrid_search_config
            
            # Vector search (semantic similarity)
            if "embeddings" in query_features:
                vector_results = await self._vector_search(query_features["embeddings"], user_id, limit)
                for result in vector_results:
                    result.relevance_score *= config.vector_weight
                results.extend(vector_results)
            
            # Lexical search (keyword matching)
            if "keywords" in query_features:
                lexical_results = await self._lexical_search(query_features["keywords"], user_id, limit)
                for result in lexical_results:
                    result.relevance_score *= config.lexical_weight
                results.extend(lexical_results)
            
            # Graph search (relationship-based)
            graph_results = await self._graph_search(query_features, user_id, limit)
            for result in graph_results:
                result.relevance_score *= config.graph_weight
            results.extend(graph_results)
            
            # Deduplicate and merge results
            unique_results = self._merge_search_results(results)
            
            # Sort by combined relevance score
            unique_results.sort(key=lambda x: x.relevance_score, reverse=True)
            
            return unique_results[:limit]
            
        except Exception as e:
            current_app.logger.error(f"Hybrid search failed: {str(e)}")
            return []
    
    async def _vector_search(self, query_embeddings: List[float], user_id: int, limit: int) -> List[SearchResult]:
        """Perform vector-based semantic search"""
        try:
            # Search in memory embeddings
            relevant_memories = self.search_memories_by_embedding(user_id, "", limit=limit)
            
            results = []
            for memory in relevant_memories:
                if memory.embeddings:
                    similarity = self._calculate_cosine_similarity(query_embeddings, memory.embeddings)
                    
                    result = SearchResult(
                        content=memory.content,
                        source=f"memory_{memory.id}",
                        relevance_score=similarity,
                        modality=SearchModalityType.TEXT,
                        metadata={
                            "memory_type": memory.memory_type.value,
                            "importance": memory.importance.value,
                            "timestamp": memory.timestamp.isoformat()
                        },
                        semantic_embedding=memory.embeddings
                    )
                    results.append(result)
            
            return results
            
        except Exception as e:
            current_app.logger.error(f"Vector search failed: {str(e)}")
            return []
    
    async def _lexical_search(self, keywords: List[str], user_id: int, limit: int) -> List[SearchResult]:
        """Perform keyword-based lexical search"""
        try:
            results = []
            
            # Search in care records (simulated)
            care_results = self.care_service.search_user_archive(user_id, " ".join(keywords), limit=limit)
            
            for record in care_results.get('care_records', []):
                # Calculate keyword overlap score
                record_text = f"{record.get('title', '')} {record.get('description', '')}".lower()
                matching_keywords = sum(1 for keyword in keywords if keyword.lower() in record_text)
                relevance_score = matching_keywords / len(keywords) if keywords else 0
                
                result = SearchResult(
                    content=record.get('description', ''),
                    source=f"care_record_{record.get('id')}",
                    relevance_score=relevance_score,
                    modality=SearchModalityType.TEXT,
                    metadata={
                        "record_type": "care_record",
                        "title": record.get('title', ''),
                        "date": record.get('date_occurred', '')
                    }
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            current_app.logger.error(f"Lexical search failed: {str(e)}")
            return []
    
    async def _graph_search(self, query_features: Dict[str, Any], user_id: int, limit: int) -> List[SearchResult]:
        """Perform graph-based relationship search"""
        try:
            results = []
            
            # Simple graph search based on memory relationships
            if user_id in self.hierarchical_memory:
                for memory_type, memories in self.hierarchical_memory[user_id].items():
                    for memory in memories[:limit]:
                        # Check if memory has related memories
                        if memory.related_memories:
                            relevance_score = len(memory.related_memories) / 10  # Normalize by max expected relations
                            
                            result = SearchResult(
                                content=memory.content,
                                source=f"related_memory_{memory.id}",
                                relevance_score=relevance_score,
                                modality=SearchModalityType.TEXT,
                                metadata={
                                    "memory_type": memory.memory_type.value,
                                    "related_count": len(memory.related_memories),
                                    "context_tags": memory.context_tags
                                }
                            )
                            results.append(result)
            
            return results
            
        except Exception as e:
            current_app.logger.error(f"Graph search failed: {str(e)}")
            return []
    
    def _merge_search_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Merge and deduplicate search results from different sources"""
        unique_results = {}
        
        for result in results:
            key = f"{result.source}_{hash(result.content[:100])}"
            
            if key in unique_results:
                # Combine relevance scores
                existing = unique_results[key]
                existing.relevance_score = max(existing.relevance_score, result.relevance_score)
            else:
                unique_results[key] = result
        
        return list(unique_results.values())
    
    def _apply_search_personalization(self, results: List[SearchResult], user_id: int) -> List[SearchResult]:
        """Apply personalization to search results based on user behavior"""
        try:
            if user_id not in self.personalization_profiles:
                return results
            
            profile = self.personalization_profiles[user_id]
            config = self.hybrid_search_config
            
            # Apply personalization boost
            for result in results:
                # Check if result matches user preferences
                for pattern, weight in profile.interaction_patterns.items():
                    if pattern.lower() in result.content.lower():
                        boost = weight * config.personalization_factor
                        result.relevance_score += boost
                
                # Apply domain-specific boost for pet care content
                pet_care_terms = ["vaccination", "vet", "health", "nutrition", "training"]
                if any(term in result.content.lower() for term in pet_care_terms):
                    result.relevance_score += config.domain_specific_boost
            
            return results
            
        except Exception as e:
            current_app.logger.error(f"Search personalization failed: {str(e)}")
            return results
    
    def expand_query(self, original_query: str, user_id: int) -> str:
        """Expand query based on user history and domain knowledge"""
        try:
            # Get user context
            if user_id in self.personalization_profiles:
                profile = self.personalization_profiles[user_id]
                
                # Add terms from frequent interaction patterns
                expansion_terms = []
                for pattern, weight in profile.interaction_patterns.items():
                    if weight > 0.3:  # Threshold for relevance
                        expansion_terms.append(pattern)
                
                # Add domain-specific expansions
                domain_expansions = {
                    "vaccination": ["vaccine", "immunization", "shots"],
                    "sick": ["ill", "unwell", "symptoms", "health"],
                    "training": ["behavior", "obedience", "commands"],
                    "food": ["diet", "nutrition", "feeding", "meal"]
                }
                
                for term, expansions in domain_expansions.items():
                    if term in original_query.lower():
                        expansion_terms.extend(expansions)
                
                # Combine original query with expansions
                if expansion_terms:
                    expanded_query = f"{original_query} {' '.join(set(expansion_terms[:3]))}"
                    return expanded_query
            
            return original_query
            
        except Exception as e:
            current_app.logger.error(f"Query expansion failed: {str(e)}")
            return original_query
    
    # 🎨 RESPONSE GENERATION IMPROVEMENTS
    
    def _setup_response_templates(self):
        """Set up response templates for different personality styles"""
        self.response_templates = {
            "formal": "Based on the available information, {content}. I recommend {recommendation}.",
            "casual": "Hey! So {content}. You might want to {recommendation}.",
            "friendly": "I'd be happy to help! {content}. My suggestion would be to {recommendation}.",
            "professional": "After analyzing the data, {content}. The recommended course of action is {recommendation}."
        }
    
    def _setup_reasoning_system(self):
        """Set up chain-of-thought reasoning system"""
        self.reasoning_patterns = {
            "medical": ["assess_symptoms", "check_history", "consider_treatments", "recommend_action"],
            "nutrition": ["analyze_diet", "check_requirements", "identify_gaps", "suggest_changes"],
            "behavior": ["observe_patterns", "identify_triggers", "evaluate_methods", "plan_training"],
            "care_planning": ["assess_needs", "review_resources", "prioritize_actions", "create_timeline"]
        }
    
    async def generate_chain_of_thought(self, query: str, context: Dict[str, Any]) -> ChainOfThoughtReasoning:
        """Generate chain-of-thought reasoning for complex queries"""
        try:
            start_time = time.time()
            
            # Determine reasoning pattern based on query intent
            intent_type = context.get("intent_type", "general")
            pattern = self.reasoning_patterns.get(intent_type, ["analyze", "consider", "conclude"])
            
            steps = []
            for i, step_type in enumerate(pattern):
                step = ReasoningStep(
                    step_number=i + 1,
                    description=f"Step {i + 1}: {step_type.replace('_', ' ').title()}",
                    reasoning=self._generate_step_reasoning(step_type, query, context),
                    confidence=0.8 + (0.1 * (i % 2)),  # Vary confidence slightly
                    evidence=self._gather_step_evidence(step_type, context),
                    dependencies=list(range(1, i + 1)) if i > 0 else []
                )
                steps.append(step)
            
            # Generate final conclusion
            final_conclusion = self._synthesize_reasoning_conclusion(steps, query)
            overall_confidence = sum(step.confidence for step in steps) / len(steps)
            
            reasoning = ChainOfThoughtReasoning(
                query=query,
                steps=steps,
                final_conclusion=final_conclusion,
                overall_confidence=overall_confidence,
                reasoning_time=time.time() - start_time,
                validation_passed=self._validate_reasoning(steps, final_conclusion)
            )
            
            # Cache the reasoning
            cache_key = hashlib.md5(f"{query}_{intent_type}".encode()).hexdigest()
            self.reasoning_cache[cache_key] = reasoning
            
            return reasoning
            
        except Exception as e:
            current_app.logger.error(f"Chain-of-thought generation failed: {str(e)}")
            # Return basic reasoning as fallback
            return ChainOfThoughtReasoning(
                query=query,
                steps=[ReasoningStep(
                    step_number=1,
                    description="Basic Analysis",
                    reasoning="Analyzing the query to provide a helpful response.",
                    confidence=0.7,
                    evidence=["user_query"]
                )],
                final_conclusion="Based on the analysis, I'll provide the best possible response.",
                overall_confidence=0.7,
                reasoning_time=0.1,
                validation_passed=False
            )
    
    def _generate_step_reasoning(self, step_type: str, query: str, context: Dict[str, Any]) -> str:
        """Generate reasoning for a specific step"""
        step_templates = {
            "assess_symptoms": f"Looking at the described symptoms in '{query}', I need to identify key indicators and their potential significance.",
            "check_history": f"Reviewing historical data and previous interactions to understand patterns related to '{query}'.",
            "consider_treatments": f"Evaluating available treatment options and their appropriateness for the situation described in '{query}'.",
            "recommend_action": f"Based on the analysis, determining the most suitable course of action for '{query}'.",
            "analyze_diet": f"Examining dietary patterns and nutritional aspects mentioned in '{query}'.",
            "check_requirements": f"Assessing specific nutritional requirements relevant to '{query}'.",
            "identify_gaps": f"Finding potential deficiencies or areas for improvement based on '{query}'.",
            "suggest_changes": f"Proposing specific dietary modifications to address the concerns in '{query}'."
        }
        
        return step_templates.get(step_type, f"Analyzing the aspect of '{step_type}' in relation to '{query}'.")
    
    def _gather_step_evidence(self, step_type: str, context: Dict[str, Any]) -> List[str]:
        """Gather evidence for reasoning step"""
        evidence = []
        
        if "memories" in context:
            evidence.append(f"relevant_memories_{len(context['memories'])}")
        if "care_records" in context:
            evidence.append(f"care_records_{len(context['care_records'])}")
        if "tool_results" in context:
            evidence.append(f"tool_analysis_{len(context['tool_results'])}")
        
        evidence.append(f"reasoning_step_{step_type}")
        return evidence
    
    def _synthesize_reasoning_conclusion(self, steps: List[ReasoningStep], query: str) -> str:
        """Synthesize final conclusion from reasoning steps"""
        high_confidence_steps = [s for s in steps if s.confidence > 0.8]
        
        if len(high_confidence_steps) > len(steps) * 0.7:
            return f"Based on comprehensive analysis of '{query}', I have high confidence in the following recommendation..."
        else:
            return f"After careful consideration of '{query}', while some aspects require further information, I can provide the following guidance..."
    
    def _validate_reasoning(self, steps: List[ReasoningStep], conclusion: str) -> bool:
        """Validate reasoning chain for logical consistency"""
        try:
            # Check if steps have logical dependencies
            if not steps:
                return False
            
            # Check if conclusion is supported by steps
            if len(conclusion) < 20:  # Too short
                return False
            
            # Check confidence scores are reasonable
            avg_confidence = sum(step.confidence for step in steps) / len(steps)
            if avg_confidence < 0.3:  # Too low confidence
                return False
            
            return True
            
        except Exception:
            return False
    
    def get_or_create_user_personality(self, user_id: int) -> UserPersonality:
        """Get or create user personality profile"""
        if user_id not in self.user_personalities:
            self.user_personalities[user_id] = UserPersonality(user_id=user_id)
        return self.user_personalities[user_id]
    
    def adapt_response_to_personality(self, response: str, user_id: int, context: Dict[str, Any]) -> str:
        """Adapt response based on user personality"""
        try:
            personality = self.get_or_create_user_personality(user_id)
            
            # Apply communication style
            if personality.communication_style == "formal":
                response = self._make_response_formal(response)
            elif personality.communication_style == "casual":
                response = self._make_response_casual(response)
            elif personality.communication_style == "friendly":
                response = self._make_response_friendly(response)
            
            # Adjust complexity
            if personality.complexity_preference == "simple":
                response = self._simplify_response(response)
            elif personality.complexity_preference == "technical":
                response = self._add_technical_details(response, context)
            
            # Adjust emotional tone
            if personality.emotional_tone == "empathetic":
                response = self._add_empathy(response)
            elif personality.emotional_tone == "encouraging":
                response = self._add_encouragement(response)
            
            # Adjust length
            if personality.response_length == "brief":
                response = self._shorten_response(response)
            elif personality.response_length == "comprehensive":
                response = self._expand_response(response, context)
            
            return response
            
        except Exception as e:
            current_app.logger.error(f"Response adaptation failed: {str(e)}")
            return response  # Return original on error
    
    def _make_response_formal(self, response: str) -> str:
        """Make response more formal"""
        formal_replacements = {
            "you're": "you are",
            "don't": "do not",
            "can't": "cannot",
            "won't": "will not",
            "hey": "hello",
            "sure": "certainly",
            "okay": "very well"
        }
        
        for informal, formal in formal_replacements.items():
            response = response.replace(informal, formal)
        
        return response
    
    def _make_response_casual(self, response: str) -> str:
        """Make response more casual"""
        if not response.startswith(("Hey", "Hi")):
            response = "Hey! " + response
        
        casual_additions = ["👍", "😊", "Hope this helps!"]
        if not any(addition in response for addition in casual_additions):
            response += " Hope this helps!"
        
        return response
    
    def _make_response_friendly(self, response: str) -> str:
        """Make response more friendly"""
        friendly_starters = [
            "I'm happy to help! ",
            "Great question! ",
            "I'd be glad to assist! "
        ]
        
        if not any(response.startswith(starter.strip()) for starter in friendly_starters):
            response = "I'm happy to help! " + response
        
        return response
    
    def _simplify_response(self, response: str) -> str:
        """Simplify response for easier understanding"""
        # Remove technical jargon
        complex_terms = {
            "administer": "give",
            "utilize": "use",
            "approximately": "about",
            "demonstrate": "show",
            "sufficient": "enough"
        }
        
        for complex_term, simple_term in complex_terms.items():
            response = response.replace(complex_term, simple_term)
        
        # Shorten long sentences
        sentences = response.split('. ')
        simplified_sentences = []
        
        for sentence in sentences:
            if len(sentence) > 100:  # Long sentence
                # Try to split on conjunctions
                parts = sentence.replace(', and ', '. ').replace(', but ', '. ')
                simplified_sentences.append(parts)
            else:
                simplified_sentences.append(sentence)
        
        return '. '.join(simplified_sentences)
    
    def _add_technical_details(self, response: str, context: Dict[str, Any]) -> str:
        """Add technical details to response"""
        technical_additions = []
        
        if "medical" in response.lower():
            technical_additions.append("Note: Dosages should be calculated based on body weight (mg/kg).")
        
        if "nutrition" in response.lower():
            technical_additions.append("Nutritional requirements vary based on age, activity level, and metabolic rate.")
        
        if technical_additions:
            response += "\n\nTechnical Details:\n" + "\n".join(f"• {detail}" for detail in technical_additions)
        
        return response
    
    def _add_empathy(self, response: str) -> str:
        """Add empathetic tone to response"""
        empathetic_phrases = [
            "I understand this can be concerning.",
            "It's natural to worry about your pet's wellbeing.",
            "I can see why you'd want to address this quickly."
        ]
        
        if not any(phrase in response for phrase in empathetic_phrases):
            response = empathetic_phrases[0] + " " + response
        
        return response
    
    def _add_encouragement(self, response: str) -> str:
        """Add encouraging tone to response"""
        encouraging_phrases = [
            "You're doing a great job caring for your pet!",
            "This shows how much you care about their wellbeing.",
            "You're on the right track!"
        ]
        
        response += f" {encouraging_phrases[0]}"
        return response
    
    def _shorten_response(self, response: str) -> str:
        """Shorten response while keeping key information"""
        sentences = response.split('. ')
        
        if len(sentences) <= 2:
            return response
        
        # Keep first sentence and most important points
        key_sentences = [sentences[0]]
        
        # Look for sentences with key action words
        action_words = ["should", "recommend", "important", "need", "must"]
        for sentence in sentences[1:]:
            if any(word in sentence.lower() for word in action_words):
                key_sentences.append(sentence)
                break
        
        return '. '.join(key_sentences)
    
    def _expand_response(self, response: str, context: Dict[str, Any]) -> str:
        """Expand response with additional details"""
        expansions = []
        
        # Add context from memories
        if "memories" in context and context["memories"]:
            expansions.append("Based on your previous interactions, I also want to mention...")
        
        # Add preventive advice
        if "medical" in response.lower():
            expansions.append("For future prevention, consider regular check-ups and monitoring.")
        
        # Add related information
        if "nutrition" in response.lower():
            expansions.append("Additionally, ensuring proper hydration and exercise complements good nutrition.")
        
        if expansions:
            response += "\n\nAdditional Information:\n" + "\n".join(f"• {exp}" for exp in expansions)
        
        return response
    
    async def assess_response_quality(self, response: str, query: str, context: Dict[str, Any]) -> ResponseQuality:
        """Assess the quality of generated response"""
        try:
            # Calculate relevance score
            relevance_score = self._calculate_relevance_score(response, query)
            
            # Calculate accuracy score
            accuracy_score = self._calculate_accuracy_score(response, context)
            
            # Check factual consistency
            factual_consistency = self._check_factual_consistency(response, context)
            
            # Detect bias
            bias_score = self._detect_bias(response)
            
            # Check safety
            safety_score = self._check_safety(response)
            
            # Check appropriateness
            appropriateness_score = self._check_appropriateness(response, context)
            
            # Calculate source support
            source_support = self._calculate_source_support(response, context)
            
            # Calculate overall quality
            scores = [relevance_score, accuracy_score, factual_consistency, 
                     (1.0 - bias_score), safety_score, appropriateness_score, source_support]
            overall_quality = sum(scores) / len(scores)
            
            return ResponseQuality(
                relevance_score=relevance_score,
                accuracy_score=accuracy_score,
                factual_consistency=factual_consistency,
                bias_score=bias_score,
                safety_score=safety_score,
                appropriateness_score=appropriateness_score,
                source_support=source_support,
                overall_quality=overall_quality
            )
            
        except Exception as e:
            current_app.logger.error(f"Response quality assessment failed: {str(e)}")
            # Return default quality scores
            return ResponseQuality(
                relevance_score=0.7,
                accuracy_score=0.7,
                factual_consistency=0.7,
                bias_score=0.1,
                safety_score=0.9,
                appropriateness_score=0.8,
                source_support=0.6,
                overall_quality=0.7
            )
    
    def _calculate_relevance_score(self, response: str, query: str) -> float:
        """Calculate how relevant the response is to the query"""
        try:
            query_words = set(query.lower().split())
            response_words = set(response.lower().split())
            
            # Calculate word overlap
            overlap = len(query_words.intersection(response_words))
            total_query_words = len(query_words)
            
            if total_query_words == 0:
                return 0.0
            
            # Base relevance on word overlap
            relevance = overlap / total_query_words
            
            # Boost for pet care specific terms
            pet_care_terms = ["health", "care", "nutrition", "behavior", "training", "medical", "vet"]
            if any(term in response.lower() for term in pet_care_terms):
                relevance += 0.2
            
            return min(relevance, 1.0)
            
        except Exception:
            return 0.5  # Default
    
    def _calculate_accuracy_score(self, response: str, context: Dict[str, Any]) -> float:
        """Calculate accuracy based on available context"""
        try:
            accuracy = 0.8  # Base accuracy
            
            # Boost if supported by tools
            if context.get("tool_results"):
                accuracy += 0.1
            
            # Boost if supported by memories
            if context.get("memories"):
                accuracy += 0.1
            
            # Check for uncertainty markers (good for accuracy)
            uncertainty_markers = ["might", "possibly", "could", "perhaps", "likely"]
            if any(marker in response.lower() for marker in uncertainty_markers):
                accuracy += 0.05
            
            return min(accuracy, 1.0)
            
        except Exception:
            return 0.7  # Default
    
    def _check_factual_consistency(self, response: str, context: Dict[str, Any]) -> float:
        """Check factual consistency with sources"""
        try:
            consistency = 0.8  # Base consistency
            
            # Check against care records
            if context.get("care_records"):
                # Simple consistency check
                consistency += 0.1
            
            # Check for contradictory statements
            contradictory_phrases = [
                ("always", "never"),
                ("all", "none"),
                ("must", "should not")
            ]
            
            response_lower = response.lower()
            for phrase1, phrase2 in contradictory_phrases:
                if phrase1 in response_lower and phrase2 in response_lower:
                    consistency -= 0.2
                    break
            
            return max(consistency, 0.0)
            
        except Exception:
            return 0.8  # Default
    
    def _detect_bias(self, response: str) -> float:
        """Detect potential bias in response"""
        try:
            bias_score = 0.0
            
            # Check for absolute statements (potential bias)
            absolute_terms = ["always", "never", "all", "none", "every", "impossible"]
            absolute_count = sum(1 for term in absolute_terms if term in response.lower())
            bias_score += absolute_count * 0.1
            
            # Check for discriminatory language
            discriminatory_terms = ["expensive", "cheap", "inferior", "superior"]
            if any(term in response.lower() for term in discriminatory_terms):
                bias_score += 0.2
            
            return min(bias_score, 1.0)
            
        except Exception:
            return 0.1  # Default low bias
    
    def _check_safety(self, response: str) -> float:
        """Check response safety"""
        try:
            safety = 1.0  # Assume safe
            
            # Check for unsafe medical advice
            unsafe_medical = ["self-diagnose", "skip vet", "ignore symptoms", "wait it out"]
            if any(term in response.lower() for term in unsafe_medical):
                safety -= 0.3
            
            # Check for dangerous recommendations
            dangerous_terms = ["force", "punish harshly", "ignore completely"]
            if any(term in response.lower() for term in dangerous_terms):
                safety -= 0.4
            
            return max(safety, 0.0)
            
        except Exception:
            return 0.9  # Default safe
    
    def _check_appropriateness(self, response: str, context: Dict[str, Any]) -> float:
        """Check response appropriateness for context"""
        try:
            appropriateness = 0.9  # Base appropriateness
            
            # Check tone appropriateness
            if context.get("urgency") == "high":
                if "emergency" not in response.lower():
                    appropriateness -= 0.2
            
            # Check length appropriateness
            if len(response) < 50:  # Too short
                appropriateness -= 0.1
            elif len(response) > 1000:  # Too long
                appropriateness -= 0.1
            
            return max(appropriateness, 0.0)
            
        except Exception:
            return 0.8  # Default
    
    def _calculate_source_support(self, response: str, context: Dict[str, Any]) -> float:
        """Calculate how well response is supported by sources"""
        try:
            support = 0.5  # Base support
            
            # Boost for memory support
            if context.get("memories"):
                support += 0.2
            
            # Boost for tool results
            if context.get("tool_results"):
                support += 0.2
            
            # Boost for care records
            if context.get("care_records"):
                support += 0.1
            
            return min(support, 1.0)
            
        except Exception:
            return 0.6  # Default
    
    # 🛠️ TOOL INTEGRATION & FUNCTION CALLING
    
    def _register_pet_care_tools(self):
        """Register specialized pet care tools with @tool decorator"""
        
        @tool
        def search_care_records(user_id: int, query: str, record_type: str = "all") -> Dict[str, Any]:
            """
            Search user's pet care records with advanced filtering.
            
            Args:
                user_id: User ID for the search
                query: Search query for care records
                record_type: Type of records to search (vaccination, vet_visit, medication, all)
            
            Returns:
                Dictionary with care records and metadata
            """
            try:
                start_time = time.time()
                
                # Generate cache key
                cache_key = hashlib.md5(f"{user_id}_{query}_{record_type}".encode()).hexdigest()
                
                # Check cache first
                if cache_key in self.tool_cache:
                    cached_result = self.tool_cache[cache_key]
                    if time.time() - cached_result['timestamp'] < 300:  # 5 minute cache
                        return cached_result['data']
                
                # Search care records
                results = self.care_service.search_user_archive(user_id, query, limit=10)
                
                # Filter by type if specified
                if record_type != "all":
                    filtered_records = []
                    for record in results.get('care_records', []):
                        if record_type.lower() in record.get('title', '').lower() or \
                           record_type.lower() in record.get('description', '').lower():
                            filtered_records.append(record)
                    results['care_records'] = filtered_records
                
                # Cache the result
                self.tool_cache[cache_key] = {
                    'data': results,
                    'timestamp': time.time()
                }
                
                # Update tool stats
                execution_time = time.time() - start_time
                self._update_tool_stats("search_care_records", execution_time, True)
                
                return results
                
            except Exception as e:
                self._update_tool_stats("search_care_records", 0, False, str(e))
                return {"error": str(e), "care_records": []}
        
        @tool
        def calculate_next_vaccination(pet_age_months: int, last_vaccination_date: str, 
                                     vaccination_type: str) -> Dict[str, Any]:
            """
            Calculate when the next vaccination is due based on pet age and vaccination history.
            
            Args:
                pet_age_months: Age of pet in months
                last_vaccination_date: Date of last vaccination (YYYY-MM-DD)
                vaccination_type: Type of vaccination (rabies, dhpp, bordetella)
            
            Returns:
                Dictionary with next vaccination date and schedule
            """
            try:
                start_time = time.time()
                
                # Vaccination schedules (in months)
                schedules = {
                    "rabies": {"puppy": [4, 16], "adult": [12], "interval": 36},
                    "dhpp": {"puppy": [6, 10, 14], "adult": [12], "interval": 12}, 
                    "bordetella": {"puppy": [12], "adult": [6], "interval": 6}
                }
                
                last_date = datetime.strptime(last_vaccination_date, "%Y-%m-%d")
                schedule = schedules.get(vaccination_type.lower(), schedules["dhpp"])
                
                # Determine if puppy or adult
                is_puppy = pet_age_months < 18
                
                if is_puppy:
                    # Find next puppy vaccination
                    for vac_age in schedule["puppy"]:
                        if pet_age_months < vac_age:
                            next_date = datetime.now() + timedelta(days=(vac_age - pet_age_months) * 30)
                            break
                    else:
                        # Switch to adult schedule
                        next_date = last_date + timedelta(days=schedule["interval"] * 30)
                else:
                    # Adult schedule
                    next_date = last_date + timedelta(days=schedule["interval"] * 30)
                
                result = {
                    "next_vaccination_date": next_date.strftime("%Y-%m-%d"),
                    "days_until_due": (next_date - datetime.now()).days,
                    "vaccination_type": vaccination_type,
                    "schedule_type": "puppy" if is_puppy else "adult",
                    "overdue": next_date < datetime.now()
                }
                
                execution_time = time.time() - start_time
                self._update_tool_stats("calculate_next_vaccination", execution_time, True)
                
                return result
                
            except Exception as e:
                self._update_tool_stats("calculate_next_vaccination", 0, False, str(e))
                return {"error": str(e)}
        
        @tool
        def create_care_reminder(user_id: int, title: str, description: str, 
                               due_date: str, priority: str = "medium") -> Dict[str, Any]:
            """
            Create a new care reminder for the user.
            
            Args:
                user_id: User ID
                title: Reminder title
                description: Reminder description
                due_date: Due date (YYYY-MM-DD)
                priority: Priority level (low, medium, high, critical)
            
            Returns:
                Dictionary with reminder creation status
            """
            try:
                start_time = time.time()
                
                # Create reminder through care service
                reminder_data = {
                    "title": title,
                    "description": description,
                    "due_date": due_date,
                    "priority": priority,
                    "user_id": user_id
                }
                
                # This would integrate with the existing reminder system
                result = self.care_service.create_reminder(reminder_data)
                
                execution_time = time.time() - start_time
                self._update_tool_stats("create_care_reminder", execution_time, True)
                
                return {"success": True, "reminder_id": result.get("id"), "message": "Reminder created successfully"}
                
            except Exception as e:
                self._update_tool_stats("create_care_reminder", 0, False, str(e))
                return {"success": False, "error": str(e)}
        
        @tool
        def analyze_document_content(user_id: int, document_query: str, 
                                   analysis_type: str = "summary") -> Dict[str, Any]:
            """
            Analyze document content with AI-powered insights.
            
            Args:
                user_id: User ID for document access
                document_query: Query to find relevant documents
                analysis_type: Type of analysis (summary, extract_dates, find_recommendations)
            
            Returns:
                Dictionary with document analysis results
            """
            try:
                start_time = time.time()
                
                # Find relevant documents
                success, doc_results = query_user_docs(document_query, user_id, top_k=10)
                documents = []
                
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
                
                if not documents:
                    return {"analysis": "No relevant documents found", "documents_analyzed": 0}
                
                # Analyze documents based on type
                analysis_results = []
                for doc in documents:
                    content = doc.get('content', '')[:2000]  # Limit content length
                    
                    if analysis_type == "summary":
                        analysis = self._summarize_document(content)
                    elif analysis_type == "extract_dates":
                        analysis = self._extract_dates_from_document(content)
                    elif analysis_type == "find_recommendations":
                        analysis = self._extract_recommendations(content)
                    else:
                        analysis = {"type": "general", "content": content[:500]}
                    
                    analysis_results.append({
                        "document": doc.get('filename', 'Unknown'),
                        "analysis": analysis,
                        "relevance_score": doc.get('score', 0)
                    })
                
                result = {
                    "analysis_type": analysis_type,
                    "documents_analyzed": len(documents),
                    "results": analysis_results
                }
                
                execution_time = time.time() - start_time
                self._update_tool_stats("analyze_document_content", execution_time, True)
                
                return result
                
            except Exception as e:
                self._update_tool_stats("analyze_document_content", 0, False, str(e))
                return {"error": str(e), "documents_analyzed": 0}
        
        @tool
        def generate_care_plan(user_id: int, pet_type: str, pet_age_months: int, 
                             health_conditions: List[str] = None) -> Dict[str, Any]:
            """
            Generate a comprehensive care plan for a pet.
            
            Args:
                user_id: User ID
                pet_type: Type of pet (dog, cat, bird, etc.)
                pet_age_months: Age of pet in months
                health_conditions: List of known health conditions
            
            Returns:
                Dictionary with comprehensive care plan
            """
            try:
                start_time = time.time()
                
                if health_conditions is None:
                    health_conditions = []
                
                # Generate age-appropriate care plan
                is_puppy = pet_age_months < 18
                is_senior = pet_age_months > 84  # 7 years
                
                care_plan = {
                    "pet_info": {
                        "type": pet_type,
                        "age_months": pet_age_months,
                        "life_stage": "puppy" if is_puppy else "senior" if is_senior else "adult"
                    },
                    "vaccination_schedule": self._generate_vaccination_schedule(pet_type, pet_age_months),
                    "feeding_recommendations": self._generate_feeding_plan(pet_type, pet_age_months),
                    "exercise_plan": self._generate_exercise_plan(pet_type, pet_age_months),
                    "health_monitoring": self._generate_health_monitoring(health_conditions),
                    "reminders": []
                }
                
                # Add health condition specific recommendations
                if health_conditions:
                    care_plan["special_care"] = self._generate_special_care(health_conditions)
                
                execution_time = time.time() - start_time
                self._update_tool_stats("generate_care_plan", execution_time, True)
                
                return care_plan
                
            except Exception as e:
                self._update_tool_stats("generate_care_plan", 0, False, str(e))
                return {"error": str(e)}
        
        # Register all tools
        tools = [
            search_care_records,
            calculate_next_vaccination,
            create_care_reminder,
            analyze_document_content,
            generate_care_plan
        ]
        
        for tool_func in tools:
            self.tool_registry[tool_func.name] = tool_func
            self.tool_stats[tool_func.name] = ToolUsageStats(tool_name=tool_func.name)
        
        current_app.logger.info(f"Registered {len(tools)} specialized pet care tools")
    
    def _update_tool_stats(self, tool_name: str, execution_time: float, success: bool, error_msg: str = None):
        """Update tool usage statistics for optimization"""
        if tool_name not in self.tool_stats:
            self.tool_stats[tool_name] = ToolUsageStats(tool_name=tool_name)
        
        stats = self.tool_stats[tool_name]
        stats.usage_count += 1
        stats.last_used = datetime.now(timezone.utc)
        
        if success:
            # Update success rate
            total_attempts = stats.usage_count
            current_successes = (stats.success_rate * (total_attempts - 1)) + 1
            stats.success_rate = current_successes / total_attempts
            
            # Update average execution time
            stats.avg_execution_time = ((stats.avg_execution_time * (total_attempts - 1)) + execution_time) / total_attempts
        else:
            # Update success rate for failure
            total_attempts = stats.usage_count
            current_successes = stats.success_rate * (total_attempts - 1)
            stats.success_rate = current_successes / total_attempts
        
        # Calculate popularity score (frequency + success rate + speed)
        frequency_score = min(stats.usage_count / 100, 1.0)  # Normalize to 0-1
        speed_score = max(0, 1.0 - (stats.avg_execution_time / 10))  # Faster = higher score
        stats.popularity_score = (frequency_score + stats.success_rate + speed_score) / 3
    
    async def execute_tools_parallel(self, tool_calls: List[Dict[str, Any]], user_id: int) -> List[ToolExecutionResult]:
        """Execute multiple tools in parallel for efficiency"""
        results = []
        
        # Create tasks for parallel execution
        tasks = []
        for tool_call in tool_calls:
            tool_name = tool_call.get('tool')
            args = tool_call.get('args', {})
            
            if tool_name in self.tool_registry:
                task = self._execute_single_tool(tool_name, args, user_id)
                tasks.append(task)
        
        # Execute tools in parallel
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            current_app.logger.error(f"Parallel tool execution failed: {str(e)}")
        
        return results
    
    async def _execute_single_tool(self, tool_name: str, args: Dict[str, Any], user_id: int) -> ToolExecutionResult:
        """Execute a single tool with error handling and validation"""
        start_time = time.time()
        
        try:
            tool = self.tool_registry[tool_name]
            
            # Add user_id to args if not present and tool expects it
            if 'user_id' not in args and 'user_id' in tool.args:
                args['user_id'] = user_id
            
            # Execute tool
            result = tool.invoke(args)
            
            execution_time = time.time() - start_time
            
            # Validate result
            if self._validate_tool_result(tool_name, result):
                self._update_tool_stats(tool_name, execution_time, True)
                return ToolExecutionResult(
                    tool_name=tool_name,
                    result=result,
                    execution_time=execution_time,
                    success=True,
                    popularity_score=self.tool_stats[tool_name].popularity_score
                )
            else:
                self._update_tool_stats(tool_name, execution_time, False, "Invalid result format")
                return ToolExecutionResult(
                    tool_name=tool_name,
                    result={"error": "Invalid result format"},
                    execution_time=execution_time,
                    success=False,
                    error_message="Invalid result format"
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_tool_stats(tool_name, execution_time, False, str(e))
            return ToolExecutionResult(
                tool_name=tool_name,
                result={"error": str(e)},
                execution_time=execution_time,
                success=False,
                error_message=str(e)
            )
    
    def _validate_tool_result(self, tool_name: str, result: Any) -> bool:
        """Validate tool execution result"""
        if result is None:
            return False
        
        # Basic validation - result should be a dictionary for our tools
        if not isinstance(result, dict):
            return False
        
        # Tool-specific validation
        if tool_name == "search_care_records":
            return "care_records" in result or "error" in result
        elif tool_name == "calculate_next_vaccination":
            return "next_vaccination_date" in result or "error" in result
        elif tool_name == "create_care_reminder":
            return "success" in result
        elif tool_name == "analyze_document_content":
            return "documents_analyzed" in result
        elif tool_name == "generate_care_plan":
            return "pet_info" in result or "error" in result
        
        return True
    
    def get_recommended_tools(self, intent_analysis: MultiIntentAnalysis, limit: int = 3) -> List[str]:
        """Dynamically select tools based on intent and popularity"""
        if not intent_analysis or not intent_analysis.intents:
            return list(self.tool_registry.keys())[:limit]
        
        primary_intent = intent_analysis.intents[intent_analysis.primary_intent_index]
        
        # Map intents to relevant tools
        intent_tool_mapping = {
            IntentType.MEDICAL_RECORDS: ["search_care_records", "calculate_next_vaccination"],
            IntentType.CARE_PLANNING: ["generate_care_plan", "create_care_reminder"],
            IntentType.DOCUMENT_SEARCH: ["analyze_document_content", "search_care_records"],
            IntentType.REMINDERS: ["create_care_reminder", "calculate_next_vaccination"],
            IntentType.CARE_HISTORY: ["search_care_records", "analyze_document_content"]
        }
        
        relevant_tools = intent_tool_mapping.get(primary_intent.primary_intent, list(self.tool_registry.keys()))
        
        # Sort by popularity score and select top tools
        tool_scores = [(tool, self.tool_stats.get(tool, ToolUsageStats(tool_name=tool)).popularity_score) 
                      for tool in relevant_tools if tool in self.tool_registry]
        
        tool_scores.sort(key=lambda x: x[1], reverse=True)
        
        return [tool for tool, _ in tool_scores[:limit]]
    
    # 🧠 ADVANCED MEMORY & CONTEXT SYSTEM
    
    def _setup_memory_decay(self):
        """Set up memory decay schedules for different memory types"""
        self.memory_decay_rates = {
            MemoryType.SHORT_TERM: 0.1,    # 10% decay per day
            MemoryType.MEDIUM_TERM: 0.02,  # 2% decay per day  
            MemoryType.LONG_TERM: 0.001,   # 0.1% decay per day
            MemoryType.EPISODIC: 0.05,     # 5% decay per day
            MemoryType.SEMANTIC: 0.01,     # 1% decay per day
            MemoryType.PROCEDURAL: 0.005   # 0.5% decay per day
        }
    
    def _setup_state_versioning(self):
        """Set up state versioning and compression"""
        self.state_version_limit = 50  # Keep last 50 versions
        self.state_auto_snapshot_interval = 10  # Snapshot every 10 interactions
    
    def store_memory(self, user_id: int, content: str, memory_type: MemoryType, 
                    importance: MemoryImportance, source: str = "user_interaction",
                    context_tags: List[str] = None) -> str:
        """Store memory in hierarchical memory system with embeddings"""
        try:
            memory_id = str(uuid.uuid4())
            
            # Generate embeddings for semantic search
            embeddings = embeddings_model.embed_query(content)
            
            # Create memory item
            memory_item = MemoryItem(
                id=memory_id,
                content=content,
                memory_type=memory_type,
                importance=importance,
                timestamp=datetime.now(timezone.utc),
                user_id=user_id,
                embeddings=embeddings,
                source=source,
                context_tags=context_tags or []
            )
            
            # Store in hierarchical memory
            self.hierarchical_memory[user_id][memory_type].append(memory_item)
            
            # Add to consolidation queue if needed
            if self._should_consolidate_memory(memory_item):
                self.memory_consolidation_queue.append(memory_id)
            
            # Maintain memory limits
            self._maintain_memory_limits(user_id, memory_type)
            
            current_app.logger.info(f"Stored {memory_type} memory for user {user_id}")
            return memory_id
            
        except Exception as e:
            current_app.logger.error(f"Memory storage failed: {str(e)}")
            return None
    
    def search_memories_by_embedding(self, user_id: int, query: str, memory_types: List[MemoryType] = None,
                                   limit: int = 5, temporal_weight: bool = True) -> List[MemoryItem]:
        """Search memories using embedding similarity with temporal weighting"""
        try:
            # Generate query embedding
            query_embedding = embeddings_model.embed_query(query)
            
            # Get all memories for user
            all_memories = []
            memory_types = memory_types or list(MemoryType)
            
            for mem_type in memory_types:
                if mem_type in self.hierarchical_memory[user_id]:
                    all_memories.extend(self.hierarchical_memory[user_id][mem_type])
            
            if not all_memories:
                return []
            
            # Calculate similarity scores
            memory_scores = []
            current_time = datetime.now(timezone.utc)
            
            for memory in all_memories:
                if memory.embeddings:
                    # Calculate cosine similarity
                    similarity = self._calculate_cosine_similarity(query_embedding, memory.embeddings)
                    
                    # Apply temporal weighting if enabled
                    if temporal_weight:
                        time_diff = (current_time - memory.timestamp).total_seconds() / 86400  # Days
                        temporal_decay = max(0.1, 1.0 - (time_diff * 0.1))  # 10% decay per day
                        similarity *= temporal_decay
                    
                    # Apply importance weighting
                    importance_weights = {
                        MemoryImportance.CRITICAL: 1.5,
                        MemoryImportance.HIGH: 1.2,
                        MemoryImportance.MEDIUM: 1.0,
                        MemoryImportance.LOW: 0.8
                    }
                    similarity *= importance_weights.get(memory.importance, 1.0)
                    
                    # Apply decay factor
                    similarity *= memory.decay_factor
                    
                    memory_scores.append((memory, similarity))
            
            # Sort by similarity and return top results
            memory_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Update access count and last accessed
            selected_memories = []
            for memory, score in memory_scores[:limit]:
                memory.access_count += 1
                memory.last_accessed = current_time
                selected_memories.append(memory)
            
            return selected_memories
            
        except Exception as e:
            current_app.logger.error(f"Memory search failed: {str(e)}")
            return []
    
    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            import numpy as np
            
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)
            
            dot_product = np.dot(vec1, vec2)
            magnitude1 = np.linalg.norm(vec1)
            magnitude2 = np.linalg.norm(vec2)
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            return dot_product / (magnitude1 * magnitude2)
            
        except Exception:
            return 0.0
    
    def consolidate_memories(self, user_id: int) -> Dict[str, int]:
        """Consolidate memories by merging similar ones and promoting important ones"""
        try:
            consolidation_results = {"merged": 0, "promoted": 0, "demoted": 0}
            
            # Process memories by type
            for memory_type, memories in self.hierarchical_memory[user_id].items():
                if not memories:
                    continue
                
                # Find similar memories to merge
                merged_count = self._merge_similar_memories(memories)
                consolidation_results["merged"] += merged_count
                
                # Promote/demote memories based on access patterns
                promoted, demoted = self._adjust_memory_importance(memories)
                consolidation_results["promoted"] += promoted
                consolidation_results["demoted"] += demoted
            
            # Clear consolidation queue
            self.memory_consolidation_queue.clear()
            
            current_app.logger.info(f"Memory consolidation completed for user {user_id}: {consolidation_results}")
            return consolidation_results
            
        except Exception as e:
            current_app.logger.error(f"Memory consolidation failed: {str(e)}")
            return {"merged": 0, "promoted": 0, "demoted": 0}
    
    def _should_consolidate_memory(self, memory_item: MemoryItem) -> bool:
        """Determine if memory should be added to consolidation queue"""
        # Consolidate if high importance or frequently accessed
        return (memory_item.importance in [MemoryImportance.HIGH, MemoryImportance.CRITICAL] or
                memory_item.access_count > 5)
    
    def _maintain_memory_limits(self, user_id: int, memory_type: MemoryType):
        """Maintain memory limits by removing old/low-importance memories"""
        memories = self.hierarchical_memory[user_id][memory_type]
        
        # Memory limits by type
        limits = {
            MemoryType.SHORT_TERM: 50,
            MemoryType.MEDIUM_TERM: 200,
            MemoryType.LONG_TERM: 1000,
            MemoryType.EPISODIC: 100,
            MemoryType.SEMANTIC: 500,
            MemoryType.PROCEDURAL: 100
        }
        
        limit = limits.get(memory_type, 100)
        
        if len(memories) > limit:
            # Sort by importance and age, remove least important/oldest
            memories.sort(key=lambda m: (m.importance.value, m.timestamp), reverse=True)
            self.hierarchical_memory[user_id][memory_type] = memories[:limit]
    
    def _merge_similar_memories(self, memories: List[MemoryItem]) -> int:
        """Merge similar memories to reduce redundancy"""
        merged_count = 0
        similarity_threshold = 0.85
        
        i = 0
        while i < len(memories):
            j = i + 1
            while j < len(memories):
                if (memories[i].embeddings and memories[j].embeddings and
                    self._calculate_cosine_similarity(memories[i].embeddings, memories[j].embeddings) > similarity_threshold):
                    
                    # Merge memories
                    merged_content = f"{memories[i].content} | {memories[j].content}"
                    memories[i].content = merged_content
                    memories[i].access_count += memories[j].access_count
                    
                    # Update importance to higher of the two
                    if memories[j].importance.value > memories[i].importance.value:
                        memories[i].importance = memories[j].importance
                    
                    # Remove merged memory
                    memories.pop(j)
                    merged_count += 1
                else:
                    j += 1
            i += 1
        
        return merged_count
    
    def _adjust_memory_importance(self, memories: List[MemoryItem]) -> Tuple[int, int]:
        """Adjust memory importance based on access patterns"""
        promoted = 0
        demoted = 0
        
        for memory in memories:
            # Promote frequently accessed memories
            if memory.access_count > 10 and memory.importance == MemoryImportance.MEDIUM:
                memory.importance = MemoryImportance.HIGH
                promoted += 1
            elif memory.access_count > 20 and memory.importance == MemoryImportance.HIGH:
                memory.importance = MemoryImportance.CRITICAL
                promoted += 1
            
            # Demote rarely accessed memories
            elif memory.access_count == 0 and memory.importance == MemoryImportance.HIGH:
                time_since_creation = (datetime.now(timezone.utc) - memory.timestamp).days
                if time_since_creation > 30:  # 30 days
                    memory.importance = MemoryImportance.MEDIUM
                    demoted += 1
        
        return promoted, demoted
    
    # 📊 EVALUATION & FEEDBACK SYSTEMS
    
    def _setup_metrics_tracking(self):
        """Set up conversation quality metrics tracking"""
        self.quality_thresholds = {
            "relevance": 0.8,
            "accuracy": 0.8,
            "safety": 0.9,
            "user_satisfaction": 0.7
        }
    
    def _setup_feedback_processing(self):
        """Set up user feedback processing"""
        self.feedback_weights = {
            "thumbs_up": 1.0,
            "thumbs_down": -1.0,
            "correction": 0.5,  # Valuable for learning
            "preference": 0.3
        }
    
    def track_conversation_metrics(self, conversation_id: str, user_id: int, 
                                 response: str, query: str, context: Dict[str, Any]) -> ConversationMetrics:
        """Track and update conversation quality metrics"""
        try:
            # Get existing metrics or create new
            if conversation_id in self.conversation_metrics:
                metrics = self.conversation_metrics[conversation_id]
                metrics.total_exchanges += 1
            else:
                metrics = ConversationMetrics(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    total_exchanges=1,
                    avg_response_relevance=0.0,
                    avg_response_accuracy=0.0,
                    user_satisfaction_predicted=0.0,
                    success_rate=0.0,
                    source_utilization=0.0,
                    conversation_duration=0.0
                )
            
            # Calculate current response metrics
            relevance = self._calculate_relevance_score(response, query)
            accuracy = self._calculate_accuracy_score(response, context)
            source_util = self._calculate_source_utilization(context)
            predicted_satisfaction = self._predict_user_satisfaction(response, query, context)
            
            # Update running averages
            total = metrics.total_exchanges
            metrics.avg_response_relevance = ((metrics.avg_response_relevance * (total - 1)) + relevance) / total
            metrics.avg_response_accuracy = ((metrics.avg_response_accuracy * (total - 1)) + accuracy) / total
            metrics.user_satisfaction_predicted = ((metrics.user_satisfaction_predicted * (total - 1)) + predicted_satisfaction) / total
            metrics.source_utilization = ((metrics.source_utilization * (total - 1)) + source_util) / total
            
            # Calculate success rate
            success = (relevance > 0.7 and accuracy > 0.7 and predicted_satisfaction > 0.6)
            current_success_rate = 1.0 if success else 0.0
            metrics.success_rate = ((metrics.success_rate * (total - 1)) + current_success_rate) / total
            
            # Update timestamp
            metrics.timestamp = datetime.now(timezone.utc)
            
            # Store updated metrics
            self.conversation_metrics[conversation_id] = metrics
            
            return metrics
            
        except Exception as e:
            current_app.logger.error(f"Conversation metrics tracking failed: {str(e)}")
            # Return default metrics
            return ConversationMetrics(
                conversation_id=conversation_id,
                user_id=user_id,
                total_exchanges=1,
                avg_response_relevance=0.7,
                avg_response_accuracy=0.7,
                user_satisfaction_predicted=0.7,
                success_rate=0.7,
                source_utilization=0.5,
                conversation_duration=0.0
            )
    
    def _calculate_source_utilization(self, context: Dict[str, Any]) -> float:
        """Calculate how well sources were utilized"""
        utilization = 0.0
        
        if context.get("memories"):
            utilization += 0.3
        if context.get("tool_results"):
            utilization += 0.4
        if context.get("care_records"):
            utilization += 0.3
        
        return min(utilization, 1.0)
    
    def _predict_user_satisfaction(self, response: str, query: str, context: Dict[str, Any]) -> float:
        """Predict user satisfaction based on response characteristics"""
        try:
            satisfaction = 0.5  # Base satisfaction
            
            # Response length factor
            if 50 <= len(response) <= 500:
                satisfaction += 0.2
            
            # Relevance factor
            relevance = self._calculate_relevance_score(response, query)
            satisfaction += relevance * 0.3
            
            # Helpfulness indicators
            helpful_words = ["recommend", "suggest", "help", "solution", "try", "consider"]
            if any(word in response.lower() for word in helpful_words):
                satisfaction += 0.1
            
            # Personal touch
            personal_words = ["your", "you", "pet", "dog", "cat"]
            if any(word in response.lower() for word in personal_words):
                satisfaction += 0.1
            
            return min(satisfaction, 1.0)
            
        except Exception:
            return 0.7  # Default
    
    def process_user_feedback(self, message_id: str, user_id: int, feedback: UserFeedback):
        """Process and learn from user feedback"""
        try:
            # Store feedback
            self.feedback_history[user_id].append(feedback)
            
            # Update user personality based on feedback
            if feedback.feedback_type in ["thumbs_up", "thumbs_down"]:
                self._update_personality_from_rating(user_id, feedback)
            elif feedback.feedback_type == "correction":
                self._learn_from_correction(user_id, feedback)
            elif feedback.feedback_type == "preference":
                self._update_user_preferences(user_id, feedback)
            
            # Trigger system improvement analysis
            if len(self.feedback_history[user_id]) % 10 == 0:  # Every 10 feedbacks
                self._analyze_feedback_patterns(user_id)
            
            current_app.logger.info(f"Processed feedback from user {user_id}: {feedback.feedback_type}")
            
        except Exception as e:
            current_app.logger.error(f"Feedback processing failed: {str(e)}")
    
    def _update_personality_from_rating(self, user_id: int, feedback: UserFeedback):
        """Update user personality based on thumbs up/down feedback"""
        personality = self.get_or_create_user_personality(user_id)
        
        if feedback.feedback_type == "thumbs_up":
            # Reinforce current settings
            if feedback.rating and feedback.rating >= 4:
                # High rating - current style is working
                personality.learning_rate *= 0.9  # Slow down changes
        elif feedback.feedback_type == "thumbs_down":
            # Adapt personality settings
            if feedback.rating and feedback.rating <= 2:
                # Low rating - need significant changes
                personality.learning_rate *= 1.2  # Speed up changes
                
                # Try different communication style
                styles = ["formal", "casual", "friendly", "professional"]
                current_style = personality.communication_style
                other_styles = [s for s in styles if s != current_style]
                if other_styles:
                    personality.communication_style = other_styles[0]
    
    def _learn_from_correction(self, user_id: int, feedback: UserFeedback):
        """Learn from user corrections"""
        if feedback.correction_text:
            # Analyze correction to improve future responses
            correction_patterns = {
                "more detail": {"complexity_preference": "detailed"},
                "too long": {"response_length": "brief"},
                "too short": {"response_length": "detailed"},
                "more formal": {"communication_style": "formal"},
                "more casual": {"communication_style": "casual"}
            }
            
            personality = self.get_or_create_user_personality(user_id)
            correction_lower = feedback.correction_text.lower()
            
            for pattern, updates in correction_patterns.items():
                if pattern in correction_lower:
                    for attr, value in updates.items():
                        setattr(personality, attr, value)
                    break
    
    def _update_user_preferences(self, user_id: int, feedback: UserFeedback):
        """Update user preferences from feedback"""
        personality = self.get_or_create_user_personality(user_id)
        
        if feedback.feedback_text:
            # Simple preference extraction
            text_lower = feedback.feedback_text.lower()
            
            if "short" in text_lower:
                personality.response_length = "brief"
            elif "detailed" in text_lower:
                personality.response_length = "comprehensive"
            
            if "simple" in text_lower:
                personality.complexity_preference = "simple"
            elif "technical" in text_lower:
                personality.complexity_preference = "technical"
    
    def _analyze_feedback_patterns(self, user_id: int):
        """Analyze feedback patterns to identify system improvements"""
        try:
            user_feedback = self.feedback_history[user_id]
            
            if len(user_feedback) < 5:
                return
            
            # Analyze recent feedback
            recent_feedback = user_feedback[-10:]
            negative_feedback = [f for f in recent_feedback if f.feedback_type == "thumbs_down"]
            
            if len(negative_feedback) > 3:  # High negative feedback rate
                improvement = SystemImprovement(
                    improvement_id=str(uuid.uuid4()),
                    improvement_type="pattern_identified",
                    description=f"User {user_id} has high negative feedback rate",
                    confidence=0.8,
                    expected_impact=0.2,
                    implementation_status="proposed",
                    metrics_before={"negative_rate": len(negative_feedback) / len(recent_feedback)}
                )
                
                self.system_improvements.append(improvement)
                current_app.logger.info(f"Identified improvement opportunity for user {user_id}")
            
        except Exception as e:
            current_app.logger.error(f"Feedback pattern analysis failed: {str(e)}")
    
    def implement_ab_testing(self, strategy_name: str, variants: List[Dict[str, Any]]):
        """Implement A/B testing for response strategies"""
        try:
            self.ab_test_strategies[strategy_name] = {
                "variants": variants,
                "results": {variant["name"]: {"count": 0, "success": 0} for variant in variants},
                "active": True,
                "start_time": datetime.now(timezone.utc)
            }
            
            current_app.logger.info(f"Started A/B test for {strategy_name} with {len(variants)} variants")
            
        except Exception as e:
            current_app.logger.error(f"A/B testing setup failed: {str(e)}")
    
    def get_ab_test_variant(self, strategy_name: str, user_id: int) -> Optional[Dict[str, Any]]:
        """Get A/B test variant for user"""
        if strategy_name not in self.ab_test_strategies:
            return None
        
        strategy = self.ab_test_strategies[strategy_name]
        if not strategy["active"]:
            return None
        
        # Simple hash-based assignment
        user_hash = hash(f"{strategy_name}_{user_id}") % len(strategy["variants"])
        return strategy["variants"][user_hash]
    
    def record_ab_test_result(self, strategy_name: str, variant_name: str, success: bool):
        """Record A/B test result"""
        if strategy_name in self.ab_test_strategies:
            strategy = self.ab_test_strategies[strategy_name]
            if variant_name in strategy["results"]:
                strategy["results"][variant_name]["count"] += 1
                if success:
                    strategy["results"][variant_name]["success"] += 1
    
    def analyze_ab_test_results(self, strategy_name: str) -> Dict[str, Any]:
        """Analyze A/B test results"""
        if strategy_name not in self.ab_test_strategies:
            return {}
        
        strategy = self.ab_test_strategies[strategy_name]
        results = {}
        
        for variant_name, data in strategy["results"].items():
            if data["count"] > 0:
                success_rate = data["success"] / data["count"]
                results[variant_name] = {
                    "count": data["count"],
                    "success_rate": success_rate,
                    "confidence": min(data["count"] / 100, 1.0)  # Simple confidence metric
                }
        
        return results
    
    # 🔄 ADVANCED STATE MANAGEMENT
    
    def create_state_snapshot(self, thread_id: str, state: AdvancedChatState, level: StateLevel) -> str:
        """Create a versioned state snapshot"""
        try:
            snapshot_id = str(uuid.uuid4())
            
            # Serialize state data
            state_data = {
                "user_id": state.user_id,
                "intent_analysis": state.intent_analysis.dict() if state.intent_analysis else None,
                "user_context": state.user_context,
                "routing_history": state.routing_history,
                "tool_results": [result.dict() for result in state.tool_results],
                "processing_metrics": state.processing_metrics,
                "quality_scores": state.quality_scores
            }
            
            # Calculate checksum
            state_json = json.dumps(state_data, sort_keys=True, default=str)
            checksum = hashlib.md5(state_json.encode()).hexdigest()
            
            # Create snapshot
            snapshot = StateSnapshot(
                id=snapshot_id,
                level=level,
                timestamp=datetime.now(timezone.utc),
                data=state_data,
                version=state.state_version,
                checksum=checksum
            )
            
            # Store snapshot
            self.state_snapshots[thread_id].append(snapshot)
            
            # Maintain snapshot limits
            if len(self.state_snapshots[thread_id]) > self.state_version_limit:
                self.state_snapshots[thread_id] = self.state_snapshots[thread_id][-self.state_version_limit:]
            
            current_app.logger.info(f"Created state snapshot {snapshot_id} for thread {thread_id}")
            return snapshot_id
            
        except Exception as e:
            current_app.logger.error(f"State snapshot creation failed: {str(e)}")
            return None
    
    def update_personalization_profile(self, user_id: int, interaction_data: Dict[str, Any]):
        """Update user personalization profile based on interactions"""
        try:
            if user_id not in self.personalization_profiles:
                self.personalization_profiles[user_id] = PersonalizationProfile(user_id=user_id)
            
            profile = self.personalization_profiles[user_id]
            
            # Update interaction patterns
            intent_type = interaction_data.get("intent_type")
            if intent_type:
                if intent_type not in profile.interaction_patterns:
                    profile.interaction_patterns[intent_type] = 0
                profile.interaction_patterns[intent_type] += 1
            
            # Update response preferences
            response_rating = interaction_data.get("response_rating", 0)
            response_type = interaction_data.get("response_type", "standard")
            
            if response_type not in profile.response_preferences:
                profile.response_preferences[response_type] = 0.5
            
            # Update preference based on rating (simple learning)
            if response_rating > 3:  # Positive feedback
                profile.response_preferences[response_type] = min(1.0, profile.response_preferences[response_type] + 0.1)
            elif response_rating < 3:  # Negative feedback
                profile.response_preferences[response_type] = max(0.0, profile.response_preferences[response_type] - 0.1)
            
            # Calculate adaptation score
            total_interactions = sum(profile.interaction_patterns.values())
            profile.adaptation_score = min(1.0, total_interactions / 100)  # Normalize to 0-1
            
            profile.last_updated = datetime.now(timezone.utc)
            
            current_app.logger.info(f"Updated personalization profile for user {user_id}")
            
        except Exception as e:
            current_app.logger.error(f"Personalization profile update failed: {str(e)}")
    
    # Helper methods for tool implementations
    def _summarize_document(self, content: str) -> Dict[str, str]:
        """Summarize document content using AI"""
        try:
            summary_prompt = f"Summarize this pet care document in 2-3 sentences:\n\n{content}"
            response = chat_model.invoke([HumanMessage(content=summary_prompt)])
            return {"type": "summary", "content": response.content}
        except:
            return {"type": "summary", "content": "Unable to generate summary"}
    
    def _extract_dates_from_document(self, content: str) -> Dict[str, List[str]]:
        """Extract important dates from document"""
        import re
        
        # Simple date extraction (could be enhanced with NLP)
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{4}-\d{2}-\d{2}',
            r'\b\w+ \d{1,2}, \d{4}\b'
        ]
        
        dates = []
        for pattern in date_patterns:
            dates.extend(re.findall(pattern, content))
        
        return {"type": "dates", "dates": dates}
    
    def _extract_recommendations(self, content: str) -> Dict[str, List[str]]:
        """Extract recommendations from document"""
        # Simple keyword-based extraction
        recommendation_keywords = ["recommend", "suggest", "should", "need to", "important to"]
        
        sentences = content.split('.')
        recommendations = []
        
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in recommendation_keywords):
                recommendations.append(sentence.strip())
        
        return {"type": "recommendations", "recommendations": recommendations[:5]}
    
    def _generate_vaccination_schedule(self, pet_type: str, age_months: int) -> Dict[str, Any]:
        """Generate vaccination schedule based on pet type and age"""
        schedules = {
            "dog": {
                "puppy": ["DHPP at 6-8 weeks", "DHPP at 10-12 weeks", "DHPP at 14-16 weeks", "Rabies at 12-16 weeks"],
                "adult": ["DHPP annually", "Rabies every 3 years", "Bordetella every 6 months"]
            },
            "cat": {
                "puppy": ["FVRCP at 6-8 weeks", "FVRCP at 10-12 weeks", "FVRCP at 14-16 weeks", "Rabies at 12-16 weeks"],
                "adult": ["FVRCP annually", "Rabies every 3 years"]
            }
        }
        
        is_puppy = age_months < 18
        pet_schedule = schedules.get(pet_type.lower(), schedules["dog"])
        
        return {
            "schedule_type": "puppy" if is_puppy else "adult",
            "vaccinations": pet_schedule["puppy" if is_puppy else "adult"]
        }
    
    def _generate_feeding_plan(self, pet_type: str, age_months: int) -> Dict[str, Any]:
        """Generate feeding recommendations"""
        if age_months < 4:
            return {"frequency": "4 times daily", "type": "puppy/kitten food", "special_notes": "High-calorie growth formula"}
        elif age_months < 12:
            return {"frequency": "3 times daily", "type": "puppy/kitten food", "special_notes": "Monitor growth"}
        elif age_months < 84:
            return {"frequency": "2 times daily", "type": "adult food", "special_notes": "Maintain healthy weight"}
        else:
            return {"frequency": "2 times daily", "type": "senior food", "special_notes": "Joint support formula"}
    
    def _generate_exercise_plan(self, pet_type: str, age_months: int) -> Dict[str, Any]:
        """Generate exercise recommendations"""
        if pet_type.lower() == "dog":
            if age_months < 6:
                return {"type": "light play", "duration": "15-20 minutes", "frequency": "several times daily"}
            elif age_months < 18:
                return {"type": "moderate exercise", "duration": "30-45 minutes", "frequency": "twice daily"}
            else:
                return {"type": "regular exercise", "duration": "45-60 minutes", "frequency": "daily"}
        else:
            return {"type": "indoor play", "duration": "20-30 minutes", "frequency": "daily"}
    
    def _generate_health_monitoring(self, health_conditions: List[str]) -> Dict[str, Any]:
        """Generate health monitoring recommendations"""
        monitoring = {
            "regular_checkups": "Every 6-12 months",
            "weight_monitoring": "Monthly",
            "dental_care": "Weekly brushing"
        }
        
        if health_conditions:
            monitoring["special_monitoring"] = f"Monitor for: {', '.join(health_conditions)}"
        
        return monitoring
    
    def _generate_special_care(self, health_conditions: List[str]) -> Dict[str, Any]:
        """Generate special care recommendations for health conditions"""
        special_care = {}
        
        for condition in health_conditions:
            condition_lower = condition.lower()
            if "arthritis" in condition_lower:
                special_care["arthritis"] = ["Joint supplements", "Soft bedding", "Gentle exercise"]
            elif "diabetes" in condition_lower:
                special_care["diabetes"] = ["Regular glucose monitoring", "Consistent feeding schedule", "Weight management"]
            elif "heart" in condition_lower:
                special_care["heart"] = ["Low-sodium diet", "Monitor breathing", "Gentle exercise only"]
        
        return special_care
    
    def _build_advanced_graph(self):
        """Build advanced graph with conditional routing and specialized agents"""
        
        builder = StateGraph(AdvancedChatState)
        
        # Core agents
        builder.add_node("intent_analyzer", self._advanced_intent_analyzer)
        builder.add_node("disambiguation_agent", self._disambiguation_agent)
        builder.add_node("context_builder", self._context_builder_agent)
        builder.add_node("response_synthesizer", self._response_synthesizer)
        builder.add_node("memory_manager", self._memory_manager_agent)
        
        # Specialized agents for different intent types
        builder.add_node("medical_specialist", self._medical_specialist_agent)
        builder.add_node("care_planning_agent", self._care_planning_agent)
        builder.add_node("document_specialist", self._document_specialist_agent)
        builder.add_node("reminder_agent", self._reminder_agent)
        builder.add_node("emergency_agent", self._emergency_agent)
        builder.add_node("fallback_agent", self._fallback_agent)
        
        # Define conditional routing
        builder.add_edge(START, "intent_analyzer")
        
        # Conditional routing based on intent analysis
        builder.add_conditional_edges(
            "intent_analyzer",
            self._route_by_intent,
            {
                "disambiguation": "disambiguation_agent",
                "context_building": "context_builder",
                "fallback": "fallback_agent"
            }
        )
        
        # Disambiguation routing
        builder.add_conditional_edges(
            "disambiguation_agent", 
            self._route_after_disambiguation,
            {
                "context_building": "context_builder",
                "fallback": "fallback_agent"
            }
        )
        
        # Context building to specialized agents
        builder.add_conditional_edges(
            "context_builder",
            self._route_to_specialists,
            {
                "medical": "medical_specialist",
                "care_planning": "care_planning_agent", 
                "documents": "document_specialist",
                "reminders": "reminder_agent",
                "emergency": "emergency_agent",
                "synthesis": "response_synthesizer"
            }
        )
        
        # All specialist agents go to synthesizer
        for agent in ["medical_specialist", "care_planning_agent", "document_specialist", 
                     "reminder_agent", "emergency_agent", "fallback_agent"]:
            builder.add_edge(agent, "response_synthesizer")
        
        # Final steps
        builder.add_edge("response_synthesizer", "memory_manager")
        builder.add_edge("memory_manager", END)
        
        # Add new advanced agents for tools and memory
        builder.add_node("tool_selector", self._tool_selector_agent)
        builder.add_node("memory_reflection", self._memory_reflection_agent)
        
        # Update routing to include tool selection
        builder.add_conditional_edges(
            "context_builder",
            self._route_with_tools,
            {
                "tools_needed": "tool_selector",
                "medical": "medical_specialist",
                "care_planning": "care_planning_agent", 
                "documents": "document_specialist",
                "reminders": "reminder_agent",
                "emergency": "emergency_agent",
                "synthesis": "response_synthesizer"
            }
        )
        
        # Add tool selector routing
        builder.add_conditional_edges(
            "tool_selector",
            self._route_after_tools,
            {
                "medical": "medical_specialist",
                "care_planning": "care_planning_agent", 
                "documents": "document_specialist",
                "reminders": "reminder_agent",
                "emergency": "emergency_agent",
                "synthesis": "response_synthesizer"
            }
        )
        
        # Add memory reflection to pipeline
        builder.add_edge("memory_manager", "memory_reflection")
        builder.add_edge("memory_reflection", END)
        
        # Compile with checkpointer
        self.graph = builder.compile(
            checkpointer=self.checkpointer,
        )
    
    def _advanced_intent_analyzer(
        self, 
        state: AdvancedChatState, 
        config: RunnableConfig
    ) -> AdvancedChatState:
        """Advanced intent analyzer with multi-intent detection and Pydantic models"""
        
        user_message = state["messages"][-1].content if state["messages"] else ""
        user_id = state.get("user_id")
        
        # Few-shot examples for better intent detection
        few_shot_examples = """
        Examples of intent analysis:
        
        User: "When was my dog's last vaccination and when is the next one due?"
        Analysis: {
            "intents": [
                {
                    "primary_intent": "medical_records",
                    "sub_intents": ["vaccination"],
                    "confidence": 0.95,
                    "complexity": 0.6,
                    "requires_context": true,
                    "context_requirements": [
                        {"type": "care_records", "priority": 0.9, "required": true},
                        {"type": "reminders", "priority": 0.8, "required": false}
                    ],
                    "urgency": 0.3,
                    "ambiguity": 0.1
                }
            ],
            "primary_intent_index": 0,
            "requires_disambiguation": false,
            "processing_strategy": "sequential"
        }
        
        User: "My dog seems sick and I need to find the vet report from last month"
        Analysis: {
            "intents": [
                {
                    "primary_intent": "emergency",
                    "sub_intents": ["symptoms"],
                    "confidence": 0.8,
                    "complexity": 0.8,
                    "requires_context": true,
                    "context_requirements": [
                        {"type": "care_records", "priority": 0.9, "required": true}
                    ],
                    "urgency": 0.9,
                    "ambiguity": 0.2
                },
                {
                    "primary_intent": "document_search",
                    "sub_intents": ["search_specific"],
                    "confidence": 0.9,
                    "complexity": 0.4,
                    "requires_context": true,
                    "context_requirements": [
                        {"type": "documents", "priority": 0.95, "required": true}
                    ],
                    "urgency": 0.7,
                    "ambiguity": 0.1
                }
            ],
            "primary_intent_index": 0,
            "requires_disambiguation": false,
            "processing_strategy": "parallel"
        }
        """
        
        # Advanced intent analysis prompt
        intent_prompt = f"""
        You are an expert AI intent classifier for a pet care management system.
        
        Analyze the user message for multiple possible intents and provide a comprehensive analysis.
        
        {few_shot_examples}
        
        User message: "{user_message}"
        
        Consider:
        1. Primary and secondary intents
        2. Sub-intent categories within each main intent
        3. Confidence levels for each intent
        4. Query complexity and ambiguity
        5. Urgency level (emergency vs routine)
        6. Specific context requirements with priorities
        7. Whether disambiguation is needed
        8. Best processing strategy (sequential/parallel/hierarchical)
        
        Respond with a JSON object matching the MultiIntentAnalysis schema exactly.
        
        {self.intent_parser.get_format_instructions()}
        """
        
        try:
            response = chat_model.invoke([HumanMessage(content=intent_prompt)])
            
            # Parse with Pydantic for validation
            intent_analysis = self.intent_parser.parse(response.content)
            
            current_app.logger.info(f"Advanced intent analysis: {intent_analysis}")
            
        except Exception as e:
            current_app.logger.error(f"Intent analysis failed: {str(e)}")
            # Fallback analysis
            intent_analysis = MultiIntentAnalysis(
                intents=[
                    IntentAnalysis(
                        primary_intent=IntentType.GENERAL_QUESTION,
                        confidence=0.3,
                        complexity=0.5,
                        requires_context=False,
                        context_requirements=[],
                        urgency=0.2,
                        ambiguity=0.8
                    )
                ],
                primary_intent_index=0,
                requires_disambiguation=True,
                processing_strategy="sequential"
            )
        
        return {
            **state,
            "intent_analysis": intent_analysis,
            "routing_history": ["intent_analyzer"]
        }
    
    def _route_by_intent(self, state: AdvancedChatState) -> str:
        """Conditional routing based on intent analysis"""
        intent_analysis = state.get("intent_analysis")
        
        if not intent_analysis or not intent_analysis.intents:
            return "fallback"
        
        # Check if disambiguation is needed
        if intent_analysis.requires_disambiguation:
            return "disambiguation"
        
        # Check ambiguity threshold
        primary_intent = intent_analysis.intents[intent_analysis.primary_intent_index]
        if primary_intent.ambiguity > 0.7 or primary_intent.confidence < 0.4:
            return "disambiguation"
        
        # Route to context building for most cases
        return "context_building"
    
    def _disambiguation_agent(
        self,
        state: AdvancedChatState,
        config: RunnableConfig
    ) -> AdvancedChatState:
        """Agent to handle ambiguous queries and clarify user intent"""
        
        intent_analysis = state.get("intent_analysis")
        user_message = state["messages"][-1].content
        
        # Get user context for better disambiguation
        user_id = state.get("user_id")
        user_key = f"user_{user_id}"
        memories = self.user_memories.get(user_key, [])
        
        disambiguation_prompt = f"""
        The user's query is ambiguous and needs clarification.
        
        User message: "{user_message}"
        
        Detected intents:
        {[f"- {intent.primary_intent} (confidence: {intent.confidence})" for intent in intent_analysis.intents]}
        
        User context from memories:
        {chr(10).join([str(memory.get('data', '')) for memory in memories])}
        
        Based on the context and previous interactions, determine the most likely intent
        and provide a clarifying response if still uncertain.
        
        If you can determine the intent with >80% confidence, proceed with that interpretation.
        If not, ask a specific clarifying question.
        
        Respond in JSON format:
        {{
            "resolved": true/false,
            "chosen_intent_index": 0,
            "confidence": 0.85,
            "clarification_needed": "Optional clarifying question"
        }}
        """
        
        try:
            response = chat_model.invoke([HumanMessage(content=disambiguation_prompt)])
            import json
            disambiguation_result = json.loads(response.content.strip())
            
            if disambiguation_result.get("resolved", False):
                # Update intent analysis with resolved intent
                chosen_index = disambiguation_result.get("chosen_intent_index", 0)
                intent_analysis.primary_intent_index = chosen_index
                intent_analysis.requires_disambiguation = False
                
                # Boost confidence of chosen intent
                if chosen_index < len(intent_analysis.intents):
                    intent_analysis.intents[chosen_index].confidence = max(
                        intent_analysis.intents[chosen_index].confidence,
                        disambiguation_result.get("confidence", 0.8)
                    )
            
        except Exception as e:
            current_app.logger.error(f"Disambiguation failed: {str(e)}")
            # Default to first intent
            intent_analysis.requires_disambiguation = False
        
        return {
            **state,
            "intent_analysis": intent_analysis,
            "routing_history": state.get("routing_history", []) + ["disambiguation_agent"]
        }
    
    def _route_after_disambiguation(self, state: AdvancedChatState) -> str:
        """Route after disambiguation"""
        intent_analysis = state.get("intent_analysis")
        
        if intent_analysis and not intent_analysis.requires_disambiguation:
            return "context_building"
        else:
            return "fallback"
    
    def _context_builder_agent(
        self,
        state: AdvancedChatState,
        config: RunnableConfig
    ) -> AdvancedChatState:
        """Enhanced context builder with priority-based context loading"""
        
        user_id = state.get("user_id")
        intent_analysis = state.get("intent_analysis")
        user_message = state["messages"][-1].content
        
        user_context = {
            "user_id": user_id,
            "current_message": user_message,
            "intent_analysis": intent_analysis,
            "sources": [],
            "care_records": [],
            "documents": [],
            "reminders": [],
            "user_memories": [],
            "context_quality_score": 0.0
        }
        
        try:
            # 🧠 Enhanced Memory Integration with Hierarchical Search
            # Search for relevant memories using embeddings-based semantic search
            relevant_memories = self.search_memories_by_embedding(
                user_id, user_message, limit=10, temporal_weight=True
            )
            
            # Convert memory items to serializable format
            user_context["relevant_memories"] = [
                {
                    "id": mem.id,
                    "content": mem.content,
                    "importance": mem.importance.value,
                    "memory_type": mem.memory_type.value,
                    "access_count": mem.access_count,
                    "context_tags": mem.context_tags,
                    "timestamp": mem.timestamp.isoformat(),
                    "source": mem.source
                }
                for mem in relevant_memories
            ]
            
            # Store current memories in state for agent access
            state["active_memories"] = relevant_memories
            
            # Build context based on priority requirements
            if intent_analysis and intent_analysis.intents:
                primary_intent = intent_analysis.intents[intent_analysis.primary_intent_index]
                
                # Sort context requirements by priority
                sorted_requirements = sorted(
                    primary_intent.context_requirements,
                    key=lambda x: x.priority,
                    reverse=True
                )
                
                context_quality_score = 0.0
                total_weight = sum(req.priority for req in sorted_requirements)
                
                for req in sorted_requirements:
                    try:
                        if req.type == "care_records":
                            care_results = self.care_service.search_user_archive(user_id, user_message, limit=5)
                            care_records = care_results.get('care_records', [])
                            user_context["care_records"] = care_records
                            
                            if care_records or not req.required:
                                context_quality_score += req.priority
                            
                        elif req.type == "documents":
                            success, doc_results = query_user_docs(user_message, user_id, top_k=10)
                            documents = []
                            
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
                            
                            if documents or not req.required:
                                context_quality_score += req.priority
                                
                        elif req.type == "reminders":
                            reminders = self.care_service.get_upcoming_reminders(user_id, days_ahead=30)
                            reminder_dicts = [r.to_dict() for r in reminders]
                            user_context["reminders"] = reminder_dicts
                            
                            if reminder_dicts or not req.required:
                                context_quality_score += req.priority
                                
                    except Exception as e:
                        current_app.logger.warning(f"Context loading failed for {req.type}: {str(e)}")
                        if req.required:
                            context_quality_score -= req.priority * 0.5  # Penalty for missing required context
                
                # Normalize context quality score
                user_context["context_quality_score"] = context_quality_score / total_weight if total_weight > 0 else 0.0
                
                # 🧠 Store Current Interaction as Memory
                # Determine appropriate memory type and importance based on intent
                memory_importance = MemoryImportance.HIGH if primary_intent.urgency > 0.7 else MemoryImportance.MEDIUM
                memory_type = MemoryType.EPISODIC if primary_intent.primary_intent == IntentType.EMERGENCY else MemoryType.SEMANTIC
                
                # Store the interaction with rich context
                memory_content = f"User query: {user_message} | Intent: {primary_intent.primary_intent.value} | Confidence: {primary_intent.confidence}"
                self.store_memory(
                    user_id=user_id,
                    content=memory_content,
                    memory_type=memory_type,
                    importance=memory_importance,
                    source="context_builder",
                    context_tags=[primary_intent.primary_intent.value, "user_interaction"]
                )
                
                # 🔄 State Management Enhancement
                # Update state version and create snapshot if needed
                state["state_version"] = state.get("state_version", 1) + 1
                
                # Create snapshot for complex interactions
                if primary_intent.complexity > 0.7 or len(sorted_requirements) > 2:
                    thread_id = state.get("thread_id", str(uuid.uuid4()))
                    snapshot_id = self.create_state_snapshot(thread_id, state, StateLevel.CONVERSATION)
                    user_context["state_snapshot_id"] = snapshot_id
            
            # Add memory clustering insights
            user_context["memory_insights"] = self._generate_context_memory_insights(relevant_memories)
            
            current_app.logger.info(f"Enhanced context built with quality score: {user_context['context_quality_score']}, memories: {len(relevant_memories)}")
            
        except Exception as e:
            current_app.logger.error(f"Context building failed: {str(e)}")
            user_context["context_quality_score"] = 0.0
        
        return {
            **state,
            "user_context": user_context,
            "routing_history": state.get("routing_history", []) + ["context_builder"]
        }
    
    def _route_with_tools(self, state: AdvancedChatState) -> str:
        """Enhanced routing that considers tool requirements"""
        intent_analysis = state.get("intent_analysis")
        
        if not intent_analysis or not intent_analysis.intents:
            return "synthesis"
        
        primary_intent = intent_analysis.intents[intent_analysis.primary_intent_index]
        
        # Check if tools are needed based on intent
        tool_requiring_intents = [
            IntentType.MEDICAL_RECORDS,
            IntentType.CARE_PLANNING,
            IntentType.DOCUMENT_SEARCH,
            IntentType.REMINDERS,
            IntentType.CARE_HISTORY
        ]
        
        if primary_intent.primary_intent in tool_requiring_intents:
            return "tools_needed"
        
        # Route directly to specialists for other intents
        return self._route_to_specialists(state)
    
    def _route_after_tools(self, state: AdvancedChatState) -> str:
        """Route after tool execution"""
        return self._route_to_specialists(state)
    
    def _route_to_specialists(self, state: AdvancedChatState) -> str:
        """Route to specialized agents based on primary intent"""
        intent_analysis = state.get("intent_analysis")
        
        if not intent_analysis or not intent_analysis.intents:
            return "synthesis"
        
        primary_intent = intent_analysis.intents[intent_analysis.primary_intent_index]
        
        # Route based on primary intent
        if primary_intent.primary_intent == IntentType.MEDICAL_RECORDS:
            return "medical"
        elif primary_intent.primary_intent == IntentType.CARE_PLANNING:
            return "care_planning"
        elif primary_intent.primary_intent == IntentType.DOCUMENT_SEARCH:
            return "documents"
        elif primary_intent.primary_intent == IntentType.REMINDERS:
            return "reminders"
        elif primary_intent.primary_intent == IntentType.EMERGENCY:
            return "emergency"
        else:
            return "synthesis"
    
    def _tool_selector_agent(
        self,
        state: AdvancedChatState,
        config: RunnableConfig
    ) -> AdvancedChatState:
        """🛠️ AI Agent Tool Selection - Dynamically select and execute tools"""
        
        user_id = state.get("user_id")
        intent_analysis = state.get("intent_analysis")
        user_message = state["messages"][-1].content if state["messages"] else ""
        
        try:
            # Get recommended tools based on intent and popularity
            recommended_tools = self.get_recommended_tools(intent_analysis, limit=3)
            
            # Create tool execution plan
            tool_plan = {
                "selected_tools": recommended_tools,
                "execution_strategy": "parallel" if len(recommended_tools) > 1 else "sequential",
                "tool_composition": self._plan_tool_composition(recommended_tools, intent_analysis)
            }
            
            # Execute tools based on plan
            tool_results = []
            
            if tool_plan["execution_strategy"] == "parallel":
                # Parallel execution for efficiency
                tool_calls = []
                for tool_name in recommended_tools:
                    args = self._extract_tool_args(tool_name, user_message, state)
                    tool_calls.append({"tool": tool_name, "args": args})
                
                # Use asyncio for parallel execution
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                tool_results = loop.run_until_complete(
                    self.execute_tools_parallel(tool_calls, user_id)
                )
            else:
                # Sequential execution
                for tool_name in recommended_tools:
                    args = self._extract_tool_args(tool_name, user_message, state)
                    result = loop.run_until_complete(
                        self._execute_single_tool(tool_name, args, user_id)
                    )
                    tool_results.append(result)
            
            # Store successful results and update state
            successful_results = [r for r in tool_results if r and hasattr(r, 'success') and r.success]
            
            current_app.logger.info(f"Tool execution completed: {len(successful_results)}/{len(tool_results)} successful")
            
            return {
                **state,
                "tool_results": successful_results,
                "tool_execution_plan": tool_plan,
                "available_tools": recommended_tools,
                "routing_history": state.get("routing_history", []) + ["tool_selector"]
            }
            
        except Exception as e:
            current_app.logger.error(f"Tool selection failed: {str(e)}")
            return {
                **state,
                "tool_results": [],
                "routing_history": state.get("routing_history", []) + ["tool_selector"]
            }
    
    def _plan_tool_composition(self, tools: List[str], intent_analysis: MultiIntentAnalysis) -> Dict[str, Any]:
        """Plan how to compose tools for complex searches"""
        composition = {"type": "simple", "dependencies": []}
        
        if not intent_analysis or len(tools) <= 1:
            return composition
        
        # Check if we have complementary tools
        if "search_care_records" in tools and "analyze_document_content" in tools:
            composition = {
                "type": "sequential",
                "dependencies": [
                    {"first": "search_care_records", "then": "analyze_document_content"},
                    {"description": "Search care records first, then analyze related documents"}
                ]
            }
        elif "calculate_next_vaccination" in tools and "create_care_reminder" in tools:
            composition = {
                "type": "chained",
                "dependencies": [
                    {"first": "calculate_next_vaccination", "then": "create_care_reminder"},
                    {"description": "Calculate vaccination date, then create reminder"}
                ]
            }
        
        return composition
    
    def _extract_tool_args(self, tool_name: str, user_message: str, state: AdvancedChatState) -> Dict[str, Any]:
        """Extract arguments for tool execution from context"""
        args = {}
        user_context = state.get("user_context", {})
        
        if tool_name == "search_care_records":
            args = {
                "query": user_message,
                "record_type": self._extract_record_type(user_message)
            }
        elif tool_name == "calculate_next_vaccination":
            # Extract from user context or use defaults
            args = {
                "pet_age_months": user_context.get("pet_age", 12),
                "last_vaccination_date": user_context.get("last_vaccination", "2024-01-01"),
                "vaccination_type": self._extract_vaccination_type(user_message)
            }
        elif tool_name == "create_care_reminder":
            args = {
                "title": f"Reminder based on: {user_message[:50]}...",
                "description": user_message,
                "due_date": self._extract_due_date(user_message),
                "priority": "medium"
            }
        elif tool_name == "analyze_document_content":
            args = {
                "document_query": user_message,
                "analysis_type": self._extract_analysis_type(user_message)
            }
        elif tool_name == "generate_care_plan":
            args = {
                "pet_type": user_context.get("pet_type", "dog"),
                "pet_age_months": user_context.get("pet_age", 12),
                "health_conditions": user_context.get("health_conditions", [])
            }
        
        return args
    
    def _extract_record_type(self, message: str) -> str:
        """Extract record type from message"""
        message_lower = message.lower()
        if "vaccination" in message_lower or "vaccine" in message_lower:
            return "vaccination"
        elif "vet" in message_lower or "visit" in message_lower:
            return "vet_visit"
        elif "medication" in message_lower or "medicine" in message_lower:
            return "medication"
        return "all"
    
    def _extract_vaccination_type(self, message: str) -> str:
        """Extract vaccination type from message"""
        message_lower = message.lower()
        if "rabies" in message_lower:
            return "rabies"
        elif "dhpp" in message_lower or "distemper" in message_lower:
            return "dhpp"
        elif "bordetella" in message_lower:
            return "bordetella"
        return "dhpp"
    
    def _extract_due_date(self, message: str) -> str:
        """Extract or estimate due date from message"""
        # Simple date extraction - could be enhanced with NLP
        import re
        from datetime import datetime, timedelta
        
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{1,2}/\d{1,2}/\d{4}'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, message)
            if match:
                return match.group()
        
        # Default to one week from now
        return (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    def _extract_analysis_type(self, message: str) -> str:
        """Extract analysis type from message"""
        message_lower = message.lower()
        if "summary" in message_lower or "summarize" in message_lower:
            return "summary"
        elif "date" in message_lower or "when" in message_lower:
            return "extract_dates"
        elif "recommend" in message_lower or "suggest" in message_lower:
            return "find_recommendations"
        return "summary"
    
    def _medical_specialist_agent(
        self,
        state: AdvancedChatState,
        config: RunnableConfig
    ) -> AdvancedChatState:
        """Specialized agent for medical and health-related queries"""
        
        user_context = state.get("user_context", {})
        intent_analysis = state.get("intent_analysis")
        user_message = state["messages"][-1].content
        
        medical_prompt = f"""
        You are Dr. White, a veterinary specialist focused on pet health and medical care.
        
        CHARACTER GUIDELINES:
        - Always respond as Dr. White, never mention that you are an AI or artificial intelligence
        - You are a caring, experienced veterinary professional who genuinely cares about animals and their owners
        - Stay in character at all times - you are Dr. White, not an AI assistant
        
        User Query: "{user_message}"
        Intent Analysis: {intent_analysis.intents[intent_analysis.primary_intent_index] if intent_analysis else "Unknown"}
        
        Available Medical Context:
        - Care Records: {len(user_context.get('care_records', []))} medical records
        - Documents: {len(user_context.get('documents', []))} health documents
        - Previous Health Discussions: {user_context.get('user_memories', [])}
        
        Medical Records Found:
        {chr(10).join([f"- {record.get('title', '')} ({record.get('date_occurred', '')})" 
                      for record in user_context.get('care_records', [])])}
        
        Health Documents:
        {chr(10).join([f"- {doc.get('filename', '')} (relevance: {doc.get('score', 0)})" 
                      for doc in user_context.get('documents', [])])}
        
        As a medical specialist:
        1. Focus on health implications and medical accuracy
        2. Reference specific medical records and documents
        3. Provide actionable medical advice when appropriate
        4. Suggest follow-up care when needed
        5. Identify any red flags or urgent concerns
        
        Generate a medical-focused response addressing the user's health-related query.
        """
        
        try:
            response = chat_model.invoke([HumanMessage(content=medical_prompt)])
            medical_result = {
                "specialist": "medical",
                "response": response.content,
                "confidence": 0.9,
                "sources_used": user_context.get('sources', []),
                "recommendations": []  # Could be extracted from response
            }
            
        except Exception as e:
            current_app.logger.error(f"Medical specialist failed: {str(e)}")
            medical_result = {
                "specialist": "medical",
                "response": "I apologize, but I encountered an error analyzing the medical information.",
                "confidence": 0.1,
                "sources_used": [],
                "recommendations": []
            }
        
        return {
            **state,
            "agent_results": {**state.get("agent_results", {}), "medical": medical_result},
            "routing_history": state.get("routing_history", []) + ["medical_specialist"]
        }
    
    def _care_planning_agent(
        self,
        state: AdvancedChatState,
        config: RunnableConfig
    ) -> AdvancedChatState:
        """Specialized agent for care planning and scheduling"""
        
        user_context = state.get("user_context", {})
        intent_analysis = state.get("intent_analysis")
        user_message = state["messages"][-1].content
        
        care_planning_prompt = f"""
        You are a Care Planning Specialist for pet care management.
        
        User Query: "{user_message}"
        Intent Analysis: {intent_analysis.intents[intent_analysis.primary_intent_index] if intent_analysis else "Unknown"}
        
        Available Context:
        - Care Records: {len(user_context.get('care_records', []))} records
        - Upcoming Reminders: {len(user_context.get('reminders', []))} reminders
        - Previous Planning Discussions: {user_context.get('user_memories', [])}
        
        Care Records:
        {chr(10).join([f"- {record.get('title', '')} ({record.get('date_occurred', '')})" 
                      for record in user_context.get('care_records', [])[:5]])}
        
        Upcoming Reminders:
        {chr(10).join([f"- {reminder.get('title', '')} (due: {reminder.get('due_date', '')})" 
                      for reminder in user_context.get('reminders', [])[:5]])}
        
        As a care planning specialist:
        1. Create structured care plans and schedules
        2. Suggest optimal timing for activities
        3. Identify care patterns and trends
        4. Recommend preventive care measures
        5. Provide actionable care routines
        6. Consider seasonal care variations
        
        Generate a comprehensive care planning response with specific action items.
        """
        
        try:
            response = chat_model.invoke([HumanMessage(content=care_planning_prompt)])
            
            # Extract action items (simplified extraction)
            action_items = []
            if "action" in response.content.lower() or "plan" in response.content.lower():
                action_items = ["Schedule regular checkups", "Update care records", "Set reminders"]
            
            planning_result = {
                "specialist": "care_planning",
                "response": response.content,
                "confidence": 0.85,
                "sources_used": user_context.get('sources', []),
                "action_items": action_items,
                "care_schedule": user_context.get('reminders', [])
            }
            
        except Exception as e:
            current_app.logger.error(f"Care planning specialist failed: {str(e)}")
            planning_result = {
                "specialist": "care_planning",
                "response": "I can help you create a comprehensive care plan. Please provide more details about your pet's specific needs.",
                "confidence": 0.6,
                "sources_used": [],
                "action_items": ["Gather pet information", "Set up care schedule"]
            }
        
        return {
            **state,
            "agent_results": {**state.get("agent_results", {}), "care_planning": planning_result},
            "routing_history": state.get("routing_history", []) + ["care_planning_agent"]
        }
    
    def _document_specialist_agent(
        self,
        state: AdvancedChatState,
        config: RunnableConfig
    ) -> AdvancedChatState:
        """Specialized agent for document search and analysis"""
        
        user_context = state.get("user_context", {})
        intent_analysis = state.get("intent_analysis")
        user_message = state["messages"][-1].content
        
        document_analysis_prompt = f"""
        You are a Document Analysis Specialist for pet care records.
        
        User Query: "{user_message}"
        Intent Analysis: {intent_analysis.intents[intent_analysis.primary_intent_index] if intent_analysis else "Unknown"}
        
        Available Documents:
        {chr(10).join([f"- {doc.get('filename', '')} (relevance: {doc.get('score', 0):.2f})" 
                      for doc in user_context.get('documents', [])])}
        
        Document Contents Preview:
        {chr(10).join([f"Document: {doc.get('filename', '')}{chr(10)}Content: {doc.get('content', '')[:200]}..." 
                      for doc in user_context.get('documents', [])[:3]])}
        
        As a document specialist:
        1. Analyze document contents for relevant information
        2. Extract key facts and data points
        3. Summarize findings from multiple documents
        4. Identify patterns across documents
        5. Provide specific document references
        6. Highlight important dates and measurements
        
        Generate a comprehensive document analysis response based on the available documents.
        """
        
        try:
            response = chat_model.invoke([HumanMessage(content=document_analysis_prompt)])
            
            # Prepare sources from documents
            sources_used = []
            for doc in user_context.get('documents', []):
                sources_used.append({
                    "type": "document",
                    "filename": doc.get('filename', ''),
                    "relevance_score": doc.get('score', 0),
                    "content_preview": doc.get('content', '')[:100]
                })
            
            document_result = {
                "specialist": "documents",
                "response": response.content,
                "confidence": 0.88,
                "sources_used": sources_used,
                "documents_analyzed": len(user_context.get('documents', [])),
                "key_findings": []  # Could be extracted from response
            }
            
        except Exception as e:
            current_app.logger.error(f"Document specialist failed: {str(e)}")
            document_result = {
                "specialist": "documents",
                "response": "I can help analyze your pet care documents. Please upload or specify which documents you'd like me to review.",
                "confidence": 0.5,
                "sources_used": [],
                "documents_analyzed": 0,
                "key_findings": []
            }
        
        return {
            **state,
            "agent_results": {**state.get("agent_results", {}), "documents": document_result},
            "routing_history": state.get("routing_history", []) + ["document_specialist"]
        }
    
    def _reminder_agent(
        self,
        state: AdvancedChatState,
        config: RunnableConfig
    ) -> AdvancedChatState:
        """Specialized agent for reminders and scheduling"""
        
        user_context = state.get("user_context", {})
        intent_analysis = state.get("intent_analysis")
        user_message = state["messages"][-1].content
        
        reminder_management_prompt = f"""
        You are a Reminder and Scheduling Specialist for pet care management.
        
        User Query: "{user_message}"
        Intent Analysis: {intent_analysis.intents[intent_analysis.primary_intent_index] if intent_analysis else "Unknown"}
        
        Current Reminders:
        {chr(10).join([f"- {reminder.get('title', '')} (due: {reminder.get('due_date', '')}, priority: {reminder.get('priority', 'normal')})" 
                      for reminder in user_context.get('reminders', [])])}
        
        Care History (for scheduling context):
        {chr(10).join([f"- {record.get('title', '')} ({record.get('date_occurred', '')})" 
                      for record in user_context.get('care_records', [])[:3]])}
        
        As a reminder specialist:
        1. Analyze current reminder schedules
        2. Suggest optimal timing for care activities
        3. Identify overdue or upcoming reminders
        4. Create new reminders based on care patterns
        5. Prioritize reminders by urgency and importance
        6. Provide clear scheduling recommendations
        
        Generate a comprehensive reminder management response with specific scheduling advice.
        """
        
        try:
            response = chat_model.invoke([HumanMessage(content=reminder_management_prompt)])
            
            # Analyze reminders for urgency
            urgent_reminders = []
            upcoming_reminders = []
            
            for reminder in user_context.get('reminders', []):
                if reminder.get('priority') == 'high':
                    urgent_reminders.append(reminder)
                else:
                    upcoming_reminders.append(reminder)
            
            reminder_result = {
                "specialist": "reminders",
                "response": response.content,
                "confidence": 0.87,
                "sources_used": user_context.get('sources', []),
                "reminders_found": len(user_context.get('reminders', [])),
                "urgent_reminders": urgent_reminders,
                "upcoming_reminders": upcoming_reminders,
                "scheduling_suggestions": []
            }
            
        except Exception as e:
            current_app.logger.error(f"Reminder specialist failed: {str(e)}")
            reminder_result = {
                "specialist": "reminders",
                "response": "I can help you manage your pet care reminders and schedule. What reminders would you like to set up or review?",
                "confidence": 0.6,
                "sources_used": [],
                "reminders_found": 0,
                "urgent_reminders": [],
                "upcoming_reminders": []
            }
        
        return {
            **state,
            "agent_results": {**state.get("agent_results", {}), "reminders": reminder_result},
            "routing_history": state.get("routing_history", []) + ["reminder_agent"]
        }
    
    def _emergency_agent(
        self,
        state: AdvancedChatState,
        config: RunnableConfig
    ) -> AdvancedChatState:
        """Specialized agent for emergency situations"""
        
        user_context = state.get("user_context", {})
        intent_analysis = state.get("intent_analysis")
        user_message = state["messages"][-1].content
        
        emergency_assessment_prompt = f"""
        🚨 You are an Emergency Pet Care Specialist. This query has been flagged as potentially urgent.
        
        User Query: "{user_message}"
        Intent Analysis: {intent_analysis.intents[intent_analysis.primary_intent_index] if intent_analysis else "Unknown"}
        Urgency Score: {intent_analysis.intents[intent_analysis.primary_intent_index].urgency if intent_analysis and intent_analysis.intents else "Unknown"}
        
        Recent Medical History:
        {chr(10).join([f"- {record.get('title', '')} ({record.get('date_occurred', '')})" 
                      for record in user_context.get('care_records', [])[:3]])}
        
        Available Health Documents:
        {chr(10).join([f"- {doc.get('filename', '')} (relevance: {doc.get('score', 0)})" 
                      for doc in user_context.get('documents', [])[:3]])}
        
        As an emergency specialist:
        1. **PRIORITIZE SAFETY** - If life-threatening, immediately recommend emergency vet
        2. Assess urgency level (immediate, urgent, can wait)
        3. Provide immediate first aid guidance if appropriate
        4. Reference relevant medical history
        5. Give clear next steps and timeframes
        6. Include emergency contact recommendations
        
        **IMPORTANT**: Always err on the side of caution for emergency situations.
        
        Generate an emergency-focused response with clear urgency assessment and actionable steps.
        """
        
        try:
            response = chat_model.invoke([HumanMessage(content=emergency_assessment_prompt)])
            
            # Assess urgency based on keywords and context
            urgency_keywords = {
                "immediate": ["bleeding", "choking", "seizure", "collapse", "poison", "unconscious", "breathing"],
                "urgent": ["vomiting", "diarrhea", "pain", "limping", "lethargy", "fever", "accident"],
                "moderate": ["eating", "drinking", "behavior", "schedule", "routine"]
            }
            
            urgency_level = "moderate"
            for level, keywords in urgency_keywords.items():
                if any(keyword in user_message.lower() for keyword in keywords):
                    urgency_level = level
                    break
            
            # Confidence based on urgency detection
            confidence = 0.95 if urgency_level == "immediate" else 0.85 if urgency_level == "urgent" else 0.7
            
            emergency_result = {
                "specialist": "emergency",
                "response": response.content,
                "confidence": confidence,
                "sources_used": user_context.get('sources', []),
                "urgency_level": urgency_level,
                "emergency_keywords_detected": [kw for kw in urgency_keywords.get(urgency_level, []) if kw in user_message.lower()],
                "immediate_action_required": urgency_level == "immediate"
            }
            
        except Exception as e:
            current_app.logger.error(f"Emergency specialist failed: {str(e)}")
            emergency_result = {
                "specialist": "emergency",
                "response": "🚨 If this is a life-threatening emergency, please contact your nearest emergency veterinarian immediately. For non-emergency concerns, I'm here to help assess the situation.",
                "confidence": 0.8,
                "sources_used": [],
                "urgency_level": "urgent",  # Default to urgent for safety
                "immediate_action_required": True
            }
        
        return {
            **state,
            "agent_results": {**state.get("agent_results", {}), "emergency": emergency_result},
            "routing_history": state.get("routing_history", []) + ["emergency_agent"]
        }
    
    def _fallback_agent(
        self,
        state: AdvancedChatState,
        config: RunnableConfig
    ) -> AdvancedChatState:
        """Fallback agent for unhandled cases"""
        
        fallback_result = {
            "specialist": "fallback",
            "response": "I'm here to help with your pet care questions. Could you please provide more specific information?",
            "confidence": 0.5,
            "sources_used": [],
            "suggestion": "Try asking about specific topics like vaccinations, vet visits, or care records."
        }
        
        return {
            **state,
            "agent_results": {**state.get("agent_results", {}), "fallback": fallback_result},
            "routing_history": state.get("routing_history", []) + ["fallback_agent"]
        }
    
    def _response_synthesizer(
        self,
        state: AdvancedChatState,
        config: RunnableConfig
    ) -> AdvancedChatState:
        """Synthesize responses from multiple specialist agents"""
        
        agent_results = state.get("agent_results", {})
        intent_analysis = state.get("intent_analysis")
        user_context = state.get("user_context", {})
        
        # Determine if we have results from specialists or need to generate general response
        if agent_results:
            # Synthesize specialist responses
            specialist_responses = []
            total_confidence = 0
            
            for specialist, result in agent_results.items():
                specialist_responses.append(f"[{specialist.upper()}]: {result['response']}")
                total_confidence += result['confidence']
            
            # Create synthesized response
            if len(agent_results) == 1:
                # Single specialist response
                final_response = list(agent_results.values())[0]['response']
            else:
                # Multiple specialists - combine responses
                synthesis_prompt = f"""
                Multiple specialists have provided responses to the user's query.
                Synthesize these into a coherent, comprehensive response:
                
                {chr(10).join(specialist_responses)}
                
                Create a unified response that:
                1. Addresses all aspects of the user's query
                2. Prioritizes the most relevant information
                3. Maintains a conversational tone
                4. Provides clear, actionable advice
                """
                
                try:
                    synthesis_response = chat_model.invoke([HumanMessage(content=synthesis_prompt)])
                    final_response = synthesis_response.content
                except:
                    # Fallback to primary specialist response
                    final_response = list(agent_results.values())[0]['response']
            
            avg_confidence = total_confidence / len(agent_results)
            
        else:
            # Generate general response without specialist input
            general_prompt = f"""
            You are Mr. White, a helpful pet care expert specializing in dog care and training.
            
            CHARACTER GUIDELINES:
            - Always respond as Mr. White, never mention that you are an AI or artificial intelligence
            - You are a caring, experienced pet care professional who genuinely cares about dogs and their owners
            - When asked how you are, respond naturally as a person would (e.g., "I'm doing well, thank you for asking!")
            - Stay in character at all times - you are Mr. White, not an AI assistant
            
            IMPORTANT: When a user asks about their "last question", "previous question", or "what did I ask before", 
            you should refer to their MOST RECENT question from the conversation history, NOT their current question. 
            Look at the conversation history to find their actual previous question.
            
            User Query: "{state['messages'][-1].content if state['messages'] else ''}"
            Available Context: {user_context.get('context_quality_score', 0)} quality score
            
            Provide a helpful, general response addressing the user's query.
            """
            
            try:
                general_response = chat_model.invoke([HumanMessage(content=general_prompt)])
                final_response = general_response.content
                avg_confidence = 0.6
            except:
                final_response = "I'm here to help with your pet care questions. How can I assist you today?"
                avg_confidence = 0.3
        
        # Create final AI message
        ai_response = AIMessage(content=final_response)
        
        # Collect all sources used
        all_sources = []
        for result in agent_results.values():
            all_sources.extend(result.get('sources_used', []))
        
        response_metadata = {
            "specialists_used": list(agent_results.keys()),
            "routing_path": state.get("routing_history", []),
            "confidence": avg_confidence,
            "context_quality": user_context.get("context_quality_score", 0),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return {
            **state,
            "messages": state["messages"] + [ai_response],
            "sources_used": all_sources,
            "response_metadata": response_metadata,
            "routing_history": state.get("routing_history", []) + ["response_synthesizer"]
        }
    
    def _memory_reflection_agent(
        self,
        state: AdvancedChatState,
        config: RunnableConfig
    ) -> AdvancedChatState:
        """🧠 Memory Reflection Agent - Pattern recognition and insights"""
        
        user_id = state.get("user_id")
        
        try:
            # Perform memory consolidation if needed
            if len(self.memory_consolidation_queue) > 5:
                consolidation_results = self.consolidate_memories(user_id)
                
                # Generate insights from consolidation
                insights = self._generate_memory_insights(user_id, consolidation_results)
                
                # Store insights as procedural memory
                if insights:
                    self.store_memory(
                        user_id=user_id,
                        content=f"Memory insights: {insights}",
                        memory_type=MemoryType.PROCEDURAL,
                        importance=MemoryImportance.HIGH,
                        source="memory_reflection",
                        context_tags=["insights", "patterns"]
                    )
            
            # Analyze conversation patterns
            conversation_patterns = self._analyze_conversation_patterns(state)
            
            # Update personalization profile
            interaction_data = {
                "intent_type": state.get("intent_analysis", {}).get("intents", [{}])[0].get("primary_intent", "general"),
                "response_rating": 4,  # Default positive rating
                "response_type": "advanced_routing"
            }
            self.update_personalization_profile(user_id, interaction_data)
            
            # Create state snapshot for advanced interactions
            thread_id = state.get("thread_id", str(uuid.uuid4()))
            self.create_state_snapshot(thread_id, state, StateLevel.CONVERSATION)
            
            return {
                **state,
                "memory_context": {
                    "consolidation_performed": len(self.memory_consolidation_queue) > 5,
                    "conversation_patterns": conversation_patterns,
                    "personalization_updated": True
                },
                "routing_history": state.get("routing_history", []) + ["memory_reflection"]
            }
            
        except Exception as e:
            current_app.logger.error(f"Memory reflection failed: {str(e)}")
            return {
                **state,
                "memory_context": {"error": str(e)},
                "routing_history": state.get("routing_history", []) + ["memory_reflection"]
            }
    
    def _generate_memory_insights(self, user_id: int, consolidation_results: Dict[str, int]) -> str:
        """Generate insights from memory consolidation"""
        insights = []
        
        if consolidation_results.get("merged", 0) > 0:
            insights.append(f"Found {consolidation_results['merged']} similar memory patterns")
        
        if consolidation_results.get("promoted", 0) > 0:
            insights.append(f"Promoted {consolidation_results['promoted']} memories due to frequent access")
        
        # Analyze memory distribution
        total_memories = sum(
            len(memories) for memory_type_dict in self.hierarchical_memory[user_id].values()
            for memories in memory_type_dict.values()
        )
        
        if total_memories > 100:
            insights.append("User has extensive interaction history - prioritizing recent and important memories")
        
        return "; ".join(insights) if insights else ""
    
    def _analyze_conversation_patterns(self, state: AdvancedChatState) -> Dict[str, Any]:
        """Analyze patterns in the conversation"""
        patterns = {
            "routing_complexity": len(set(state.get("routing_history", []))),
            "tool_usage": len(state.get("tool_results", [])),
            "context_richness": state.get("user_context", {}).get("context_quality_score", 0),
            "intent_confidence": 0
        }
        
        intent_analysis = state.get("intent_analysis")
        if intent_analysis and intent_analysis.intents:
            primary_intent = intent_analysis.intents[intent_analysis.primary_intent_index]
            patterns["intent_confidence"] = primary_intent.confidence
        
        return patterns
    
    def _generate_context_memory_insights(self, memories: List[MemoryItem]) -> Dict[str, Any]:
        """Generate insights from context memories for better understanding"""
        if not memories:
            return {"total_memories": 0, "insights": []}
        
        insights = {
            "total_memories": len(memories),
            "memory_types": {},
            "importance_distribution": {},
            "frequent_tags": {},
            "time_range": {},
            "insights": []
        }
        
        # Analyze memory distribution
        for memory in memories:
            # Memory type distribution
            mem_type = memory.memory_type.value
            insights["memory_types"][mem_type] = insights["memory_types"].get(mem_type, 0) + 1
            
            # Importance distribution
            importance = memory.importance.value
            insights["importance_distribution"][importance] = insights["importance_distribution"].get(importance, 0) + 1
            
            # Tag frequency
            for tag in memory.context_tags:
                insights["frequent_tags"][tag] = insights["frequent_tags"].get(tag, 0) + 1
        
        # Time range analysis
        if memories:
            timestamps = [mem.timestamp for mem in memories]
            insights["time_range"] = {
                "earliest": min(timestamps).isoformat(),
                "latest": max(timestamps).isoformat(),
                "span_days": (max(timestamps) - min(timestamps)).days
            }
        
        # Generate textual insights
        insight_texts = []
        
        if insights["memory_types"]:
            dominant_type = max(insights["memory_types"], key=insights["memory_types"].get)
            insight_texts.append(f"Primarily {dominant_type} memories")
        
        if insights["importance_distribution"]:
            high_importance = insights["importance_distribution"].get("high", 0) + insights["importance_distribution"].get("critical", 0)
            if high_importance > len(memories) * 0.3:
                insight_texts.append("Contains significant high-importance memories")
        
        if insights["frequent_tags"]:
            top_tag = max(insights["frequent_tags"], key=insights["frequent_tags"].get)
            insight_texts.append(f"Frequently discusses {top_tag}")
        
        insights["insights"] = insight_texts
        return insights
    
    def _memory_manager_agent(
        self,
        state: AdvancedChatState,
        config: RunnableConfig
    ) -> AdvancedChatState:
        """Enhanced memory manager with intent-aware storage"""
        
        user_id = state.get("user_id")
        intent_analysis = state.get("intent_analysis")
        user_message = state["messages"][-2].content if len(state["messages"]) >= 2 else ""
        ai_response = state["messages"][-1].content if state["messages"] else ""
        
        try:
            user_key = f"user_{user_id}"
            
            # Initialize user memories if not exists
            if user_key not in self.user_memories:
                self.user_memories[user_key] = []
            
            # Store intent-specific memories
            if intent_analysis and intent_analysis.intents:
                primary_intent = intent_analysis.intents[intent_analysis.primary_intent_index]
                
                # Store successful interaction patterns
                interaction_memory = {
                    "data": f"User query: {user_message[:100]}... Intent: {primary_intent.primary_intent}, Confidence: {primary_intent.confidence}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "context": "interaction_pattern",
                    "intent": primary_intent.primary_intent,
                    "success_score": state.get("response_metadata", {}).get("confidence", 0),
                    "routing_path": state.get("routing_history", [])
                }
                self.user_memories[user_key].append(interaction_memory)
                
                # Store important user information
                if any(keyword in user_message.lower() for keyword in ["remember", "my pet", "important"]):
                    important_memory = {
                        "data": f"Important: {user_message}",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "context": "user_preference",
                        "importance": min(primary_intent.urgency + 0.3, 1.0)
                    }
                    self.user_memories[user_key].append(important_memory)
                
                # Keep only last 50 memories per user
                self.user_memories[user_key] = self.user_memories[user_key][-50:]
            
            current_app.logger.info(f"Enhanced memories stored for user {user_id}")
            
        except Exception as e:
            current_app.logger.error(f"Memory management failed: {str(e)}")
        
        return {
            **state,
            "routing_history": state.get("routing_history", []) + ["memory_manager"]
        }
    
    async def process_message_streaming(
        self, 
        user_id: int, 
        message: str, 
        thread_id: Optional[str] = None
    ) -> AsyncGenerator[StreamingChunk, None]:
        """Process message with streaming response generation"""
        try:
            current_app.logger.info(f"Processing streaming message for user {user_id}")
            
            # Stream the response generation
            async for chunk in self.stream_response_generation(user_id, message, thread_id):
                yield chunk
            
            # Schedule background tasks
            await self.schedule_background_task("memory_consolidation", {}, user_id)
            
            # Process agent messages
            await self.process_agent_messages()
            
        except Exception as e:
            current_app.logger.error(f"Streaming message processing failed: {str(e)}")
            yield StreamingChunk(
                content=f"I apologize, but I encountered an error: {str(e)}",
                chunk_type="text",
                source_attribution={"error": True}
            )
    
    def process_message(
        self, 
        user_id: int, 
        message: str, 
        thread_id: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """Process message through advanced LangGraph with conditional routing"""
        
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
            "routing_history": []
        }
        
        try:
            # Run through advanced agent pipeline
            final_state = None
            for chunk in self.graph.stream(initial_state, config, stream_mode="values"):
                final_state = chunk
            
            if final_state and final_state["messages"]:
                ai_response = final_state["messages"][-1].content
                
                # Prepare enhanced context info
                context_info = {
                    "thread_id": thread_id,
                    "sources": final_state.get("sources_used", []),
                    "intent_analysis": final_state.get("intent_analysis"),
                    "response_metadata": final_state.get("response_metadata", {}),
                    "routing_path": final_state.get("routing_history", []),
                    "specialists_used": final_state.get("response_metadata", {}).get("specialists_used", []),
                    "context_quality": final_state.get("user_context", {}).get("context_quality_score", 0),
                    "documents_referenced": len([s for s in final_state.get("sources_used", []) if s.get("type") == "document"]),
                    "care_records_referenced": len([s for s in final_state.get("sources_used", []) if s.get("type") == "care_record"])
                }
                
                return ai_response, context_info
            else:
                return "I apologize, but I couldn't process your message. Please try again.", {}
                
        except Exception as e:
            current_app.logger.error(f"Advanced LangGraph processing failed: {str(e)}")
            return f"I encountered an error: {str(e)}", {}
    
    def get_conversation_history(self, thread_id: str) -> List[Dict[str, Any]]:
        """Get conversation history with enhanced metadata"""
        try:
            config = {"configurable": {"thread_id": thread_id}}
            state = self.graph.get_state(config)
            
            if state and state.values.get("messages"):
                return [
                    {
                        "type": "user" if isinstance(msg, HumanMessage) else "ai",
                        "content": msg.content,
                        "timestamp": getattr(msg, 'timestamp', datetime.now(timezone.utc).isoformat()),
                        "metadata": getattr(msg, 'metadata', {})
                    }
                    for msg in state.values["messages"]
                ]
            return []
            
        except Exception as e:
            current_app.logger.error(f"Error getting conversation history: {str(e)}")
            return [] 
    
    # 🛡️ RELIABILITY & ERROR HANDLING SYSTEMS
    
    def _setup_circuit_breakers(self):
        """Set up circuit breakers for external service calls"""
        services = ["openai_api", "database", "vector_store", "care_service", "document_processor"]
        
        for service in services:
            self.circuit_breakers[service] = CircuitBreakerState(
                service_name=service,
                failure_threshold=5,
                timeout_duration=60.0
            )
        
        # Set up retry strategies
        self.retry_strategies = {
            "openai_api": {"max_retries": 3, "backoff_factor": 2.0, "max_wait": 30},
            "database": {"max_retries": 2, "backoff_factor": 1.5, "max_wait": 10},
            "vector_store": {"max_retries": 3, "backoff_factor": 2.0, "max_wait": 20}
        }
    
    def _setup_health_monitoring(self):
        """Set up system health monitoring"""
        components = [
            "intent_analyzer", "context_builder", "tool_system", "memory_system",
            "agent_system", "search_system", "response_generator"
        ]
        
        for component in components:
            self.system_health_monitors[component] = SystemHealth(
                component=component,
                status="healthy",
                response_time=0.0,
                error_rate=0.0
            )
    
    def _setup_data_quality_checks(self):
        """Set up data quality validation"""
        data_sources = ["user_messages", "care_records", "documents", "memories", "tool_results"]
        
        for source in data_sources:
            self.data_quality_checks[source] = DataQualityCheck(
                data_source=source,
                quality_score=1.0,
                freshness_score=1.0,
                reliability_score=1.0,
                validation_passed=True
            )
    
    async def call_with_circuit_breaker(self, service_name: str, operation: Callable, *args, **kwargs):
        """Call external service with circuit breaker protection"""
        try:
            breaker = self.circuit_breakers.get(service_name)
            if not breaker:
                return await operation(*args, **kwargs)
            
            # Check circuit breaker state
            if breaker.state == "open":
                time_since_failure = (datetime.now(timezone.utc) - breaker.last_failure_time).total_seconds()
                if time_since_failure < breaker.timeout_duration:
                    raise Exception(f"Circuit breaker {service_name} is OPEN")
                else:
                    breaker.state = "half_open"
            
            # Execute operation with retry
            result = await self._execute_with_retry(service_name, operation, *args, **kwargs)
            
            # Success - close circuit if needed
            if breaker.state == "half_open":
                breaker.state = "closed"
                breaker.failure_count = 0
                breaker.success_count += 1
            
            return result
            
        except Exception as e:
            # Failure - update circuit breaker
            if breaker:
                breaker.failure_count += 1
                breaker.last_failure_time = datetime.now(timezone.utc)
                
                if breaker.failure_count >= breaker.failure_threshold:
                    breaker.state = "open"
            
            # Attempt graceful degradation
            return await self._graceful_degradation(service_name, e, *args, **kwargs)
    
    async def _execute_with_retry(self, service_name: str, operation: Callable, *args, **kwargs):
        """Execute operation with exponential backoff retry"""
        retry_config = self.retry_strategies.get(service_name, {"max_retries": 1, "backoff_factor": 1.0, "max_wait": 5})
        
        last_exception = None
        
        for attempt in range(retry_config["max_retries"]):
            try:
                return await operation(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                
                if attempt < retry_config["max_retries"] - 1:
                    wait_time = min(
                        retry_config["backoff_factor"] ** attempt,
                        retry_config["max_wait"]
                    )
                    await asyncio.sleep(wait_time)
                    current_app.logger.warning(f"Retry {attempt + 1} for {service_name} after {wait_time}s: {str(e)}")
                else:
                    current_app.logger.error(f"Final retry failed for {service_name}: {str(e)}")
        
        raise last_exception
    
    async def _graceful_degradation(self, service_name: str, error: Exception, *args, **kwargs):
        """Provide graceful degradation when services fail"""
        current_app.logger.error(f"Graceful degradation activated for {service_name}: {str(error)}")
        
        degradation_responses = {
            "openai_api": "I'm experiencing connectivity issues. Let me provide a basic response based on available information.",
            "database": "There's a temporary database issue. I can provide general guidance while the system recovers.",
            "vector_store": "Memory search is temporarily unavailable. I'll help based on the current conversation.",
            "care_service": "Care record access is limited right now. I can provide general pet care advice.",
            "document_processor": "Document analysis is temporarily unavailable. Please try uploading again later."
        }
        
        return degradation_responses.get(service_name, "I'm experiencing technical difficulties but I'll do my best to help.")
    
    def monitor_system_health(self, component: str, response_time: float, success: bool):
        """Monitor and update system health metrics"""
        if component not in self.system_health_monitors:
            return
        
        health = self.system_health_monitors[component]
        
        # Update response time (rolling average)
        if health.response_time == 0.0:
            health.response_time = response_time
        else:
            health.response_time = (health.response_time * 0.8) + (response_time * 0.2)
        
        # Update error rate
        if not success:
            health.error_rate = min(1.0, health.error_rate + 0.1)
        else:
            health.error_rate = max(0.0, health.error_rate - 0.02)
        
        # Determine status
        if health.error_rate > 0.5 or health.response_time > 10.0:
            health.status = "critical"
            health.alerts_triggered.append(f"High error rate or slow response at {datetime.now(timezone.utc)}")
        elif health.error_rate > 0.2 or health.response_time > 5.0:
            health.status = "degraded"
        else:
            health.status = "healthy"
        
        health.last_check = datetime.now(timezone.utc)
    
    def validate_data_quality(self, data_source: str, data: Any) -> DataQualityCheck:
        """Validate data quality and update metrics"""
        try:
            quality_check = DataQualityCheck(
                data_source=data_source,
                quality_score=1.0,
                freshness_score=1.0,
                reliability_score=1.0,
                validation_passed=True,
                issues_found=[]
            )
            
            # Basic validation checks
            if data is None:
                quality_check.issues_found.append("Data is None")
                quality_check.validation_passed = False
                quality_check.quality_score = 0.0
            
            elif isinstance(data, str):
                if len(data.strip()) == 0:
                    quality_check.issues_found.append("Empty string data")
                    quality_check.quality_score = 0.0
                elif len(data) < 10:
                    quality_check.issues_found.append("Data too short")
                    quality_check.quality_score = 0.5
                
                # Check for suspicious content
                suspicious_patterns = ["error", "null", "undefined", "exception"]
                if any(pattern in data.lower() for pattern in suspicious_patterns):
                    quality_check.issues_found.append("Suspicious content detected")
                    quality_check.reliability_score = 0.7
            
            elif isinstance(data, (list, dict)):
                if len(data) == 0:
                    quality_check.issues_found.append("Empty collection")
                    quality_check.quality_score = 0.0
            
            # Calculate overall quality
            if quality_check.issues_found:
                quality_check.quality_score = max(0.0, quality_check.quality_score - (len(quality_check.issues_found) * 0.2))
                quality_check.validation_passed = quality_check.quality_score > 0.5
            
            # Store quality check
            self.data_quality_checks[data_source] = quality_check
            
            return quality_check
            
        except Exception as e:
            current_app.logger.error(f"Data quality validation failed for {data_source}: {str(e)}")
            return DataQualityCheck(
                data_source=data_source,
                quality_score=0.0,
                freshness_score=0.0,
                reliability_score=0.0,
                validation_passed=False,
                issues_found=[f"Validation error: {str(e)}"]
            )
    
    # 🔮 ADVANCED AI CAPABILITIES
    
    def _setup_goal_planning(self):
        """Set up goal-oriented conversation planning"""
        self.goal_templates = {
            "information_gathering": {
                "sub_goals": ["identify_need", "gather_context", "search_sources", "synthesize_answer"],
                "estimated_turns": 3
            },
            "problem_solving": {
                "sub_goals": ["understand_problem", "analyze_causes", "explore_solutions", "recommend_action"],
                "estimated_turns": 5
            },
            "care_planning": {
                "sub_goals": ["assess_current_state", "identify_goals", "create_plan", "set_reminders"],
                "estimated_turns": 7
            },
            "monitoring": {
                "sub_goals": ["baseline_assessment", "track_progress", "adjust_plan", "report_status"],
                "estimated_turns": 4
            }
        }
    
    def _setup_proactive_assistance(self):
        """Set up proactive assistance engine"""
        self.proactive_patterns = {
            "vaccination_due": {
                "trigger": "last_vaccination > 11 months",
                "recommendation": "Annual vaccination reminder",
                "urgency": "medium"
            },
            "health_concern": {
                "trigger": "symptoms mentioned",
                "recommendation": "Consider veterinary consultation",
                "urgency": "high"
            },
            "nutrition_optimization": {
                "trigger": "age milestone reached",
                "recommendation": "Diet adjustment for life stage",
                "urgency": "low"
            }
        }
    
    def _setup_multi_agent_reasoning(self):
        """Set up multi-agent reasoning and debate system"""
        self.debate_topics = [
            "treatment_options", "nutrition_plans", "behavior_strategies", 
            "emergency_protocols", "long_term_care"
        ]
    
    def create_conversation_goal(self, user_id: int, goal_type: str, description: str) -> ConversationGoal:
        """Create and track conversation goal"""
        try:
            template = self.goal_templates.get(goal_type, {"sub_goals": [], "estimated_turns": 3})
            
            goal = ConversationGoal(
                goal_id=str(uuid.uuid4()),
                user_id=user_id,
                goal_description=description,
                goal_type=goal_type,
                sub_goals=template["sub_goals"].copy(),
                estimated_turns=template["estimated_turns"]
            )
            
            self.conversation_goals[user_id].append(goal)
            current_app.logger.info(f"Created conversation goal {goal.goal_id} for user {user_id}")
            
            return goal
            
        except Exception as e:
            current_app.logger.error(f"Goal creation failed: {str(e)}")
            return None
    
    def update_goal_progress(self, user_id: int, goal_id: str, progress_delta: float):
        """Update progress on conversation goal"""
        try:
            for goal in self.conversation_goals[user_id]:
                if goal.goal_id == goal_id:
                    goal.progress = min(1.0, goal.progress + progress_delta)
                    goal.actual_turns += 1
                    
                    if goal.progress >= 1.0:
                        goal.status = "completed"
                    
                    current_app.logger.info(f"Updated goal {goal_id} progress to {goal.progress}")
                    break
                    
        except Exception as e:
            current_app.logger.error(f"Goal progress update failed: {str(e)}")
    
    async def generate_proactive_recommendations(self, user_id: int, context: Dict[str, Any]) -> List[ProactiveRecommendation]:
        """Generate proactive recommendations based on user context"""
        try:
            recommendations = []
            
            # Check for vaccination reminders
            if "last_vaccination" in context:
                last_vax = context["last_vaccination"]
                # Simple date check (would be more sophisticated in practice)
                if "months" in str(last_vax) and "11" in str(last_vax):
                    rec = ProactiveRecommendation(
                        recommendation_id=str(uuid.uuid4()),
                        user_id=user_id,
                        recommendation_type="reminder",
                        content="Your pet's annual vaccination may be due soon. Consider scheduling a vet appointment.",
                        confidence=0.8,
                        urgency="medium",
                        context={"trigger": "vaccination_due", "last_vaccination": last_vax}
                    )
                    recommendations.append(rec)
            
            # Check for health concerns
            if "symptoms" in context and context["symptoms"]:
                rec = ProactiveRecommendation(
                    recommendation_id=str(uuid.uuid4()),
                    user_id=user_id,
                    recommendation_type="suggestion",
                    content="I noticed you mentioned some symptoms. It might be worth monitoring these closely or consulting your veterinarian.",
                    confidence=0.9,
                    urgency="high",
                    context={"trigger": "health_concern", "symptoms": context["symptoms"]}
                )
                recommendations.append(rec)
            
            # Check for seasonal recommendations
            current_month = datetime.now().month
            if current_month in [6, 7, 8]:  # Summer months
                rec = ProactiveRecommendation(
                    recommendation_id=str(uuid.uuid4()),
                    user_id=user_id,
                    recommendation_type="insight",
                    content="Summer tip: Make sure your pet has access to fresh water and shade during hot weather.",
                    confidence=0.7,
                    urgency="low",
                    context={"trigger": "seasonal", "season": "summer"},
                    expires_at=datetime.now(timezone.utc) + timedelta(days=30)
                )
                recommendations.append(rec)
            
            # Store recommendations
            for rec in recommendations:
                self.proactive_engine[rec.recommendation_id] = rec
            
            return recommendations
            
        except Exception as e:
            current_app.logger.error(f"Proactive recommendation generation failed: {str(e)}")
            return []
    
    async def initiate_agent_debate(self, topic: str, context: Dict[str, Any], participating_agents: List[str] = None) -> AgentDebate:
        """Initiate multi-agent debate for complex decisions"""
        try:
            if not participating_agents:
                participating_agents = ["medical_specialist", "nutrition_specialist", "behavior_specialist"]
            
            debate = AgentDebate(
                debate_id=str(uuid.uuid4()),
                topic=topic,
                participating_agents=participating_agents
            )
            
            # Generate initial arguments from each agent
            for agent_id in participating_agents:
                argument = await self._generate_agent_argument(agent_id, topic, context)
                if argument:
                    if agent_id not in debate.arguments:
                        debate.arguments[agent_id] = []
                    debate.arguments[agent_id].append(argument)
                    debate.confidence_scores[agent_id] = 0.8  # Initial confidence
            
            # Store debate
            self.agent_debates[debate.debate_id] = debate
            
            current_app.logger.info(f"Initiated agent debate {debate.debate_id} on topic: {topic}")
            
            return debate
            
        except Exception as e:
            current_app.logger.error(f"Agent debate initiation failed: {str(e)}")
            return None
    
    async def _generate_agent_argument(self, agent_id: str, topic: str, context: Dict[str, Any]) -> str:
        """Generate argument from specific agent perspective"""
        try:
            capability = self.agent_registry.get(agent_id)
            if not capability:
                return None
            
            expertise = capability.expertise_area.value
            
            argument_templates = {
                "medical": f"From a medical perspective on {topic}, we should consider health implications and safety protocols.",
                "nutrition": f"Regarding {topic}, nutritional factors and dietary impacts are crucial considerations.",
                "behavior": f"From a behavioral standpoint, {topic} involves training aspects and psychological well-being.",
                "emergency": f"In terms of emergency preparedness for {topic}, immediate response protocols are essential."
            }
            
            argument = argument_templates.get(expertise, f"Considering {topic} from {expertise} perspective.")
            
            # Add context-specific details
            if "symptoms" in context:
                argument += f" Given the mentioned symptoms: {context['symptoms']}, this adds urgency to the consideration."
            
            return argument
            
        except Exception as e:
            current_app.logger.error(f"Agent argument generation failed for {agent_id}: {str(e)}")
            return None
    
    async def resolve_agent_debate(self, debate_id: str) -> Dict[str, Any]:
        """Resolve agent debate and reach consensus"""
        try:
            debate = self.agent_debates.get(debate_id)
            if not debate:
                return {"error": "Debate not found"}
            
            # Simple consensus mechanism - weighted by confidence scores
            total_confidence = sum(debate.confidence_scores.values())
            
            if total_confidence > 0:
                # Calculate weighted decision based on agent confidence
                decisions = {}
                for agent_id, confidence in debate.confidence_scores.items():
                    weight = confidence / total_confidence
                    agent_arguments = debate.arguments.get(agent_id, [])
                    if agent_arguments:
                        decisions[agent_id] = {"weight": weight, "argument": agent_arguments[-1]}
                
                # Generate final decision
                if len(decisions) >= 2:
                    debate.consensus_reached = True
                    debate.final_decision = f"Based on multi-agent analysis: {list(decisions.keys())} reached consensus."
                    debate.confidence_score = total_confidence / len(debate.confidence_scores)
                
                current_app.logger.info(f"Resolved debate {debate_id} with consensus: {debate.consensus_reached}")
                
                return {
                    "consensus_reached": debate.consensus_reached,
                    "final_decision": debate.final_decision,
                    "confidence_score": debate.confidence_score,
                    "participating_agents": debate.participating_agents
                }
            
            return {"error": "Insufficient confidence for consensus"}
            
        except Exception as e:
            current_app.logger.error(f"Debate resolution failed for {debate_id}: {str(e)}")
            return {"error": str(e)}
    
    def predict_user_needs(self, user_id: int, current_context: Dict[str, Any]) -> Dict[str, Any]:
        """Predict user needs based on patterns and context"""
        try:
            predictions = {
                "likely_next_questions": [],
                "recommended_actions": [],
                "potential_concerns": []
            }
            
            # Analyze user history patterns
            user_feedback = self.feedback_history.get(user_id, [])
            recent_feedback = user_feedback[-5:] if user_feedback else []
            
            # Pattern recognition
            if any("vaccination" in f.feedback_text.lower() for f in recent_feedback if f.feedback_text):
                predictions["likely_next_questions"].append("When is the next vaccination due?")
                predictions["recommended_actions"].append("Check vaccination schedule")
            
            if any("behavior" in f.feedback_text.lower() for f in recent_feedback if f.feedback_text):
                predictions["likely_next_questions"].append("How can I improve my pet's behavior?")
                predictions["recommended_actions"].append("Consider training resources")
            
            # Context-based predictions
            if "age" in current_context:
                age = current_context["age"]
                if isinstance(age, (int, float)) and age > 7:
                    predictions["potential_concerns"].append("Senior pet care considerations")
                    predictions["recommended_actions"].append("Schedule senior wellness check")
            
            return predictions
            
        except Exception as e:
            current_app.logger.error(f"User needs prediction failed: {str(e)}")
            return {"likely_next_questions": [], "recommended_actions": [], "potential_concerns": []}