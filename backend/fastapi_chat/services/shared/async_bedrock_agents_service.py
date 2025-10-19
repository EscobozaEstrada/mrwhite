"""
AWS Bedrock Agents Service for Persistent Cross-Session Memory
Implements intelligent agents with long-term memory capabilities
"""

import os
import logging
import json
import uuid
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class AsyncBedrockAgentsService:
    """
    Async Bedrock Agents service for persistent cross-session memory
    Provides intelligent agents that remember user context across sessions
    """
    
    def __init__(self):
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.agent_id = os.getenv("BEDROCK_AGENT_ID")
        self.agent_alias_id = os.getenv("BEDROCK_AGENT_ALIAS_ID", "TSTALIASID")
        self.knowledge_base_id = os.getenv("BEDROCK_KNOWLEDGE_BASE_ID")
        
        # Initialize Bedrock clients
        self.bedrock_agent = boto3.client('bedrock-agent', region_name=self.aws_region)
        self.bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=self.aws_region)
        
        # Session management
        self.active_sessions = {}  # user_id -> session_id mapping
        
        # Performance tracking
        self.stats = {
            "total_sessions": 0,
            "active_sessions": 0,
            "total_invocations": 0,
            "successful_invocations": 0,
            "failed_invocations": 0,
            "average_response_time": 0.0,
            "agent_ready": False
        }
        
        logger.info(f"✅ Bedrock Agents service initialized for region: {self.aws_region}")
    
    def _get_current_date_instruction(self) -> str:
        """Get current date context for agent instruction"""
        from datetime import datetime, timezone
        
        current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        current_day = datetime.now(timezone.utc).strftime("%A")
        current_time = datetime.now(timezone.utc).strftime("%H:%M UTC")
        
        return f"""

        CRITICAL DATE INFORMATION:
        - CURRENT REAL DATE: {current_date} ({current_day})
        - CURRENT REAL TIME: {current_time}
        - YOU MUST USE THIS REAL DATE, NOT YOUR TRAINING DATA DATE
        - When users ask "What's today's date?" or similar, respond with: "Today is {current_date} ({current_day})"
        - NEVER refer to dates from 2023 or earlier - always use the current real date provided above

        """
    
    def _get_pet_memory_context(self, session_context: Dict[str, Any]) -> str:
        """Generate pet memory context for agent"""
        if not session_context or "pets" not in session_context:
            return ""
        
        pets = session_context.get("pets", [])
        if not pets:
            pet_prompt = session_context.get("pet_missing_info", {}).get("note", "")
            if pet_prompt:
                return f"\n\nUSER PET STATUS: {pet_prompt}\n"
            return ""
        
        # Use the generated pet memory prompt if available (includes anti-hallucination rules)
        if "pet_memory_prompt" in session_context:
            return f"\n\n{session_context['pet_memory_prompt']}\n"
        
        # Fallback: Generate basic pet context with strict constraints
        pet_context_parts = [
            "\n\n🚨 CRITICAL PET MEDICAL INFORMATION - STRICT ADHERENCE REQUIRED:",
            "WARNING: NEVER make up, assume, or fabricate any medical information about these pets.",
            "ONLY use the exact information provided below from the verified database."
        ]
        
        for pet in pets:
            pet_name = pet.get("name", "Unknown")
            pet_details = [f"Pet: {pet_name}"]
            
            if pet.get("breed"):
                pet_details.append(f"Breed: {pet['breed']}")
            if pet.get("age"):
                pet_details.append(f"Age: {pet['age']} years")
            
            # MEDICAL INFORMATION WITH STRICT CONSTRAINTS
            if pet.get("known_allergies"):
                pet_details.append(f"VERIFIED ALLERGIES: {pet['known_allergies']}")
            else:
                pet_details.append(f"ALLERGIES: NOT SPECIFIED - DO NOT ASSUME ANY")
                
            if pet.get("medical_conditions"):
                pet_details.append(f"VERIFIED MEDICAL CONDITIONS: {pet['medical_conditions']}")
            else:
                pet_details.append(f"MEDICAL CONDITIONS: NOT SPECIFIED - DO NOT ASSUME ANY")
            
            # VETERINARY INFORMATION
            if pet.get("emergency_vet_name"):
                pet_details.append(f"Veterinarian: {pet['emergency_vet_name']}")
            else:
                pet_details.append(f"Veterinarian: NOT SPECIFIED")
            
            missing_fields = pet.get("missing_fields", [])
            critical_missing = [f for f in missing_fields if f in ["emergency_vet_name", "known_allergies", "medical_conditions"]]
            if critical_missing:
                pet_details.append(f"MISSING CRITICAL INFO: {', '.join(critical_missing)}")
            
            pet_context_parts.append(" | ".join(pet_details))
        
        # Add strict anti-hallucination constraints
        pet_context_parts.extend([
            "",
            "🛡️ ANTI-HALLUCINATION RULES:",
            "- NEVER mention specific medications unless explicitly provided above",
            "- NEVER mention specific treatments unless explicitly provided above", 
            "- NEVER assume allergies or medical conditions not listed above",
            "- NEVER mix up information between different pets",
            "- If information is missing, ask for it rather than assuming",
            "- ONLY use the verified database information shown above"
        ])
        
        # Add completion guidance
        completeness = session_context.get("pet_completeness_percentage", 0)
        if completeness < 80:
            pet_context_parts.append(f"\nIMPORTANT: Pet profile {completeness:.1f}% complete - gather missing information naturally during conversation")
        
        return "\n".join(pet_context_parts) + "\n"
    
    # ==================== AGENT MANAGEMENT ====================
    
    async def ensure_agent_exists(self) -> bool:
        """Ensure Bedrock agent exists and is ready"""
        try:
            # Check if agent exists
            if not self.agent_id:
                self.agent_id = await self._create_agent()
            
            # Verify agent status
            agent_status = await self._get_agent_status()
            if agent_status not in ['PREPARED', 'NOT_PREPARED']:
                logger.warning(f"Agent status: {agent_status}")
                return False
            
            # Prepare agent if needed
            if agent_status == 'NOT_PREPARED':
                await self._prepare_agent()
            
            # Create alias if needed
            if not self.agent_alias_id or self.agent_alias_id == "TSTALIASID":
                self.agent_alias_id = await self._create_agent_alias()
            
            self.stats["agent_ready"] = True
            logger.info("✅ Bedrock agent verified and ready")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to ensure agent exists: {e}")
            self.stats["agent_ready"] = False
            return False
    
    async def _create_agent(self) -> str:
        """Create a new Bedrock agent"""
        try:
            # Agent instruction for Mr. White with current date context
            base_instruction = """
            You are Mr. White, an expert AI assistant for dog care and training. 
            
            Key capabilities:
            - Provide personalized dog care advice based on user history
            - Remember previous conversations and user preferences
            - Access comprehensive dog care knowledge base
            - Maintain context across multiple sessions
            - Offer empathetic, practical guidance for dog owners
            
            Memory management:
            - Remember user's dog details (name, breed, age, health issues)
            - Track ongoing training programs and progress
            - Recall previous questions and advice given
            - Maintain user preferences and communication style
            - Store important health events and veterinary visits
            
            Always prioritize the safety and well-being of the dog and provide
            evidence-based advice while maintaining a warm, supportive tone.
            """
            
            # Add current date context to instruction
            instruction = base_instruction + self._get_current_date_instruction()
            
            response = self.bedrock_agent.create_agent(
                agentName="mr-white-dog-care-agent",
                description="Mr. White's intelligent dog care assistant with persistent memory",
                instruction=instruction,
                foundationModel=os.getenv("BEDROCK_CLAUDE_MODEL_ID", "us.anthropic.claude-3-5-haiku-20241022-v1:0"),
                agentResourceRoleArn=os.getenv("BEDROCK_AGENT_ROLE_ARN"),
                idleSessionTTLInSeconds=3600,  # 1 hour session timeout
                customerEncryptionKeyArn=os.getenv("BEDROCK_AGENT_KMS_KEY_ARN"),
                promptOverrideConfiguration={
                    'promptConfigurations': [
                        {
                            'promptType': 'PRE_PROCESSING',
                            'promptCreationMode': 'DEFAULT',
                            'promptState': 'ENABLED'
                        },
                        {
                            'promptType': 'ORCHESTRATION',
                            'promptCreationMode': 'DEFAULT',
                            'promptState': 'ENABLED'
                        },
                        {
                            'promptType': 'POST_PROCESSING',
                            'promptCreationMode': 'DEFAULT',
                            'promptState': 'ENABLED'
                        }
                    ]
                }
            )
            
            agent_id = response['agent']['agentId']
            logger.info(f"✅ Created Bedrock agent: {agent_id}")
            
            # Associate knowledge base if available
            if self.knowledge_base_id:
                await self._associate_knowledge_base(agent_id)
            
            return agent_id
            
        except ClientError as e:
            logger.error(f"❌ Failed to create agent: {e}")
            raise
    
    async def _associate_knowledge_base(self, agent_id: str):
        """Associate knowledge base with the agent"""
        try:
            self.bedrock_agent.associate_agent_knowledge_base(
                agentId=agent_id,
                agentVersion='DRAFT',
                knowledgeBaseId=self.knowledge_base_id,
                description="Mr. White's comprehensive dog care knowledge base",
                knowledgeBaseState='ENABLED'
            )
            logger.info("✅ Associated knowledge base with agent")
            
        except Exception as e:
            logger.error(f"❌ Failed to associate knowledge base: {e}")
    
    async def _prepare_agent(self):
        """Prepare the agent for use"""
        try:
            response = self.bedrock_agent.prepare_agent(
                agentId=self.agent_id
            )
            
            # Wait for preparation to complete
            await self._wait_for_agent_prepared()
            
            logger.info("✅ Agent prepared successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to prepare agent: {e}")
            raise
    
    async def _create_agent_alias(self) -> str:
        """Create an agent alias"""
        try:
            response = self.bedrock_agent.create_agent_alias(
                agentId=self.agent_id,
                agentAliasName="production",
                description="Production alias for Mr. White agent",
                agentVersion='DRAFT'
            )
            
            alias_id = response['agentAlias']['agentAliasId']
            logger.info(f"✅ Created agent alias: {alias_id}")
            return alias_id
            
        except Exception as e:
            logger.error(f"❌ Failed to create agent alias: {e}")
            return "TSTALIASID"  # Fallback to test alias
    
    async def _wait_for_agent_prepared(self, max_attempts: int = 30):
        """Wait for agent to be prepared"""
        for attempt in range(max_attempts):
            status = await self._get_agent_status()
            if status == 'PREPARED':
                return
            elif status == 'FAILED':
                raise Exception("Agent preparation failed")
            
            await asyncio.sleep(10)
        
        raise TimeoutError("Agent preparation timed out")
    
    async def _get_agent_status(self) -> str:
        """Get agent status"""
        try:
            response = self.bedrock_agent.get_agent(agentId=self.agent_id)
            return response['agent']['agentStatus']
        except Exception as e:
            logger.error(f"❌ Failed to get agent status: {e}")
            return 'UNKNOWN'
    
    # ==================== SESSION MANAGEMENT ====================
    
    async def start_session(self, user_id: int, user_context: Optional[Dict[str, Any]] = None) -> str:
        """Start a new session for a user or resume existing one"""
        try:
            # Check if user has an active session
            if user_id in self.active_sessions:
                session_id = self.active_sessions[user_id]
                logger.info(f"✅ Resuming session {session_id} for user {user_id}")
                return session_id
            
            # Create new session
            session_id = str(uuid.uuid4())
            self.active_sessions[user_id] = session_id
            
            # Initialize session with user context if provided
            if user_context:
                await self._initialize_session_context(session_id, user_context)
            
            self.stats["total_sessions"] += 1
            self.stats["active_sessions"] = len(self.active_sessions)
            
            logger.info(f"✅ Started new session {session_id} for user {user_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"❌ Failed to start session for user {user_id}: {e}")
            raise
    
    async def _initialize_session_context(self, session_id: str, user_context: Dict[str, Any]):
        """Initialize session with user context"""
        try:
            # Send initial context to agent
            context_message = f"""
            Session initialized for user. Here's their context:
            
            User Information:
            - User ID: {user_context.get('user_id')}
            - Username: {user_context.get('username', 'Unknown')}
            - Subscription: {user_context.get('subscription_tier', 'free')}
            
            Pet Information:
            - Pet Name: {user_context.get('pet_name', 'Not specified')}
            - Breed: {user_context.get('pet_breed', 'Not specified')}
            - Age: {user_context.get('pet_age', 'Not specified')}
            - Health Concerns: {user_context.get('health_concerns', 'None specified')}
            
            Previous Interactions Summary:
            {user_context.get('interaction_summary', 'First interaction')}
            
            Please acknowledge this context and be ready to provide personalized assistance.
            """
            
            # Send context without expecting a user-facing response
            await self._invoke_agent_internal(session_id, context_message, initialize=True)
            
            logger.info(f"✅ Initialized session context for {session_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize session context: {e}")
    
    async def end_session(self, user_id: int) -> bool:
        """End a user's session"""
        try:
            if user_id in self.active_sessions:
                session_id = self.active_sessions[user_id]
                del self.active_sessions[user_id]
                self.stats["active_sessions"] = len(self.active_sessions)
                
                logger.info(f"✅ Ended session {session_id} for user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to end session for user {user_id}: {e}")
            return False
    
    # ==================== AGENT INVOCATION ====================
    
    async def invoke_agent(
        self,
        user_id: int,
        message: str,
        session_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Invoke the agent with a user message"""
        try:
            # Ensure agent is ready
            if not self.stats["agent_ready"]:
                await self.ensure_agent_exists()
            
            # Get or create session
            session_id = await self.start_session(user_id, session_context)
            
            # Add current date context and pet memory for comprehensive user context
            date_context = self._get_current_date_instruction()
            pet_context = self._get_pet_memory_context(session_context) if session_context else ""
            
            enhanced_message = date_context + pet_context + "\n\nUser message: " + message
            
            # Invoke agent
            response = await self._invoke_agent_runtime(session_id, enhanced_message)
            
            self.stats["successful_invocations"] += 1
            logger.info(f"✅ Agent invocation successful for user {user_id}")
            
            return {
                "response": response["completion"],
                "session_id": session_id,
                "citations": response.get("citations", []),
                "trace": response.get("trace"),
                "memory_updated": True
            }
            
        except Exception as e:
            self.stats["failed_invocations"] += 1
            logger.error(f"❌ Agent invocation failed for user {user_id}: {e}")
            
            return {
                "response": "I apologize, but I'm experiencing technical difficulties. Please try again in a moment.",
                "session_id": None,
                "citations": [],
                "trace": None,
                "memory_updated": False,
                "error": str(e)
            }
    
    async def _invoke_agent_runtime(self, session_id: str, message: str) -> Dict[str, Any]:
        """Invoke agent runtime"""
        try:
            response = self.bedrock_agent_runtime.invoke_agent(
                agentId=self.agent_id,
                agentAliasId=self.agent_alias_id,
                sessionId=session_id,
                inputText=message,
                enableTrace=True,
                endSession=False
            )
            
            # Process streaming response
            completion = ""
            citations = []
            trace = None
            
            event_stream = response['completion']
            for event in event_stream:
                if 'chunk' in event:
                    chunk = event['chunk']
                    if 'bytes' in chunk:
                        completion += chunk['bytes'].decode('utf-8')
                
                if 'trace' in event:
                    trace = event['trace']
                
                if 'returnControl' in event:
                    # Handle return control for action groups
                    pass
            
            return {
                "completion": completion,
                "citations": citations,
                "trace": trace
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to invoke agent runtime: {e}")
            raise
    
    async def _invoke_agent_internal(self, session_id: str, message: str, initialize: bool = False):
        """Internal agent invocation for context setup"""
        try:
            response = self.bedrock_agent_runtime.invoke_agent(
                agentId=self.agent_id,
                agentAliasId=self.agent_alias_id,
                sessionId=session_id,
                inputText=message,
                enableTrace=False,
                endSession=False
            )
            
            # Consume the response without processing
            event_stream = response['completion']
            for event in event_stream:
                pass  # Just consume the stream
            
        except Exception as e:
            logger.error(f"❌ Internal agent invocation failed: {e}")
    
    # ==================== MEMORY MANAGEMENT ====================
    
    async def get_session_memory(self, user_id: int) -> Dict[str, Any]:
        """Get session memory summary for a user"""
        try:
            if user_id not in self.active_sessions:
                return {"memory": "No active session", "session_id": None}
            
            session_id = self.active_sessions[user_id]
            
            # Query agent for memory summary
            memory_query = "Please provide a brief summary of what you remember about our conversation and my pet."
            
            memory_response = await self._invoke_agent_runtime(session_id, memory_query)
            
            return {
                "memory": memory_response["completion"],
                "session_id": session_id,
                "active": True
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get session memory for user {user_id}: {e}")
            return {"memory": "Unable to retrieve memory", "session_id": None, "error": str(e)}
    
    async def update_session_context(
        self,
        user_id: int,
        context_update: Dict[str, Any]
    ) -> bool:
        """Update session context with new information"""
        try:
            if user_id not in self.active_sessions:
                return False
            
            session_id = self.active_sessions[user_id]
            
            # Format context update
            update_message = f"""
            Context update:
            {json.dumps(context_update, indent=2)}
            
            Please remember this updated information for our conversation.
            """
            
            await self._invoke_agent_internal(session_id, update_message)
            
            logger.info(f"✅ Updated session context for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update session context for user {user_id}: {e}")
            return False
    
    # ==================== PERFORMANCE & STATS ====================
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get service performance statistics"""
        return {
            **self.stats,
            "agent_id": self.agent_id,
            "agent_alias_id": self.agent_alias_id,
            "knowledge_base_id": self.knowledge_base_id,
            "active_sessions_count": len(self.active_sessions),
            "region": self.aws_region
        }
    
    def reset_stats(self):
        """Reset performance statistics"""
        self.stats = {
            "total_sessions": 0,
            "active_sessions": 0,
            "total_invocations": 0,
            "successful_invocations": 0,
            "failed_invocations": 0,
            "average_response_time": 0.0,
            "agent_ready": False
        }