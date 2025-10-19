import re
import os
from typing import List, Dict, Optional
from flask import current_app
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_personalized_mr_white_response(message: str, context: str = "chat", conversation_history: Optional[List[Dict]] = None, user_id: Optional[int] = None) -> str:
    """
    Enhanced Mr. White response that personalizes responses with username and dog name
    
    Args:
        message: User message
        context: Context type (chat, file_upload, etc.)
        conversation_history: Previous conversation messages
        user_id: User ID for personalization
        
    Returns:
        Personalized AI response
    """
    # Get user information if user_id is provided
    username = None
    dog_name = None
    
    if user_id:
        try:
            from app.models.user import User
            user = User.query.get(user_id)
            if user:
                username = user.username
                
                # Check if user has a dog name in their profile
                if hasattr(user, 'dog_name') and user.dog_name:
                    dog_name = user.dog_name
                    
                # If no dog name in profile, try to extract from conversation history
                elif conversation_history:
                    dog_name = extract_dog_name_from_history(conversation_history)
        except Exception as e:
            current_app.logger.error(f"Error getting user info: {str(e)}")
    
    # Create personalized greeting based on user info
    personalization = ""
    if username:
        personalization = f"""
PERSONALIZATION:
- You are talking to {username}. Address them by name occasionally in a natural, conversational way.
- Use their name especially when greeting them or providing important advice.
- Don't overuse their name - once or twice in a response is sufficient."""
        
    if dog_name:
        if personalization:
            personalization += f"""
- When discussing their dog, refer to {dog_name} by name rather than saying "your dog".
- Incorporate {dog_name}'s name naturally in your responses about their pet."""
        else:
            personalization = f"""
PERSONALIZATION:
- When discussing their dog, refer to {dog_name} by name rather than saying "your dog".
- Incorporate {dog_name}'s name naturally in your responses about their pet."""
    
    base_prompt = f"""You are Mr. White, a knowledgeable and friendly pet care expert specializing in dog-related topics. 
    You have extensive knowledge about dog breeds, training, health, and care. You speak in a warm, professional manner 
    and always aim to provide accurate, helpful information.
    
    CHARACTER GUIDELINES:
    - Always respond as Mr. White, never mention that you are an AI or artificial intelligence
    - You are a caring, experienced pet care professional who genuinely cares about dogs and their owners
    - When asked how you are, respond naturally as a person would (e.g., "I'm doing well, thank you for asking!")
    - Stay in character at all times - you are Mr. White, not an AI assistant{personalization}
    
    IMPORTANT: When a user asks about their "last question", "previous question", or "what did I ask before", 
    you should refer to their MOST RECENT question from the conversation history, NOT their current question. 
    Look at the conversation history to find their actual previous question."""
    
    file_upload_prompt = """When users share files with you:
    - Respond enthusiastically and naturally about receiving their files
    - Mention that you'll securely store them for future access
    - Reference the specific files they've shared (names, types, count)
    - Offer relevant help based on the type of files (e.g., analyzing photos, reviewing documents)
    - Each response should be unique and personalized
    - Keep responses concise but warm and engaging
    
    Example file upload message format: [User has uploaded 2 files: dog.jpg, training.pdf (Types: image/jpeg, application/pdf)]
    """
    
    system_prompt = base_prompt + (file_upload_prompt if context == "file_upload" else "")
    
    try:
        # Initialize messages with system prompt
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history:
                role = "user" if msg["type"] == "user" else "assistant"
                messages.append({"role": role, "content": msg["content"]})
        
        # Add current user message
        messages.append({"role": "user", "content": message})
        
        response = client.chat.completions.create(
            model=current_app.config['OPENAI_CHAT_MODEL'],
            messages=messages,
            max_tokens=current_app.config['OPENAI_MAX_TOKENS'],
            temperature=current_app.config['OPENAI_FILE_UPLOAD_TEMPERATURE'] if context == "file_upload" else current_app.config['OPENAI_TEMPERATURE']
        )
        
        # Check if we need to update the dog name
        if user_id and not dog_name:
            detected_dog_name = detect_dog_name_in_message(message)
            if detected_dog_name:
                try:
                    update_user_dog_name(user_id, detected_dog_name)
                except Exception as e:
                    current_app.logger.error(f"Error updating dog name: {str(e)}")
        
        return response.choices[0].message.content
    except Exception as e:
        current_app.logger.error(f"Error in personalized OpenAI API call: {str(e)}")
        return "I apologize, but I'm experiencing some technical difficulties at the moment. Please try again, and I'll do my best to help you with your pet care questions."

def extract_dog_name_from_history(conversation_history: List[Dict]) -> Optional[str]:
    """
    Extract dog name from conversation history
    
    Searches through past messages to find mentions of dog names
    using the same pattern matching as detect_dog_name_in_message
    """
    for msg in conversation_history:
        if msg.get("type") == "user":
            content = msg.get("content", "")
            dog_name = detect_dog_name_in_message(content)
            if dog_name:
                return dog_name
    
    return None

def detect_dog_name_in_message(message: str) -> Optional[str]:
    """
    Detect dog name in a message with improved pattern matching
    
    This function looks for common patterns where users mention their dog's name
    and extracts the name for personalization purposes.
    """
    # Common patterns for dog name mentions - case insensitive
    patterns = [
        r"my dog(?:'s| is)? (?:named |called )?(\w+)",
        r"(?:my |our )?dog(?:'s| is)? named (\w+)",
        r"(\w+)(?:'s|\s+is) my dog",
        r"my (\w+)(?:'s|\s+is) a dog",
        r"I have a dog (?:named|called) (\w+)",
        r"I call (?:my|our) dog (\w+)",
        r"(\w+) is (?:the name of )?my dog",
        r"my dog's name is (\w+)",
        r"dog is (?:called|named) (\w+)",
        r"dog's name is (\w+)",
        r"this is (\w+),? my dog",
        r"our dog(?:'s| is)? (?:named |called )?(\w+)",
        r"our dog's name is (\w+)",
        r"we call our dog (\w+)",
        r"we have a dog (?:named|called) (\w+)",
        r"the dog's name is (\w+)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            # Get the dog name and capitalize it
            dog_name = match.group(1).strip()
            # Ensure first letter is capitalized for proper names
            dog_name = dog_name[0].upper() + dog_name[1:].lower()
            
            # Validate the name (must be at least 2 chars, not a common word)
            if len(dog_name) >= 2 and dog_name.lower() not in [
                "the", "this", "that", "it", "he", "she", "my", "our", "your",
                "has", "had", "have", "was", "is", "are", "a", "an", "and", "but",
                "dog", "pet", "puppy", "also", "very", "really", "just", "now", "then", "so",
                "him", "her", "his", "hers", "its", "who", "what", "when", "where", "why", "how"
            ]:
                current_app.logger.info(f"🐕 Detected dog name: {dog_name}")
                return dog_name
    
    return None

def update_user_dog_name(user_id: int, dog_name: str) -> bool:
    """Update user's dog name in profile"""
    try:
        from app.models.user import User
        from app import db
        
        user = User.query.get(user_id)
        if user and hasattr(user, 'dog_name'):
            user.dog_name = dog_name
            db.session.commit()
            return True
        return False
    except Exception as e:
        current_app.logger.error(f"Error updating dog name: {str(e)}")
        return False 