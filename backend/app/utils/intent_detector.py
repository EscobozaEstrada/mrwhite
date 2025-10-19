from langchain_openai import ChatOpenAI
from typing import List, Dict, Optional, Tuple
import os
from flask import current_app
import json

# Define common intents
INTENTS = {
    "QUESTION": "General question about dogs",
    "FOLLOW_UP": "Follow-up question related to previous conversation",
    "DOCUMENT_QUERY": "Question about user documents",
    "FILE_MANAGEMENT": "Request to upload, manage, or send files",
    "GREETING": "General greeting or conversation starter",
    "HELP": "Request for help with chatbot capabilities",
    "FAREWELL": "Ending the conversation",
    "FEEDBACK": "Providing feedback about the chatbot",
    "UNKNOWN": "Intent cannot be determined"
}

# Define capability suggestions for each intent
CAPABILITY_SUGGESTIONS = {
    "QUESTION": [
        "I can help with specific dog breed information",
        "Ask me about dog training techniques",
        "I can provide information about dog health and care",
        "I can recommend dog foods based on breed and age"
    ],
    "FOLLOW_UP": [
        "I can search your past conversations for context",
        "You can ask me to summarize our previous discussions",
        "I remember details from our earlier chats"
    ],
    "DOCUMENT_QUERY": [
        "Upload more documents to expand my knowledge base",
        "I can summarize your documents",
        "Ask me to compare information across multiple documents",
        "I can extract specific details from your files"
    ],
    "FILE_MANAGEMENT": [
        "I can email documents to you",
        "Upload images for me to analyze",
        "I can help organize your documents by topic"
    ],
    "GREETING": [
        "Ask me about dog care and training",
        "Upload documents for me to analyze",
        "I can answer questions about specific dog breeds"
    ],
    "HELP": [
        "I can answer questions about dogs",
        "Upload documents for me to analyze and reference",
        "I can remember our conversations for better context",
        "Ask me to email documents to you"
    ],
    "FAREWELL": [
        "Feel free to return anytime with more questions",
        "Upload documents for our next conversation",
        "I'll remember our discussion for next time"
    ],
    "FEEDBACK": [
        "I'm constantly learning to serve you better",
        "Try asking me about other dog-related topics",
        "Upload documents for more personalized assistance"
    ],
    "UNKNOWN": [
        "Ask me about dog breeds, training, or health",
        "Upload documents for me to analyze",
        "I can recall our previous conversations",
        "Ask for help to see more of my capabilities"
    ]
}

class IntentDetector:
    """Detects user intent and provides relevant capability suggestions."""
    
    def __init__(self):
        """Initialize the intent detector with the OpenAI model."""
        self.llm = ChatOpenAI(
            model=current_app.config['OPENAI_CHAT_MODEL'],
            temperature=0.2,
            api_key=os.getenv("OPENAI_API_KEY")
        )
    
    def detect_intent(self, user_message: str, conversation_history: Optional[List[Dict]] = None) -> Tuple[str, List[str]]:
        """
        Detect the intent of a user message and provide capability suggestions.
        
        Args:
            user_message: The current message from the user
            conversation_history: Optional list of previous messages in the conversation
            
        Returns:
            A tuple containing (intent_key, suggestions_list)
        """
        # Prepare the system prompt
        system_prompt = """You are an intent detection system for Mr. White, a dog-focused pet care expert.

        Your job is to analyze user messages and determine their intent. Return your response in the following JSON format:
        {
          "intent": "primary_intent_name",
          "confidence": 0.95,
          "entities": ["entity1", "entity2"],
          "context": "brief_explanation"
        }

        Possible intents:
        - general_question: General pet care questions
        - health_concern: Health-related questions or concerns
        - training_help: Training and behavior questions  
        - emergency: Urgent health situations requiring immediate attention
        - appointment: Scheduling or reminder requests
        - file_upload: User wants to upload documents or images
        - previous_context: User asking about previous conversation

        Always return valid JSON only."""
        
        # Prepare conversation context if available
        context = ""
        if conversation_history and len(conversation_history) > 0:
            # Take the last 3 messages for context
            recent_messages = conversation_history[-3:]
            context = "Previous conversation:\n"
            for msg in recent_messages:
                role = "User" if msg["type"] == "user" else "Assistant"
                context += f"{role}: {msg['content']}\n"
        
        # Construct the full prompt
        full_prompt = f"{context}\nCurrent user message: {user_message}\n\nWhat is the intent?"
        
        try:
            # Get intent prediction
            response = self.llm.with_system_prompt(system_prompt).invoke(full_prompt)
            intent_key = response.content.strip().upper()
            
            # Validate the intent key
            if intent_key not in INTENTS:
                intent_key = "UNKNOWN"
                
            # Get capability suggestions for this intent
            suggestions = CAPABILITY_SUGGESTIONS.get(intent_key, CAPABILITY_SUGGESTIONS["UNKNOWN"])
            
            # Choose 1-2 random suggestions based on the intent
            import random
            num_suggestions = min(2, len(suggestions))
            selected_suggestions = random.sample(suggestions, num_suggestions)
            
            return intent_key, selected_suggestions
            
        except Exception as e:
            print(f"Error in intent detection: {str(e)}")
            return "UNKNOWN", CAPABILITY_SUGGESTIONS["UNKNOWN"][:2]
    
    def enhance_response(self, ai_response: str, intent: str, suggestions: List[str]) -> str:
        """
        Enhance the AI response with capability suggestions based on the detected intent.
        
        Args:
            ai_response: Original response from the chatbot
            intent: Detected intent key
            suggestions: List of capability suggestions
            
        Returns:
            Enhanced response with capability suggestions
        """
        # Skip enhancing for certain intents
        if intent in ["FAREWELL", "FEEDBACK"]:
            return ai_response
            
        # Add suggestions to the response
        if suggestions:
            # Craft a natural transition based on the intent
            transitions = {
                "QUESTION": "By the way, did you know you can also",
                "FOLLOW_UP": "I can help with that. Also, you might want to know you can",
                "DOCUMENT_QUERY": "I hope that answers your question about your documents. You can also",
                "FILE_MANAGEMENT": "Happy to help with your files. You might also be interested to know you can",
                "GREETING": "It's great to chat with you. Feel free to",
                "HELP": "Here are some other things you can do:",
                "UNKNOWN": "Is there anything else you'd like to know? You can also"
            }
            
            transition = transitions.get(intent, "Also, you can")
            
            # Format the suggestions
            suggestion_text = " or ".join(suggestions)
            
            # Combine with the original response
            enhanced_response = f"{ai_response}\n\n{transition} {suggestion_text}."
            return enhanced_response
        
        return ai_response

# Helper function to integrate with the existing chatbot
def process_with_intent_detection(user_message: str, ai_response: str, conversation_history: Optional[List[Dict]] = None) -> str:
    """
    Process the user message and AI response with intent detection to enhance the response.
    
    Args:
        user_message: The user's message
        ai_response: The original AI response
        conversation_history: Optional list of previous messages
        
    Returns:
        Enhanced AI response with capability suggestions
    """
    try:
        detector = IntentDetector()
        intent, suggestions = detector.detect_intent(user_message, conversation_history)
        enhanced_response = detector.enhance_response(ai_response, intent, suggestions)
        return enhanced_response
    except Exception as e:
        print(f"Error in intent detection processing: {str(e)}")
        return ai_response  # Return original response if there's an error 