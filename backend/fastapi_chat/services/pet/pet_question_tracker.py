"""
Pet Question Tracker - Prevents repetitive questioning about missing pet information
Tracks what questions have been asked and user responses to avoid annoying repetition
"""

import json
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class PetQuestionTracker:
    """
    Smart tracking system to prevent repetitive questions about missing pet information
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        
        # TTL settings
        self.question_tracking_ttl = 604800  # 7 days
        self.user_declined_ttl = 2592000     # 30 days (remember longer when declined)
        self.recently_asked_ttl = 3600       # 1 hour cooldown between same questions
        
        # Critical fields that are important to ask about
        self.critical_fields = {
            "emergency_vet_name": "veterinarian contact",
            "emergency_vet_phone": "veterinarian phone number", 
            "known_allergies": "known allergies",
            "medical_conditions": "medical conditions",
            "weight": "current weight",
            "age": "age"
        }
        
        # Less critical fields (ask less frequently)
        self.optional_fields = {
            "breed": "breed information",
            "gender": "gender",
            "spay_neuter_status": "spay/neuter status",
            "microchip_id": "microchip information"
        }
    
    async def has_been_asked_recently(
        self, 
        user_id: int, 
        pet_name: str, 
        field_name: str,
        timeframe_hours: int = 24
    ) -> bool:
        """Check if this specific question was asked recently"""
        try:
            question_key = f"pet_question_asked:{user_id}:{pet_name.lower()}:{field_name}"
            last_asked = await self.redis.get(question_key)
            
            if not last_asked:
                return False
            
            last_time = datetime.fromisoformat(last_asked)
            time_since = datetime.utcnow() - last_time
            
            return time_since < timedelta(hours=timeframe_hours)
            
        except Exception as e:
            logger.error(f"❌ Error checking question history: {e}")
            return False
    
    async def user_declined_to_provide(
        self, 
        user_id: int, 
        pet_name: str, 
        field_name: str
    ) -> bool:
        """Check if user has declined to provide this information"""
        try:
            declined_key = f"pet_declined:{user_id}:{pet_name.lower()}:{field_name}"
            declined = await self.redis.get(declined_key)
            return declined is not None
            
        except Exception as e:
            logger.error(f"❌ Error checking declined status: {e}")
            return False
    
    async def record_question_asked(
        self, 
        user_id: int, 
        pet_name: str, 
        field_name: str,
        question_context: str = None
    ) -> None:
        """Record that we asked about this information"""
        try:
            question_key = f"pet_question_asked:{user_id}:{pet_name.lower()}:{field_name}"
            current_time = datetime.utcnow().isoformat()
            
            # Store when we asked
            await self.redis.setex(question_key, self.question_tracking_ttl, current_time)
            
            # Also store context for analytics
            if question_context:
                context_key = f"pet_question_context:{user_id}:{pet_name.lower()}:{field_name}"
                context_data = {
                    "question": question_context,
                    "timestamp": current_time
                }
                await self.redis.setex(
                    context_key, 
                    self.question_tracking_ttl, 
                    json.dumps(context_data)
                )
            
            logger.info(f"📝 Recorded question about {field_name} for {pet_name} (user {user_id})")
            
        except Exception as e:
            logger.error(f"❌ Error recording question: {e}")
    
    async def record_user_declined(
        self, 
        user_id: int, 
        pet_name: str, 
        field_name: str,
        reason: str = "user_declined"
    ) -> None:
        """Record that user declined to provide this information"""
        try:
            declined_key = f"pet_declined:{user_id}:{pet_name.lower()}:{field_name}"
            declined_data = {
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.redis.setex(
                declined_key, 
                self.user_declined_ttl, 
                json.dumps(declined_data)
            )
            
            logger.info(f"🚫 User {user_id} declined to provide {field_name} for {pet_name}: {reason}")
            
        except Exception as e:
            logger.error(f"❌ Error recording decline: {e}")
    
    async def get_safe_questions_to_ask(
        self, 
        user_id: int, 
        pets_missing_info: Dict[str, List[str]],
        max_questions: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Get a safe list of questions to ask, avoiding repetition and respecting user preferences
        """
        try:
            safe_questions = []
            
            for pet_name, missing_fields in pets_missing_info.items():
                if len(safe_questions) >= max_questions:
                    break
                
                # Prioritize critical fields
                critical_missing = [f for f in missing_fields if f in self.critical_fields]
                optional_missing = [f for f in missing_fields if f in self.optional_fields]
                
                # Check critical fields first
                for field in critical_missing:
                    if len(safe_questions) >= max_questions:
                        break
                    
                    # Skip if asked recently or user declined
                    if await self.has_been_asked_recently(user_id, pet_name, field, 24):
                        continue
                    if await self.user_declined_to_provide(user_id, pet_name, field):
                        continue
                    
                    safe_questions.append({
                        "pet_name": pet_name,
                        "field_name": field,
                        "field_description": self.critical_fields[field],
                        "priority": "critical",
                        "question_template": f"I notice I don't have {self.critical_fields[field]} information for {pet_name}. This would be helpful for providing better care advice."
                    })
                
                # Then optional fields (less frequently)
                for field in optional_missing:
                    if len(safe_questions) >= max_questions:
                        break
                    
                    # More restrictive for optional fields - 72 hours cooldown
                    if await self.has_been_asked_recently(user_id, pet_name, field, 72):
                        continue
                    if await self.user_declined_to_provide(user_id, pet_name, field):
                        continue
                    
                    safe_questions.append({
                        "pet_name": pet_name,
                        "field_name": field,
                        "field_description": self.optional_fields[field],
                        "priority": "optional",
                        "question_template": f"If you don't mind me asking, what is {pet_name}'s {self.optional_fields[field]}?"
                    })
            
            return safe_questions
            
        except Exception as e:
            logger.error(f"❌ Error generating safe questions: {e}")
            return []
    
    async def detect_user_provided_info(
        self, 
        user_id: int, 
        message: str,
        pet_names: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Detect if user provided missing information in their message
        """
        try:
            provided_info = []
            message_lower = message.lower()
            
            # Look for patterns indicating user provided information
            for pet_name in pet_names:
                pet_lower = pet_name.lower()
                
                # Check for vet information
                if any(word in message_lower for word in ["vet", "veterinarian", "doctor"]):
                    if pet_lower in message_lower or len(pet_names) == 1:
                        provided_info.append({
                            "pet_name": pet_name,
                            "field_name": "emergency_vet_name",
                            "confidence": 0.8
                        })
                
                # Check for phone numbers
                if any(char in message for char in ["(", ")", "-"]) or any(word in message_lower for word in ["phone", "number", "call"]):
                    if pet_lower in message_lower or len(pet_names) == 1:
                        provided_info.append({
                            "pet_name": pet_name,
                            "field_name": "emergency_vet_phone",
                            "confidence": 0.7
                        })
                
                # Check for allergy information
                if any(word in message_lower for word in ["allergic", "allergy", "allergies", "reaction"]):
                    if pet_lower in message_lower or len(pet_names) == 1:
                        provided_info.append({
                            "pet_name": pet_name,
                            "field_name": "known_allergies",
                            "confidence": 0.9
                        })
                
                # Check for medical conditions
                if any(word in message_lower for word in ["condition", "medical", "health", "disease", "illness"]):
                    if pet_lower in message_lower or len(pet_names) == 1:
                        provided_info.append({
                            "pet_name": pet_name,
                            "field_name": "medical_conditions",
                            "confidence": 0.7
                        })
            
            return provided_info
            
        except Exception as e:
            logger.error(f"❌ Error detecting provided info: {e}")
            return []
    
    async def detect_user_declined(
        self, 
        user_id: int, 
        message: str,
        pet_names: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Detect if user declined to provide information
        """
        try:
            declined_info = []
            message_lower = message.lower()
            
            # Decline patterns
            decline_patterns = [
                "don't know", "i don't know", "not sure", "don't have",
                "don't remember", "can't remember", "no vet", "no veterinarian",
                "don't want to share", "prefer not to say", "private",
                "none", "no allergies", "no conditions", "healthy"
            ]
            
            if any(pattern in message_lower for pattern in decline_patterns):
                # User seems to be declining - mark recent questions as declined
                for pet_name in pet_names:
                    for field in self.critical_fields.keys():
                        if await self.has_been_asked_recently(user_id, pet_name, field, 1):  # Last hour
                            declined_info.append({
                                "pet_name": pet_name,
                                "field_name": field,
                                "reason": "user_indicated_unknown_or_declined"
                            })
            
            return declined_info
            
        except Exception as e:
            logger.error(f"❌ Error detecting declined info: {e}")
            return []
    
    async def clear_question_history(self, user_id: int, pet_name: str = None) -> None:
        """Clear question history for debugging/admin purposes"""
        try:
            if pet_name:
                # Clear for specific pet
                pattern = f"pet_question_*:{user_id}:{pet_name.lower()}:*"
            else:
                # Clear all for user
                pattern = f"pet_question_*:{user_id}:*"
            
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                await self.redis.delete(*keys)
                logger.info(f"🗑️ Cleared {len(keys)} question history entries for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error clearing question history: {e}")
    
    async def get_question_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get statistics about questions asked for debugging"""
        try:
            stats = {
                "questions_asked_count": 0,
                "declined_count": 0,
                "recent_questions": []
            }
            
            # Count questions asked
            async for key in self.redis.scan_iter(match=f"pet_question_asked:{user_id}:*"):
                stats["questions_asked_count"] += 1
            
            # Count declined
            async for key in self.redis.scan_iter(match=f"pet_declined:{user_id}:*"):
                stats["declined_count"] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting question stats: {e}")
            return {"error": str(e)}
