"""
Pet Context Manager
Intelligent pet context management with Redis caching and database integration
"""

import json
import logging
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, date
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.pet_repository import PetRepository
from services.pet.simple_pet_extractor import SimplePetExtractor, PetExtractionResult
from services.pet.pet_question_tracker import PetQuestionTracker
from pet_models_pkg.pet_models import PetProfile

logger = logging.getLogger(__name__)

class PetContextManager:
    """
    Manages pet context with intelligent information gathering and Redis caching
    """
    
    def __init__(self, redis_client: redis.Redis, db_session_factory, openai_client=None):
        self.redis = redis_client
        self.db_session_factory = db_session_factory
        self.extractor = SimplePetExtractor(openai_client)
        
        # Initialize question tracker to prevent repetitive questioning
        self.question_tracker = PetQuestionTracker(redis_client)
        
        # Cache TTL settings
        self.pet_context_ttl = 1800  # 30 minutes
        self.missing_fields_ttl = 3600  # 1 hour
        self.conversation_state_ttl = 7200  # 2 hours
        self.extraction_cache_ttl = 86400  # 24 hours
        self.question_throttle_ttl = 86400  # 24 hours
        
        # Throttling limits
        self.max_questions_per_day = 5
        self.max_questions_per_conversation = 2
    
    async def get_user_pet_context(self, user_id: int, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get complete pet context for user with Redis caching
        """
        try:
            # Check cache first (unless force_refresh is True)
            cache_key = f"pet_context:{user_id}"
            cached_context = None
            
            if not force_refresh:
                cached_context = await self.redis.get(cache_key)
            
            if cached_context and not force_refresh:
                context = json.loads(cached_context)
                logger.info(f"📊 Pet context cache hit for user {user_id}: {len(context.get('pets', []))} pets")
                return context
            else:
                if force_refresh:
                    logger.info(f"🔄 Force refreshing pet context from database for user {user_id}")
                else:
                    logger.info(f"📊 Pet context cache miss for user {user_id}, loading from database")
            
            # Load from database
            db_session = self.db_session_factory()
            async with db_session as session:
                pet_repo = PetRepository(session)
                pets = await pet_repo.get_user_pets(user_id)
                
                # Convert to context format
                context = {
                    "user_id": user_id,
                    "pets": [self._pet_to_context(pet) for pet in pets],
                    "total_pets": len(pets),
                    "last_updated": datetime.utcnow().isoformat(),
                    "missing_info_summary": await self._get_missing_info_summary(pets)
                }
                
                # Cache the context
                await self.redis.setex(
                    cache_key,
                    self.pet_context_ttl,
                    json.dumps(context, default=str)
                )
                
                logger.info(f"📊 Pet context loaded from DB for user {user_id}: {len(pets)} pets")
                return context
                
        except Exception as e:
            logger.error(f"❌ Error loading pet context for user {user_id}: {e}")
            return {"user_id": user_id, "pets": [], "total_pets": 0, "missing_info_summary": {}}
    
    async def process_message_for_pet_info(
        self, 
        user_id: int, 
        message: str,
        conversation_id: Optional[int] = None,
        conversation_context: str = None
    ) -> Dict[str, Any]:
        """
        Process user message for pet information extraction and storage
        """
        try:
            # Get current pet context
            current_context = await self.get_user_pet_context(user_id)
            
            # Extract information from message
            extraction_result = await self._extract_with_caching(
                message, conversation_context, current_context
            )
            
            # Store extracted information (only if there is any)
            storage_result = {"success": False, "pets_updated": [], "new_pets_created": []}
            if extraction_result.extracted_fields:
                logger.info(f"🎯 EXTRACTION RESULT for user {user_id}: {extraction_result.extracted_fields}")
                storage_result = await self._store_extracted_information(
                    user_id, extraction_result, current_context
                )
                logger.info(f"🔍 Extracted and stored pet info for user {user_id}: {list(extraction_result.extracted_fields.keys())}")
                logger.info(f"📊 STORAGE RESULT: {storage_result}")
            else:
                logger.debug(f"🔍 No specific pet information extracted from message for user {user_id}")
            
            
            if storage_result["success"]:
                # Re-fetch context after successful storage to get updated pet data
                updated_context = await self.get_user_pet_context(user_id)
                raw_questions = self.extractor.generate_follow_up_questions(
                    extraction_result.extracted_fields, updated_context.get("pets", []), extraction_result, 
                    self.question_tracker, user_id
                )
                # Filter questions using question tracker to prevent repetition
                follow_up_questions = await self._filter_questions_with_tracker(user_id, raw_questions, updated_context.get("pets", []))
                logger.info(f"🔄 Using updated context for follow-up generation (after successful storage)")
            else:
                # Use original context if storage failed
                raw_questions = self.extractor.generate_follow_up_questions(
                        extraction_result.extracted_fields, current_context.get("pets", []), extraction_result,
                        self.question_tracker, user_id
                )
                # Filter questions using question tracker to prevent repetition
                follow_up_questions = await self._filter_questions_with_tracker(user_id, raw_questions, current_context.get("pets", []))
            
            # Process user message for question tracking (detect if user provided info that was asked about)
            await self._process_user_response_for_tracking(user_id, message, extraction_result.extracted_fields)
            
            # Update context cache
            await self._invalidate_context_cache(user_id)
            
            result = {
                "extraction_successful": True,
                "extracted_data": extraction_result.extracted_fields,
                "confidence_score": extraction_result.confidence_score,
                "follow_up_questions": follow_up_questions,
                "context_updated": storage_result["success"],
                "pets_updated": storage_result.get("pets_updated", []),
                "new_pets_created": storage_result.get("new_pets_created", [])
            }
            
            logger.info(f"✅ Pet info processing complete for user {user_id}: {len(extraction_result.extracted_fields)} fields extracted")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error processing pet info for user {user_id}: {e}")
            return {
                "extraction_successful": False,
                "extracted_data": {},
                "follow_up_questions": [],
                "context_updated": False,
                "error": str(e)
            }
    
    async def get_missing_information_for_context(
        self, 
        user_id: int, 
        context_type: str = "general"
    ) -> Dict[str, List[str]]:
        """
        Get missing information prioritized by context
        """
        try:
            cache_key = f"missing_fields:{user_id}:{context_type}"
            cached_missing = await self.redis.get(cache_key)
            
            if cached_missing:
                return json.loads(cached_missing)
            
            # Get current pet context
            pet_context = await self.get_user_pet_context(user_id)
            missing_info = {}
            
            for pet in pet_context.get("pets", []):
                pet_missing = []
                
                # Context-specific priority fields
                priority_fields = self._get_priority_fields_for_context(context_type)
                
                for field in priority_fields:
                    if not pet.get(field) or pet[field] is None:
                        pet_missing.append(field)
                
                if pet_missing:
                    missing_info[pet["name"]] = pet_missing
            
            # Cache the result
            await self.redis.setex(
                cache_key,
                self.missing_fields_ttl,
                json.dumps(missing_info)
            )
            
            return missing_info
            
        except Exception as e:
            logger.error(f"❌ Error getting missing info for user {user_id}: {e}")
            return {}
    
    async def should_ask_follow_up_question(
        self, 
        user_id: int, 
        conversation_id: Optional[int] = None
    ) -> bool:
        """
        Determine if we should ask a follow-up question (smart throttling)
        """
        try:
            # Check daily question limit
            today = datetime.now().date().isoformat()
            daily_key = f"questions_asked:{user_id}:{today}"
            daily_count = await self.redis.get(daily_key)
            
            if daily_count and int(daily_count) >= self.max_questions_per_day:
                logger.info(f"🚫 Daily question limit reached for user {user_id}")
                return False
            
            # Check conversation-specific limit
            if conversation_id:
                conv_key = f"conv_questions:{user_id}:{conversation_id}"
                conv_count = await self.redis.get(conv_key)
                
                if conv_count and int(conv_count) >= self.max_questions_per_conversation:
                    logger.info(f"🚫 Conversation question limit reached for user {user_id}")
                    return False
            
            # Check recent question timing (avoid overwhelming user)
            recent_key = f"last_question:{user_id}"
            last_question_time = await self.redis.get(recent_key)
            
            if last_question_time:
                last_time = datetime.fromisoformat(last_question_time)
                if datetime.utcnow() - last_time < timedelta(minutes=5):
                    logger.info(f"🚫 Recent question throttle for user {user_id}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error checking follow-up throttling: {e}")
            return False
    
    async def record_question_asked(
        self, 
        user_id: int, 
        conversation_id: Optional[int] = None,
        question: str = None
    ) -> None:
        """
        Record that a follow-up question was asked (for throttling)
        """
        try:
            current_time = datetime.utcnow().isoformat()
            
            # Update daily counter
            today = datetime.now().date().isoformat()
            daily_key = f"questions_asked:{user_id}:{today}"
            await self.redis.incr(daily_key)
            await self.redis.expire(daily_key, self.question_throttle_ttl)
            
            # Update conversation counter
            if conversation_id:
                conv_key = f"conv_questions:{user_id}:{conversation_id}"
                await self.redis.incr(conv_key)
                await self.redis.expire(conv_key, self.conversation_state_ttl)
            
            # Record last question time
            await self.redis.setex(
                f"last_question:{user_id}",
                3600,  # 1 hour
                current_time
            )
            
            logger.info(f"📝 Recorded question for user {user_id}: {question[:50]}..." if question else "📝 Question recorded")
            
        except Exception as e:
            logger.error(f"❌ Error recording question: {e}")
    
    async def update_pet_field_direct(
        self, 
        user_id: int, 
        pet_name: str, 
        field_name: str, 
        field_value: Any
    ) -> bool:
        """
        Directly update a specific pet field
        """
        try:
            db_session = self.db_session_factory()
            async with db_session as session:
                pet_repo = PetRepository(session)
                success = await pet_repo.update_pet_field(user_id, pet_name, field_name, field_value)
                
                if success:
                    # Invalidate cache
                    await self._invalidate_context_cache(user_id)
                    logger.info(f"✅ Updated {field_name} for {pet_name} (user {user_id})")
                
                return success
                
        except Exception as e:
            logger.error(f"❌ Error updating pet field: {e}")
            return False
    
    # Private helper methods
    
    def _smart_merge_pet_data(self, existing_pet: Any, new_pet_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Smart merge that protects existing high-quality data from being overwritten
        by lower-quality extracted data
        """
        update_data = {}
        
        # Define generic/low-quality values that shouldn't overwrite specific ones
        GENERIC_BREEDS = {"dog", "cat", "pet", "animal", "puppy", "kitten", "canine", "feline"}
        GENERIC_NAMES = {"dog", "cat", "pet", "animal", "boy", "girl", "male", "female"}
        
        for field, new_value in new_pet_data.items():
            if field == "name":  # Never update name
                continue
                
            if not new_value or new_value in ["", "null", "none"]:  # Skip empty values
                continue
                
            existing_value = getattr(existing_pet, field, None)
            
            # Special handling for breed field
            if field == "breed":
                new_breed_lower = str(new_value).lower().strip()
                existing_breed_lower = str(existing_value).lower().strip() if existing_value else ""
                
                # CRITICAL PROTECTION: Don't overwrite specific breeds with generic ones
                if (existing_value and existing_breed_lower not in GENERIC_BREEDS 
                    and new_breed_lower in GENERIC_BREEDS):
                    logger.info(f"🛡️ BREED PROTECTION: Preserving existing breed '{existing_value}' "
                              f"over generic '{new_value}' for {existing_pet.name}")
                    continue
                
                # Allow update if new breed is more specific
                if new_breed_lower not in GENERIC_BREEDS:
                    update_data[field] = new_value
                    logger.info(f"🔄 BREED UPDATE: Updating breed from '{existing_value}' "
                              f"to '{new_value}' for {existing_pet.name}")
                    
            # Special handling for name-like fields  
            elif field in ["emergency_vet_name", "vet_name"]:
                new_name_lower = str(new_value).lower().strip()
                if new_name_lower not in GENERIC_NAMES:
                    update_data[field] = new_value
                    
            # For numeric fields, prefer non-zero values
            elif field in ["age", "weight"]:
                try:
                    new_numeric = float(new_value) if new_value else 0
                    existing_numeric = float(existing_value) if existing_value else 0
                    
                    # Update if new value is reasonable and existing is empty/zero
                    if new_numeric > 0 and (not existing_value or existing_numeric == 0):
                        update_data[field] = new_value
                    # Or if new value is more specific (e.g., 2.5 vs 2)
                    elif new_numeric > 0 and abs(new_numeric - existing_numeric) > 0.1:
                        update_data[field] = new_value
                        logger.info(f"🔄 NUMERIC UPDATE: Updating {field} from '{existing_value}' "
                                  f"to '{new_value}' for {existing_pet.name}")
                except (ValueError, TypeError):
                    # If conversion fails, treat as string
                    if not existing_value:
                        update_data[field] = new_value
                        
            # For other fields, only update if existing is empty or new is more detailed
            else:
                if not existing_value:
                    update_data[field] = new_value
                elif len(str(new_value)) > len(str(existing_value)) * 1.5:  # New is significantly more detailed
                    update_data[field] = new_value
                    logger.info(f"🔄 DETAIL UPDATE: Updating {field} with more detailed info for {existing_pet.name}")
        
        logger.info(f"🛡️ Smart merge for {existing_pet.name}: {len(update_data)} fields to update: {list(update_data.keys())}")
        return update_data
    
    async def _get_missing_info_summary(self, pets: List[PetProfile]) -> Dict[str, Any]:
        """Generate comprehensive missing information summary"""
        summary = {
            "total_missing_fields": 0,
            "critical_missing": [],
            "pets_with_missing_info": 0,
            "per_pet_missing": {},
            "missing_by_category": {
                "health": [],
                "basic": [],
                "emergency": [],
                "documentation": []
            },
            "completeness_percentage": 0.0,
            "next_priority_questions": []
        }
        
        # Field categorization
        field_categories = {
            "health": ["known_allergies", "medical_conditions", "spayed_neutered"],
            "basic": ["age", "breed", "weight", "gender", "date_of_birth"],
            "emergency": ["emergency_vet_name", "emergency_vet_phone"],
            "documentation": ["microchip_id"]
        }
        
        # Critical fields that should be prioritized
        critical_fields = ["emergency_vet_name", "known_allergies", "medical_conditions", "age", "breed"]
        
        total_possible_fields = len(field_categories["health"]) + len(field_categories["basic"]) + \
                               len(field_categories["emergency"]) + len(field_categories["documentation"])
        total_filled_fields = 0
        total_pets = len(pets)
        
        for pet in pets:
            missing = pet.get_missing_fields()
            if missing:
                summary["pets_with_missing_info"] += 1
                summary["total_missing_fields"] += len(missing)
                summary["per_pet_missing"][pet.name] = missing
                
                # Categorize missing fields
                for field in missing:
                    for category, fields_list in field_categories.items():
                        if field in fields_list and field not in summary["missing_by_category"][category]:
                            summary["missing_by_category"][category].append(field)
                    
                    # Track critical missing fields
                    if field in critical_fields and field not in summary["critical_missing"]:
                        summary["critical_missing"].append(field)
            
            # Calculate filled fields for this pet
            filled_fields = total_possible_fields - len(missing)
            total_filled_fields += filled_fields
        
        # Calculate overall completeness
        if total_pets > 0:
            max_possible_fields = total_possible_fields * total_pets
            summary["completeness_percentage"] = (total_filled_fields / max_possible_fields) * 100
        
        # Generate priority questions for the most critical missing info
        summary["next_priority_questions"] = self._generate_priority_questions(pets, summary["critical_missing"])
        
        return summary
    
    def _generate_priority_questions(self, pets: List[PetProfile], critical_missing: List[str]) -> List[str]:
        """Generate priority questions based on missing critical information"""
        questions = []
        
        # Question templates for critical fields
        question_templates = {
            "emergency_vet_name": "Who is {pet_name}'s veterinarian or preferred animal clinic?",
            "emergency_vet_phone": "What's the phone number for {pet_name}'s vet?",
            "known_allergies": "Does {pet_name} have any known allergies or food sensitivities?",
            "medical_conditions": "Does {pet_name} have any ongoing medical conditions?",
            "age": "How old is {pet_name}?",
            "breed": "What breed is {pet_name}?"
        }
        
        # Generate questions for each pet with critical missing fields
        for pet in pets:
            missing_fields = pet.get_missing_fields()
            for field in critical_missing:
                if field in missing_fields and len(questions) < 3:  # Limit to 3 priority questions
                    question = question_templates.get(field, f"What is {pet.name}'s {field.replace('_', ' ')}?")
                    questions.append(question.format(pet_name=pet.name))
        
        return questions
    
    async def _extract_with_caching(
        self, 
        message: str, 
        conversation_context: str,
        current_context: Dict[str, Any]
    ) -> PetExtractionResult:
        """Extract information with caching to avoid re-processing"""
        # Create cache key from message content
        message_hash = hashlib.md5(message.encode('utf-8')).hexdigest()
        cache_key = f"extraction:{message_hash}"
        

        skip_cache = True
        

        if not skip_cache:
            cached_result = await self.redis.get(cache_key)
            if cached_result:
                cached_data = json.loads(cached_result)
                return PetExtractionResult(**cached_data)
        
        # Extract information
        result = await self.extractor.extract_pet_information(
            message, current_context
        )
        
        # Cache the result
        await self.redis.setex(
            cache_key,
            self.extraction_cache_ttl,
            json.dumps({
                "extracted_fields": result.extracted_fields,
                "confidence_score": result.confidence_score,
                "raw_message": result.raw_message
            })
        )
        
        return result
    
    def _smart_merge_comprehensive_data(self, existing_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Intelligently merge comprehensive data, handling additive information.
        
        Args:
            existing_data: Current comprehensive profile data
            new_data: New data to merge, may contain ADDITIVE: prefixes
            
        Returns:
            Merged comprehensive data
        """
        merged_data = {**existing_data}
        
        for key, value in new_data.items():
            if isinstance(value, str) and value.startswith("ADDITIVE:"):
                # Handle additive information
                new_value = value[9:]  # Remove "ADDITIVE:" prefix
                
                if key in merged_data and merged_data[key]:
                    # Combine with existing data
                    existing_value = merged_data[key]
                    
                    # Smart combination logic
                    if key == "likes":
                        # For "likes", combine activities
                        if "and" not in existing_value and "and" not in new_value:
                            merged_data[key] = f"{existing_value} and {new_value}"
                        else:
                            # Already has multiple items, append
                            merged_data[key] = f"{existing_value}, {new_value}"
                    elif key in ["habits", "medical_notes", "personality"]:
                        # For descriptive fields, append with separator
                        merged_data[key] = f"{existing_value}; {new_value}"
                    else:
                        # For other fields, append with comma
                        merged_data[key] = f"{existing_value}, {new_value}"
                        
                    logger.info(f"🔄 ADDITIVE MERGE - {key}: '{existing_value}' + '{new_value}' = '{merged_data[key]}'")
                else:
                    # No existing data, just use new value without prefix
                    merged_data[key] = new_value
                    logger.info(f"🆕 ADDITIVE NEW - {key}: '{new_value}'")
            else:
                # Regular replacement
                merged_data[key] = value
                if key in existing_data:
                    logger.info(f"🔄 REPLACE - {key}: '{existing_data[key]}' → '{value}'")
                else:
                    logger.info(f"🆕 NEW - {key}: '{value}'")
        
        return merged_data
    
    async def _store_extracted_information(
        self, 
        user_id: int, 
        extraction_result: PetExtractionResult,
        current_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Store extracted information in database"""
        try:
            db_session = self.db_session_factory()
            async with db_session as session:
                pet_repo = PetRepository(session)
                
                pets_updated = []
                new_pets_created = []
                
                # Process primary pet (first extracted pet)  
                pets_to_process = []
                primary_pet_data = {}  # Initialize to prevent NameError
                
                # Handle new equal treatment structure vs legacy structure
                if "all_pets" in extraction_result.extracted_fields:
                    # New equal treatment structure - all pets treated equally
                    all_pets = extraction_result.extracted_fields["all_pets"]
                    if isinstance(all_pets, list):
                        pets_to_process.extend(all_pets)
                        logger.info(f"🐕 Processing {len(pets_to_process)} pets equally for user {user_id}")
                else:
                    # Legacy structure handling
                    primary_pet_data = {k: v for k, v in extraction_result.extracted_fields.items() 
                                          if k not in ["_additional_pets", "all_pets"]}
                
                # If there's a name field, treat as pet-specific data
                if primary_pet_data and "name" in primary_pet_data:
                    pets_to_process.append(primary_pet_data)
                # If no name but we have other pet data (e.g., vet info), apply to existing pets
                elif primary_pet_data:
                    # First try current context, then check database directly for existing pets
                    current_pets = current_context.get("pets", [])
                    if not current_pets:
                        # Query database directly for existing pets
                        logger.info(f"🔍 No pets in current context, checking database for existing pets for user {user_id}")
                        existing_pets_from_db = await pet_repo.get_pets_by_user_id(user_id)
                        current_pets = [{"name": pet.name, "id": pet.id} for pet in existing_pets_from_db] if existing_pets_from_db else []
                        logger.info(f"📋 Found {len(current_pets)} existing pets in database")
                    
                    if current_pets:
                            # Enhanced vet handling: Apply to all existing pets (ONLY when no specific pet mentioned)
                        # This handles cases where user says "my vet is Dr. Smith" without specifying which dog
                        for pet in current_pets:
                            pet_data_with_name = {"name": pet["name"], **primary_pet_data}
                            pets_to_process.append(pet_data_with_name)
                            logger.info(f"🏥 Applying vet/medical info to {len(current_pets)} existing pets (no specific pet mentioned): {list(primary_pet_data.keys())}")
                    else:
                        # No existing pets - store the vet info for future use
                        logger.info(f"🏥 Vet/medical information provided but no existing pets: {list(primary_pet_data.keys())}")
                        pass
                
                    # Process legacy additional pets if any (multi-pet extraction)
                if "_additional_pets" in extraction_result.extracted_fields:
                    additional_pets = extraction_result.extracted_fields["_additional_pets"]
                    if isinstance(additional_pets, list):
                        pets_to_process.extend(additional_pets)
                        logger.info(f"🐕 Processing {len(pets_to_process)} total pets for user {user_id} (legacy mode)")
                
                # Store each pet as separate row
                for pet_data in pets_to_process:
                    if "name" in pet_data:
                        pet_name = pet_data["name"]
                        
                        # Look for existing pet
                        existing_pet = await pet_repo.get_pet_by_name(user_id, pet_name)
                        
                        if existing_pet:
                            # CRITICAL FIX: Smart update with data quality protection
                            update_data = self._smart_merge_pet_data(existing_pet, pet_data)
                            
                            # 🆕 COMPREHENSIVE JSON INTEGRATION: Use each pet's individual comprehensive data
                            comprehensive_data_to_merge = {}
                            
                            # Each pet has its own comprehensive_profile data - treat all equally
                            if "comprehensive_profile" in pet_data and pet_data["comprehensive_profile"]:
                                comprehensive_data_to_merge = pet_data["comprehensive_profile"]
                                logger.info(f"📋 Using individual comprehensive data for {pet_name}: {len(comprehensive_data_to_merge)} fields")
                            # Check if this pet's data is in the extraction comprehensive_json (for single pet scenarios)
                            elif (hasattr(extraction_result, 'comprehensive_json') and extraction_result.comprehensive_json and 
                                  len(pets_to_process) == 1):
                                comprehensive_data_to_merge = extraction_result.comprehensive_json
                                logger.info(f"📋 Using comprehensive data for single pet {pet_name}: {len(comprehensive_data_to_merge)} fields")
                            
                            if comprehensive_data_to_merge:
                                # Get existing comprehensive profile
                                existing_comprehensive = existing_pet.comprehensive_profile or {}
                                
                                # Smart merge new comprehensive data with existing
                                merged_comprehensive = self._smart_merge_comprehensive_data(existing_comprehensive, comprehensive_data_to_merge)
                                update_data["comprehensive_profile"] = merged_comprehensive
                                
                                logger.info(f"📋 Merging comprehensive profile for {pet_name}: "
                                           f"Existing: {len(existing_comprehensive)} fields, "
                                           f"New: {len(comprehensive_data_to_merge)} fields, "
                                           f"Total: {len(merged_comprehensive)} fields")
                            
                            if update_data:
                                logger.info(f"🔄 Updating pet {pet_name} with structured + comprehensive data: {list(update_data.keys())}")
                                updated_pet = await pet_repo.update_pet_profile(user_id, existing_pet.id, update_data)
                                if updated_pet:
                                    pets_updated.append(pet_name)
                                    logger.info(f"✅ Successfully updated pet {pet_name} (structured + comprehensive)")
                                else:
                                    logger.error(f"❌ Failed to update pet {pet_name}")
                            else:
                                logger.info(f"ℹ️ No update data for pet {pet_name}")
                        else:
                            # SAFEGUARD: Check total pets before creating new ones to prevent duplication
                            existing_pets_count = len(await pet_repo.get_user_pets(user_id))
                            
                            if existing_pets_count >= 5:  # Reasonable limit
                                logger.warning(f"⚠️ User {user_id} already has {existing_pets_count} pets. Skipping creation of new pet '{pet_name}' to prevent duplication.")
                                # Try to find similar pets by breed/age instead
                                all_pets = await pet_repo.get_user_pets(user_id)
                                similar_pet = None
                                for existing in all_pets:
                                    existing_dict = existing.to_dict()
                                    if (pet_data.get('breed') and existing_dict.get('breed') == pet_data.get('breed') and
                                        pet_data.get('age') and existing_dict.get('age') == pet_data.get('age')):
                                        similar_pet = existing
                                        break
                                
                                if similar_pet:
                                    # Update the similar pet instead of creating new one (with comprehensive data)
                                    logger.info(f"🔄 Found similar pet {similar_pet.name} (breed: {similar_pet.breed}, age: {similar_pet.age}). Updating instead of creating '{pet_name}'.")
                                    update_data = {k: v for k, v in pet_data.items() if k != "name"}
                                    
                                    # 🆕 COMPREHENSIVE JSON INTEGRATION: Merge comprehensive profile with correct data for each pet
                                    comprehensive_data_to_merge = {}
                                    
                                    # For primary pet (first in pets_to_process), use extraction_result.comprehensive_json
                                    if pet_data == pets_to_process[0] and hasattr(extraction_result, 'comprehensive_json') and extraction_result.comprehensive_json:
                                        comprehensive_data_to_merge = extraction_result.comprehensive_json
                                        logger.info(f"📋 Using primary pet comprehensive data for similar pet {similar_pet.name}: {len(comprehensive_data_to_merge)} fields")
                                    # For additional pets, use their individual comprehensive_profile
                                    elif "comprehensive_profile" in pet_data and pet_data["comprehensive_profile"]:
                                        comprehensive_data_to_merge = pet_data["comprehensive_profile"]
                                        logger.info(f"📋 Using individual comprehensive data for additional similar pet {similar_pet.name}: {len(comprehensive_data_to_merge)} fields")
                                    
                                    if comprehensive_data_to_merge:
                                        # Get existing comprehensive profile
                                        existing_comprehensive = similar_pet.comprehensive_profile or {}
                                        
                                        # Smart merge new comprehensive data with existing
                                        merged_comprehensive = self._smart_merge_comprehensive_data(existing_comprehensive, comprehensive_data_to_merge)
                                        update_data["comprehensive_profile"] = merged_comprehensive
                                        
                                        logger.info(f"📋 Merging comprehensive profile for similar pet {similar_pet.name}: "
                                                   f"Existing: {len(existing_comprehensive)} fields, "
                                                   f"New: {len(comprehensive_data_to_merge)} fields, "
                                                   f"Total: {len(merged_comprehensive)} fields")
                                    
                                    if update_data:
                                        updated_pet = await pet_repo.update_pet_profile(user_id, similar_pet.id, update_data)
                                        if updated_pet:
                                            pets_updated.append(similar_pet.name)
                                            logger.info(f"✅ Updated similar pet {similar_pet.name} instead of creating duplicate (structured + comprehensive)")
                            else:
                                # Create new pet with both structured + comprehensive data
                                # 🆕 COMPREHENSIVE JSON INTEGRATION: Use each pet's individual comprehensive data
                                comprehensive_data = {}
                                
                                # Each pet has its own comprehensive_profile data - treat all equally
                                if "comprehensive_profile" in pet_data and pet_data["comprehensive_profile"]:
                                    comprehensive_data = pet_data["comprehensive_profile"]
                                    logger.info(f"📋 Creating pet {pet_name} with comprehensive profile: "
                                               f"{len(comprehensive_data)} fields")
                                # Fallback: Use extraction comprehensive_json for single pet scenarios
                                elif (hasattr(extraction_result, 'comprehensive_json') and extraction_result.comprehensive_json and 
                                      len(pets_to_process) == 1):
                                    comprehensive_data = extraction_result.comprehensive_json
                                    logger.info(f"📋 Creating single pet {pet_name} with comprehensive profile: "
                                               f"{len(comprehensive_data)} fields")
                                
                                # Clean pet_data to remove comprehensive_profile before passing to constructor
                                clean_pet_data = {k: v for k, v in pet_data.items() if k != "comprehensive_profile"}
                                
                                # Add comprehensive_profile to clean data if we have comprehensive data
                                if comprehensive_data:
                                    clean_pet_data["comprehensive_profile"] = comprehensive_data
                                
                                new_pet = await pet_repo.create_pet_profile(user_id, clean_pet_data)
                                if new_pet:
                                    new_pets_created.append(pet_name)
                                    logger.info(f"✅ Created new pet {pet_name} for user {user_id} (total: {existing_pets_count + 1}) "
                                               f"with structured + comprehensive data")
                
                else:
                    # No pet-specific data to process - check for general vet/medical info
                    # CRITICAL FIX: Only apply to all pets if NO specific pets were processed
                    if extraction_result.extracted_fields and not pets_updated and not new_pets_created:
                        existing_pets = current_context.get("pets", [])
                        
                        if existing_pets:
                            # Apply vet/medical info to all existing pets (ONLY when no specific pets mentioned)
                            vet_fields = {k: v for k, v in extraction_result.extracted_fields.items() 
                                        if k in ["emergency_vet_name", "emergency_vet_phone", "vet_name", "vet_phone", "vet_contact", "vet_experience"]}
                            
                            if vet_fields:
                                logger.info(f"🏥 Applying vet information to {len(existing_pets)} existing pets (no specific pets mentioned): {list(vet_fields.keys())}")
                                
                                # Apply to all existing pets
                                for pet in existing_pets:
                                    pet_name = pet.get("name")
                                    if pet_name:
                                        try:
                                            existing_pet = await pet_repo.get_pet_by_name(user_id, pet_name)
                                            if existing_pet:
                                                # Update with vet information
                                                update_data = {}
                                                
                                                # Map vet name fields
                                                if "emergency_vet_name" in vet_fields or "vet_name" in vet_fields:
                                                    update_data["emergency_vet_name"] = vet_fields.get("emergency_vet_name") or vet_fields.get("vet_name")
                                                
                                                # Map vet phone fields  
                                                if "emergency_vet_phone" in vet_fields or "vet_phone" in vet_fields or "vet_contact" in vet_fields:
                                                    update_data["emergency_vet_phone"] = (vet_fields.get("emergency_vet_phone") or 
                                                                                         vet_fields.get("vet_phone") or 
                                                                                         vet_fields.get("vet_contact"))
                                                
                                                # Store vet experience in comprehensive profile if available
                                                comprehensive_data = {}
                                                if "vet_experience" in vet_fields:
                                                    comprehensive_data["vet_experience"] = vet_fields["vet_experience"]
                                                
                                                if comprehensive_data:
                                                    # Merge with existing comprehensive profile
                                                    existing_comprehensive = existing_pet.comprehensive_profile or {}
                                                    merged_comprehensive = self._smart_merge_comprehensive_data(existing_comprehensive, comprehensive_data)
                                                    update_data["comprehensive_profile"] = merged_comprehensive
                                                
                                                if update_data:
                                                    await pet_repo.update_pet_profile(user_id, existing_pet.id, update_data)
                                                    pets_updated.append(pet_name)
                                                    logger.info(f"✅ Updated vet info for {pet_name}: {list(update_data.keys())}")
                                        except Exception as e:
                                            logger.error(f"❌ Error updating vet info for {pet_name}: {e}")
                        else:
                            logger.info(f"🏥 Vet/medical information provided but no existing pets to apply to: {list(extraction_result.extracted_fields.keys())}")
                    # If no pet-specific or vet info was processed, that's fine - user might just be chatting
                
                # Invalidate cache after successful pet data changes
                if len(pets_updated) > 0 or len(new_pets_created) > 0:
                    await self._invalidate_context_cache(user_id)
                    logger.info(f"🗑️ Invalidated pet context cache for user {user_id} after updating {len(pets_updated)} and creating {len(new_pets_created)} pets")
                
                return {
                    "success": len(pets_updated) > 0 or len(new_pets_created) > 0,
                    "pets_updated": pets_updated,
                    "new_pets_created": new_pets_created
                }
                
        except Exception as e:
            logger.error(f"❌ Error storing extracted information: {e}")
            return {"success": False, "error": str(e)}
    
    async def _generate_smart_follow_ups(
        self, 
        user_id: int, 
        extraction_result: PetExtractionResult,
        conversation_id: Optional[int],
        storage_result: Dict[str, Any]
    ) -> List[str]:
        """Generate smart follow-up questions with throttling"""
        # Check if we should ask questions
        if not await self.should_ask_follow_up_question(user_id, conversation_id):
            return []
        
        # Get relevant follow-up questions
        questions = extraction_result.follow_up_questions[:2]  # Limit to 2
        
        # Filter out questions for fields we just extracted
        extracted_fields = set(extraction_result.extracted_fields.keys())
        filtered_questions = []
        
        for question in questions:
            # Simple check - if question doesn't relate to just-extracted fields
            question_lower = question.lower()
            skip_question = False
            
            for field in extracted_fields:
                if field in question_lower or field.replace("_", " ") in question_lower:
                    skip_question = True
                    break
            
            if not skip_question:
                filtered_questions.append(question)
        
        # Record questions that will be asked
        for question in filtered_questions:
            await self.record_question_asked(user_id, conversation_id, question)
        
        return filtered_questions
    
    def _get_priority_fields_for_context(self, context_type: str) -> List[str]:
        """Get priority fields based on context"""
        context_priorities = {
            "health": ["medical_conditions", "known_allergies", "emergency_vet_name", "emergency_vet_phone", "age", "weight"],
            "emergency": ["emergency_vet_name", "emergency_vet_phone", "medical_conditions", "known_allergies"],
            "basic": ["breed", "age", "weight", "gender", "date_of_birth"],
            "general": ["breed", "age", "weight", "microchip_id", "spayed_neutered"]
        }
        
        return context_priorities.get(context_type, context_priorities["general"])
    
    def _pet_to_context(self, pet: PetProfile) -> Dict[str, Any]:
        """Convert PetProfile to context dictionary for chat responses"""
        try:
            # Base pet information
            context = {
                "id": pet.id,
                "name": pet.name,
                "breed": pet.breed,
                "age": pet.age,
                "weight": float(pet.weight) if pet.weight else None,
                "gender": pet.gender,
                "date_of_birth": pet.date_of_birth.isoformat() if pet.date_of_birth else None,
                "microchip_id": pet.microchip_id,
                "spayed_neutered": pet.spayed_neutered,
                "known_allergies": pet.known_allergies,
                "emergency_vet_name": pet.emergency_vet_name,
                "emergency_vet_phone": pet.emergency_vet_phone,
                "created_at": pet.created_at.isoformat() if pet.created_at else None,
                "updated_at": pet.updated_at.isoformat() if pet.updated_at else None
            }
            
            # Add comprehensive profile data (colors, favorite foods, personality traits, etc.)
            if pet.comprehensive_profile:
                context["comprehensive_profile"] = pet.comprehensive_profile
                
                # Extract key details for easy access
                if isinstance(pet.comprehensive_profile, dict):
                    context["color"] = pet.comprehensive_profile.get("color")
                    context["favorite_food"] = pet.comprehensive_profile.get("favorite_food") 
                    context["personality"] = pet.comprehensive_profile.get("personality")
                    context["special_traits"] = pet.comprehensive_profile.get("special_traits")
                    context["likes"] = pet.comprehensive_profile.get("likes")
                    context["habits"] = pet.comprehensive_profile.get("habits")
                    context["dislikes"] = pet.comprehensive_profile.get("dislikes")
            
            # Remove None values for cleaner context
            return {k: v for k, v in context.items() if v is not None}
            
        except Exception as e:
            logger.error(f"❌ Error converting pet to context: {e}")
            return {
                "id": getattr(pet, 'id', None),
                "name": getattr(pet, 'name', 'Unknown'),
                "breed": getattr(pet, 'breed', None),
                "age": getattr(pet, 'age', None)
            }
    
    async def _invalidate_context_cache(self, user_id: int) -> None:
        """Invalidate all pet context caches for user and chat service caches"""
        try:
            cache_keys = [
                f"pet_context:{user_id}",
                f"missing_fields:{user_id}:*",
                f"user_context:{user_id}",  # Chat service user context cache
                f"agent_session:{user_id}",  # Bedrock agents session cache
            ]
            
            for key_pattern in cache_keys:
                if "*" in key_pattern:
                    # Get matching keys and delete them
                    keys = await self.redis.keys(key_pattern)
                    if keys:
                        await self.redis.delete(*keys)
                else:
                    await self.redis.delete(key_pattern)
            
            logger.debug(f"🗑️ Invalidated pet context cache for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error invalidating cache: {e}")
    
    async def _process_user_response_for_tracking(self, user_id: int, message: str, extracted_fields: Dict[str, Any]) -> None:
        """Process user message to detect if they provided information that was previously asked about"""
        try:
            if not self.question_tracker:
                return
            
            # Get current pet context to find pet names
            current_context = await self.get_user_pet_context(user_id)
            pets = current_context.get("pets", [])
            pet_names = [pet.get("name", "unknown") for pet in pets if pet.get("name")]
            
            if not pet_names:
                # No pets to track for
                return
            
            # Use the built-in detection methods from question tracker
            provided_info = await self.question_tracker.detect_user_provided_info(user_id, message, pet_names)
            declined_info = await self.question_tracker.detect_user_declined(user_id, message, pet_names)
            
            # Record declined information
            for decline in declined_info:
                await self.question_tracker.record_user_declined(
                    user_id,
                    decline["pet_name"],
                    decline["field_name"],
                    decline.get("reason", "user_declined")
                )
                logger.debug(f"🚫 Recorded user declined {decline['field_name']} for {decline['pet_name']} (user {user_id})")
            
            # Log provided information (the extraction itself already records this data)
            if provided_info:
                logger.debug(f"📝 Detected user provided information: {provided_info}")
                
        except Exception as e:
            logger.error(f"❌ Error processing user response for tracking: {e}")
    
    async def _filter_questions_with_tracker(self, user_id: int, raw_questions: List[str], pets: List[Dict]) -> List[str]:
        """Filter questions using question tracker to prevent repetitive questioning"""
        try:
            if not self.question_tracker or not raw_questions:
                return raw_questions
            
            filtered_questions = []
            
            # Map question text to potential field names for tracking
            field_keywords = {
                "age": ["old", "age"],
                "breed": ["breed", "type"],
                "weight": ["weight", "weigh", "heavy"],
                "emergency_vet_name": ["vet", "veterinarian", "doctor"],
                "known_allergies": ["allergies", "allergic", "sensitive"],
                "medical_conditions": ["medical", "conditions", "health", "sick", "illness"]
            }
            
            for question in raw_questions:
                should_ask = True
                question_lower = question.lower()
                
                # Initialize pet_name early to avoid scope issues
                pet_name = "your pet"  # default
                
                # Try to identify which field this question is about
                field_name = None
                for field, keywords in field_keywords.items():
                    if any(keyword in question_lower for keyword in keywords):
                        field_name = field
                        break
                
                if field_name:
                    # Find which pet this question is about
                    for pet in pets:
                        name = pet.get("name", "")
                        if name and name.lower() in question_lower:
                            pet_name = name
                            break
                    
                    # Check if we should ask this question
                    recently_asked = await self.question_tracker.has_been_asked_recently(
                        user_id, pet_name, field_name, 24
                    )
                    user_declined = await self.question_tracker.user_declined_to_provide(
                        user_id, pet_name, field_name
                    )
                    
                    if recently_asked or user_declined:
                        should_ask = False
                        logger.debug(f"🚫 Filtered out question '{question[:50]}...' for {pet_name} - recently_asked: {recently_asked}, declined: {user_declined}")
                
                if should_ask:
                    filtered_questions.append(question)
                    
                    # Record that we're asking this question
                    if field_name:
                        await self.question_tracker.record_question_asked(user_id, pet_name, field_name, question)
            
            if len(filtered_questions) < len(raw_questions):
                logger.info(f"🔧 Question tracker filtered {len(raw_questions) - len(filtered_questions)} repetitive questions for user {user_id}")
            
            return filtered_questions
            
        except Exception as e:
            logger.error(f"❌ Error filtering questions with tracker: {e}")
            # Return original questions as fallback
            return raw_questions
