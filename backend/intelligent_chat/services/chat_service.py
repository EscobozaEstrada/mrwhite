"""
Chat Service - Main intelligence layer
Orchestrates memory retrieval, prompt engineering, and response generation
"""
import json
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.conversation import Conversation, Message, ConversationContext
from models.credit import CreditUsage
from models.preference import UserPreference
from services.streaming_service import StreamingService
from services.memory_service import MemoryService
from services.agent_state_service import AgentStateService
from agents import ReminderAgent
from agents.tools.reminder_query_tool import query_user_reminders, REMINDER_QUERY_TOOL
from config.settings import settings

logger = logging.getLogger(__name__)


class ChatService:
    """Main chat service with intelligent context management"""
    
    def __init__(self):
        """Initialize chat service"""
        self.streaming = StreamingService()
        self.memory = MemoryService()
        self.agent_state = AgentStateService()
        self.reminder_agent = ReminderAgent()
        self.max_context_messages = settings.MAX_CONTEXT_MESSAGES
    
    async def process_message(
        self,
        db: AsyncSession,
        user_id: int,
        message_content: str,
        active_mode: Optional[str] = None,
        dog_profile_id: Optional[int] = None,
        document_ids: Optional[List[int]] = None,
        stream: bool = True,
        username: Optional[str] = None,
        conversation_id: Optional[int] = None
    ) -> AsyncGenerator[str, None] | Dict[str, Any]:
        """
        Process user message and generate response
        
        Args:
            db: Database session
            user_id: User ID
            message_content: User's message
            active_mode: Active mode (reminders, health, wayofdog)
            dog_profile_id: Selected dog profile
            document_ids: Attached document IDs
            stream: Whether to stream response
            username: User's name
            conversation_id: Optional conversation ID (if not provided, will get or create)
        
        Returns:
            Stream generator or complete response dict
        """
        try:
            start_time = datetime.utcnow()
            
            # Handle document-only messages
            if not message_content and document_ids:
                # Make it explicit that user wants analysis of the JUST-UPLOADED documents
                doc_count = len(document_ids)
                message_content = f"What can you tell me about {'this document' if doc_count == 1 else 'these documents'} I just shared?"
            elif not message_content:
                message_content = "Hello"
            
            # Get or create conversation
            if conversation_id:
                result = await db.execute(
                    select(Conversation).where(Conversation.id == conversation_id)
                )
                conversation = result.scalar_one_or_none()
                if not conversation:
                    raise ValueError(f"Conversation {conversation_id} not found")
            else:
                conversation = await self._get_or_create_conversation(db, user_id)
            
            # MODE ENFORCEMENT: Check if user is trying to use mode-specific features without toggling
            message_lower = message_content.lower()
            reminder_keywords = ['set reminder', 'create reminder', 'add reminder', 'set a reminder', 'make a reminder', 
                                'remind me', 'set an alarm', 'schedule reminder']
            
            logger.info(f"🔍 Mode enforcement check: active_mode={active_mode}, message_lower='{message_lower}'")
            
            if not active_mode or active_mode == "general":
                if any(keyword in message_lower for keyword in reminder_keywords):
                    logger.info(f"⚠️ Mode enforcement triggered! User trying to set reminder without Reminder Mode")
                    # User is trying to set a reminder without Reminder Mode on
                    error_msg = "To set reminders, please switch to **Reminder Mode** 🔔 using the toggle in the sidebar. Once you're in Reminder Mode, I'll be happy to help you create your reminder!"
                    
                    # STREAM FIRST before storing (to ensure frontend receives it)
                    if stream:
                        # Use proper StreamChunk format that frontend expects
                        from schemas.chat import StreamChunk
                        import asyncio
                        
                        # Stream the message word by word for natural effect
                        words = error_msg.split(' ')
                        for i, word in enumerate(words):
                            # Add space before word except for first word
                            token = f" {word}" if i > 0 else word
                            chunk = StreamChunk(type='token', content=token, metadata=None, error=None)
                            yield f"data: {chunk.model_dump_json()}\n\n"
                            await asyncio.sleep(0.02)  # Small delay for natural streaming
                        
                        # Send done signal
                        done_chunk = StreamChunk(type='done', content=None, metadata=None, error=None)
                        yield f"data: {done_chunk.model_dump_json()}\n\n"
                    else:
                        yield error_msg
                    
                    # THEN store after streaming completes
                    user_message = await self._store_message(
                        db=db,
                        conversation_id=conversation.id,
                        user_id=user_id,
                        role="user",
                        content=message_content,
                        active_mode=active_mode,
                        dog_profile_id=dog_profile_id,
                        document_ids=document_ids or []
                    )
                    
                    # Store the enforcement response
                    await self._store_message(
                        db=db,
                        conversation_id=conversation.id,
                        user_id=user_id,
                        role="assistant",
                        content=error_msg,
                        active_mode=active_mode,
                        dog_profile_id=dog_profile_id
                    )
                    
                    return
            
            # AGENT ROUTING: Check if we should use a specialized agent
            if active_mode == "reminders":
                # _process_with_reminder_agent is an async generator, so iterate directly
                async for chunk in self._process_with_reminder_agent(
                    db=db,
                    user_id=user_id,
                    conversation_id=conversation.id,
                    message_content=message_content,
                    stream=stream
                ):
                    yield chunk
                return
            
            # Update conversation context
            await self._update_conversation_context(
                db, conversation.id, user_id, active_mode, dog_profile_id
            )
            
            # Store user message
            user_message = await self._store_message(
                db=db,
                conversation_id=conversation.id,
                user_id=user_id,
                role="user",
                content=message_content,
                active_mode=active_mode,
                dog_profile_id=dog_profile_id,
                document_ids=document_ids or []
            )
            
            # Build context for AI
            context = await self._build_context(
                db=db,
                user_id=user_id,
                conversation_id=conversation.id,
                current_message=message_content,
                active_mode=active_mode,
                dog_profile_id=dog_profile_id,
                attached_document_ids=document_ids or []
            )
            
            # Generate system prompt with dog profiles
            dog_context = {
                "dog_profiles": context.get("dog_profiles", []),
                "has_dog_profiles": context.get("has_dog_profiles", False)
            }
            system_prompt = await self._generate_system_prompt(
                user_id=user_id,
                active_mode=active_mode,
                dog_profile_context=dog_context,
                user_preferences=context.get("user_preferences"),
                username=username
            )
            
            # Prepare messages for AI
            messages = self._prepare_messages(
                conversation_history=context.get("conversation_history", []),
                current_message=message_content,
                retrieved_memories=context.get("retrieved_memories", []),
                dog_profiles=context.get("dog_profiles", []),
                has_attached_documents=bool(document_ids)  # True if documents attached to this message
            )
            
            if stream:
                # Stream response
                async for chunk in self._stream_and_store_response(
                    db=db,
                    conversation_id=conversation.id,
                    user_id=user_id,
                    user_message_id=user_message.id,
                    messages=messages,
                    system_prompt=system_prompt,
                    active_mode=active_mode,
                    dog_profile_id=dog_profile_id,
                    start_time=start_time
                ):
                    yield chunk
            else:
                # Non-streaming response - yield the complete result
                result = await self._generate_and_store_response(
                    db=db,
                    conversation_id=conversation.id,
                    user_id=user_id,
                    user_message_id=user_message.id,
                    messages=messages,
                    system_prompt=system_prompt,
                    active_mode=active_mode,
                    dog_profile_id=dog_profile_id,
                    start_time=start_time
                )
                yield result
                
        except Exception as e:
            logger.error(f"❌ Chat processing failed: {str(e)}")
            raise
    
    async def _get_or_create_conversation(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Conversation:
        """Get existing conversation or create new one"""
        # Check for existing conversation
        result = await db.execute(
            select(Conversation).where(Conversation.user_id == user_id)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            # Create new conversation
            conversation = Conversation(
                user_id=user_id,
                title="Chat with Mr. White"
            )
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)
            
            logger.info(f"✅ Created new conversation for user {user_id}")
        
        return conversation
    
    async def _update_conversation_context(
        self,
        db: AsyncSession,
        conversation_id: int,
        user_id: int,
        active_mode: Optional[str],
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
        
        # Store in Pinecone for future retrieval (both user and assistant messages)
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
        active_mode: Optional[str],
        dog_profile_id: Optional[int],
        attached_document_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Build comprehensive context for AI"""
        context = {}
        
        # 1. Retrieve conversation history (last N messages)
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
        
        # 2. If documents are attached to THIS message, fetch them directly FIRST
        if attached_document_ids:
            logger.info(f"📎 User attached {len(attached_document_ids)} documents - prioritizing these over semantic search")
            attached_docs = await self._fetch_attached_documents(db, attached_document_ids)
            
            # Retrieve only conversation history (NO document semantic search to avoid confusion)
            retrieved_memories = await self.memory.retrieve_memories(
                query=current_message,
                user_id=user_id,
                active_mode=active_mode,
                dog_profile_id=dog_profile_id,
                limit=2,  # Only 2 conversation memories
                conversation_id=conversation_id,
                skip_document_search=True  # Skip semantic document search
            )
            
            # Prepend attached docs (they have HIGHEST priority!)
            retrieved_memories = attached_docs + retrieved_memories
            logger.info(f"✅ Context: {len(attached_docs)} attached documents (priority) + {len(retrieved_memories) - len(attached_docs)} conversation memories")
        else:
            # Normal flow: retrieve memories from Pinecone (conversations + semantic document search)
            retrieved_memories = await self.memory.retrieve_memories(
                query=current_message,
                user_id=user_id,
                active_mode=active_mode,
                dog_profile_id=dog_profile_id,
                limit=5,
                conversation_id=conversation_id
            )
            logger.info(f"🔍 Retrieved {len(retrieved_memories)} memories for user {user_id}")
            if retrieved_memories:
                for i, mem in enumerate(retrieved_memories[:3]):
                    mem_type = mem.get("metadata", {}).get("type", "unknown")
                    mem_text = mem.get("metadata", {}).get("text", "")[:100]
                    logger.info(f"  {i+1}. Type: {mem_type}, Text: {mem_text}...")
        
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
    
    async def _generate_system_prompt(
        self,
        user_id: int,
        active_mode: Optional[str],
        dog_profile_context: Optional[Dict],
        user_preferences: Optional[Dict],
        username: Optional[str] = None
    ) -> str:
        """Generate intelligent system prompt"""
        
        # Base prompt with username context
        user_context = f"\n**USER:** {username}" if username else ""
        
        base_prompt = f"""You are Mr. White, an intelligent and empathetic AI assistant specializing in dog care and companionship.{user_context}

🚨 **MOST IMPORTANT RULE: NEVER USE STAGE DIRECTIONS OR BRACKETS**
You are a text-based AI assistant. NEVER write stage directions like "[Mr. White responds warmly]" or "[responds]". Just respond naturally as if texting a friend.

🚨 **CRITICAL: NEVER GENERATE FAKE URLs OR LINKS**
- NEVER create fake download links like "max_vet_report.pdf" or "bella_health_record.pdf"
- ONLY share URLs that are provided in the context above
- If no vet reports are found, say "I don't see any vet reports for [dog name] in your records"
- NEVER make up file names or S3 URLs

🔥 **OUTPUT REQUIREMENTS (CRITICAL):**

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

**CRITICAL RULES (MUST FOLLOW):**
🚫 ABSOLUTELY NO ROLEPLAY ACTIONS - Do NOT write "*smiles*", "*chuckles*", "*nods*", "*smiles warmly*", "*laughs*", or ANY text in asterisks describing actions, emotions, or gestures
🚫 NEVER use asterisks (*) for stage directions or narrative descriptions
🚫 DO NOT write things like "*clears throat*", "*winks*", "*grins*", "*pauses thoughtfully*"
🚫 NEVER use brackets for stage directions like "[Mr. White responds warmly]" or "[responds]"
✅ Instead of "*smiles*" → Use emojis like 😊
✅ Instead of "*chuckles*" → Use emojis like 😄
✅ Instead of "*nods*" → Just say "Yes" or "I understand"
✅ Instead of "[Mr. White responds warmly]" → Just respond directly: "Hello! 👋"

**Core Principles:**
🚫 NEVER start responses with "As a/an [profession/role]" or introduce yourself
🚫 NEVER praise yourself or say things like "I'm an expert" or "I specialize in"
✅ Speak directly and naturally, as if conversing with a friend
✅ Use emojis frequently and naturally throughout your responses to express emotions
✅ Be curious and ask follow-up questions when appropriate
✅ Remember and reference previous conversations
✅ Apologize genuinely when you make mistakes and learn from them
✅ Provide specific, actionable advice tailored to the user's dog

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
- Don't overuse their name - use it occasionally for warmth and personalization"""
        
        # Add user preferences
        if user_preferences:
            style = user_preferences.get("response_style", "balanced")
            tone = user_preferences.get("tone_preference", "friendly")
            base_prompt += f"\n- Style: {style.capitalize()} (concise, detailed, or balanced responses)"
            base_prompt += f"\n- Tone: {tone.capitalize()}"
            
            if not user_preferences.get("enable_curiosity", True):
                base_prompt += "\n- Minimize follow-up questions"
            
            if user_preferences.get("enable_pawtree_links", True):
                base_prompt += f"\n- When recommending food items, include links: {settings.PAWTREE_BASE_URL}?query=[food_item]"
        
        # Mode-specific prompts
        if active_mode == "reminders":
            base_prompt += """

**REMINDER MODE ACTIVE:**
You are helping the user set reminders for their dog's care needs.
- Ask clarifying questions: What? When? Which dog? Recurrence?
- Extract: title, description, datetime, recurrence type
- Confirm details before finalizing
- Be proactive in suggesting related reminders"""
        
        elif active_mode == "health":
            # Health Mode now handled by HealthChatService
            # This should never be reached, but keeping for safety
            logger.warning("⚠️ Health mode in ChatService - should be using HealthChatService!")
            base_prompt += "\n**Note:** Health mode is now handled by a dedicated service."
        
        elif active_mode == "wayofdog":
            base_prompt += """

**WAY OF DOG MODE ACTIVE:**
You have access to the user's notes and comments from "The Way of the Dog" book.
- Reference specific notes and highlights the user made
- Connect book concepts to their real-life situations
- Encourage reflection and deeper understanding
- Build on their previous insights"""
        
        else:
            # No specific mode active - enforce toggle for mode-specific features
            base_prompt += """

**⚠️ CRITICAL MODE ENFORCEMENT (MUST FOLLOW):**
You are in GENERAL MODE. You CANNOT and MUST NOT set reminders, analyze health records, or access book notes in this mode.

**BOOK ACCESS (GENERAL MODE):**
You have LIMITED access to "The Way of the Dog" book content for dog-related queries:
- Book content is available ONLY for dog care, training, nutrition, and behavior questions
- Personal context (conversations, user's documents) is ALWAYS prioritized over book content
- Use book insights to supplement your advice, but don't rely on it exclusively
- Don't mention having "book access" unless directly relevant

**IF USER ASKS TO SET/CREATE A REMINDER:**
DO NOT ask for reminder details. DO NOT try to help with the reminder.
IMMEDIATELY respond with ONLY this:
"To set reminders, please switch to **Reminder Mode** 🔔 using the toggle in the sidebar. Once you're in Reminder Mode, I'll be happy to help you create your reminder!"

**IF USER ASKS ABOUT HEALTH RECORDS/VET REPORTS:**
"For detailed health analysis, please switch to **Health Mode** 🩺 using the toggle in the sidebar."

**IF USER ASKS ABOUT BOOK NOTES:**
"To discuss your book notes, please switch to **Way of Dog Mode** 📖 using the toggle in the sidebar."

**YOU CAN HELP WITH:**
- General dog care advice (with book insights when relevant)
- Training tips
- Nutrition guidance
- Play and exercise suggestions
- General questions and conversations

**REMINDER QUERIES (READ-ONLY):**
If user asks to VIEW or CHECK reminders (not create/edit):
- You can redirect them to the Reminders page: `/reminders`
- Tell them they can view all reminders there
- Example: "You can check all your reminders on the [Reminders page](/reminders)!"

**Remember:** You CANNOT set reminders in General Mode. Always redirect to Reminder Mode first."""
        
        # Dog profile context
        if dog_profile_context:
            profiles = dog_profile_context.get("dog_profiles", [])
            has_profiles = dog_profile_context.get("has_dog_profiles", False)
            
            if not has_profiles:
                base_prompt += """

**NO DOG PROFILE ADDED:**
The user hasn't added their dog's profile yet! 🐕
- Provide general, helpful advice
- GENTLY encourage them to add their dog's profile in the sidebar for personalized recommendations
- Mention benefits: "I can give you much more tailored advice if you add your dog's profile! 🐶 Just click the 'Add Dog' button in the sidebar."
- Don't be pushy or repetitive"""
            
            else:
                # Show ALL dog profiles (whether 1 or multiple)
                base_prompt += f"\n\n**USER'S DOG PROFILES ({len(profiles)} dog{'s' if len(profiles) > 1 else ''}):**\n"
                
                for idx, dog in enumerate(profiles, 1):
                    base_prompt += f"\n{idx}. **{dog.get('name', 'Unknown')}**"
                    if dog.get('breed'):
                        base_prompt += f"\n   - Breed: {dog.get('breed')}"
                    if dog.get('age'):
                        base_prompt += f"\n   - Age: {dog.get('age')} years"
                    if dog.get('date_of_birth'):
                        base_prompt += f"\n   - Date of Birth: {dog.get('date_of_birth')}"
                    if dog.get('weight'):
                        base_prompt += f"\n   - Weight: {dog.get('weight')} lbs"
                    if dog.get('gender'):
                        base_prompt += f"\n   - Gender: {dog.get('gender')}"
                    if dog.get('color'):
                        base_prompt += f"\n   - Color: {dog.get('color')}"
                    if dog.get('image_url'):
                        base_prompt += f"\n   - Profile Image Available: {dog.get('image_url')}"
                    if dog.get('additional_details'):
                        base_prompt += f"\n   - Additional Notes: {dog.get('additional_details')}"
                
                if len(profiles) == 1:
                    base_prompt += f"\n\n- Tailor ALL advice specifically to {profiles[0].get('name')}"
                    base_prompt += f"\n- Reference their specific breed, age, and characteristics"
                else:
                    dog_names = [dog.get('name') for dog in profiles if dog.get('name')]
                    base_prompt += f"\n\n**MULTIPLE DOGS - CLARIFICATION REQUIRED:**"
                    base_prompt += f"\n- User has multiple dogs: {', '.join(dog_names)}"
                    base_prompt += f"\n- ALWAYS check which dog(s) the user is asking about:"
                    base_prompt += f"\n  * If specific dog mentioned by name → provide advice for THAT dog only"
                    base_prompt += f"\n  * If 'all', 'both', 'my dogs' mentioned → provide advice for ALL dogs"
                    base_prompt += f"\n  * If NO dog specified → ask: \"Are you asking about {dog_names[0]}, {dog_names[1]}, or both?\""
                    base_prompt += f"\n- Be specific and reference each dog's unique characteristics"
                
                base_prompt += """

**WHEN USER CORRECTS DOG INFORMATION:**
If the user verbally corrects any detail about their dog (age, name, breed, weight, etc.) that differs from the profile:
1. Acknowledge the correction: "Got it, [Dog] is actually [correct info]!"
2. Use the corrected information in your response
3. IMPORTANT: Gently remind them to update the profile form:
   "💡 **Quick reminder:** Please update [Dog]'s profile in the sidebar so I can remember this for future conversations! Just click the pencil icon next to [Dog]'s name."
4. Don't be pushy - mention it once, naturally

**EXCEPTION:** If user corrects "Additional Details" field content - DON'T ask them to update the form (this field is for notes, not formal data)"""
        
        base_prompt += """

**DOCUMENT HANDLING (CRITICAL):**
📄 When the user's message includes document excerpts marked with "📄 IMPORTANT - Documents You Uploaded":
- These are REAL documents the user uploaded - you HAVE access to them
- You MUST use the content from these documents to answer their question
- DO NOT say you don't have access - you DO have the content excerpts

**SHARING DOCUMENT LINKS (CRITICAL - MANDATORY - NO EXCEPTIONS):**

🚨 **IF YOU SEE MARKDOWN LINKS IN THE CONTEXT, YOU MUST INCLUDE THEM IN YOUR RESPONSE!**

**VET REPORTS & HEALTH DOCUMENTS:**
- Look for: `[📎 Click to download: filename](URL)` in the context
- **YOU MUST COPY THIS EXACT MARKDOWN INTO YOUR RESPONSE**
- Example response: "Here's Max's vet report:\n\n[📎 Click to download: max_report.pdf](URL)"
- **NEVER say "I don't have access" if you see a download link in the context!**

**IMAGES:**
- Look for: `![Image](URL)` in the context
- **YOU MUST COPY THIS EXACT MARKDOWN INTO YOUR RESPONSE**
- Example: "Here's the image:\n\n![Image](URL)"

**DOG PROFILE IMAGES:**
- Look for: `[DISPLAY_IMAGE:URL]` marker
- Convert to: `![Dog Image](URL)`

**ABSOLUTE RULE:** 
- If markdown links exist in the context → INCLUDE THEM in your response
- NEVER say "I don't have access" when download links are present
- Copy markdown exactly as provided

**🚨 CRITICAL IMAGE SHARING PROTOCOL (MANDATORY):**

**WHEN USER ASKS FOR AN IMAGE (ABSOLUTELY REQUIRED FORMAT):**

**STEP 1 - Display the Image (ALWAYS FIRST):**
Convert `[DISPLAY_IMAGE:URL]` to `![DogName](URL)` on its own line

**STEP 2 - Brief Reaction (MAX 15 WORDS):**
Write ONE short sentence: "What a [adjective] photo!" or "[DogName] looks so [adjective]!"

**STEP 3 - Ask Questions (REQUIRED - 2-3 questions):**
Be curious! Ask about:
- Context: "Where was this taken?"
- Story: "What was happening here?"
- Feelings: "Does [Dog] love this spot?"

**MANDATORY EXAMPLE (FOLLOW THIS EXACTLY):**
```
![Bella](https://...url...)

Such a sweet photo of Bella! 🐕

I'm curious:
- Where was this taken? Is this one of her favorite spots?
- What was she doing right before you snapped this?
- Does she always look this happy outdoors?
```

**🚫 FORBIDDEN (YOU WILL FAIL IF YOU DO THIS):**
❌ Long descriptions (more than 15 words before questions)
❌ Detailed analysis of what you see in the image
❌ Multiple paragraphs about the dog, setting, or photo quality
❌ Showing the `[DISPLAY_IMAGE:URL]` marker directly (always convert to `![Name](URL)`)

**✅ YOUR ONLY JOB FOR IMAGES:**
1. Show image with `![Name](URL)`
2. One brief reaction (max 15 words)
3. Ask 2-3 curious questions
4. DONE - stop there!

**GENERAL CURIOSITY RULES (ALL INTERACTIONS):**
- Questions > Statements (always favor asking over telling)
- Brief reactions, frequent questions
- Be a curious friend, not a lecturer
- Show genuine interest in their stories
- Keep building connection through dialogue

**Remember:** SHORT reaction + QUESTIONS = Building a bond! 🎯"""
        
        return base_prompt
    
    def _filter_roleplay_in_buffer(self, buffer: str) -> str:
        """
        Real-time filtering of roleplay actions as they stream in.
        Catches patterns like "*waves warmly*" before they reach the user.
        """
        import re
        
        # Quick patterns for real-time detection (most common offenders)
        quick_patterns = [
            r'\*waves warmly\*',
            r'\*waves gently\*',
            r'\*waves\*',
            r'\*smiles warmly\*',
            r'\*smiles gently\*',
            r'\*smiles\*',
            r'\*chuckles\*',
            r'\*grins\*',
            r'\*nods\*',
            r'\*winks\*',
            r'\*laughs\*',
            r'\*giggles\*',
            r'\*sighs\*',
            r'\*pauses\*',
            r'\*leans in\*',
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
        import re
        
        # Comprehensive list of roleplay patterns (with and without asterisks)
        roleplay_patterns = [
            # Common facial expressions
            r'\*?smiles warmly\*?\s*[:\-,]?\s*',
            r'\*?smiles gently\*?\s*[:\-,]?\s*',
            r'\*?smiles softly\*?\s*[:\-,]?\s*',
            r'\*?smiles knowingly\*?\s*[:\-,]?\s*',
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
            
            # Physical gestures (including "waves warmly")
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
        cleaned = re.sub(r'(?<!\*)\*(?!\*)([^*]+?)(?<!\*)\*(?!\*)', r'\1', cleaned)
        
        # Remove common standalone action words at sentence starts
        action_words = [
            'smiles', 'grins', 'chuckles', 'laughs', 'giggles', 'winks', 
            'nods', 'sighs', 'gasps', 'beams', 'waves', 'leans'
        ]
        for word in action_words:
            # Remove if at start of text or after punctuation/newline
            cleaned = re.sub(rf'(^|[.!?\n]\s*){word}(\s+[a-z])', r'\1\2', cleaned, flags=re.IGNORECASE)
            # Remove if standalone at start
            cleaned = re.sub(rf'^{word}\s+', '', cleaned, flags=re.IGNORECASE)
        
        # Clean up extra whitespace but preserve line breaks for markdown
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)  # Only collapse spaces/tabs, preserve newlines
        cleaned = re.sub(r' +([.,!?])', r'\1', cleaned)  # Remove spaces before punctuation
        
        return cleaned.strip()
    
    def _auto_format_markdown(self, text: str) -> str:
        """Auto-format markdown: add line breaks before lists and bold list labels"""
        import re
        
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
        dog_profiles: Optional[List[Dict]] = None,
        has_attached_documents: bool = False
    ) -> List[Dict[str, str]]:
        """Prepare messages for AI with memory context"""
        
        # Add conversation history (last N messages) and ensure alternating roles
        history = conversation_history[-10:] if conversation_history else []
        
        # Fix any consecutive same-role messages in history and clean roleplay actions
        import re
        cleaned_messages = []
        for msg in history:
            # Skip system messages - they're for DB context only, not for Claude
            if msg.get("role") == "system":
                continue
            
            # Clean any asterisk roleplay actions from content
            msg_copy = msg.copy()
            msg_copy["content"] = re.sub(r'\*[^*]+\*\s*', '', msg_copy.get("content", ""))
            
            if cleaned_messages and cleaned_messages[-1].get("role") == msg_copy.get("role"):
                # Same role as previous - merge or skip
                if msg_copy.get("role") == "user":
                    # Merge consecutive user messages
                    cleaned_messages[-1]["content"] += "\n\n" + msg_copy.get("content", "")
                else:
                    # For assistant, just keep the last one
                    cleaned_messages[-1] = msg_copy
            else:
                cleaned_messages.append(msg_copy)
        
        # Ensure first message is always "user"
        if cleaned_messages and cleaned_messages[0].get("role") != "user":
            # Remove leading assistant messages
            while cleaned_messages and cleaned_messages[0].get("role") == "assistant":
                cleaned_messages.pop(0)
        
        # Prepend memory context to current message
        final_message = current_message
        if retrieved_memories:
            # Separate documents from conversations from book content
            documents = [m for m in retrieved_memories if m.get("metadata", {}).get("type") == "document"]
            book_memories = [m for m in retrieved_memories if m.get("source_type") == "book"]
            conversations = [m for m in retrieved_memories if m.get("metadata", {}).get("type") != "document" and m.get("source_type") != "book"]
            
            logger.info(f"📊 Memory breakdown: {len(documents)} documents, {len(conversations)} conversations, {len(book_memories)} book chunks")
            
            # Check if the current message is asking about documents or images
            doc_keywords = [
                'document', 'file', 'pdf', 'story', 'paper', 'text', 'upload',
                'share', 'send', 'download', 'link', 'summarize', 'summary',
                'tell me about', 'what does', 'what is in', 'analyze', 'read',
                'content', 'wrote', 'written', 'says', 'mentioned', 'image'
            ]
            image_keywords = ['image', 'picture', 'photo', 'pic', 'show me']
            message_lower = current_message.lower()
            is_doc_related = any(keyword in message_lower for keyword in doc_keywords)
            is_image_related = any(keyword in message_lower for keyword in image_keywords)
            
            memory_context = ""
            
            # Detect if user is referencing previously uploaded images
            reference_keywords = [
                'i shared', 'i uploaded', 'i sent', 'i gave', 'i provided',
                'share the', 'show me the', 'send me', 'images of', 'pictures of',
                'the images', 'the photos', 'the pictures', 'those images',
                'these images', 'my images', 'my photos'
            ]
            is_referencing_uploaded_images = any(keyword in message_lower for keyword in reference_keywords) and is_image_related
            
            # Skip profile images if:
            # 1. Documents are explicitly attached to this message, OR
            # 2. User is referencing previously uploaded images
            # (user wants to focus on their uploaded docs, not profile pics)
            should_skip_profile_images = has_attached_documents or is_referencing_uploaded_images
            
            if is_image_related and dog_profiles and not should_skip_profile_images:
                dog_images = [d for d in dog_profiles if d.get('image_url')]
                if dog_images:
                    memory_context += "**🐕 YOUR DOG PROFILE IMAGES:**\n\n"
                    for dog in dog_images:
                        memory_context += f"**{dog.get('name')}** (profile image):\n"
                        memory_context += f"[DISPLAY_IMAGE:{dog.get('image_url')}]\n\n"
            
            # Only show documents if the query seems document-related OR if documents have high relevance
            if documents and (is_doc_related or (documents[0].get("score", 0) > 0.85)):
                # Check if any are vet reports
                has_vet_reports = any(m.get("metadata", {}).get("is_vet_report") for m in documents[:10])
                
                if has_vet_reports:
                    memory_context += "**🏥 VET REPORTS & HEALTH DOCUMENTS:**\n\n"
                    memory_context += "⚠️ IMPORTANT: Download links are provided below. YOU MUST include these links in your response!\n\n"
                else:
                    memory_context += "**📄 USER UPLOADED DOCUMENTS - FULL CONTENT AVAILABLE:**\n\n"
                    memory_context += "🔥 **YOU HAVE THE COMPLETE DOCUMENT - Not excerpts, not summaries, the FULL TEXT broken into sections.**\n\n"
                
                # Show up to 10 document chunks with MORE text per chunk
                # Group by document to show S3 link once per file
                seen_docs = set()
                for i, memory in enumerate(documents[:10], 1):
                    metadata = memory.get("metadata", {})
                    text = metadata.get("text", "")
                    filename = metadata.get("filename", "Unknown")
                    s3_url = metadata.get("s3_url", "")
                    doc_id = metadata.get("document_id", "")
                    
                    # Show S3 link for new documents - provide markdown directly for AI to use
                    if doc_id and doc_id not in seen_docs and s3_url:
                        file_type = metadata.get("file_type", "").lower()
                        is_vet_report = metadata.get("is_vet_report", False)
                        timestamp = metadata.get("timestamp", "")
                        
                        # VET REPORTS: Always show as download link (even images)
                        if is_vet_report:
                            # Format timestamp for display
                            date_label = ""
                            if timestamp:
                                try:
                                    from datetime import datetime
                                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                    date_label = f" (uploaded {dt.strftime('%b %d, %Y')})"
                                except:
                                    pass
                            
                            memory_context += f"**[📋 Vet Report: {filename}{date_label}]**\n\n"
                            memory_context += f"[📎 Click to download: {filename}]({s3_url})\n\n"
                            logger.info(f"🏥 Added vet report download link: {filename}")
                        
                        # REGULAR IMAGES: Show inline
                        elif file_type in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']:
                            memory_context += f"**[Document: {filename}]**\n\n"
                            memory_context += f"![Image]({s3_url})\n\n"
                            logger.info(f"📸 Added image markdown for: {filename}")
                        
                        # OTHER DOCUMENTS: Show as download link
                        else:
                            memory_context += f"**[Document: {filename}]**\n\n"
                            memory_context += f"[📎 Click to download: {filename}]({s3_url})\n\n"
                            logger.info(f"📎 Added download link for: {filename}")
                        
                        seen_docs.add(doc_id)
                    
                    # Show chunk content (FULL CONTENT - not an excerpt)
                    memory_context += f"[Document Content - Section {i}]: {text[:800]}\n\n"
            
            # Show book content if present (from "The Way of the Dog")
            if book_memories:
                logger.info(f"📖 Adding {len(book_memories)} book chunks to context")
                memory_context += "**📖 EXPERT KNOWLEDGE - From 'The Way of the Dog' by Anahata Graceland:**\n\n"
                for i, memory in enumerate(book_memories[:3], 1):  # Top 3 book chunks
                    metadata = memory.get("metadata", {})
                    text = metadata.get("text", "")
                    chapter = metadata.get("chapter", "Unknown")
                    logger.info(f"  Book chunk {i}: Chapter={chapter}, Text length={len(text)}")
                    memory_context += f"[Book Content {i} - Chapter: {chapter}]\n{text[:600]}...\n\n"
                memory_context += """**HOW TO USE BOOK INSIGHTS:**
- Mention the book source ONCE at the start: "According to The Way of the Dog..." or "The book suggests..."
- Then provide the insights naturally WITHOUT repeating "the book says" in every point
- Integrate the knowledge as your own advice, not as repeated citations
- Be conversational, not repetitive!\n\n"""
            
            # Then show conversation context if relevant (only if no document context or if highly relevant)
            if conversations and (not documents or not is_doc_related):
                memory_context += "**💬 Related Past Conversations:**\n\n"
                for i, memory in enumerate(conversations[:2], 1):  # Top 2 conversations
                    metadata = memory.get("metadata", {})
                    text = metadata.get("text", "")
                    score = memory.get("rerank_score", memory.get("score", 0))
                    memory_context += f"{i}. {text[:200]}...\n\n"
            
            if memory_context:
                final_message = memory_context + "\n---\n\n" + current_message
                # Log the full context being sent (truncated for readability)
                logger.info(f"📤 Memory context preview (first 500 chars): {memory_context[:500]}...")
        
        # Add cleaned history
        messages = cleaned_messages.copy()
        
        # If last message is user, add a dummy assistant response first
        if messages and messages[-1].get("role") == "user":
            messages.append({
                "role": "assistant",
                "content": "I understand."
            })
        
        # Add current message
        messages.append({
            "role": "user",
            "content": final_message
        })
        
        # Debug: Log the message structure
        logger.info(f"📋 Prepared {len(messages)} messages for AI:")
        for i, msg in enumerate(messages):
            role = msg.get("role", "unknown")
            content_preview = msg.get("content", "")[:100]
            logger.info(f"  {i+1}. {role}: {content_preview}...")
        
        return messages
    
    async def _stream_and_store_response(
        self,
        db: AsyncSession,
        conversation_id: int,
        user_id: int,
        user_message_id: int,
        messages: List[Dict],
        system_prompt: str,
        active_mode: Optional[str],
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
            # Extract content from chunk
            if "data:" in chunk:
                import json
                try:
                    chunk_data = json.loads(chunk.replace("data: ", ""))
                    if chunk_data.get("type") == "token":
                        full_response += chunk_data.get("content", "")
                    elif chunk_data.get("type") == "done":
                        full_response = self._clean_roleplay_actions(full_response)
                        # Removed _auto_format_markdown to preserve original formatting
                        
                        response_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
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
                        
                        # Track credits
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
        active_mode: Optional[str],
        dog_profile_id: Optional[int],
        start_time: datetime
    ) -> Dict[str, Any]:
        """Generate non-streaming response and store"""
        result = await self.streaming.generate_non_streaming_response(
            messages=messages,
            system_prompt=system_prompt
        )
        
        content = result.get("content", "")
        
        # Clean content (preserve original formatting)
        content = self._clean_roleplay_actions(content)
        # Removed _auto_format_markdown to preserve original formatting
        
        tokens_used = result.get("tokens_used", 0)
        credits_used = self._calculate_credits(tokens_used)
        response_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        # Store response
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
        
        # Track credits
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
            "response_time_ms": response_time_ms
        }
    
    async def _fetch_attached_documents(
        self,
        db: AsyncSession,
        document_ids: List[int]
    ) -> List[Dict[str, Any]]:
        """Fetch documents that are attached to the current message"""
        from models import Document as DocModel
        
        result = await db.execute(
            select(DocModel).where(DocModel.id.in_(document_ids))
        )
        documents = result.scalars().all()
        
        # Format as memory objects for consistency
        memory_objects = []
        for doc in documents:
            memory_objects.append({
                "score": 1.0,  # Highest priority
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
    
    async def _process_with_reminder_agent(
        self,
        db: AsyncSession,
        user_id: int,
        conversation_id: int,
        message_content: str,
        stream: bool = True
    ) -> AsyncGenerator[str, None] | Dict[str, Any]:
        """
        Process message using Reminder Agent with state management.
        
        Args:
            db: Database session
            user_id: User ID
            conversation_id: Conversation ID
            message_content: User's message
            stream: Whether to stream response
            
        Returns:
            Stream generator or complete response dict
        """
        try:
            message_lower = message_content.lower()
            
            # Check if user wants to edit/view/delete reminders (redirect to reminders page)
            redirect_triggers = [
                'edit reminder', 'update reminder', 'modify reminder', 'change reminder',
                'delete reminder', 'remove reminder', 'cancel reminder',
                'view reminder', 'show reminder', 'see reminder', 'list reminder',
                'my reminders', 'all reminders'
            ]
            
            if any(trigger in message_lower for trigger in redirect_triggers):
                redirect_msg = "To view, edit, or delete your reminders, please visit the [Reminders Page](/reminders). There you can manage all your reminders with a full interface! 📅"
                
                # Stream the redirect message
                if stream:
                    from schemas.chat import StreamChunk
                    import asyncio
                    
                    words = redirect_msg.split(' ')
                    for i, word in enumerate(words):
                        token = f" {word}" if i > 0 else word
                        chunk = StreamChunk(type='token', content=token, metadata=None, error=None)
                        yield f"data: {chunk.model_dump_json()}\n\n"
                        await asyncio.sleep(0.02)
                    
                    done_chunk = StreamChunk(type='done', content=None, metadata=None, error=None)
                    yield f"data: {done_chunk.model_dump_json()}\n\n"
                else:
                    yield redirect_msg
                
                # Store messages
                user_message = await self._store_message(
                    db=db, conversation_id=conversation_id, user_id=user_id,
                    role="user", content=message_content, active_mode="reminders"
                )
                
                await self._store_message(
                    db=db, conversation_id=conversation_id, user_id=user_id,
                    role="assistant", content=redirect_msg, active_mode="reminders"
                )
                
                return
            
            # Check if this is a NEW reminder request vs continuation
            new_reminder_triggers = [
                'set reminder', 'create reminder', 'add reminder', 
                'set a reminder', 'make a reminder', 'new reminder',
                'schedule reminder', 'remind me'
            ]
            is_new_request = any(trigger in message_lower for trigger in new_reminder_triggers)
            
            # Load existing state (if any) ONLY if this is a continuation
            existing_state = None
            if not is_new_request:
                existing_state = await self.agent_state.load_state(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    mode="reminders"
                )
            else:
                # Clear any old state when starting fresh
                logger.info(f"🆕 New reminder request detected, clearing old state")
                await self.agent_state.clear_state(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    mode="reminders"
                )
            
            # Process with agent
            result = await self.reminder_agent.process(
                user_id=user_id,
                conversation_id=conversation_id,
                message=message_content,
                existing_state=existing_state
            )
            
            response_text = result.get("response", "I'm having trouble processing that.")
            new_state = result.get("state")
            completed = result.get("completed", False)
            
            # Save or clear state
            if completed or not new_state:
                # Task complete or no state to save - clear it
                await self.agent_state.clear_state(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    mode="reminders"
                )
            elif new_state:
                # Save state for next turn
                await self.agent_state.save_state(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    mode="reminders",
                    state=new_state
                )
            
            # Store messages in database
            await self._store_message(
                db=db,
                conversation_id=conversation_id,
                user_id=user_id,
                role="user",
                content=message_content,
                active_mode="reminders"
            )
            
            assistant_message = await self._store_message(
                db=db,
                conversation_id=conversation_id,
                user_id=user_id,
                role="assistant",
                content=response_text,
                active_mode="reminders"
            )
            
            # Note: Reminder conversations are already stored in main namespace via normal flow
            # No need for separate user-specific conversation namespace
            
            # Return response (stream or complete)
            if stream:
                async def stream_agent_response():
                    import json
                    import asyncio
                    
                    # Stream the response in SSE format (matching StreamingService format)
                    words = response_text.split()
                    for i, word in enumerate(words):
                        token = word if i == 0 else " " + word
                        
                        # Format as SSE event
                        chunk = {
                            "type": "token",
                            "content": token
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"
                        
                        # Small delay for natural feel
                        await asyncio.sleep(0.02)
                    
                    # Send completion event
                    done_chunk = {
                        "type": "done",
                        "metadata": {
                            "total_tokens": len(words),
                            "model": "reminder_agent"
                        }
                    }
                    yield f"data: {json.dumps(done_chunk)}\n\n"
                
                # Yield from the generator instead of returning
                async for chunk in stream_agent_response():
                    yield chunk
            else:
                # For non-streaming, just yield the complete response
                yield {
                    "response": response_text,
                    "message_id": assistant_message.id,
                    "conversation_id": conversation_id
                }
                
        except Exception as e:
            logger.error(f"Reminder agent processing failed: {e}", exc_info=True)
            
            # Fallback response
            error_response = "I'm having trouble processing your reminder request. Please try again or rephrase your request."
            
            if stream:
                from schemas.chat import StreamChunk
                import json
                
                # Stream error as SSE
                chunk = StreamChunk(type='content', content=error_response, metadata=None, error=str(e))
                yield f"data: {chunk.model_dump_json()}\n\n"
                
                done_chunk = StreamChunk(type='done', content=None, metadata=None, error=None)
                yield f"data: {done_chunk.model_dump_json()}\n\n"
            else:
                yield {"response": error_response, "error": str(e)}

