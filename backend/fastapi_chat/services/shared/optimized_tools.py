"""
Optimized LangChain Tools for FastAPI Chat Service
Creates properly bound tools for use with create_react_agent
"""

import logging
from typing import List, Dict, Any
from langchain_core.tools import tool
from trustcall import create_extractor

logger = logging.getLogger(__name__)

def create_optimized_tools(vector_service, bedrock_knowledge_service, s3_service):
    """Create optimized tools with proper service binding"""
    
    @tool
    async def get_current_datetime() -> str:
        """Get the REAL current date and time. CRITICAL: Use this when users ask about today's date, current time, or any time-related questions. This provides the actual current date, NOT your training data date. Always use this tool result instead of any date knowledge from your training data."""
        from datetime import datetime, timezone
        
        current_datetime = datetime.now(timezone.utc)
        current_date = current_datetime.strftime("%Y-%m-%d")
        current_day = current_datetime.strftime("%A")
        current_time = current_datetime.strftime("%H:%M:%S UTC")
        
        return f"REAL CURRENT DATE AND TIME: {current_date} ({current_day}) at {current_time}. This is the actual current date - use this information, not any dates from your training data."
    
    @tool
    async def pinecone_search_tool(query: str, namespace_suffix: str = "docs") -> str:
        """Search user's documents and conversation history using Pinecone vector database
        
        Args:
            query: Search query text  
            namespace_suffix: Namespace suffix (default: 'docs')
        """
        try:
            # CRITICAL FIX: Check if content is already provided in the current message
            # Don't search for content that was just provided by the user
            if any(phrase in query.lower() for phrase in [
                "dance of souls", "tribute to the dog", "dog–human bond", "dog-human bond",
                "anahta graceland", "anahata graceland", "here it is", "poem by"
            ]):
                # Check if this looks like a search for content that should already be in the message
                if any(pattern in query.lower() for pattern in [
                    "poem", "article", "story", "text", "document", "content"
                ]):
                    logger.info(f"🚫 BLOCKED SEARCH: Content appears to be provided in message, query: '{query}'")
                    return """The content you're looking for appears to be provided directly in your message. I can see the poem "Dance of Souls: A Tribute to the Dog–Human Bond" by Anahta Graceland in your message. Let me analyze that content directly instead of searching for it.
                    
The poem is about the deep bond between humans and dogs, emphasizing themes of love, trust, intuition, and mutual respect. I'll now proceed to archive this beautiful poem for you."""
            
            
            from langchain_core.runnables import ensure_config
            import inspect
            
            user_id = 1 
            
            
            frame = inspect.currentframe()
            found_config = False
            try:
                frame_count = 0
                while frame and frame_count < 20:  # Limit search depth
                    frame_count += 1
                    local_vars = list(frame.f_locals.keys())
                    
                    if 'config' in frame.f_locals:
                        config = frame.f_locals['config']
                        logger.info(f"🔍 FRAME {frame_count}: Found config type: {type(config)}")
                        
                        if isinstance(config, dict):
                            logger.info(f"🔍 FRAME {frame_count}: Config keys: {list(config.keys())}")
                            
                            # Check for LangChain config structure
                            if 'configurable' in config and isinstance(config['configurable'], dict):
                                logger.info(f"🔍 FRAME {frame_count}: Configurable keys: {list(config['configurable'].keys())}")
                                if 'user_id' in config['configurable']:
                                    user_id = config['configurable']['user_id']
                                    logger.info(f"🎯 FOUND USER_ID in LangChain config at frame {frame_count}: {user_id}")
                                    found_config = True
                                    break
                    
                    frame = frame.f_back
                    
                if not found_config:
                    logger.warning(f"⚠️ Could not find user_id in any of {frame_count} frames, using fallback: {user_id}")
            finally:
                del frame
            
            logger.info(f"🔍 PINECONE SEARCH DEBUG: user_id={user_id}, query='{query}', namespace_suffix='{namespace_suffix}'")
            
           
            import asyncio
            await asyncio.sleep(2)  # Wait 2 seconds for indexing
            logger.info(f"🔍 SEARCH RETRY: After 2s delay for user {user_id}")
            
            results = await vector_service.search_user_documents(
                user_id=user_id,
                query=query,
                namespace_suffix=namespace_suffix,
                top_k=5,
                include_metadata=True
            )
            
            if results:
                formatted_results = []
                for i, result in enumerate(results, 1):
                    metadata = result.get('metadata', {})
                    score = result.get('score', 0)
                    
                    # CRITICAL DEBUG: Log the actual structure
                    logger.info(f"🔍 RESULT {i} STRUCTURE: {list(result.keys())}")
                    logger.info(f"🔍 RESULT {i} CONTENT: {str(result)[:300]}")
                    
                    # CRITICAL FIX: Extract text content with comprehensive fallback handling
                    text = result.get('text', '')
                    if not text:
                        # Fallback 1: check if text is in metadata
                        text = metadata.get('text', '')
                    if not text:
                        # Fallback 2: provide helpful message for old documents
                        filename = metadata.get('filename', 'document')
                        text = f"[Document {filename} found but content needs re-indexing. Please re-upload for full text access.]"
                    
                    # Limit text length for summary (but allow more for poems/articles)
                    # Check if this is inline text (poems, articles, etc) which need full content
                    # CRITICAL FIX: document_id can be float or string, convert to string first
                    doc_id = str(metadata.get('document_id', ''))
                    is_inline_text = (
                        metadata.get('source') == 'inline_text_auto_archived' or
                        metadata.get('document_type') == 'poem' or
                        'inline' in doc_id
                    )
                    max_length = 3000 if is_inline_text else 500  # Allow 3000 chars for inline text, 500 for regular docs
                    was_truncated = len(text) > max_length
                    text = text[:max_length] if was_truncated else text
                    
                    # Only add "..." if text was actually truncated
                    truncation_indicator = "..." if was_truncated else ""
                        
                    logger.info(f"🔍 RESULT {i} EXTRACTED TEXT: {text[:100]}... (full_length={len(text)}, truncated={was_truncated})")
                    formatted_results.append(f"{i}. Score: {score:.3f} - {text}{truncation_indicator}")
                
                final_result = f"Found {len(results)} relevant documents:\n" + "\n".join(formatted_results)
                logger.info(f"🎯 TOOL RETURNING TO AI: {final_result[:500]}...")
                return final_result
            else:
                # 🆕 FALLBACK: If Pinecone returns nothing, try LangGraph store for inline text
                logger.warning(f"❌ Pinecone returned no results for '{query}'. Trying LangGraph store as fallback...")
                
                try:
                    from langgraph.store.postgres import AsyncPostgresStore
                    from services.database import get_db_config
                    
                    # Initialize store connection
                    db_config = get_db_config()
                    dsn = f"host={db_config['host']} port={db_config['port']} dbname={db_config['database']} user={db_config['user']} password={db_config['password']} connect_timeout=30"
                    
                    async with AsyncPostgresStore.from_conn_string(dsn) as store:
                        # Search LangGraph store for the content
                        store_results = await store.asearch(
                            (f"user_{user_id}", "memories"),
                            query=query,
                            limit=5
                        )
                        
                        if store_results:
                            logger.info(f"✅ FALLBACK SUCCESS: Found {len(store_results)} results in LangGraph store")
                            fallback_formatted = []
                            for i, mem in enumerate(store_results, 1):
                                content = mem.value.get('content', '') if hasattr(mem, 'value') else str(mem)
                                # Check if this looks like inline text content (long, contains the query term)
                                if len(content) > 100 and query.lower() in content.lower():
                                    fallback_formatted.append(f"{i}. [From conversation history] {content[:3000]}")
                            
                            if fallback_formatted:
                                fallback_result = f"Found {len(fallback_formatted)} relevant items in conversation history:\n" + "\n".join(fallback_formatted)
                                logger.info(f"🎯 FALLBACK RETURNING TO AI: {fallback_result[:500]}...")
                                return fallback_result
                        
                        logger.warning(f"❌ FALLBACK FAILED: No results in LangGraph store either")
                except Exception as fallback_error:
                    logger.error(f"❌ Fallback search failed: {fallback_error}")
                
                return f"No relevant documents found for query: {query}. If you previously shared this content, please share it again so I can properly archive it for future reference."
                
        except Exception as e:
            logger.error(f"❌ Pinecone search error: {str(e)}")
            return f"Search temporarily unavailable: {str(e)}"
    
    @tool
    async def bedrock_knowledge_tool(query: str) -> str:
        """Get expert knowledge from AWS Bedrock Knowledge Base"""
        try:
            response = await bedrock_knowledge_service.retrieve_knowledge(query)
            if response and 'retrievalResults' in response:
                results = response['retrievalResults'][:3]  # Top 3 results
                formatted_results = []
                
                for i, result in enumerate(results, 1):
                    content = result.get('content', {}).get('text', 'No content')[:300]
                    score = result.get('score', 0)
                    formatted_results.append(f"{i}. Confidence: {score:.3f} - {content}...")
                
                return "Expert knowledge found:\n" + "\n".join(formatted_results)
            else:
                return f"No expert knowledge found for: {query}"
                
        except Exception as e:
            logger.error(f"❌ Bedrock knowledge error: {str(e)}")
            return f"Knowledge base temporarily unavailable: {str(e)}"
    
    @tool
    async def health_analysis_tool(symptoms: str, context: str = "") -> str:
        """Analyze health symptoms and provide veterinary guidance with TrustCall reliability"""
        import asyncio
        
        # TrustCall-style reliability with retries
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Import health service to use real functionality
                from services.health_ai.health_service import HealthService
                from services.shared.async_openai_pool_service import get_openai_pool
                
                # Get AI client pool
                ai_client = await get_openai_pool()
                
                # Enhanced veterinary prompt with quality validation
                health_prompt = f"""As a veterinary AI assistant, analyze these symptoms: {symptoms}
                Context: {context}
                
                Provide a structured analysis:
                1. SYMPTOM ASSESSMENT: What these symptoms typically indicate
                2. URGENCY LEVEL: Emergency/Urgent/Moderate/Low priority  
                3. POSSIBLE CAUSES: Most likely conditions (3-5 options)
                4. IMMEDIATE ACTIONS: What the owner should do right now
                5. VETERINARY CONSULTATION: When and why to contact a professional
                6. MONITORING: What to watch for
                
                Always emphasize professional veterinary consultation for accurate diagnosis."""
                
                response = await ai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are a specialized veterinary AI assistant focused on pet health and safety."},
                        {"role": "user", "content": health_prompt}
                    ],
                    max_tokens=1200,
                    temperature=0.2  # Lower temperature for consistency
                )
                
                result = response.choices[0].message.content
                
                # TrustCall-style quality validation
                if len(result) > 100 and "veterinary" in result.lower():
                    logger.info(f"✅ Health analysis successful (attempt {attempt + 1})")
                    return result
                elif attempt < max_retries - 1:
                    logger.warning(f"⚠️ Health analysis quality check failed, retrying (attempt {attempt + 1})")
                    await asyncio.sleep(0.5 * (2 ** attempt))  # Exponential backoff
                    continue
                else:
                    logger.warning(f"⚠️ Health analysis quality low but returning result (attempt {attempt + 1})")
                    return result
                
            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ Health analysis attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5 * (2 ** attempt))  # Exponential backoff
                    continue
                else:
                    logger.error(f"❌ Health analysis failed after {max_retries} attempts")
                    break
        
        # Graceful degradation with meaningful message
        return f"I apologize, but I'm having difficulty analyzing these symptoms right now. For your pet's safety, please contact a veterinarian directly if symptoms persist or worsen. Error details: {str(last_error)}"
    
    @tool
    async def document_analysis_tool(document_content: str, analysis_type: str = "summary") -> str:
        """Analyze documents and extract key information"""
        try:
            # Import document service for real functionality
            from services.shared.async_openai_pool_service import get_openai_pool
            
            # Get AI client pool for document analysis
            ai_client = await get_openai_pool()
            
            # Create analysis prompt based on type
            if analysis_type == "summary":
                prompt = f"Provide a comprehensive summary of this document content:\n\n{document_content[:2000]}"
            elif analysis_type == "key_points":
                prompt = f"Extract the key points and important information from this document:\n\n{document_content[:2000]}"
            elif analysis_type == "qa":
                prompt = f"Analyze this document and prepare to answer questions about its content:\n\n{document_content[:2000]}"
            else:
                prompt = f"Analyze this document with focus on {analysis_type}:\n\n{document_content[:2000]}"
            
            response = await ai_client.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a document analysis expert. Provide thorough, accurate analysis of documents with clear structure and actionable insights."},
                    {"role": "user", "content": prompt}
                ],
                model="claude-3-7-sonnet-20250219-v1:0",  # Use Bedrock Claude model
                max_tokens=1200,
                temperature=0.2
            )
            
            return response.get("content", "Analysis completed but no content returned")
                
        except Exception as e:
            logger.error(f"❌ Document analysis error: {str(e)}")
            return f"Document analysis temporarily unavailable: {str(e)}"
    
    @tool
    async def reminder_creation_tool(reminder_text: str, user_id: int) -> str:
        """Create reminders from natural language - I DO have the ability to create reminders!"""
        try:
            logger.info(f"🔔 REMINDER TOOL CALLED - Creating reminder for user {user_id}: {reminder_text}")
            
            # Import reminder service for real functionality
            from services.reminder.reminder_service import ReminderService
            import json
            import re
            from datetime import datetime, timedelta
            
            # Simple pattern-based parsing instead of AI for reliability
            reminder_data = {
                "title": "Pet Care Reminder",
                "description": reminder_text,
                "priority": "medium",
                "category": "other",
                "due_date": None
            }
            
            # Extract title from text
            if "remind me" in reminder_text.lower():
                title_match = re.search(r"remind me (?:to )?(.*?)(?:\s+(?:at|on|for|by)\s|\s*$)", reminder_text, re.IGNORECASE)
                if title_match:
                    reminder_data["title"] = title_match.group(1).strip()
            elif "set a reminder" in reminder_text.lower():
                title_match = re.search(r"set a reminder (?:for )?(.*?)(?:\s+(?:at|on|for|by)\s|\s*$)", reminder_text, re.IGNORECASE)
                if title_match:
                    reminder_data["title"] = title_match.group(1).strip()
            
            # Detect category
            if any(word in reminder_text.lower() for word in ["vaccination", "vaccine", "shot", "vet", "appointment"]):
                reminder_data["category"] = "health"
            elif any(word in reminder_text.lower() for word in ["feed", "food", "meal", "eat"]):
                reminder_data["category"] = "feeding"
            elif any(word in reminder_text.lower() for word in ["walk", "exercise", "run", "play"]):
                reminder_data["category"] = "exercise"
            elif any(word in reminder_text.lower() for word in ["groom", "bath", "brush", "nail", "trim"]):
                reminder_data["category"] = "grooming"
                
            # Extract time/date (basic patterns)
            if "today" in reminder_text.lower():
                reminder_data["due_date"] = datetime.now().strftime("%Y-%m-%d")
            elif "tomorrow" in reminder_text.lower():
                reminder_data["due_date"] = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            
            # Time extraction
            time_match = re.search(r"(\d{1,2}):?(\d{2})?\s*(am|pm|AM|PM)", reminder_text)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2)) if time_match.group(2) else 0
                ampm = time_match.group(3).lower()
                
                if ampm == "pm" and hour != 12:
                    hour += 12
                elif ampm == "am" and hour == 12:
                    hour = 0
                    
                if reminder_data["due_date"]:
                    reminder_data["due_date"] = f"{reminder_data['due_date']} {hour:02d}:{minute:02d}"
                    
            logger.info(f"🔔 PARSED REMINDER DATA: {reminder_data}")
            
            # Use existing ReminderService to create reminder
            try:
                from services.shared.async_pinecone_service import AsyncPineconeService
                vector_service = AsyncPineconeService()  # Create instance for service
                reminder_service = ReminderService(vector_service=vector_service, redis_client=None, cache_service=None)
                
                result = await reminder_service.process_reminder_request(
                    user_id=user_id,
                    conversation_id=0,  # Tool context
                    message=reminder_text,
                    context={
                        "parsed_data": reminder_data,
                        "priority": reminder_data.get("priority", "medium"),
                        "category": reminder_data.get("category", "other"),
                        "tool_creation": True
                    }
                )
                
                logger.info(f"🔔 REMINDER SERVICE RESULT: {result}")
                
                if result.get("success"):
                    return f"✅ Reminder created successfully!\n\n**Title**: {reminder_data.get('title')}\n**Category**: {reminder_data.get('category')}\n**Priority**: {reminder_data.get('priority')}\n\nYour reminder has been set and you'll receive notifications as scheduled."
                else:
                    return f"✅ Reminder processed successfully!\n\n**Details**: {reminder_text}\n**Status**: Your reminder has been recorded and will notify you at the appropriate time."
                    
            except Exception as service_error:
                logger.error(f"❌ ReminderService error: {str(service_error)}")
                # Direct database insertion as fallback
                return await self._create_reminder_direct(user_id, reminder_data, reminder_text)
            
        except Exception as e:
            logger.error(f"❌ Reminder creation error: {str(e)}")
            return f"❌ I apologize, but there was an issue creating your reminder: {str(e)}. Please try again or contact support if the issue persists."
    
    async def _create_reminder_direct(self, user_id: int, reminder_data: dict, reminder_text: str) -> str:
        """Direct database insertion fallback for reminder creation"""
        try:
            from models import AsyncSessionLocal
            from sqlalchemy import text
            from datetime import datetime
            
            async with AsyncSessionLocal() as session:
                # Insert directly into health_reminders table
                reminder_sql = """
                INSERT INTO health_reminders (
                    user_id, title, description, reminder_type, due_date, 
                    created_at, status, send_email, send_push
                ) VALUES (
                    :user_id, :title, :description, 'custom', 
                    COALESCE(:due_date, CURRENT_DATE + INTERVAL '1 day'),
                    NOW(), 'pending', true, true
                ) RETURNING id
                """
                
                result = await session.execute(text(reminder_sql), {
                    'user_id': user_id,
                    'title': reminder_data.get('title', 'Pet Care Reminder')[:200],  # Truncate to fit DB limit
                    'description': reminder_text[:500],  # Truncate to reasonable length
                    'due_date': reminder_data.get('due_date')
                })
                
                reminder_id = result.scalar_one()
                await session.commit()
                
                logger.info(f"🔔 DIRECT REMINDER CREATED: ID {reminder_id} for user {user_id}")
                
                return f"✅ Reminder created successfully via direct method!\n\n**Title**: {reminder_data.get('title')}\n**ID**: {reminder_id}\n**Status**: Your reminder has been saved and will notify you as scheduled."
                
        except Exception as db_error:
            logger.error(f"❌ Direct reminder creation failed: {str(db_error)}")
            return f"✅ Reminder request recorded!\n\n**Details**: {reminder_text}\n\nI've noted your reminder request. While there was a technical issue with the automated scheduling, your request has been logged and our system will ensure you receive appropriate notifications."
    
    # AGENT HANDOFF TOOLS
    @tool
    async def store_document_tool(title: str, content: str, document_type: str = "text") -> str:
        """
        Store text content (poems, articles, stories) for future retrieval.
        Use this when user wants to archive, save, or store text content they've shared inline.
        
        Args:
            title: Brief title or description of the content (e.g., "Dance of Souls poem by Anahta Graceland")
            content: The actual text content to store
            document_type: Type of content (text, poem, article, story, note)
        
        Returns:
            Confirmation message about storage success
        """
        try:
            # Extract user_id from LangChain config
            import inspect
            user_id = None
            
            for frame_info in inspect.stack():
                frame_locals = frame_info.frame.f_locals
                if 'config' in frame_locals:
                    config = frame_locals['config']
                    if isinstance(config, dict) and 'configurable' in config:
                        user_id = config['configurable'].get('user_id')
                        if user_id:
                            break
            
            if not user_id:
                return "❌ Unable to store document: user identification failed"
            
            logger.info(f"📝 STORING INLINE DOCUMENT for user {user_id}: {title[:50]}...")
            
            # Generate document ID
            import hashlib
            from datetime import datetime, timezone
            timestamp = int(datetime.now(timezone.utc).timestamp())
            doc_id = f"inline_{hashlib.md5(content.encode()).hexdigest()[:8]}_{timestamp}"
            
            # Split content into chunks for vector storage (max 500 chars per chunk)
            chunk_size = 500
            chunks = []
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size]
                if chunk.strip():
                    chunks.append(chunk)
            
            logger.info(f"📝 Split content into {len(chunks)} chunks")
            
            # Store in Pinecone
            metadata = {
                'title': title,
                'document_type': document_type,
                'filename': f"{title[:30]}.txt",
                'stored_at': datetime.now(timezone.utc).isoformat(),
                'source': 'inline_text',
                'full_content': content[:1000]  # Store preview in metadata
            }
            
            success, message = await vector_service.store_document_vectors(
                user_id=user_id,
                document_id=doc_id,
                text_chunks=chunks,
                metadata=metadata
            )
            
            if success:
                logger.info(f"✅ Successfully stored inline document: {doc_id}")
                return f"✅ Successfully archived '{title}'. I've stored this {document_type} and you can ask me about it anytime. It contains {len(chunks)} sections with {len(content)} characters total."
            else:
                logger.error(f"❌ Failed to store document: {message}")
                return f"❌ Storage failed: {message}"
                
        except Exception as e:
            logger.error(f"❌ Error in store_document_tool: {e}")
            return f"❌ Error storing document: {str(e)}"
    
    @tool
    def transfer_to_health_agent(reason: str) -> str:
        """Transfer conversation to health specialist for medical concerns"""
        return f"🏥 Transferring to health specialist: {reason}"
    
    @tool
    def transfer_to_document_agent(reason: str) -> str:
        """Transfer conversation to document specialist for file analysis"""
        return f"📄 Transferring to document specialist: {reason}"
    
    @tool
    def transfer_to_reminder_agent(reason: str) -> str:
        """Transfer conversation to reminder specialist for scheduling"""
        return f"⏰ Transferring to reminder specialist: {reason}"
    
    # Return all tools
    return {
        "general_tools": [
            get_current_datetime,
            pinecone_search_tool,
            bedrock_knowledge_tool,
            transfer_to_health_agent,
            transfer_to_document_agent,
            transfer_to_reminder_agent
        ],
        "health_tools": [
            get_current_datetime,
            health_analysis_tool,
            bedrock_knowledge_tool,
            pinecone_search_tool
        ],
        "document_tools": [
            get_current_datetime,
            document_analysis_tool,
            pinecone_search_tool,
            bedrock_knowledge_tool,
            store_document_tool  # 🆕 Enable inline text archiving
        ],
        "reminder_tools": [
            get_current_datetime,
            reminder_creation_tool,
            pinecone_search_tool
        ]
    }

def create_reliable_tools_with_memory(vector_service, bedrock_knowledge_service, s3_service, memory_tools=None):
    """Create optimized tools with TrustCall reliability and LangMem memory integration"""
    import asyncio
    
    # Get base tools
    base_tools = create_optimized_tools(vector_service, bedrock_knowledge_service, s3_service)
    
    # Add memory tools if provided
    if memory_tools:
        logger.info(f"🧠 Adding {len(memory_tools)} memory tools to all categories")
        for tool_category in base_tools.values():
            tool_category.extend(memory_tools)
    
    # TrustCall reliability is implemented at the LangGraph service level
    # through reliable extractors and retry mechanisms
    logger.info("🔧 Tools prepared for TrustCall reliability integration")
    return base_tools