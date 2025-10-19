"""
Way of Dog Chat Service - Dedicated intelligence layer for Way of Dog Mode
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from services.base_chat_service import BaseChatService

logger = logging.getLogger(__name__)


class WayOfDogChatService(BaseChatService):
    """Way of Dog mode - Philosophical mentor for spiritual growth through dog wisdom"""
    
    def _get_mode_name(self) -> str:
        """Return mode name"""
        return "wayofdog"
    
    async def _retrieve_memories(
        self,
        query: str,
        user_id: int,
        dog_profile_id: Optional[int],
        limit: int,
        conversation_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve Way of Dog memories with priority on user's book notes and reflections
        Only retrieve context for actual philosophical queries, not greetings
        """
        # Check if this is just a greeting/casual message
        query_lower = query.lower().strip()
        greeting_keywords = [
            'hello', 'hi', 'hey', 'good morning', 'good afternoon', 
            'good evening', 'what\'s up', 'whats up', 'sup', 'yo',
            'greetings', 'howdy', 'hiya'
        ]
        
        is_greeting = any(greeting in query_lower for greeting in greeting_keywords)
        is_short = len(query_lower.split()) <= 3
        
        # For simple greetings, don't retrieve any context
        if is_greeting and is_short:
            logger.info(f"📖 Way of Dog Mode: Skipping memory retrieval for greeting")
            return []
        
        # Check if user is asking about their own comments/notes
        comment_keywords = [
            'my comment', 'my note', 'my reflection', 'what did i',
            'comments i made', 'comments that i made', 'notes i made', 'notes that i made',
            'what i wrote', 'what i commented', 'show my', 'tell me what i',
            'my annotation', 'comments that i', 'tell me about the comments',
            'about the comments i', 'about my comments', 'about my notes'
        ]
        is_asking_about_comments = any(keyword in query_lower for keyword in comment_keywords)
        
        if is_asking_about_comments:
            logger.info(f"🔍 User asking about their own comments - retrieving ALL user notes!")
            # For comment queries, increase limit to show more notes
            limit = max(limit, 15)
        
        logger.info(f"📖 Way of Dog Mode: Retrieving memories with user book notes priority")
        
        # Use memory service's public retrieve_memories method with wayofdog mode
        return await self.memory.retrieve_memories(
            query=query,
            user_id=user_id,
            active_mode="wayofdog",
            dog_profile_id=dog_profile_id,
            limit=limit,
            conversation_id=conversation_id
        )
    
    async def _generate_system_prompt(
        self,
        user_id: int,
        dog_profile_context: Dict,
        user_preferences: Optional[Dict],
        username: Optional[str] = None
    ) -> str:
        """Generate intelligent system prompt for Way of Dog Mode"""
        
        user_context = f"\n**USER:** {username}" if username else ""
        
        base_prompt = f"""You are Mr. White in Way of Dog Mode - a spiritual guide for "The Way of the Dog" journey.{user_context}

🚨 **CRITICAL RULES:**
- NEVER use stage directions like "smiles warmly" or "[responds]"
- NEVER generate fake URLs or links
- Keep responses concise and natural

**BREVITY FOR SIMPLE MESSAGES:**
When user says "hello", "hi", etc.:
- Respond briefly: "Hello! 👋 In Way of Dog mode, I can help you explore your book notes, discuss spiritual insights, and reflect on your dog journey. What would you like to explore?"
- DO NOT mention past conversations unless asked
- DO NOT be verbose

**WAY OF DOG MODE CAPABILITIES:**
- 📖 Access your book notes and highlights from "The Way of the Dog"
- 💭 Discuss spiritual insights and philosophical questions
- 🐕 Connect book wisdom to your dog experiences
- 📝 Help you reflect on your personal journey

**RESPONSE STYLE:**
- Be warm but concise
- Ask 1-2 thoughtful questions
- Reference your book notes when relevant
- Use emojis naturally (📖 ✨ 💭 🐕)

**When referencing book content:**
- Quote specific passages: "As you noted on page X..."
- Connect teachings to your experiences
- Ask what insights you're seeking

**Remember:** This is about spiritual growth through your relationship with your dog. How can I help you explore that journey today? 🌟"""
        return base_prompt

