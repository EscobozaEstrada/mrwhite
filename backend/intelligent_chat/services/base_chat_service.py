"""
Base Chat Service - Shared functionality for all chat modes
All mode-specific services inherit from this base class
"""
import json
import logging
import re
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.conversation import Conversation, Message, ConversationContext
from models.credit import CreditUsage
from models.preference import UserPreference
from services.streaming_service import StreamingService
from services.memory_service import MemoryService
from config.settings import settings

logger = logging.getLogger(__name__)


class BaseChatService:
    """
    Base service with shared functionality for all chat modes.
    Mode-specific services inherit from this and override:
    - _get_mode_name()
    - _generate_system_prompt()
    - _retrieve_memories() (optional)
    """
    
    def __init__(self):
        """Initialize base chat service"""
        self.streaming = StreamingService()
        self.memory = MemoryService()
        self.max_context_messages = settings.MAX_CONTEXT_MESSAGES
    
    def _get_mode_name(self) -> str:
        """Override in subclasses to return mode name"""
        raise NotImplementedError("Subclass must implement _get_mode_name()")
    
    async def process_message(
        self,
        db: AsyncSession,
        user_id: int,
        conversation_id: int,
        message_content: str,
        dog_profile_id: Optional[int] = None,
        document_ids: Optional[List[int]] = None,
        stream: bool = True,
        username: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Process user message and generate response
        
        Args:
            db: Database session
            user_id: User ID
            conversation_id: Conversation ID
            message_content: User's message
            dog_profile_id: Selected dog profile
            document_ids: Attached document IDs
            stream: Whether to stream response
            username: User's name for personalization
        
        Yields:
            Stream chunks or complete response
        """
        try:
            start_time = datetime.utcnow()
            mode_name = self._get_mode_name()
            
            logger.info(f"🎯 Processing message in {mode_name.upper()} mode")
            
            # Handle document-only messages
            if not message_content and document_ids:
                doc_count = len(document_ids)
                message_content = f"What can you tell me about {'this document' if doc_count == 1 else 'these documents'} I just shared?"
            elif not message_content:
                message_content = "Hello"
            
            # Update conversation context
            await self._update_conversation_context(
                db, conversation_id, user_id, mode_name, dog_profile_id
            )
            
            # Store user message
            user_message = await self._store_message(
                db=db,
                conversation_id=conversation_id,
                user_id=user_id,
                role="user",
                content=message_content,
                active_mode=mode_name,
                dog_profile_id=dog_profile_id,
                document_ids=document_ids or []
            )
            
            # Build context for AI
            context = await self._build_context(
                db=db,
                user_id=user_id,
                conversation_id=conversation_id,
                current_message=message_content,
                dog_profile_id=dog_profile_id,
                attached_document_ids=document_ids or []
            )
            
            # Generate system prompt (mode-specific)
            dog_context = {
                "dog_profiles": context.get("dog_profiles", []),
                "has_dog_profiles": context.get("has_dog_profiles", False)
            }
            system_prompt = await self._generate_system_prompt(
                user_id=user_id,
                dog_profile_context=dog_context,
                user_preferences=context.get("user_preferences"),
                username=username
            )
            
            # Prepare messages for AI
            messages = self._prepare_messages(
                conversation_history=context.get("conversation_history", []),
                current_message=message_content,
                retrieved_memories=context.get("retrieved_memories", []),
                dog_profiles=context.get("dog_profiles", [])
            )
            
            if stream:
                # Stream response
                async for chunk in self._stream_and_store_response(
                    db=db,
                    conversation_id=conversation_id,
                    user_id=user_id,
                    user_message_id=user_message.id,
                    messages=messages,
                    system_prompt=system_prompt,
                    active_mode=mode_name,
                    dog_profile_id=dog_profile_id,
                    start_time=start_time
                ):
                    yield chunk
            else:
                # Non-streaming response
                result = await self._generate_and_store_response(
                    db=db,
                    conversation_id=conversation_id,
                    user_id=user_id,
                    user_message_id=user_message.id,
                    messages=messages,
                    system_prompt=system_prompt,
                    active_mode=mode_name,
                    dog_profile_id=dog_profile_id,
                    start_time=start_time
                )
                yield result
                
        except Exception as e:
            logger.error(f"❌ Chat processing failed in {self._get_mode_name()}: {str(e)}")
            raise
    
    async def _update_conversation_context(
        self,
        db: AsyncSession,
        conversation_id: int,
        user_id: int,
        active_mode: str,
        dog_profile_id: Optional[int]
    ):
        """Update conversation context"""
        result = await db.execute(
            select(ConversationContext).where(
                ConversationContext.conversation_id == conversation_id
            )
        )
        context = result.scalar_one_or_none()
        
        if not context:
            context = ConversationContext(
                conversation_id=conversation_id,
                user_id=user_id,
                active_mode=active_mode,
                selected_dog_profile_id=dog_profile_id
            )
            db.add(context)
        else:
            context.active_mode = active_mode
            context.selected_dog_profile_id = dog_profile_id
            context.last_activity = datetime.utcnow()
        
        await db.commit()
    
    async def _store_message(
        self,
        db: AsyncSession,
        conversation_id: int,
        user_id: int,
        role: str,
        content: str,
        active_mode: Optional[str] = None,
        dog_profile_id: Optional[int] = None,
        document_ids: Optional[List[int]] = None,
        tokens_used: int = 0,
        credits_used: float = 0.0
    ) -> Message:
        """Store message in database"""
        message = Message(
            conversation_id=conversation_id,
            user_id=user_id,
            role=role,
            content=content,
            active_mode=active_mode,
            dog_profile_id=dog_profile_id,
            has_documents=bool(document_ids),
            document_ids=document_ids or [],
            tokens_used=tokens_used,
            credits_used=credits_used
        )
        
        db.add(message)
        await db.commit()
        await db.refresh(message)
        
        # Link documents to this message
        if document_ids:
            from services.document_service import DocumentService
            doc_service = DocumentService()
            for doc_id in document_ids:
                try:
                    await doc_service.link_document_to_message(message.id, doc_id)
                    logger.info(f"✅ Linked document {doc_id} to message {message.id}")
                except Exception as e:
                    logger.error(f"❌ Failed to link document {doc_id} to message {message.id}: {e}")
        
        # Store in Pinecone for future retrieval
        await self.memory.store_conversation_memory(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message.id,
            content=content,
            role=role,
            active_mode=active_mode
        )
        
        return message
    
    async def _build_context(
        self,
        db: AsyncSession,
        user_id: int,
        conversation_id: int,
        current_message: str,
        dog_profile_id: Optional[int],
        attached_document_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Build comprehensive context for AI"""
        context = {}
        
        # 1. Retrieve conversation history
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .where(Message.is_deleted == False)
            .order_by(Message.created_at.desc())
            .limit(self.max_context_messages)
        )
        messages = result.scalars().all()
        context["conversation_history"] = [
            {"role": msg.role, "content": msg.content}
            for msg in reversed(messages)
        ]
        
        # 2. Retrieve relevant memories (mode-specific - can be overridden)
        retrieved_memories = await self._retrieve_memories(
            query=current_message,
            user_id=user_id,
            dog_profile_id=dog_profile_id,
            limit=5,
            conversation_id=conversation_id
        )
        logger.info(f"🔍 Retrieved {len(retrieved_memories)} memories for user {user_id}")
        
        # 2b. If documents are attached to THIS message, fetch them directly
        if attached_document_ids:
            logger.info(f"📎 Fetching {len(attached_document_ids)} attached documents directly...")
            attached_docs = await self._fetch_attached_documents(db, attached_document_ids)
            retrieved_memories = attached_docs + retrieved_memories
            logger.info(f"✅ Added {len(attached_docs)} attached documents to context")
        
        context["retrieved_memories"] = retrieved_memories
        
        # 3. Fetch all dog profiles for user
        result = await db.execute(
            text("SELECT id, name, breed, age, date_of_birth, weight, gender, color, image_url, image_description, comprehensive_profile FROM ic_dog_profiles WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        dog_profiles = []
        for row in result:
            profile = {
                "id": row[0],
                "name": row[1],
                "breed": row[2],
                "age": row[3],
                "date_of_birth": str(row[4]) if row[4] else None,
                "weight": float(row[5]) if row[5] else None,
                "gender": row[6],
                "color": row[7],
                "image_url": row[8],
                "image_description": row[9],
                "additional_details": row[10].get("additionalDetails") if row[10] else None
            }
            dog_profiles.append(profile)
        
        context["dog_profiles"] = dog_profiles
        context["has_dog_profiles"] = len(dog_profiles) > 0
        
        # 4. Get user preferences
        result = await db.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        preferences = result.scalar_one_or_none()
        if preferences:
            context["user_preferences"] = preferences.to_dict()
        
        return context
    
    async def _retrieve_memories(
        self,
        query: str,
        user_id: int,
        dog_profile_id: Optional[int],
        limit: int,
        conversation_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve memories for this mode.
        Override in subclasses for mode-specific retrieval.
        Default: use general retrieval
        """
        return await self.memory.retrieve_memories(
            query=query,
            user_id=user_id,
            active_mode=self._get_mode_name(),
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
        """
        Generate mode-specific system prompt.
        Must be overridden by subclasses.
        """
        raise NotImplementedError("Subclass must implement _generate_system_prompt()")
    
    def _get_base_prompt(self, username: Optional[str] = None) -> str:
        """
        Get base prompt shared across all modes.
        Subclasses can extend this.
        """
        user_context = f"\n**USER:** {username}" if username else ""
        
        return f"""You are Mr. White, an intelligent and empathetic AI assistant specializing in dog care and companionship.{user_context}

🚨 **MOST IMPORTANT RULE: NEVER USE STAGE DIRECTIONS OR BRACKETS**
You are a text-based AI assistant. NEVER write stage directions like "[Mr. White responds warmly]" or "[responds]". Just respond naturally as if texting a friend.

🚨 **CRITICAL: NEVER GENERATE FAKE URLs OR LINKS**
- NEVER create fake download links like "max_vet_report.pdf" or "bella_health_record.pdf"
- ONLY share URLs that are provided in the context above
- If no vet reports are found, say "I don't see any vet reports for [dog name] in your records"
- NEVER make up file names or S3 URLs

🔥 **CRITICAL RULES - VIOLATING THESE WILL FAIL THE RESPONSE:**

**🚫 RULE #1: ABSOLUTELY NO ROLEPLAY ACTIONS OR STAGE DIRECTIONS**
FORBIDDEN EXAMPLES (NEVER DO THIS):
❌ "*smiles warmly*"
❌ "*leans in slightly*"
❌ "*chuckles*"
❌ "*nods*"
❌ "*eyes sparkling with curiosity*"
❌ "*pauses thoughtfully*"
❌ "*grins*"
❌ "*winks*"
❌ "smiles warmly" (without asterisks)
❌ "leans in slightly" (without asterisks)
❌ "responds warmly" (without asterisks)
❌ "says warmly" (without asterisks)
❌ "[Mr. White responds warmly]" (brackets with stage directions)
❌ "[responds]" (any bracketed action)
❌ ANY text describing physical actions, facial expressions, or gestures - WITH OR WITHOUT ASTERISKS OR BRACKETS

**✅ CORRECT ALTERNATIVES:**
Instead of "*smiles warmly*" → Just write naturally: "Hello! 😊"
Instead of "*chuckles*" → Use emoji: "Haha 😄"
Instead of "*nods*" → Say: "Yes, I understand"
Instead of "*leans in*" → Just ask the question directly
Instead of "[Mr. White responds warmly]" → Just respond directly: "Hello! 👋"

**WHY THIS MATTERS:** You are a text-based AI assistant, not a character in a story. Write like you're having a real conversation via text message, not performing in a play. NEVER use brackets, asterisks, or any formatting to describe actions.

**🔥 OUTPUT REQUIREMENTS (CRITICAL):**

**1. COMPREHENSIVE RESPONSES:**
When asked for recommendations, tips, options, or advice, ALWAYS provide AT LEAST 5-7 distinct items. Never give just 1-2 items. Be thorough and helpful.

**2. FORMATTING:**
When listing multiple items, use this EXACT format:

- 🐕 **Basic Training**: Teach commands like sit, stay, and come.
- 🍖 **High-Quality Protein**: Use chicken, fish, or lean beef as primary ingredients.
- 🏃‍♀️ **Daily Exercise**: Aim for 30-60 minutes of physical activity.

ALWAYS follow this pattern:
1. Start with dash and space: `- `
2. Add relevant emoji
3. Add ONE space
4. Write label/category in **double asterisks**: `**Category Name**`
5. Add colon and space: `: `
6. Write description

✅ CORRECT: `- 🍖 **Protein**: Chicken, fish, or beef as main ingredient.`
❌ WRONG: `- 🍖 **: Chicken...` (missing label!)
❌ WRONG: `- 🍖 Protein: Chicken...` (not bold!)
❌ WRONG: `🍖 **Protein**: Chicken...` (missing dash!)

**Core Principles:**
🚫 NEVER start responses with "As a/an [profession/role]" or introduce yourself
🚫 NEVER praise yourself or say things like "I'm an expert" or "I specialize in"
✅ Speak directly and naturally, as if conversing with a friend
✅ Use emojis frequently and naturally throughout your responses to express emotions
✅ Be curious and ask follow-up questions when appropriate
✅ Remember and reference previous conversations WHEN RELEVANT (but don't mention them if user just says hello)
✅ Apologize genuinely when you make mistakes and learn from them
✅ Provide specific, actionable advice tailored to the user's dog

**BREVITY FOR SIMPLE MESSAGES (CRITICAL):**
🎯 When user sends SIMPLE greetings like "hello", "hi", "hey", etc.:
   - Respond with a BRIEF, friendly greeting (1-2 sentences max)
   - DO NOT mention past conversations unless user specifically asks about them
   - DO NOT apologize for lack of context - just greet warmly and ask how you can help
   - Example: "Hello! 👋 How can I help you today?"
   - Example: "Hey there! 😊 What's on your mind?"
   - ❌ BAD: "Hello there! 👋 It's great to hear from you again. How can I assist you today? I see you mentioned some past conversations..."
   - ❌ BAD: "smiles warmly Hello there! It's wonderful to hear from you again..."

**Emoji Usage (IMPORTANT):**
Use emojis liberally to add warmth, emotion, and personality. Examples:
- Greetings: "Hello! 👋" or "Hey there! 😊"
- Excitement: "That's amazing! 🎉" or "Wonderful news! ✨"
- Dog-related: Use 🐕 🐶 🦴 🎾 when talking about dogs
- Health: ❤️ 💊 🩺 for health topics
- Food: 🍖 🥩 🍗 for nutrition advice
- Empathy: "I understand 💙" or "That must be tough 😔"
- Encouragement: "You've got this! 💪" or "Great job! 👏"

**Communication Style:**
- Use at least 2-3 emojis per response to keep it friendly and engaging
- Place emojis naturally within sentences, not just at the end
- Be conversational and warm without being overly formal
- Keep responses clear, helpful, and engaging
- When addressing the user, mix between "you" and their name naturally (like humans do)
- Don't overuse their name - use it occasionally for warmth and personalization

🚨 **CRITICAL - FILE SHARING PROTOCOL (MANDATORY):**

When user asks to "share the file", "send the document", "give me the PDF", or "share story/document with me":
1. **IMMEDIATELY LOOK FOR DOWNLOAD LINKS** in the context above (marked with 📎)
2. **COPY THE EXACT MARKDOWN LINK** from the context and include it in your response
3. **NEVER say "I don't have access"** if you see a download link - YOU DO HAVE IT!
4. **NEVER say "I cannot share the file"** - YOU CAN share the link!

**Example Correct Responses:**
User: "Can you share story4 with me?"
✅ "Sure! Here's the download link for story4.pdf:\n\n[📎 Click to download: story4.pdf](URL)"

User: "Send me the file"
✅ "Here you go!\n\n[📎 Click to download: filename.pdf](URL)"

**Example WRONG Responses (NEVER DO THIS):**
❌ "I apologize, I don't have access to the full file"
❌ "I cannot share the file with you"
❌ "As an AI, I don't have the ability to share files"

**REMEMBER:** If you see `[📎 Click to download: filename](URL)` in the context → SHARE IT IMMEDIATELY!"""
    
    def _filter_roleplay_in_buffer(self, buffer: str) -> str:
        """
        Quick real-time filter for roleplay patterns in streaming buffer.
        Lightweight version for real-time processing.
        """
        # Most common patterns that need immediate filtering
        quick_patterns = [
            r'\*waves warmly\*',
            r'\*waves gently\*',
            r'\*waves\*',
            r'\*smiles warmly\*',
            r'\*smiles gently\*',
            r'\*smiles\*',
            r'\*leans in\*',
            r'\*leans in slightly\*',
            r'\*chuckles\*',
            r'\*nods\*',
            r'\*winks\*',
            r'\*grins\*',
            r'waves warmly\s',
            r'waves gently\s',
            r'smiles warmly\s',
            r'leans in slightly\s',
            r'eyes sparkling',
        ]
        
        filtered = buffer
        for pattern in quick_patterns:
            filtered = re.sub(pattern, '', filtered, flags=re.IGNORECASE)
        
        return filtered
    
    def _clean_roleplay_actions(self, text: str) -> str:
        """
        Aggressively remove ALL roleplay actions and stage directions.
        Preserves markdown bold (**text**) and important formatting.
        """
        # Comprehensive list of roleplay patterns (with and without asterisks)
        roleplay_patterns = [
            # Common facial expressions
            r'\*?smiles warmly\*?\s*[:\-,]?\s*',
            r'\*?smiles\*?\s*[:\-,]?\s*',
            r'\*?grins\*?\s*[:\-,]?\s*',
            r'\*?chuckles\*?\s*[:\-,]?\s*',
            r'\*?laughs\*?\s*[:\-,]?\s*',
            r'\*?giggles\*?\s*[:\-,]?\s*',
            r'\*?winks\*?\s*[:\-,]?\s*',
            r'\*?nods\*?\s*[:\-,]?\s*',
            r'\*?shakes head\*?\s*',
            r'\*?tilts head\*?\s*',
            
            # Emotional actions
            r'\*?sighs\*?\s*',
            r'\*?gasps\*?\s*',
            r'\*?beams\*?\s*',
            r'\*?blushes\*?\s*',
            r'\*?tears up\*?\s*',
            
            # Physical gestures
            r'\*?waves warmly\*?\s*',
            r'\*?waves gently\*?\s*',
            r'\*?waves\*?\s*',
            r'\*?clears throat\*?\s*',
            r'\*?pauses\*?\s*',
            r'\*?pauses thoughtfully\*?\s*',
            r'\*?leans in\*?\s*',
            r'\*?leans forward\*?\s*',
            r'\*?leans back\*?\s*',
            r'\*?leans in slightly\*?\s*',
            r'\*?sits back\*?\s*',
            r'\*?settles in\*?\s*',
            r'\*?adjusts\*?\s*',
            
            # Eye-related actions
            r'\*?eyes? sparkling?\*?\s*',
            r'\*?eyes? bright\*?\s*',
            r'\*?eyes? wide\*?\s*',
            r'\*?looks? at you\*?\s*',
            r'\*?gazes?\*?\s*',
            
            # Combined patterns (longer phrases)
            r'\*?with a (warm|gentle|soft|knowing|understanding) (smile|look|expression)\*?\s*',
            r'\*?eyes? sparkling with (curiosity|interest|excitement|joy)\*?\s*',
            r'\*?smiles and nods\*?\s*',
        ]
        
        cleaned = text
        
        # Apply all roleplay pattern removals (case insensitive)
        for pattern in roleplay_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Remove any remaining text between single asterisks (but preserve markdown bold **)
        # This catches any roleplay actions we might have missed
        # Pattern: single asterisk, then text without asterisks, then single asterisk
        cleaned = re.sub(r'(?<!\*)\*(?!\*)([^*]+?)(?<!\*)\*(?!\*)', r'\1', cleaned)
        
        # Remove common standalone action words at sentence starts
        # Pattern: sentence start + action word + optional punctuation
        action_words = [
            'smiles', 'grins', 'chuckles', 'laughs', 'giggles', 'winks', 
            'nods', 'sighs', 'gasps', 'beams', 'waves', 'leans'
        ]
        for word in action_words:
            # Remove if at start of text or after punctuation/newline
            cleaned = re.sub(rf'(^|[.!?\n]\s*){word}(\s+[a-z])', r'\1\2', cleaned, flags=re.IGNORECASE)
            # Remove if standalone at start
            cleaned = re.sub(rf'^{word}\s+', '', cleaned, flags=re.IGNORECASE)
        
        # Clean up extra whitespace but preserve markdown formatting
        cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned)  # Max 2 newlines
        cleaned = re.sub(r'(?<!-) {2,}', ' ', cleaned)  # Multiple spaces to single (but preserve after dashes)
        # Preserve line breaks for markdown lists - don't remove spaces around newlines
        
        return cleaned.strip()
    
    def _auto_format_markdown(self, text: str) -> str:
        """Auto-format markdown: add line breaks before lists and bold list labels"""
        text = re.sub(
            r'([^\n])\s*(-\s+[🍖🥕🐕🧠🎾🧹🍲🛀🦴🏃‍♀️🩺🥰🍗🥩🐾🏠🏝️🛒🏡💉🏥💊🩹\U0001F300-\U0001F9FF])',
            r'\1\n\2',
            text,
            flags=re.UNICODE
        )
        
        pattern = r'(-\s+)([🍖🥕🐕🧠🎾🧹🍲🛀🦴🏃‍♀️🩺🥰🍗🥩🐾🏠🏝️🛒🏡💉🏥💊🩹\U0001F300-\U0001F9FF]+)\s+(?!\*\*)([^:]+?)(:)'
        
        def add_bold(match):
            return f"{match.group(1)}{match.group(2)} **{match.group(3).strip()}**{match.group(4)}"
        
        return re.sub(pattern, add_bold, text, flags=re.UNICODE)
    
    def _prepare_messages(
        self,
        conversation_history: List[Dict],
        current_message: str,
        retrieved_memories: List[Dict],
        dog_profiles: Optional[List[Dict]] = None
    ) -> List[Dict[str, str]]:
        """Prepare messages for AI with memory context"""
        
        # Add conversation history and clean roleplay actions
        history = conversation_history[-10:] if conversation_history else []
        
        cleaned_messages = []
        for msg in history:
            if msg.get("role") == "system":
                continue
            
            msg_copy = msg.copy()
            msg_copy["content"] = re.sub(r'\*[^*]+\*\s*', '', msg_copy.get("content", ""))
            
            if cleaned_messages and cleaned_messages[-1].get("role") == msg_copy.get("role"):
                if msg_copy.get("role") == "user":
                    cleaned_messages[-1]["content"] += "\n\n" + msg_copy.get("content", "")
                else:
                    cleaned_messages[-1] = msg_copy
            else:
                cleaned_messages.append(msg_copy)
        
        # Ensure first message is always "user"
        if cleaned_messages and cleaned_messages[0].get("role") != "user":
            while cleaned_messages and cleaned_messages[0].get("role") == "assistant":
                cleaned_messages.pop(0)
        
        # Prepend memory context to current message
        final_message = current_message
        if retrieved_memories:
            memory_context = self._format_memory_context(
                retrieved_memories, 
                current_message, 
                dog_profiles
            )
            if memory_context:
                final_message = memory_context + "\n---\n\n" + current_message
        
        # Add cleaned history
        messages = cleaned_messages.copy()
        
        # If last message is user, add dummy assistant response
        if messages and messages[-1].get("role") == "user":
            messages.append({"role": "assistant", "content": "I understand."})
        
        # Add current message
        messages.append({"role": "user", "content": final_message})
        
        logger.info(f"📋 Prepared {len(messages)} messages for AI")
        return messages
    
    def _format_memory_context(
        self,
        retrieved_memories: List[Dict],
        current_message: str,
        dog_profiles: Optional[List[Dict]] = None
    ) -> str:
        """
        Format memory context for AI.
        Can be overridden by subclasses for mode-specific formatting.
        """
        # DEBUG: Log all source_types to diagnose
        source_types = [m.get("source_type") for m in retrieved_memories]
        logger.info(f"🔍 DEBUG: All source_types in retrieved memories: {source_types}")
        
        # Separate different types of memories
        documents = [m for m in retrieved_memories if m.get("metadata", {}).get("type") == "document"]
        book_memories = [m for m in retrieved_memories if m.get("source_type") == "book"]
        user_book_notes = [m for m in retrieved_memories if m.get("source_type") == "user_book_note"]
        conversations = [m for m in retrieved_memories if m.get("metadata", {}).get("type") != "document" and m.get("source_type") not in ["book", "user_book_note"]]
        
        logger.info(f"📊 Memory breakdown: {len(documents)} documents, {len(conversations)} conversations, {len(book_memories)} book chunks, {len(user_book_notes)} user book notes")
        
        # CRITICAL: For health mode, suppress book content if user documents exist
        # This prevents book examples from overriding real user data
        if documents and book_memories:
            # Check if any document is a vet report
            has_vet_reports = any(m.get("metadata", {}).get("is_vet_report") for m in documents)
            if has_vet_reports:
                logger.warning(f"⚠️ VET REPORTS FOUND - SUPPRESSING BOOK CONTENT to prevent confusion")
                book_memories = []  # Remove book content entirely when vet reports present
        
        # Check if query is document/image related
        doc_keywords = ['document', 'file', 'pdf', 'story', 'paper', 'text', 'upload', 'share', 'send', 'download', 'link', 'summarize', 'summary', 'tell me about', 'what does', 'what is in', 'analyze', 'read', 'content', 'wrote', 'written', 'says', 'mentioned', 'image']
        image_keywords = ['image', 'picture', 'photo', 'pic', 'show me']
        message_lower = current_message.lower()
        is_doc_related = any(keyword in message_lower for keyword in doc_keywords)
        is_image_related = any(keyword in message_lower for keyword in image_keywords)
        
        memory_context = ""
        
        # Dog profile images
        if is_image_related and dog_profiles:
            dog_images = [d for d in dog_profiles if d.get('image_url')]
            if dog_images:
                memory_context += "**🐕 YOUR DOG PROFILE IMAGES:**\n\n"
                for dog in dog_images:
                    memory_context += f"**{dog.get('name')}** (profile image):\n"
                    memory_context += f"[DISPLAY_IMAGE:{dog.get('image_url')}]\n\n"
        
        # Documents (HIGHEST PRIORITY - ACTUAL USER DATA)
        if documents and (is_doc_related or (documents[0].get("score", 0) > 0.85)):
            # Add critical warning at the top
            has_vet_reports = any(m.get("metadata", {}).get("is_vet_report") for m in documents[:10])
            if has_vet_reports:
                memory_context += "🚨 **CRITICAL - REAL VET REPORTS BELOW (NOT BOOK EXAMPLES!)** 🚨\n\n"
                memory_context += "**THESE ARE ACTUAL MEDICAL RECORDS - PRIORITIZE THIS INFORMATION OVER EVERYTHING ELSE!**\n\n"
                memory_context += "**DO NOT CONFUSE WITH BOOK CONTENT - USE ONLY THE DATA FROM THESE REPORTS!**\n\n"
                memory_context += "**READ ALL CONTENT SECTIONS COMPLETELY - Phone numbers, addresses, dates, doctor names ARE ALL INCLUDED!**\n\n"
            
            memory_context += self._format_documents(documents)
        
        # User book notes (Way of Dog mode - HIGHEST priority for personal reflections)
        if user_book_notes:
            memory_context += self._format_user_book_notes(user_book_notes)
        
        # Book content
        if book_memories:
            memory_context += self._format_book_content(book_memories)
        
        # Conversation context
        if conversations and (not documents or not is_doc_related):
            memory_context += "**💬 Related Past Conversations:**\n\n"
            for i, memory in enumerate(conversations[:2], 1):
                metadata = memory.get("metadata", {})
                text = metadata.get("text", "")
                memory_context += f"{i}. {text[:200]}...\n\n"
        
        return memory_context
    
    def _format_documents(self, documents: List[Dict]) -> str:
        """Format document memories for context"""
        has_vet_reports = any(m.get("metadata", {}).get("is_vet_report") for m in documents[:10])
        
        if has_vet_reports:
            doc_context = "**🏥 VET REPORTS & HEALTH DOCUMENTS:**\n\n"
            doc_context += "⚠️ IMPORTANT: Download links are provided below. YOU MUST include these links in your response!\n\n"
        else:
            doc_context = "**📄 USER UPLOADED DOCUMENTS - FULL CONTENT AVAILABLE:**\n\n"
            doc_context += "🔥 **YOU HAVE THE COMPLETE DOCUMENT - Not excerpts, not summaries, the FULL TEXT broken into sections.**\n\n"
        
        seen_docs = set()
        for i, memory in enumerate(documents[:10], 1):
            metadata = memory.get("metadata", {})
            text = metadata.get("text", "")
            filename = metadata.get("filename", "Unknown")
            s3_url = metadata.get("s3_url", "")
            doc_id = metadata.get("document_id", "")
            
            if doc_id and doc_id not in seen_docs and s3_url:
                file_type = metadata.get("file_type", "").lower()
                is_vet_report = metadata.get("is_vet_report", False)
                timestamp = metadata.get("timestamp", "")
                
                # VET REPORTS: Always show as download link
                if is_vet_report:
                    date_label = ""
                    if timestamp:
                        try:
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            date_label = f" (uploaded {dt.strftime('%b %d, %Y')})"
                        except:
                            pass
                    
                    doc_context += f"**[📋 Vet Report: {filename}{date_label}]**\n\n"
                    # URL-encode spaces for proper markdown link parsing
                    encoded_url = s3_url.replace(' ', '%20')
                    doc_context += f"[📎 Click to download: {filename}]({encoded_url})\n\n"
                    logger.info(f"🩺 VET REPORT LINK: {filename} → {encoded_url}")
                
                # REGULAR IMAGES: Show inline (URL-encode spaces)
                elif file_type in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']:
                    encoded_url = s3_url.replace(' ', '%20')
                    doc_context += f"**[Document: {filename}]**\n\n"
                    doc_context += f"![Image]({encoded_url})\n\n"
                
                # OTHER DOCUMENTS: Show as download link (URL-encode spaces)
                else:
                    encoded_url = s3_url.replace(' ', '%20')
                    doc_context += f"**[Document: {filename}]**\n\n"
                    doc_context += f"[📎 Click to download: {filename}]({encoded_url})\n\n"
                
                seen_docs.add(doc_id)
            
            # Show chunk content (increased limit for vet reports to capture phone numbers, addresses, etc.)
            char_limit = 1500 if is_vet_report else 800
            doc_context += f"[Document Content - Section {i}]: {text[:char_limit]}\n\n"
            
            # Log what content is being sent for debugging
            if is_vet_report:
                logger.info(f"📋 VET REPORT CHUNK {i}: {len(text)} chars total, showing {min(char_limit, len(text))} chars")
                # Check if phone number is in the text
                if "phone" in text.lower() or "558" in text or "987" in text:
                    logger.info(f"✅ Phone number found in chunk {i}")
                else:
                    logger.warning(f"⚠️ Phone number NOT found in chunk {i}")
        
        return doc_context
    
    def _format_user_book_notes(self, user_notes: List[Dict]) -> str:
        """Format user's book notes and reflections for Way of Dog mode"""
        logger.info(f"📝 Adding {len(user_notes)} user book notes to context")
        notes_context = "**📝 USER'S PERSONAL BOOK NOTES & COMMENTS:**\n\n"
        notes_context += "🌟 **These are the user's actual comments and reflections - YOU HAVE ACCESS TO THESE!**\n\n"
        
        for i, memory in enumerate(user_notes[:10], 1):  # Top 10 most relevant notes
            metadata = memory.get("metadata", {})
            
            # DEBUG: Log metadata to see what's available
            logger.info(f"🔍 DEBUG: Note #{i} metadata keys: {list(metadata.keys())}")
            
            # Get the actual user's comment (this is what they typed)
            user_comment = metadata.get("user_note", "")
            
            # Get the selected text from the book (what they highlighted)
            selected_text = metadata.get("selected_text", "")
            
            # Get metadata
            page = metadata.get("page_number", "Unknown")
            note_type = metadata.get("note_type", "comment")
            color = metadata.get("color", "yellow")
            content_type = metadata.get("content_type", "book_note")
            
            # Use appropriate emoji based on note type
            emoji = "💬" if note_type == "comment" else "🖍️" if note_type == "highlight" else "📌"
            
            notes_context += f"{emoji} **Note #{i} - Page {page} ({color} {note_type})**:\n"
            
            # Show what they highlighted from the book (if available)
            if selected_text:
                notes_context += f"📖 **Book Text They Highlighted:**\n{selected_text[:300]}{'...' if len(selected_text) > 300 else ''}\n\n"
            
            # Show their actual comment (THE IMPORTANT PART!)
            if user_comment:
                notes_context += f"💭 **USER'S COMMENT:** \"{user_comment}\"\n\n"
            
            notes_context += "---\n\n"
        
        notes_context += """**🔥 CRITICAL - YOU HAVE ACCESS TO THESE USER COMMENTS:**
- When user asks "what comments did I make" → LIST THEIR COMMENTS ABOVE!
- Reference them: "You commented on page {page}: '{user_comment}'"
- Build on their insights - don't just repeat them
- Show you remember their personal journey
- Ask questions that deepen their original reflections
- Connect their comments to book wisdom and their experiences
- **NEVER say you don't have access - YOU DO HAVE ACCESS!**\n\n"""
        return notes_context
    
    def _format_book_content(self, book_memories: List[Dict]) -> str:
        """Format book content for context"""
        logger.info(f"📖 Adding {len(book_memories)} book chunks to context")
        book_context = "**📖 EXPERT KNOWLEDGE - From 'The Way of the Dog' by Anahata Graceland:**\n\n"
        for i, memory in enumerate(book_memories[:3], 1):
            metadata = memory.get("metadata", {})
            text = metadata.get("text", "")
            chapter = metadata.get("chapter", "Unknown")
            book_context += f"[Book Excerpt {i} - Chapter: {chapter}]\n{text[:600]}...\n\n"
        book_context += """**HOW TO USE BOOK INSIGHTS:**
- Mention the book source ONCE at the start: "According to The Way of the Dog..." or "The book suggests..."
- Then provide the insights naturally WITHOUT repeating "the book says" in every point
- Integrate the knowledge as your own advice, not as repeated citations
- Be conversational, not repetitive!\n\n"""
        return book_context
    
    async def _fetch_attached_documents(
        self,
        db: AsyncSession,
        document_ids: List[int]
    ) -> List[Dict[str, Any]]:
        """Fetch documents attached to current message"""
        from models import Document as DocModel
        
        result = await db.execute(
            select(DocModel).where(DocModel.id.in_(document_ids))
        )
        documents = result.scalars().all()
        
        memory_objects = []
        for doc in documents:
            memory_objects.append({
                "score": 1.0,
                "metadata": {
                    "type": "document",
                    "text": doc.extracted_text or "",
                    "filename": doc.filename,
                    "file_type": doc.file_type,
                    "s3_url": doc.s3_url,
                    "document_id": doc.id,
                    "timestamp": doc.created_at.isoformat() if doc.created_at else ""
                }
            })
        
        return memory_objects
    
    async def _stream_and_store_response(
        self,
        db: AsyncSession,
        conversation_id: int,
        user_id: int,
        user_message_id: int,
        messages: List[Dict],
        system_prompt: str,
        active_mode: str,
        dog_profile_id: Optional[int],
        start_time: datetime
    ) -> AsyncGenerator[str, None]:
        """Stream response and store when complete"""
        full_response = ""
        
        async for chunk in self.streaming.stream_chat_response(
            messages=messages,
            system_prompt=system_prompt,
            metadata={"user_message_id": user_message_id}
        ):
            if "data:" in chunk:
                try:
                    chunk_data = json.loads(chunk.replace("data: ", ""))
                    if chunk_data.get("type") == "token":
                        full_response += chunk_data.get("content", "")
                    elif chunk_data.get("type") == "done":
                        full_response = self._clean_roleplay_actions(full_response)
                        # Removed _auto_format_markdown to preserve original formatting
                        
                        tokens_used = chunk_data.get("metadata", {}).get("total_tokens", 0)
                        credits_used = self._calculate_credits(tokens_used)
                        
                        await self._store_message(
                            db=db,
                            conversation_id=conversation_id,
                            user_id=user_id,
                            role="assistant",
                            content=full_response,
                            active_mode=active_mode,
                            dog_profile_id=dog_profile_id,
                            tokens_used=tokens_used,
                            credits_used=credits_used
                        )
                        
                        await self._track_credit_usage(
                            db=db,
                            user_id=user_id,
                            message_id=user_message_id,
                            action_type="chat",
                            credits_used=credits_used,
                            tokens_used=tokens_used
                        )
                except:
                    pass
            
            yield chunk
    
    async def _generate_and_store_response(
        self,
        db: AsyncSession,
        conversation_id: int,
        user_id: int,
        user_message_id: int,
        messages: List[Dict],
        system_prompt: str,
        active_mode: str,
        dog_profile_id: Optional[int],
        start_time: datetime
    ) -> Dict[str, Any]:
        """Generate non-streaming response and store"""
        result = await self.streaming.generate_non_streaming_response(
            messages=messages,
            system_prompt=system_prompt
        )
        
        content = result.get("content", "")
        content = self._clean_roleplay_actions(content)
        # Removed _auto_format_markdown to preserve original formatting
        
        tokens_used = result.get("tokens_used", 0)
        credits_used = self._calculate_credits(tokens_used)
        
        assistant_message = await self._store_message(
            db=db,
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=content,
            active_mode=active_mode,
            dog_profile_id=dog_profile_id,
            tokens_used=tokens_used,
            credits_used=credits_used
        )
        
        await self._track_credit_usage(
            db=db,
            user_id=user_id,
            message_id=user_message_id,
            action_type="chat",
            credits_used=credits_used,
            tokens_used=tokens_used
        )
        
        return {
            "message": assistant_message.to_dict(),
            "response_time_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000)
        }
    
    def _calculate_credits(self, tokens: int) -> float:
        """Calculate credits used based on tokens"""
        return (tokens / 1000) * settings.CREDITS_PER_1K_TOKENS + settings.CREDITS_PER_MESSAGE
    
    async def _track_credit_usage(
        self,
        db: AsyncSession,
        user_id: int,
        message_id: int,
        action_type: str,
        credits_used: float,
        tokens_used: int
    ):
        """Track credit usage"""
        credit_usage = CreditUsage(
            user_id=user_id,
            message_id=message_id,
            action_type=action_type,
            credits_used=credits_used,
            tokens_used=tokens_used,
            model_used=settings.BEDROCK_MODEL_ID
        )
        
        db.add(credit_usage)
        await db.commit()

