"""
Context7 Semantic Enhancement Service

This service implements Context7 patterns for semantic understanding,
content scoring, emotional resonance analysis, and knowledge enhancement.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import numpy as np
from flask import current_app

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class ContentType(Enum):
    """Content type categories for Context7 analysis"""
    HEALTH_QUERY = "health_query"
    CARE_INSTRUCTION = "care_instruction"
    EMOTIONAL_BOND = "emotional_bond"
    TRAINING_ADVICE = "training_advice"
    EMERGENCY_SITUATION = "emergency_situation"
    GENERAL_QUESTION = "general_question"
    DOCUMENT_REQUEST = "document_request"
    REMINDER_REQUEST = "reminder_request"

class SemanticRelevanceLevel(Enum):
    """Semantic relevance levels for content scoring"""
    CRITICAL = "critical"      # 0.9-1.0
    HIGH = "high"              # 0.7-0.89
    MEDIUM = "medium"          # 0.5-0.69
    LOW = "low"                # 0.3-0.49
    MINIMAL = "minimal"        # 0.0-0.29

@dataclass
class SemanticAnalysis:
    """Context7 semantic analysis result"""
    content_type: ContentType
    relevance_score: float
    emotional_resonance: float
    urgency_level: int  # 1-5 scale
    key_concepts: List[str]
    semantic_tags: List[str]
    context_requirements: List[str]
    enhancement_suggestions: List[str]
    confidence_score: float

class Context7SemanticService:
    """Context7 semantic enhancement and analysis service"""
    
    def __init__(self):
        self.chat_model = ChatOpenAI(
            model="gpt-4",
            temperature=0.1,
            max_tokens=2000
        )
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
        
        # Context7 semantic patterns
        self.semantic_patterns = self._initialize_semantic_patterns()
        self.relevance_thresholds = self._initialize_relevance_thresholds()
        
    def _initialize_semantic_patterns(self) -> Dict[str, List[str]]:
        """Initialize Context7 semantic patterns for different content types"""
        return {
            "health_patterns": [
                "symptoms", "medication", "veterinarian", "illness", "treatment",
                "diagnosis", "pain", "injury", "vaccination", "wellness check"
            ],
            "emotional_patterns": [
                "love", "bond", "connection", "comfort", "joy", "worry", 
                "fear", "happiness", "companionship", "trust"
            ],
            "training_patterns": [
                "training", "behavior", "command", "teach", "learn", 
                "obedience", "discipline", "trick", "reward", "reinforce"
            ],
            "emergency_patterns": [
                "emergency", "urgent", "immediately", "critical", "danger",
                "poisoned", "bleeding", "choking", "breathing", "collapse"
            ],
            "nutrition_patterns": [
                "food", "diet", "feeding", "nutrition", "eat", "meal",
                "treats", "water", "weight", "appetite"
            ],
            "care_patterns": [
                "grooming", "bath", "nail", "fur", "coat", "brush",
                "clean", "hygiene", "care", "maintenance"
            ],
            "document_patterns": [
                "document", "pdf", "file", "upload", "uploaded", "summarize", 
                "summary", "extract", "analyze document", "document content",
                "what's in the document", "what does the document say", 
                "read the document", "tell me about the document", 
                "explain the document", "document analysis", "document summary",
                "information in the document", "content of the document",
                "document extraction", "document understanding", "document insights",
                "document overview", "document review", "document interpretation",
                "document key points", "document highlights", "document findings"
            ],
            "reminder_patterns": [
                "remind", "reminder", "schedule", "appointment", "remember",
                "notification", "alert", "upcoming", "calendar", "event"
            ],
            "image_patterns": [
                "image", "picture", "photo", "see", "look", "visual",
                "camera", "snapshot", "photograph", "gallery"
            ],
            "voice_patterns": [
                "voice", "audio", "recording", "sound", "speak", "listen",
                "message", "hear", "speech", "conversation"
            ]
        }
    
    def _initialize_relevance_thresholds(self) -> Dict[str, float]:
        """Initialize Context7 relevance scoring thresholds"""
        return {
            "critical_threshold": 0.9,
            "high_threshold": 0.7,
            "medium_threshold": 0.5,
            "low_threshold": 0.3,
            "semantic_similarity_weight": 0.4,
            "emotional_resonance_weight": 0.3,
            "context_alignment_weight": 0.3
        }
    
    def analyze_content_semantics(
        self, 
        content: str, 
        context_history: Optional[List[Dict[str, Any]]] = None,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> SemanticAnalysis:
        """
        Perform comprehensive Context7 semantic analysis on content
        
        Args:
            content: The content to analyze
            context_history: Previous conversation context
            user_profile: User's profile and preferences
            
        Returns:
            SemanticAnalysis with complete Context7 assessment
        """
        try:
            current_app.logger.info(f"🧠 Context7 semantic analysis for content: {content[:100]}...")
            
            # 1. Content type classification
            content_type = self._classify_content_type(content)
            
            # 2. Semantic relevance scoring
            relevance_score = self._calculate_semantic_relevance(content, content_type)
            
            # 3. Emotional resonance analysis
            emotional_resonance = self._analyze_emotional_resonance(content)
            
            # 4. Urgency level assessment
            urgency_level = self._assess_urgency_level(content, content_type)
            
            # 5. Key concept extraction
            key_concepts = self._extract_key_concepts(content)
            
            # 6. Semantic tag generation
            semantic_tags = self._generate_semantic_tags(content, content_type)
            
            # 7. Context requirements analysis
            context_requirements = self._analyze_context_requirements(content, context_history)
            
            # 8. Enhancement suggestions
            enhancement_suggestions = self._generate_enhancement_suggestions(
                content, content_type, relevance_score
            )
            
            # 9. Overall confidence calculation
            confidence_score = self._calculate_confidence_score(
                relevance_score, emotional_resonance, len(key_concepts)
            )
            
            analysis = SemanticAnalysis(
                content_type=content_type,
                relevance_score=relevance_score,
                emotional_resonance=emotional_resonance,
                urgency_level=urgency_level,
                key_concepts=key_concepts,
                semantic_tags=semantic_tags,
                context_requirements=context_requirements,
                enhancement_suggestions=enhancement_suggestions,
                confidence_score=confidence_score
            )
            
            current_app.logger.info(f"✅ Context7 analysis complete: {content_type.value}, score: {relevance_score:.3f}")
            return analysis
            
        except Exception as e:
            current_app.logger.error(f"❌ Context7 semantic analysis failed: {str(e)}")
            # Return default analysis
            return SemanticAnalysis(
                content_type=ContentType.GENERAL_QUESTION,
                relevance_score=0.5,
                emotional_resonance=0.5,
                urgency_level=2,
                key_concepts=[],
                semantic_tags=[],
                context_requirements=[],
                enhancement_suggestions=[],
                confidence_score=0.3
            )
    
    def _classify_content_type(self, content: str) -> ContentType:
        """Classify content type based on semantic patterns and keywords"""
        content_lower = content.lower()
        
        # Check for emergency keywords first (highest priority)
        emergency_keywords = ["emergency", "urgent", "help", "immediately", "dying", "severe", "critical"]
        if any(keyword in content_lower for keyword in emergency_keywords):
            for pattern in self.semantic_patterns["emergency_patterns"]:
                if pattern in content_lower:
                    return ContentType.EMERGENCY_SITUATION
        
        # IMPROVED: Check for document requests (highest priority after emergencies)
        document_keywords = ["document", "pdf", "file", "summarize", "summary", "uploaded"]
        
        # Strong document request indicators - if these are present, it's definitely a document request
        strong_doc_indicators = ["summarize this document", "document summary", "summarize the pdf", 
                              "summarize the file", "summarize this pdf", "summarize this file",
                              "what's in this document", "what does this document say"]
                              
        for indicator in strong_doc_indicators:
            if indicator in content_lower:
                current_app.logger.info(f"📄 Strong document request detected: '{indicator}' in '{content}'")
                return ContentType.DOCUMENT_REQUEST
        
        # Check for document keywords
        if any(keyword in content_lower for keyword in document_keywords):
            # Count document patterns for confidence
            doc_pattern_count = sum(1 for pattern in self.semantic_patterns["document_patterns"] if pattern in content_lower)
            
            # If we have multiple document patterns, it's a document request
            if doc_pattern_count >= 2:
                current_app.logger.info(f"📄 Document request detected with {doc_pattern_count} patterns")
                return ContentType.DOCUMENT_REQUEST
            
            # Additional document-related phrases
            document_phrases = [
                "what's in", "what is in", "tell me about", "explain", "analyze",
                "extract from", "information in", "content of", "read", "understand"
            ]
            
            # If we have both a document keyword and a document phrase, it's a document request
            if any(phrase in content_lower for phrase in document_phrases) and \
               any(doc_word in content_lower for doc_word in ["document", "pdf", "file", "upload"]):
                current_app.logger.info(f"📄 Document request detected with keyword and phrase")
                return ContentType.DOCUMENT_REQUEST
        
        # Check for reminder requests (high priority)
        reminder_keywords = ["remind", "reminder", "schedule", "appointment"]
        if any(keyword in content_lower for keyword in reminder_keywords):
            for pattern in self.semantic_patterns["reminder_patterns"]:
                if pattern in content_lower:
                    return ContentType.REMINDER_REQUEST
        
        # Check for health queries
        health_count = sum(1 for pattern in self.semantic_patterns["health_patterns"] if pattern in content_lower)
        if health_count >= 2:
            return ContentType.HEALTH_QUERY
        
        # Check for care instructions
        care_count = sum(1 for pattern in self.semantic_patterns["care_patterns"] if pattern in content_lower)
        if care_count >= 2:
            return ContentType.CARE_INSTRUCTION
        
        # Check for training advice
        training_count = sum(1 for pattern in self.semantic_patterns["training_patterns"] if pattern in content_lower)
        if training_count >= 2:
            return ContentType.TRAINING_ADVICE
        
        # Check for emotional bond content
        emotional_count = sum(1 for pattern in self.semantic_patterns["emotional_patterns"] if pattern in content_lower)
        if emotional_count >= 2:
            return ContentType.EMOTIONAL_BOND
        
        # Default to general question
        return ContentType.GENERAL_QUESTION
    
    def _calculate_semantic_relevance(self, content: str, content_type: ContentType) -> float:
        """Calculate semantic relevance score using Context7 patterns"""
        try:
            # Base score from content type
            type_scores = {
                ContentType.EMERGENCY_SITUATION: 0.95,
                ContentType.REMINDER_REQUEST: 0.90,
                ContentType.HEALTH_QUERY: 0.85,
                ContentType.CARE_INSTRUCTION: 0.80,
                ContentType.TRAINING_ADVICE: 0.75,
                ContentType.EMOTIONAL_BOND: 0.70,
                ContentType.DOCUMENT_REQUEST: 0.65,
                ContentType.GENERAL_QUESTION: 0.50
            }
            
            base_score = type_scores.get(content_type, 0.50)
            
            # Adjust based on content complexity and specificity
            content_length = len(content.split())
            if content_length > 20:  # Detailed query
                base_score += 0.1
            elif content_length < 5:  # Very short query
                base_score -= 0.1
            
            # Check for specific indicators
            specific_indicators = ["specific", "detailed", "urgent", "immediate", "help"]
            if any(indicator in content.lower() for indicator in specific_indicators):
                base_score += 0.05
            
            return min(1.0, max(0.0, base_score))
            
        except Exception as e:
            current_app.logger.error(f"Semantic relevance calculation failed: {str(e)}")
            return 0.5
    
    def _analyze_emotional_resonance(self, content: str) -> float:
        """Analyze emotional resonance using Context7 emotional patterns"""
        try:
            emotional_words = ["love", "worried", "scared", "happy", "sad", "anxious", 
                             "concerned", "excited", "frustrated", "grateful", "hopeful"]
            
            content_lower = content.lower()
            emotional_matches = [word for word in emotional_words if word in content_lower]
            
            # Base emotional score
            if not emotional_matches:
                return 0.3
            
            # Calculate emotional intensity
            intensity_words = ["very", "extremely", "really", "so", "deeply", "incredibly"]
            intensity_multiplier = 1.0
            if any(word in content_lower for word in intensity_words):
                intensity_multiplier = 1.3
            
            # Emotional complexity bonus
            complexity_bonus = min(0.2, len(emotional_matches) * 0.05)
            
            base_score = min(len(emotional_matches) * 0.2, 0.8)
            final_score = (base_score + complexity_bonus) * intensity_multiplier
            
            return min(1.0, final_score)
            
        except Exception as e:
            current_app.logger.error(f"Emotional resonance analysis failed: {str(e)}")
            return 0.5
    
    def _assess_urgency_level(self, content: str, content_type: ContentType) -> int:
        """Assess urgency level (1-5 scale) using Context7 patterns"""
        content_lower = content.lower()
        
        # Emergency indicators
        if content_type == ContentType.EMERGENCY_SITUATION:
            return 5
        
        urgent_words = ["urgent", "emergency", "immediate", "asap", "critical", "serious"]
        if any(word in content_lower for word in urgent_words):
            return 4
        
        # Health-related urgency
        if content_type == ContentType.HEALTH_QUERY:
            concern_words = ["pain", "bleeding", "vomiting", "difficulty", "won't eat"]
            if any(word in content_lower for word in concern_words):
                return 3
        
        # Time-sensitive requests
        time_words = ["today", "now", "quickly", "soon"]
        if any(word in content_lower for word in time_words):
            return 3
        
        # Default urgency levels by content type
        type_urgency = {
            ContentType.HEALTH_QUERY: 3,
            ContentType.REMINDER_REQUEST: 3,
            ContentType.CARE_INSTRUCTION: 2,
            ContentType.TRAINING_ADVICE: 2,
            ContentType.EMOTIONAL_BOND: 1,
            ContentType.DOCUMENT_REQUEST: 2,
            ContentType.GENERAL_QUESTION: 1
        }
        
        return type_urgency.get(content_type, 2)
    
    def _extract_key_concepts(self, content: str) -> List[str]:
        """Extract key concepts using Context7 semantic understanding"""
        try:
            # Use AI for concept extraction
            concept_prompt = f"""
            Extract the key concepts from this pet care message. Focus on:
            1. Health conditions or symptoms
            2. Pet behaviors
            3. Care activities
            4. Specific breeds or animals mentioned
            5. Training or behavioral concepts
            6. Emotional states
            
            Message: "{content}"
            
            Return only a JSON list of key concepts (max 8 concepts).
            Example: ["dog training", "separation anxiety", "golden retriever", "behavioral modification"]
            """
            
            response = self.chat_model.invoke([
                SystemMessage(content="You are an expert at extracting key concepts from pet care content. Always return valid JSON."),
                HumanMessage(content=concept_prompt)
            ])
            
            try:
                concepts = json.loads(response.content)
                return concepts[:8] if isinstance(concepts, list) else []
            except json.JSONDecodeError:
                # Fallback to simple extraction
                return self._simple_concept_extraction(content)
                
        except Exception as e:
            current_app.logger.error(f"Key concept extraction failed: {str(e)}")
            return self._simple_concept_extraction(content)
    
    def _simple_concept_extraction(self, content: str) -> List[str]:
        """Simple fallback concept extraction"""
        words = content.lower().split()
        concepts = []
        
        # Look for important nouns and phrases
        important_words = ["dog", "cat", "pet", "training", "health", "behavior", "medication", 
                          "vet", "food", "exercise", "grooming", "puppy", "kitten"]
        
        for word in important_words:
            if word in words:
                concepts.append(word)
        
        return concepts[:5]
    
    def _generate_semantic_tags(self, content: str, content_type: ContentType) -> List[str]:
        """Generate semantic tags for content categorization"""
        tags = [content_type.value]
        content_lower = content.lower()
        
        # Add pattern-based tags
        for pattern_type, patterns in self.semantic_patterns.items():
            if any(pattern in content_lower for pattern in patterns):
                tag = pattern_type.replace("_patterns", "")
                if tag not in tags:
                    tags.append(tag)
        
        # Add urgency tags
        if "urgent" in content_lower or "emergency" in content_lower:
            tags.append("urgent")
        
        # Add emotional tags
        emotional_indicators = ["worried", "scared", "happy", "sad", "concerned"]
        if any(emotion in content_lower for emotion in emotional_indicators):
            tags.append("emotional")
        
        return tags[:6]  # Limit to 6 tags
    
    def _analyze_context_requirements(
        self, 
        content: str, 
        context_history: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """Analyze what context is needed for optimal response"""
        requirements = []
        content_lower = content.lower()
        
        # Document context indicators
        if any(word in content_lower for word in ["show", "find", "my", "previous", "last"]):
            requirements.append("user_documents")
        
        # Health context indicators
        if any(word in content_lower for word in ["health", "medical", "vet", "symptoms"]):
            requirements.append("health_records")
        
        # Chat history context indicators
        if any(word in content_lower for word in ["we discussed", "you said", "before", "earlier"]):
            requirements.append("chat_history")
        
        # Care record context indicators
        if any(word in content_lower for word in ["care", "routine", "schedule", "tracking"]):
            requirements.append("care_records")
        
        # Common knowledge indicators
        if any(word in content_lower for word in ["how to", "best way", "advice", "recommend"]):
            requirements.append("common_knowledge")
        
        return requirements
    
    def _generate_enhancement_suggestions(
        self, 
        content: str, 
        content_type: ContentType, 
        relevance_score: float
    ) -> List[str]:
        """Generate Context7 enhancement suggestions"""
        suggestions = []
        
        if relevance_score < 0.6:
            suggestions.append("Add more specific details for better assistance")
        
        if content_type == ContentType.HEALTH_QUERY:
            suggestions.append("Consider including pet's age, breed, and symptoms duration")
            suggestions.append("Mention if this is urgent or emergency situation")
        
        if content_type == ContentType.TRAINING_ADVICE:
            suggestions.append("Specify pet's age and current training level")
            suggestions.append("Include information about specific behaviors observed")
        
        if len(content.split()) < 10:
            suggestions.append("Provide more context for personalized advice")
        
        return suggestions[:3]  # Limit suggestions
    
    def _calculate_confidence_score(
        self, 
        relevance_score: float, 
        emotional_resonance: float, 
        concept_count: int
    ) -> float:
        """Calculate overall confidence score for the analysis"""
        # Weight different factors
        relevance_weight = 0.4
        emotional_weight = 0.3
        concept_weight = min(concept_count / 8.0, 1.0) * 0.3
        
        confidence = (
            relevance_score * relevance_weight +
            emotional_resonance * emotional_weight +
            concept_weight
        )
        
        return min(1.0, max(0.3, confidence))
    
    def enhance_response_with_context7(
        self,
        original_response: str,
        semantic_analysis: SemanticAnalysis,
        knowledge_sources: Dict[str, List[Any]]
    ) -> str:
        """Enhance AI response using Context7 semantic patterns"""
        try:
            enhancement_prompt = f"""
            Enhance this AI response using Context7 semantic understanding patterns:
            
            Original Response: "{original_response}"
            
            Semantic Analysis:
            - Content Type: {semantic_analysis.content_type.value}
            - Relevance Score: {semantic_analysis.relevance_score:.2f}
            - Emotional Resonance: {semantic_analysis.emotional_resonance:.2f}
            - Urgency Level: {semantic_analysis.urgency_level}/5
            - Key Concepts: {semantic_analysis.key_concepts}
            
            Available Knowledge Sources: {list(knowledge_sources.keys())}
            
            Enhancement Guidelines:
            1. Maintain the original helpfulness while adding semantic depth
            2. Reference relevant knowledge sources when appropriate
            3. Match the emotional tone to the user's resonance level
            4. Address urgency level appropriately
            5. Include key concepts naturally
            6. Add practical, actionable insights when possible
            
            Return only the enhanced response, no explanations.
            """
            
            response = self.chat_model.invoke([
                SystemMessage(content="You are an expert at enhancing AI responses with semantic understanding."),
                HumanMessage(content=enhancement_prompt)
            ])
            
            return response.content
            
        except Exception as e:
            current_app.logger.error(f"Context7 response enhancement failed: {str(e)}")
            return original_response  # Return original if enhancement fails


# Global service instance
_context7_service = None

def get_context7_service() -> Context7SemanticService:
    """Get singleton instance of Context7 semantic service"""
    global _context7_service
    if _context7_service is None:
        _context7_service = Context7SemanticService()
    return _context7_service 