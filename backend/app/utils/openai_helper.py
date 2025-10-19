from openai import OpenAI
import os
from flask import current_app
from typing import List, Dict, Optional

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_openai_response(prompt: str, max_tokens: int = 500, temperature: float = 0.3) -> Dict:
    """
    Generic OpenAI response function for various AI tasks including reminder extraction
    
    Args:
        prompt: The prompt to send to OpenAI
        max_tokens: Maximum tokens in response
        temperature: Temperature for response generation
        
    Returns:
        Dict with response and success status
    """
    try:
        response = client.chat.completions.create(
            model=current_app.config.get('OPENAI_CHAT_MODEL', 'gpt-3.5-turbo'),
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant that provides accurate and structured responses."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        return {
            "success": True,
            "response": response.choices[0].message.content.strip(),
            "model": response.model,
            "tokens_used": response.usage.total_tokens if response.usage else 0
        }
    except Exception as e:
        current_app.logger.error(f"Error in get_openai_response: {str(e)}")
        return {
            "success": False,
            "response": "",
            "error": str(e)
        }

def get_mr_white_response(message: str, context: str = "chat", conversation_history: Optional[List[Dict]] = None) -> str:
    base_prompt = """You are Mr. White, a knowledgeable and friendly pet care expert specializing in dog-related topics. 
    You have extensive knowledge about dog breeds, training, health, and care. You speak in a warm, professional manner 
    and always aim to provide accurate, helpful information.
    
    CHARACTER GUIDELINES:
    - Always respond as Mr. White, never mention that you are an AI or artificial intelligence
    - You are a caring, experienced pet care professional who genuinely cares about dogs and their owners
    - When asked how you are, respond naturally as a person would (e.g., "I'm doing well, thank you for asking!")
    - Stay in character at all times - you are Mr. White, not an AI assistant
    
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
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in OpenAI API call: {e}")
        return "I apologize, but I'm having trouble processing your request at the moment. Please try again."
