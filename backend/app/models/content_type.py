from enum import Enum

class ContentType(Enum):
    """Enum for different content types detected in user messages"""
    
    GENERAL_CHAT = "general_chat"
    GENERAL_QUESTION = "general_question"
    DOCUMENT_REQUEST = "document_request"
    EMERGENCY = "emergency"
    REMINDER_REQUEST = "reminder_request"
    HEALTH_QUERY = "health_query"
    EMOTIONAL_BOND = "emotional_bond"
    TRAINING_ADVICE = "training_advice"
    CARE_INSTRUCTION = "care_instruction"

class UrgencyLevel(Enum):
    """Enum for different urgency levels"""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical" 