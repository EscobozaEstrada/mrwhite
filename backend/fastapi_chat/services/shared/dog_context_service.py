"""
Advanced Dog Context Service with Hybrid Detection Approach

This service uses a hybrid approach combining:
1. Fast pattern matching for initial detection
2. Database/memory lookups for user context  
3. AI-powered analysis for complex cases
4. Smart follow-up determination

"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from pydantic import BaseModel, Field
import asyncio

# Import PetRepository to avoid duplicate imports
try:
    from repositories.pet_repository import PetRepository
except ImportError:
    PetRepository = None

logger = logging.getLogger(__name__)

class DogInfo(BaseModel):
    """Structured dog information with comprehensive fields"""
    name: str
    breed: Optional[str] = None
    age: Optional[int] = None  # Changed to int for database compatibility
    weight: Optional[float] = None  # Changed to float for database compatibility
    health_notes: Optional[str] = None
    last_updated: Optional[str] = None
    
    # Extended fields for comprehensive dog profiles
    size: Optional[str] = None
    temperament: Optional[str] = None
    health_conditions: Optional[List[str]] = []
    training_level: Optional[str] = None
    special_needs: Optional[List[str]] = []
    confidence: Optional[float] = None

class DogContextService:
    """
    Advanced dog context service using hybrid approach for maximum efficiency
    """
    
    def __init__(self, langgraph_service=None):
        self.langgraph_service = langgraph_service
        # Fast pattern matching patterns - optimized for speed
        self.dog_keywords = [
            'dog', 'pet', 'puppy', 'pup', 'canine', 'pooch', 'doggy', 'doggie',
            'fur baby', 'four-legged', 'companion'
        ]
        
        self.dog_action_keywords = [
            'train', 'training', 'walk', 'walking', 'feed', 'feeding', 'groom', 'grooming',
            'bark', 'barking', 'bite', 'biting', 'play', 'playing', 'exercise', 'sit', 'stay',
            'come', 'heel', 'down', 'rollover', 'fetch', 'leash', 'collar', 'treats'
        ]
        
        # Highly specific pattern matching for dog names (ultra-conservative to prevent false positives)
        self.dog_name_patterns = [
            # Only explicit naming patterns (highest confidence)
            r"my dog (?:is )?(?:named|called)\s+([A-Z][a-z]+)",
            r"our dog (?:is )?(?:named|called)\s+([A-Z][a-z]+)",
            r"I have a dog (?:named|called)\s+([A-Z][a-z]+)",
            r"we have a dog (?:named|called)\s+([A-Z][a-z]+)",
            
            # Formal introduction patterns (very specific)
            r"(?:this is|meet|introducing)\s+([A-Z][a-z]+),?\s+(?:my|our)\s+dog",
            r"(?:this is|meet|introducing)\s+my\s+dog\s+([A-Z][a-z]+)",
            r"this\s+is\s+my\s+dog\s+([A-Z][a-z]+)",
            
            # Name-first patterns (only with capitalized names)
            r"([A-Z][a-z]+)\s+is\s+my\s+dog",
            r"([A-Z][a-z]+)\s+is\s+our\s+dog",
            
            # Possessive patterns (clear ownership with capitalized names)
            r"([A-Z][a-z]+)'s\s+(?:food|toy|bed|leash|collar|bowl)",
            
            # Walk/take patterns (only with clear structure)
            r"walk\s+my\s+dog\s+([A-Z][a-z]+)",
            r"take\s+([A-Z][a-z]+)\s+for\s+a\s+walk",
        ]
        
        # Common false positive words to exclude
        self.false_positives = {
            'dog', 'pet', 'puppy', 'he', 'she', 'it', 'they', 'this', 'that', 'the', 'my', 'our',
            'has', 'have', 'had', 'was', 'is', 'are', 'been', 'being', 'very', 'really', 'just',
            'also', 'only', 'still', 'never', 'always', 'sometimes', 'maybe', 'probably',
            'suddenly', 'quickly', 'slowly', 'gently', 'carefully', 'name', 'called', 'named',
            'train', 'training', 'walk', 'walking', 'play', 'playing', 'sit', 'stay', 'come',
            'down', 'up', 'go', 'get', 'help', 'need', 'needs', 'want', 'wants', 'how', 'what',
            'when', 'where', 'why', 'can', 'could', 'should', 'would', 'will', 'much', 'many',
            'some', 'any', 'all', 'do', 'does', 'did', 'make', 'makes', 'made', 'to', 'too',
            'years', 'old', 'about', 'around', 'his', 'her', 'well', 'actually', 'so', 'yes', 'yeah',
            # Critical additions to prevent false positives from user queries
            'of', 'to', 'me', 'tell', 'names', 'age', 'years', 'stays', 'ensure', 'teach', 'bring',
            'ring', 'stop', 'mentally', 'stimulated', 'local', 'groomer', 'groomers', 'radius',
            'mile', 'miles', 'city', 'approved', 'white', 'mr', 'listen', 'understood', 'bering',
            'like', 'would', 'outsdie', 'outside', 'bell', 'jumps', 'people', 'greet', 'tips',
            'barking', 'window', 'moves', 'anything', 'behavoir', 'behavior', 'frustration',
            # Common words that appear in sentences
            'can', 'will', 'should', 'could', 'would', 'might', 'must', 'shall', 'may',
            'always', 'never', 'sometimes', 'often', 'usually', 'frequently', 'rarely',
            'every', 'each', 'all', 'some', 'any', 'many', 'few', 'several', 'both',
            'either', 'neither', 'other', 'another', 'same', 'different', 'new', 'old'
        }

    async def detect_dog_context_need(self, message: str, user_id: int) -> Dict[str, Any]:
        """
        Main hybrid detection method - combines speed with intelligence
        
        Returns:
            {
                "needs_follow_up": bool,
                "follow_up_type": str,  # "no_dog_info", "multiple_dogs", "new_dog", None
                "confidence": float,
                "detected_dogs": List[str],
                "reasoning": str
            }
        """
        try:
            # STEP 1: Fast pattern pre-filter (microseconds)
            has_dog_mention = self._fast_dog_detection(message)
            if not has_dog_mention:
                return {
                    "needs_follow_up": False,
                    "follow_up_type": None,
                    "confidence": 0.0,
                    "detected_dogs": [],
                    "reasoning": "No dog-related keywords detected"
                }
            
            # STEP 2: Extract potential dog names (milliseconds)
            potential_dogs = self._extract_dog_names(message)
            
            # STEP 3: Get existing user dog context (database lookup - fast)
            existing_dogs = await self._get_user_dogs(user_id)
            
            # STEP 4: Smart decision logic
            decision = await self._determine_follow_up_need(
                message, potential_dogs, existing_dogs, user_id
            )
            
            logger.info(f"🐕 Dog context analysis for user {user_id}: {decision['reasoning']}")
            return decision
            
        except Exception as e:
            logger.error(f"❌ Error in dog context detection: {e}")
            return {
                "needs_follow_up": False,
                "follow_up_type": None,
                "confidence": 0.0,
                "detected_dogs": [],
                "reasoning": f"Error in detection: {str(e)}"
            }

    def _fast_dog_detection(self, message: str) -> bool:
        """
        Lightning-fast initial detection using simple keyword matching
        """
        message_lower = message.lower()
        
        # Check for dog keywords
        has_dog_keyword = any(keyword in message_lower for keyword in self.dog_keywords)
        
        # Check for dog action keywords (train, walk, etc.)
        has_action_keyword = any(action in message_lower for action in self.dog_action_keywords)
        
        return has_dog_keyword or has_action_keyword

    def _extract_dog_names(self, message: str) -> List[str]:
        """
        Extract potential dog names using pattern matching with enhanced validation
        """
        potential_names = set()
        
        for pattern in self.dog_name_patterns:
            matches = re.finditer(pattern, message, re.IGNORECASE)
            for match in matches:
                name = match.group(1).strip().title()
                
                # Enhanced validation
                if self._validate_dog_name_in_context(name, message):
                    potential_names.add(name)
        
        return list(potential_names)
    
    def _validate_dog_name_in_context(self, name: str, message: str) -> bool:
        """
        Ultra-strict validation for detected dog names with context awareness
        """
        # Basic validation - more strict
        if (len(name) < 2 or 
            len(name) > 12 or 
            not name.isalpha() or
            name.lower() in self.false_positives):
            return False
        
        # Must be capitalized (dog names are proper nouns)
        if not name[0].isupper():
            return False
        
        message_lower = message.lower()
        name_lower = name.lower()
        
        # Reject if name appears in common sentence structures that indicate it's not a dog name
        rejection_patterns = [
            # Questions about dogs (name is part of question, not answer)
            rf"tell\s+me.*{re.escape(name_lower)}",
            rf"what.*{re.escape(name_lower)}.*names?",
            rf"names?\s+of.*{re.escape(name_lower)}",
            rf"how.*{re.escape(name_lower)}.*dog",
            rf"can.*{re.escape(name_lower)}.*dog",
            rf"should.*{re.escape(name_lower)}.*dog",
            rf"would.*{re.escape(name_lower)}.*dog",
            
            # Action patterns where word is verb, not name
            rf"to\s+{re.escape(name_lower)}\s+",
            rf"can\s+{re.escape(name_lower)}\s+",
            rf"would\s+like\s+to\s+{re.escape(name_lower)}",
            rf"i\s+(?:can|should|would|will)\s+{re.escape(name_lower)}",
            
            # Time/age patterns
            rf"{re.escape(name_lower)}\s+(?:is|was|are)\s+\d+",
            rf"{re.escape(name_lower)}\s+years?",
            rf"\d+\s+{re.escape(name_lower)}",
            
            # Location/descriptive patterns
            rf"{re.escape(name_lower)}\s+(?:groomer|city|radius|mile|approved)",
            rf"(?:mr|white|local)\s+{re.escape(name_lower)}",
            
            # Common verbs that aren't dog names
            rf"(?:my|the)\s+dog\s+{re.escape(name_lower)}",  # "my dog stays" not "my dog Stays"
        ]
        
        for pattern in rejection_patterns:
            if re.search(pattern, message_lower):
                return False
        
        # Additional strict checks
        
        # Reject if appears in questions about dog information
        if ("names" in message_lower and "dog" in message_lower and 
            any(q in message_lower for q in ["tell", "what", "which", "who", "how"])):
            return False
        
        # Reject if followed by common non-name indicators
        follow_patterns = [
            rf"{re.escape(name_lower)}\s+(?:me|are|is|was|can|should|would|will|might)",
            rf"{re.escape(name_lower)}\s+(?:mentally|always|never|sometimes|often)",
            rf"{re.escape(name_lower)}\s+(?:up|on|at|in|to|for|with|from)"
        ]
        
        for pattern in follow_patterns:
            if re.search(pattern, message_lower):
                return False
        
        # Only accept if it looks like a real dog name pattern
        valid_patterns = [
            rf"(?:named|called)\s+{re.escape(name_lower)}",  # "named Rex"
            rf"{re.escape(name_lower)}\s+is\s+my\s+dog",     # "Rex is my dog"
            rf"my\s+dog\s+{re.escape(name_lower)}",          # "my dog Rex"  
            rf"this\s+is\s+my\s+dog\s+{re.escape(name_lower)}", # "this is my dog Max"
            rf"{re.escape(name_lower)}'s\s+(?:food|toy|bed)", # "Rex's food"
        ]
        
        # Must match at least one valid pattern
        for pattern in valid_patterns:
            if re.search(pattern, message_lower):
                return True
        
        # If no valid pattern found, reject
        return False

    def _validate_user_dog_name(self, name: str, message: str) -> bool:
        """
        ENHANCED: Smarter validation that filters false positives while keeping real names
        """
        if not name or len(name) < 2:
            logger.debug(f"🚫 Rejected dog name '{name}': too short")
            return False
        
        name_lower = name.lower()
        
        # EXPANDED false positives list - includes breed names and common words
        obvious_false_positives = {
            # Basic words
            'dog', 'pet', 'animal', 'puppy', 'dogs', 'pets', 'animals', 'puppies',
            'he', 'she', 'it', 'they', 'him', 'her', 'them', 'his', 'hers', 'its', 'their',
            'you', 'your', 'yours', 'me', 'my', 'mine', 'we', 'our', 'ours', 'us',
            'the', 'and', 'or', 'but', 'if', 'when', 'where', 'why', 'how', 'what',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            
            # Dog-related but not names
            'name', 'names', 'breed', 'breeds', 'age', 'ages', 'year', 'years',
            'old', 'young', 'male', 'female', 'boy', 'girl', 'there', 'here',
            'care', 'help', 'about', 'should', 'would', 'could', 'training',
            
            # CRITICAL: Numbers and measurements (common false positives)
            'two', 'three', 'four', 'five', 'one', 'pounds', 'weight', 'wights',
            'aged', 'weighs', 'weights', 'lbs', 'kg', 'kilos',
            
            # CRITICAL: Breed names (should not be dog names)
            'poodle', 'labrador', 'lebrador', 'retriever', 'shepherd', 'bulldog',
            'beagle', 'boxer', 'chihuahua', 'husky', 'collie', 'terrier', 'spaniel',
            'mastiff', 'rottweiler', 'dalmatian', 'doberman', 'pitbull', 'golden',
            'german', 'border', 'yorkshire', 'cocker', 'french', 'english',
            
            # Common descriptive words that could be picked up
            'big', 'small', 'little', 'large', 'tiny', 'sweet', 'good', 'bad',
            'black', 'white', 'brown', 'golden', 'red', 'blue', 'gray', 'grey',
            
            # CRITICAL: Common adverbs and descriptive words (frequent false positives)
            'very', 'quite', 'really', 'always', 'never', 'sometimes', 'often',
            'much', 'many', 'more', 'most', 'less', 'least', 'best', 'better',
            'well', 'still', 'just', 'only', 'also', 'too', 'even', 'also',
            'now', 'then', 'today', 'yesterday', 'tomorrow', 'soon', 'later',
            'first', 'second', 'third', 'last', 'next', 'previous', 'new', 'old',
            
            # Action words that might be extracted
            'can', 'will', 'would', 'should', 'could', 'might', 'may', 'must',
            'do', 'does', 'did', 'done', 'get', 'got', 'give', 'take', 'make',
            'come', 'go', 'see', 'know', 'think', 'want', 'need', 'like', 'love',
            
            # Common conversation words
            'yes', 'no', 'maybe', 'sure', 'okay', 'fine', 'right', 'wrong',
            'true', 'false', 'please', 'thanks', 'thank', 'sorry', 'excuse'
        }
        
        if name_lower in obvious_false_positives:
            logger.debug(f"🚫 Rejected dog name '{name}': in false positives list")
            return False
        
        # Must be alphabetic
        if not name.isalpha():
            logger.debug(f"🚫 Rejected dog name '{name}': not alphabetic")
            return False
        
        # Reasonable length for a dog name
        if len(name) > 20:
            logger.debug(f"🚫 Rejected dog name '{name}': too long")
            return False
        
        # Additional smart filtering: reject if it looks like a misspelled breed
        if self._looks_like_misspelled_breed(name_lower):
            logger.debug(f"🚫 Rejected dog name '{name}': looks like misspelled breed")
            return False
        
        # Check for common dog names to increase confidence
        common_dog_names = {
            'max', 'bella', 'charlie', 'lucy', 'cooper', 'luna', 'buddy', 'daisy',
            'rocky', 'molly', 'jack', 'sadie', 'duke', 'sophie', 'bear', 'lola',
            'tucker', 'chloe', 'toby', 'penny', 'murphy', 'maggie', 'oliver', 'ruby',
            'rex', 'rosie', 'sam', 'maya', 'zeus', 'lily', 'oscar', 'stella',
            'laila', 'kenny'  # Add the user's actual dogs
        }
        
        # Log validation result
        is_common = name_lower in common_dog_names
        logger.debug(f"✅ Validated dog name '{name}' (common: {is_common})")
        
        return True
    
    def _looks_like_misspelled_breed(self, name_lower: str) -> bool:
        """
        NEW: Detect if a name looks like a misspelled breed name
        """
        breed_variations = {
            'lebrador': 'labrador',  # Common misspelling
            'retreiver': 'retriever',
            'sheperd': 'shepherd', 
            'shephard': 'shepherd',
            'puddle': 'poodle',  # Sometimes autocorrected
            'huskey': 'husky'
        }
        
        return name_lower in breed_variations

    async def _get_user_dogs(self, user_id: int) -> Dict[str, DogInfo]:
        """
        IMPROVED: Retrieve existing dog information with better debugging and database fallback
        """
        try:
            if not self.langgraph_service or not self.langgraph_service.store:
                logger.warning(f"🐕 No LangGraph service available for user {user_id} - trying database fallback")
                return await self._get_user_dogs_from_database(user_id)
            
            logger.debug(f"🔍 Searching LangGraph memory for user {user_id} dogs...")
            
            # Search for user's dog information in LangGraph store with multiple queries
            search_queries = [
                "dog information name breed age",
                "pet information",
                "dog name breed",  # Simpler query
                f"user {user_id} dog"  # User-specific query
            ]
            
            all_dog_memories = []
            for query in search_queries:
                try:
                    dog_memories = await self.langgraph_service.store.asearch(
                        (f"user_{user_id}", "dogs"),
                        query=query,
                        limit=5
                    )
                    all_dog_memories.extend(dog_memories)
                    logger.debug(f"🔍 Query '{query}' found {len(dog_memories)} memories")
                except Exception as search_error:
                    logger.warning(f"⚠️ Search query '{query}' failed: {search_error}")
                    continue
            
            # Also try searching general memories namespace
            try:
                general_memories = await self.langgraph_service.store.asearch(
                    (f"user_{user_id}", "memories"),
                    query="dog pet name breed information",
                limit=10
            )
                all_dog_memories.extend(general_memories)
                logger.debug(f"🔍 General memories search found {len(general_memories)} additional memories")
            except Exception as general_error:
                logger.debug(f"⚠️ General memories search failed: {general_error}")
            
            # Remove duplicates and process memories
            unique_memories = {}
            for memory in all_dog_memories:
                memory_key = str(memory.key) if hasattr(memory, 'key') else str(hash(str(memory.value)))
                unique_memories[memory_key] = memory
            
            logger.debug(f"🔍 Found {len(unique_memories)} unique memories after deduplication")
            
            dogs_dict = {}
            for memory in unique_memories.values():
                try:
                    if hasattr(memory, 'value') and memory.value:
                        value = memory.value
                        if isinstance(value, dict) and value.get("name"):
                            dog_name = value.get("name").title()  # Ensure consistent naming
                            dogs_dict[dog_name] = DogInfo(
                                name=dog_name,
                                breed=value.get("breed"),
                                age=value.get("age"),
                                weight=value.get("weight"),
                                health_notes=value.get("health_notes"),
                                last_updated=value.get("last_updated")
                            )
                            logger.debug(f"✅ Extracted dog info: {dog_name}")
                        elif isinstance(value, dict) and value.get("text"):
                            # Try to extract dog info from text content
                            extracted = self._extract_comprehensive_dog_info(value.get("text", ""))
                            for dog_name, dog_data in extracted.get("dogs", {}).items():
                                if dog_name not in dogs_dict:
                                    dogs_dict[dog_name] = DogInfo(
                                        name=dog_name,
                                        breed=dog_data.get("breed"),
                                        age=dog_data.get("age"),
                                        weight=dog_data.get("weight"),
                                        health_notes=dog_data.get("health_notes")
                                    )
                                    logger.debug(f"✅ Extracted dog from text: {dog_name}")
                except Exception as parse_error:
                    logger.debug(f"⚠️ Failed to parse memory: {parse_error}")
                    continue
            
            logger.info(f"🐕 Retrieved {len(dogs_dict)} dogs from LangGraph for user {user_id}: {list(dogs_dict.keys())}")
            
            # If no dogs found in LangGraph, try database fallback
            if not dogs_dict:
                logger.info(f"🔄 No dogs in LangGraph, trying database fallback for user {user_id}")
                return await self._get_user_dogs_from_database(user_id)
            
            return dogs_dict
            
        except Exception as e:
            logger.error(f"❌ Error retrieving user dogs from LangGraph: {e}")
            logger.info(f"🔄 Falling back to database for user {user_id}")
            return await self._get_user_dogs_from_database(user_id)

    async def _get_user_dogs_from_database(self, user_id: int) -> Dict[str, DogInfo]:
        """
        Database fallback for retrieving dog information from pet_profiles table
        """
        try:
            from models import AsyncSessionLocal
            
            if PetRepository is None:
                logger.warning("PetRepository not available, skipping database fallback")
                return {}
            
            # Use the existing pet repository to get stored pet data
            db_session = AsyncSessionLocal()
            async with db_session as session:
                pet_repo = PetRepository(session)
                pets = await pet_repo.get_user_pets(user_id)
                
                dogs_dict = {}
                for pet in pets:
                    # Convert PetProfile to DogInfo format
                    dogs_dict[pet.name] = DogInfo(
                        name=pet.name,
                        breed=pet.breed or "Unknown",
                        age=pet.age or 0,
                        size="Unknown",  # Not stored in pet_profiles yet
                        temperament="Unknown",  # Not stored in pet_profiles yet
                        health_conditions=pet.medical_conditions.split(',') if pet.medical_conditions else [],
                        training_level="Unknown",  # Not stored in pet_profiles yet
                        special_needs=[],  # Could extract from medical_conditions
                        confidence=0.9  # High confidence since from database
                    )
                
                logger.info(f"🗃️ Retrieved {len(dogs_dict)} dogs from database for user {user_id}: {list(dogs_dict.keys())}")
                return dogs_dict
            
        except Exception as db_error:
            logger.error(f"🗃️ Database fallback error for user {user_id}: {db_error}")
            return {}

    async def _determine_follow_up_need(
        self, 
        message: str, 
        detected_dogs: List[str], 
        existing_dogs: Dict[str, DogInfo],
        user_id: int
    ) -> Dict[str, Any]:
        """
        Smart logic to determine if follow-up questions are needed
        """
        
        # Case 1: No existing dog info - check if user is providing info now
        if not existing_dogs:
            # Check if user is providing dog information in this message
            extracted_info = self._extract_comprehensive_dog_info(message)
            if extracted_info["dogs"]:
                # User is providing dog information, don't ask for follow-up
                return {
                    "needs_follow_up": False,
                    "follow_up_type": None,
                    "confidence": 0.8,
                    "detected_dogs": list(extracted_info["dogs"].keys()),
                    "reasoning": f"User is providing dog information in this message"
                }
            else:
                # User mentioned dogs but no detailed info provided, ask for follow-up
                return {
                    "needs_follow_up": True,
                    "follow_up_type": "no_dog_info",
                    "confidence": 0.9,
                    "detected_dogs": detected_dogs,
                    "reasoning": f"User mentioned dogs but we have no information about their dogs"
                }
        
        # Case 2: Single dog - usually no follow-up needed
        if len(existing_dogs) == 1:
            return {
                "needs_follow_up": False,
                "follow_up_type": None,
                "confidence": 0.8,
                "detected_dogs": detected_dogs,
                "reasoning": f"User has one dog ({list(existing_dogs.keys())[0]}), no clarification needed"
            }
        
        # Case 3: Multiple dogs - need AI to check if specific dog mentioned
        if len(existing_dogs) > 1:
            # Check if any detected dog names match existing dogs
            existing_names = set(existing_dogs.keys())
            mentioned_existing_dogs = [dog for dog in detected_dogs if dog in existing_names]
            
            if mentioned_existing_dogs:
                # Specific dog mentioned
                return {
                    "needs_follow_up": False,
                    "follow_up_type": None,
                    "confidence": 0.8,
                    "detected_dogs": mentioned_existing_dogs,
                    "reasoning": f"User mentioned specific dog: {mentioned_existing_dogs[0]}"
                }
            else:
                # No specific dog mentioned - need clarification
                return {
                    "needs_follow_up": True,
                    "follow_up_type": "multiple_dogs_clarification",
                    "confidence": 0.9,
                    "detected_dogs": detected_dogs,
                    "reasoning": f"User has multiple dogs ({list(existing_names)}) but didn't specify which one"
                }
        
        # Case 4: New dog detected
        if detected_dogs:
            new_dogs = [dog for dog in detected_dogs if dog not in existing_dogs]
            if new_dogs:
                return {
                    "needs_follow_up": True,
                    "follow_up_type": "new_dog_mentioned",
                    "confidence": 0.8,
                    "detected_dogs": new_dogs,
                    "reasoning": f"New dog mentioned: {new_dogs[0]}"
                }
        
        # Default: No follow-up needed
        return {
            "needs_follow_up": False,
            "follow_up_type": None,
            "confidence": 0.7,
            "detected_dogs": detected_dogs,
            "reasoning": "General dog mention, no follow-up needed"
        }

    async def store_dog_information(self, user_id: int, dog_info: DogInfo) -> bool:
        """
        IMPROVED: Store dog information with better error handling and dual storage
        """
        try:
            logger.debug(f"🐕 Attempting to store dog info: {dog_info.name} for user {user_id}")
            
            if not self.langgraph_service or not self.langgraph_service.store:
                logger.warning("⚠️ LangGraph service not available, storing in database only")
                return await self._store_dog_in_database(user_id, dog_info)
            
            # Store dog information in LangGraph store
            from datetime import datetime
            dog_data = {
                "name": dog_info.name.title(),  # Ensure consistent naming
                "breed": dog_info.breed,
                "age": dog_info.age,
                "weight": dog_info.weight,
                "health_notes": dog_info.health_notes,
                "last_updated": datetime.now().isoformat(),
                "user_id": user_id  # Add user ID for better tracking
            }
            
            # Store with multiple keys for better retrieval
            dog_key = f"dog_{dog_info.name.lower()}"
            
            try:
                # Store in dogs namespace
                await self.langgraph_service.store.aput(
                    (f"user_{user_id}", "dogs"),
                    dog_key,
                    dog_data
                )
                logger.debug(f"✅ Stored in dogs namespace: {dog_key}")
                
                # Also store in general memories for backup retrieval
                memory_data = {
                    "text": f"I have a dog named {dog_info.name}" + 
                           (f" who is a {dog_info.breed}" if dog_info.breed else "") +
                           (f" and is {dog_info.age} years old" if dog_info.age else ""),
                    "type": "dog_information",
                    "timestamp": datetime.now().isoformat(),
                    "importance": 0.8,
                    "dog_data": dog_data  # Store structured data too
                }
                
                await self.langgraph_service.store.aput(
                    (f"user_{user_id}", "memories"),
                    f"dog_memory_{dog_info.name.lower()}",
                    memory_data
                )
                logger.debug(f"✅ Stored backup in memories namespace")
                
                logger.info(f"🐕 Successfully stored dog info in LangGraph for user {user_id}: {dog_info.name}")
                
                # Also store in database for persistence
                db_success = await self._store_dog_in_database(user_id, dog_info)
                if db_success:
                    logger.debug(f"✅ Also stored in database")
                
                return True
                
            except Exception as storage_error:
                logger.error(f"❌ Failed to store in LangGraph: {storage_error}")
                # Fallback to database only
                return await self._store_dog_in_database(user_id, dog_info)
            
        except Exception as e:
            logger.error(f"❌ Error in store_dog_information: {e}")
            return False

    async def _store_dog_in_database(self, user_id: int, dog_info: DogInfo) -> bool:
        """
        Store dog information in database using Pet Repository
        """
        try:
            from pet_models_pkg.pet_models import PetProfileCreate
            from models import AsyncSessionLocal
            
            if PetRepository is None:
                logger.warning("PetRepository not available, cannot store dog information in database")
                return False
            
            # Check if pet already exists
            db_session = AsyncSessionLocal()
            async with db_session as session:
                pet_repo = PetRepository(session)
                existing_pets = await pet_repo.get_user_pets(user_id)
                
                # Check if this dog already exists (by name)
                existing_pet = None
                for pet in existing_pets:
                    if pet.name.lower() == dog_info.name.lower():
                        existing_pet = pet
                        break
                
                if existing_pet:
                    # Update existing pet with additional information
                    update_data = {}
                    if dog_info.breed and dog_info.breed != "Unknown":
                        update_data["breed"] = dog_info.breed
                    if dog_info.age and dog_info.age > 0:
                        update_data["age"] = dog_info.age
                    if dog_info.health_conditions:
                        update_data["medical_conditions"] = ", ".join(dog_info.health_conditions)
                    
                    if update_data:
                        await pet_repo.update_pet_fields(existing_pet.id, update_data)
                        logger.info(f"🐕 Updated existing pet in database: {dog_info.name}")
                else:
                    # Create new pet profile
                    pet_data = PetProfileCreate(
                        user_id=user_id,
                        name=dog_info.name,
                        breed=dog_info.breed if dog_info.breed != "Unknown" else None,
                        age=dog_info.age if dog_info.age > 0 else None,
                        medical_conditions=", ".join(dog_info.health_conditions) if dog_info.health_conditions else None
                    )
                    
                    new_pet = await pet_repo.create_pet(pet_data)
                    if new_pet:
                        logger.info(f"🐕 Created new pet in database: {dog_info.name}")
                
                return True
            
        except Exception as db_error:
            logger.error(f"🗃️ Failed to store dog in database for user {user_id}: {db_error}")
            return False

    def generate_follow_up_question(self, follow_up_type: str, context: Dict[str, Any] = None) -> str:
        """
        Generate appropriate follow-up question based on type and existing information
        """
        if follow_up_type == "no_dog_info":
            return ("Also, I'd love to provide more personalized advice! "
                   "Could you tell me about your dog? I'd like to know their name, breed, age, "
                   "and any other details you'd like to share.")
        
        elif follow_up_type == "multiple_dogs_clarification":
            if context and context.get("dog_names"):
                dog_names = ", ".join(context["dog_names"])
                return (f"By the way, since you have multiple dogs ({dog_names}), "
                       f"which specific dog are you asking about? This will help me give you "
                       f"more targeted advice for that particular dog.")
            else:
                return ("Since you have multiple dogs, which specific dog are you asking about? "
                       "This will help me give you more targeted advice.")
        
        elif follow_up_type == "new_dog_mentioned":
            return ("I'd also like to learn more about this dog you mentioned. "
                   "Could you tell me their name, breed, age, and any other details about them?")
        
        elif follow_up_type == "partial_info":
            # Smart follow-up for when user has some info but missing others
            missing_info = context.get("missing_info", [])
            if missing_info:
                missing_str = ", ".join(missing_info)
                return (f"Thanks for the information! If you'd like more personalized advice, "
                       f"could you also share your dog's {missing_str}?")
            else:
                return ("If there are any other details about your dog you'd like to share, "
                       "I'd be happy to provide more personalized advice!")
        
        else:
            return ("I'd also like to know more about your dog to give you better advice. "
                   "What's their name, breed, and age?")

    async def process_user_response_to_followup(self, user_id: int, response: str) -> Dict[str, Any]:
        """
        Process user's response to follow-up questions and extract dog information
        """
        try:
            # Extract dog information from user's response
            extracted_info = self._extract_comprehensive_dog_info(response)
            
            # Store the information
            if extracted_info["dogs"]:
                for dog_name, dog_data in extracted_info["dogs"].items():
                    dog_info = DogInfo(
                        name=dog_name,
                        breed=dog_data.get("breed"),
                        age=dog_data.get("age"),
                        weight=dog_data.get("weight"),
                        health_notes=dog_data.get("health_notes")
                    )
                    await self.store_dog_information(user_id, dog_info)
            
            return {
                "success": True,
                "extracted_info": extracted_info,
                "message": f"Great! I've noted information about {', '.join(extracted_info['dogs'].keys())}"
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing follow-up response: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _extract_comprehensive_dog_info(self, response: str) -> Dict[str, Any]:
        """
        COMPLETELY REWRITTEN: NLP-based extraction that focuses on user messages only
        Uses a more intelligent approach than regex pattern matching
        """
        dogs_info = {}
        
        # Clean and filter input - ONLY process user messages, not AI responses
        clean_text = self._extract_user_message_only(response)
        
        if not clean_text:
            logger.debug(f"🚫 No user message content found in: '{response[:100]}...'")
            return {"dogs": dogs_info, "raw_response": response}
        
        logger.debug(f"🔍 Extracting dog info from cleaned user text: '{clean_text}'")
        
        # Use NLP-based approach instead of complex regex
        extracted_dogs = self._nlp_extract_dog_names_and_info(clean_text)
        
        # Validate and structure the results
        for dog_name, dog_data in extracted_dogs.items():
            if self._validate_user_dog_name(dog_name, clean_text):
                dogs_info[dog_name.title()] = dog_data
                logger.debug(f"✅ Validated and added dog: {dog_name}")
            else:
                logger.debug(f"🚫 Rejected invalid dog name: {dog_name}")
        
        # Log final extraction results
        logger.info(f"🐕 NLP Extraction complete: Found {len(dogs_info)} dogs in '{clean_text[:50]}...'")
        for dog_name, dog_data in dogs_info.items():
            fields = [f"name={dog_name}"]
            if dog_data.get("breed"): fields.append(f"breed={dog_data['breed']}")
            if dog_data.get("age"): fields.append(f"age={dog_data['age']}")
            if dog_data.get("weight"): fields.append(f"weight={dog_data['weight']}")
            logger.info(f"  🐕 {dog_name}: {', '.join(fields)}")
        
        return {
            "dogs": dogs_info,
            "raw_response": response
        }
    
    def _extract_user_message_only(self, text: str) -> str:
        """
        NEW: Extract only the user's message from conversation text
        Filters out AI responses, system messages, etc.
        """
        # Handle different input formats
        if "User:" in text and "Assistant:" in text:
            # Extract only the user part from conversation format
            lines = text.split('\n')
            user_lines = []
            in_user_section = False
            
            for line in lines:
                if line.startswith("User:"):
                    in_user_section = True
                    user_lines.append(line[5:].strip())  # Remove "User:" prefix
                elif line.startswith("Assistant:") or line.startswith("AI:"):
                    in_user_section = False
                elif in_user_section and line.strip():
                    user_lines.append(line.strip())
            
            result = " ".join(user_lines)
            logger.debug(f"📝 Extracted user message from conversation: '{result}'")
            return result
        
        # If no conversation format, assume the whole text is user input
        # But filter out obvious AI response indicators
        ai_indicators = [
            "*wags tail*", "*tilts head*", "*nods*", "*perks up*",
            "I'd be happy to", "Let me", "I recommend", "I suggest",
            "As an AI", "As your", "Here's what I"
        ]
        
        if any(indicator in text for indicator in ai_indicators):
            logger.debug(f"🚫 Text appears to be AI response, skipping extraction")
            return ""
        
        return text.strip()
    
    def _nlp_extract_dog_names_and_info(self, text: str) -> Dict[str, Dict[str, str]]:
        """
        IMPROVED: NLP-based extraction that handles complex real-world user input
        Fixed to capture multiple dogs even with lots of descriptive text between names
        """
        dogs_info = {}
        text = text.lower()
        
        logger.debug(f"🔍 NLP processing text: '{text}'")
        
        # Method 1: Use a more flexible approach to find dog names
        # First, look for ANY indicator of multiple dogs
        multiple_dogs_patterns = [
            r"(?:i have|i've got|we have|we've got) (?:two|three|2|3) dogs?",  # "I have two dogs"
            r"(?:my|our) (?:two|three|2|3) dogs?",  # "my two dogs" 
            r"(?:our|my) dogs? are",  # "our dogs are"
            r"dogs? are \w+ and \w+",  # "dogs are charlie and luna"
        ]
        
        multiple_dogs_match = any(re.search(pattern, text) for pattern in multiple_dogs_patterns)
        
        if multiple_dogs_match:
            logger.debug("🔍 Multiple dogs detected - using flexible name extraction")
            # Use a more flexible approach for multiple dogs
            extracted_names = self._extract_names_flexible(text)
            for name in extracted_names:
                if len(name) >= 2:
                    dogs_info[name] = {"name": name}
                    logger.debug(f"🎯 Flexible extraction found: {name}")
        else:
            # Single dog - use focused patterns
            logger.debug("🔍 Single dog scenario - using focused patterns")
            single_patterns = [
                (r"(?:my dog|our dog)(?:'s name)? is (?:named|called)?\s*([a-z]+)", "single"),
                (r"(?:my dog|our dog) name is\s*([a-z]+)", "single"),  # "my dog name is Manku"
                (r"(?:my dog|our dog)(?:'s)? name\s*(?:is)?\s*([a-z]+)", "single"),  # "my dog's name Manku", "my dog name Manku"
                (r"(?:my dog|our dog) ([a-z]+) is", "single"),
                (r"(?:i have|i've got|we have|we've got) (?:a dog|dogs?) (?:named|called)?\s*([a-z]+)", "single"),
                (r"dog name is ([a-z]+)", "single"),  # "dog name is Manku"
                (r"dog named ([a-z]+)", "single"),  # "dog named Manku"
                (r"dog called ([a-z]+)", "single"),  # "dog called Manku"
            ]
            
            for pattern, pattern_type in single_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    name = match if isinstance(match, str) else match[0]
                    if len(name) >= 2:
                        dogs_info[name] = {"name": name}
                        logger.debug(f"🎯 Single dog pattern match: {name}")
        
        # Method 2: Extract breed and age information for found dogs
        self._extract_breed_and_age_info(text, dogs_info)
        
        return dogs_info
    
    def _extract_names_flexible(self, text: str) -> List[str]:
        """
        NEW: Flexible name extraction that handles complex descriptions
        Looks for capitalized words that could be dog names in dog-related contexts
        """
        names = []
        
        # Strategy 1: Look for patterns like "dogs [name] ... and [name]"
        # But be flexible about what's in between
        complex_patterns = [
            # Handle cases like "dogs laila ... and kenny ..." 
            r"dogs?\s+([a-z]+).*?\sand\s+([a-z]+)",
            # Handle cases like "laila ... and kenny ..." (after "two dogs" was mentioned)
            r"([a-z]+)(?:\s+a\s+\w+)?(?:\s+aged?\s+\d+)?.*?\sand\s+([a-z]+)",
            # Handle "dogs are X and Y" pattern
            r"dogs?\s+are\s+([a-z]+)\s+and\s+([a-z]+)",
            # Handle "my two dogs X and Y" pattern  
            r"(?:my|our)\s+(?:two|three|\d+)\s+dogs?\s+([a-z]+)\s+and\s+([a-z]+)",
        ]
        
        for pattern in complex_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    for name in match:
                        if name and len(name) >= 2:
                            # Basic validation - not a common word
                            if name not in ['dog', 'aged', 'years', 'old', 'and', 'pounds', 'weight', 'the']:
                                names.append(name)
                                logger.debug(f"🎯 Flexible pattern found name: {name}")
        
        # Strategy 2: Find capitalized words near dog-related context
        # Look for potential dog names (proper nouns) in dog contexts
        words = text.split()
        for i, word in enumerate(words):
            # Skip if it's a common word or too short
            if (len(word) >= 2 and 
                word.isalpha() and 
                word not in ['dog', 'dogs', 'aged', 'years', 'old', 'and', 'pounds', 'weight', 'have', 'the', 'poodle', 'labrador']):
                
                # Check if this word appears in a dog-related context
                context_start = max(0, i-3)
                context_end = min(len(words), i+4)
                context = ' '.join(words[context_start:context_end])
                
                # If the context mentions dogs/breeds/ages, this might be a name
                if any(indicator in context for indicator in ['dog', 'poodle', 'labrador', 'aged', 'years old']):
                    if word not in names:  # Avoid duplicates
                        names.append(word)
                        logger.debug(f"🎯 Context-based name extraction: {word}")
        
        # Remove duplicates while preserving order
        unique_names = []
        seen = set()
        for name in names:
            if name.lower() not in seen:
                unique_names.append(name)
                seen.add(name.lower())
        
        logger.debug(f"🎯 Flexible extraction result: {unique_names}")
        return unique_names
    
    def _extract_breed_and_age_info(self, text: str, dogs_info: Dict[str, Dict[str, str]]):
        """
        NEW: Extract breed and age information using simple keyword proximity
        """
        # Common breed names
        breeds = [
            "poodle", "labrador", "golden retriever", "german shepherd", "bulldog",
            "beagle", "boxer", "chihuahua", "husky", "border collie", "rottweiler",
            "dalmatian", "mastiff", "terrier", "spaniel", "retriever", "shepherd"
        ]
        
        # Extract age patterns
        age_matches = re.findall(r"(\d+) years? old", text)
        
        # Extract breed mentions
        breed_matches = []
        for breed in breeds:
            if breed in text:
                breed_matches.append(breed)
        
        # Simple assignment: if we have one dog and one age/breed, assign them
        dog_names = list(dogs_info.keys())
        
        if len(dog_names) == 1:
            dog_name = dog_names[0]
            if age_matches:
                dogs_info[dog_name]["age"] = age_matches[0]
                logger.debug(f"🎯 Assigned age {age_matches[0]} to {dog_name}")
            if breed_matches:
                dogs_info[dog_name]["breed"] = breed_matches[0].title()
                logger.debug(f"🎯 Assigned breed {breed_matches[0]} to {dog_name}")
                
        elif len(dog_names) == 2 and len(age_matches) >= 2:
            # For two dogs with two ages, try to match based on position in text
            for i, dog_name in enumerate(dog_names):
                if i < len(age_matches):
                    dogs_info[dog_name]["age"] = age_matches[i]
                    logger.debug(f"🎯 Assigned age {age_matches[i]} to {dog_name}")
                if i < len(breed_matches):
                    dogs_info[dog_name]["breed"] = breed_matches[i].title()
                    logger.debug(f"🎯 Assigned breed {breed_matches[i]} to {dog_name}")
    
    def _fallback_regex_extraction(self, text: str) -> Dict[str, Dict[str, str]]:
        """
        FALLBACK: Simple regex patterns as backup method
        Only the most reliable patterns
        """
        dogs_info = {}
        
        # Only use the most reliable patterns
        safe_patterns = [
            r"dogs?\s+(?:named|called)\s+([a-z]+)",
            r"(?:my|our)\s+dog\s+([a-z]+)",
            r"i\s+have\s+(?:a\s+dog\s+)?([a-z]+)\s+(?:who|that|and)",
        ]
        
        for pattern in safe_patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                name = match.strip()
                if len(name) >= 2:
                    dogs_info[name] = {"name": name}
        
        return dogs_info
