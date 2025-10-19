"""
Unified Dog Knowledge Manager

Manages dog knowledge across all systems with real-time sync.
Prevents knowledge conflicts by maintaining single source of truth.
Preserves all legitimate follow-up scenarios while eliminating false positives.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime

from .dog_context_service import DogInfo

logger = logging.getLogger(__name__)

class UnifiedDogKnowledgeManager:
    """
    Manages dog knowledge across all systems with real-time sync
    Prevents knowledge conflicts by maintaining single source of truth
    """
    
    def __init__(self, langgraph_service, dog_context_service):
        self.langgraph = langgraph_service
        self.dog_service = dog_context_service
        
        
        # Only extract names when explicitly talking about a specific named dog
        self.ai_knowledge_patterns = [
            # Only when AI explicitly mentions "your dog [Name]" or "the dog [Name]" 
            r"(?:your dog|the dog)\s+(?:named\s+|called\s+)?([A-Z][a-z]+)",
            
            # Only when AI mentions dog with age AND breed together (highly specific)
            r"([A-Z][a-z]+)\s+(?:the|your)\s+\d+(?:-year-old|\s+years?\s+old)\s+(?:bulldog|labrador|retriever|shepherd|terrier|poodle|beagle|husky|collie|boxer)",
            
            # Only possessive patterns with explicit dog context
            r"([A-Z][a-z]+)'s\s+(?:health|age|breed|nutrition|diet|exercise|care)\s+(?:needs|is|should)",
            
            # Only when giving advice specifically "for [Name]"
            r"for\s+([A-Z][a-z]+),?\s+(?:I recommend|I suggest|you should|consider|try)",
            
            # Only senior dog mentions with explicit context
            r"senior\s+dog\s+([A-Z][a-z]+)",
            r"([A-Z][a-z]+),?\s+(?:at\s+his|at\s+her|in\s+his|in\s+her)\s+(?:age|golden\s+years)",
        ]
        
     
        # Must have explicit dog context to avoid false positives like "Key", "Control", etc.
        self.knowledge_indicators = [
            r"your dog ([A-Z][a-z]+)",
            r"the dog ([A-Z][a-z]+)", 
            r"([A-Z][a-z]+) (?:the|your) \d+(?:-year-old|\s+years?\s+old) (?:bulldog|labrador|retriever|shepherd|terrier|poodle|beagle|husky|collie|boxer)",
            r"for ([A-Z][a-z]+),? (?:I recommend|I suggest|you should|consider|try)",
            r"senior dog ([A-Z][a-z]+)",
            r"([A-Z][a-z]+)'s (?:health|age|breed|nutrition|diet|exercise|care) (?:needs|is|should)",
            r"([A-Z][a-z]+),? (?:at his|at her|in his|in her) (?:age|golden years)",
            # The specific pattern that should catch "Hoppy the 12-year-old bulldog"
            r"([A-Z][a-z]+) the \d+(?:-year-old|\s+years?\s+old) (?:bulldog|labrador|retriever|shepherd|terrier|poodle|beagle|husky|collie|boxer)",
        ]
        
        # Common words that should not be considered dog names
        self.false_positives = {
            'dog', 'pet', 'animal', 'puppy', 'dogs', 'pets', 'animals', 'puppies',
            'name', 'names', 'breed', 'breeds', 'age', 'ages',
            # Context words that were being incorrectly detected
            'connection', 'pups', 'elderly', 'human', 'canine', 'companion', 'friend',
            'training', 'behavior', 'exercise', 'nutrition', 'health', 'care', 'advice',
            # NEW: False positives found in logs
            'key', 'nutritional', 'control', 'labradors', 'important', 'essential',
            'proper', 'good', 'best', 'right', 'correct', 'appropriate', 'suitable',
            'regular', 'daily', 'weekly', 'monthly', 'special', 'specific', 'general',
            'he', 'she', 'it', 'they', 'him', 'her', 'them', 'his', 'hers', 'its', 'their',
            'you', 'your', 'yours', 'me', 'my', 'mine', 'we', 'our', 'ours', 'us',
            'i', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must',
            'can', 'cannot', 'cant', 'wont', 'wouldnt', 'couldnt', 'shouldnt', 'may', 'might',
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'between', 'among', 'until', 'while', 'since', 'without',
            'this', 'that', 'these', 'those', 'here', 'there', 'where', 'when', 'why', 'how',
            'what', 'which', 'who', 'whom', 'whose', 'all', 'some', 'any', 'no', 'none',
            'many', 'much', 'few', 'little', 'more', 'most', 'less', 'least', 'every', 'each',
            'other', 'another', 'same', 'different', 'new', 'old', 'good', 'bad', 'big', 'small',
            'long', 'short', 'high', 'low', 'hot', 'cold', 'warm', 'cool', 'hard', 'soft',
            'heavy', 'light', 'dark', 'bright', 'clean', 'dirty', 'safe', 'dangerous',
            'happy', 'sad', 'angry', 'calm', 'excited', 'tired', 'hungry', 'full',
            'healthy', 'sick', 'strong', 'weak', 'fast', 'slow', 'loud', 'quiet',
            # CRITICAL: Common adverbs that were being falsely detected as dog names
            'very', 'quite', 'really', 'always', 'never', 'sometimes', 'often',
            'usually', 'frequently', 'rarely', 'constantly', 'immediately', 'suddenly',
            'eventually', 'definitely', 'probably', 'possibly', 'certainly', 'likely',
            'yes', 'no', 'maybe', 'sure', 'okay', 'ok', 'please', 'thank', 'thanks',
            'sorry', 'excuse', 'help', 'need', 'want', 'like', 'love', 'hate', 'know',
            'think', 'feel', 'see', 'hear', 'say', 'tell', 'ask', 'answer', 'call', 'come',
            'go', 'get', 'give', 'take', 'make', 'let', 'put', 'keep', 'find', 'look',
            'try', 'use', 'work', 'play', 'run', 'walk', 'eat', 'drink', 'sleep', 'wake',
            'start', 'stop', 'end', 'begin', 'finish', 'continue', 'break', 'fix', 'change',
            'move', 'stay', 'leave', 'arrive', 'return', 'send', 'receive', 'buy', 'sell',
            'pay', 'cost', 'save', 'spend', 'win', 'lose', 'choose', 'decide', 'remember',
            'forget', 'learn', 'teach', 'understand', 'explain', 'describe', 'show', 'hide',
            'open', 'close', 'lock', 'unlock', 'push', 'pull', 'lift', 'drop', 'throw',
            'catch', 'hold', 'release', 'touch', 'hit', 'kick', 'bite', 'scratch', 'lick',
            'smell', 'taste', 'breathe', 'cough', 'sneeze', 'yawn', 'smile', 'laugh', 'cry',
            'bark', 'howl', 'whine', 'growl', 'purr', 'meow', 'chirp', 'sing', 'whistle',
            'read', 'write', 'count', 'measure', 'weigh', 'compare', 'match', 'mix', 'separate',
            'clean', 'wash', 'dry', 'cook', 'bake', 'fry', 'boil', 'freeze', 'melt', 'burn',
            'cut', 'chop', 'slice', 'dice', 'crush', 'grind', 'blend', 'stir', 'shake', 'pour',
            'fill', 'empty', 'pack', 'unpack', 'wrap', 'unwrap', 'tie', 'untie', 'attach',
            'detach', 'connect', 'disconnect', 'join', 'split', 'add', 'remove', 'insert',
            'delete', 'replace', 'switch', 'turn', 'twist', 'bend', 'fold', 'unfold', 'roll',
            'unroll', 'squeeze', 'stretch', 'compress', 'expand', 'shrink', 'grow', 'develop',
            'improve', 'worsen', 'increase', 'decrease', 'raise', 'lower', 'enhance', 'reduce',
            # Common false positives from previous issues
            'of', 'to', 'me', 'tell', 'names', 'age', 'years', 'stays', 'ensure', 'teach', 'bring',
            'ring', 'stop', 'mentally', 'stimulated', 'local', 'groomer', 'groomers', 'radius',
            'mile', 'miles', 'city', 'approved', 'white', 'mr', 'listen', 'understood', 'bering',
            'like', 'would', 'outside', 'bell', 'jumps', 'people', 'greet', 'tips', 'barking',
            'window', 'moves', 'anything', 'behavior', 'frustration', 'always', 'never',
            'sometimes', 'often', 'usually', 'frequently', 'rarely', 'several', 'both',
            'either', 'neither', 'general', 'detail', 'information', 'advice', 'question'
        }

    async def get_comprehensive_dog_knowledge(self, user_id: int) -> Dict[str, Any]:
        """
        Get dog knowledge from ALL sources and merge intelligently
        This is the single source of truth for dog information
        """
        try:
            # Source 1: Dog service database
            db_dogs = await self.dog_service._get_user_dogs(user_id)
            
            # Source 2: AI memory extraction
            ai_dogs = await self._extract_ai_dog_knowledge(user_id)
            
            # Source 3: Enhanced conversation history search
            conversation_dogs = await self._search_conversation_history(user_id)
            
            # Merge all sources with conflict resolution
            unified_knowledge = self._merge_dog_knowledge(db_dogs, ai_dogs)
            
            # Add dogs found in conversation history
            for name, info in conversation_dogs.items():
                if name not in unified_knowledge:
                    unified_knowledge[name] = info
            
            # Clean up corrupted data (remove false positives)
            cleaned_knowledge = self._clean_false_positive_dogs(unified_knowledge)
            
            # Auto-sync any new valid knowledge found
            if cleaned_knowledge and len(cleaned_knowledge) != len(db_dogs):
                logger.info(f"🔄 Auto-syncing cleaned dog knowledge to service for user {user_id}")
                await self._sync_to_dog_service(user_id, cleaned_knowledge)
            
            logger.info(f"🐕 Unified knowledge for user {user_id}: {list(cleaned_knowledge.keys())}")
            return cleaned_knowledge
            
        except Exception as e:
            logger.error(f"❌ Error getting comprehensive dog knowledge: {e}")
            return {}

    async def _extract_ai_dog_knowledge(self, user_id: int) -> Dict[str, Any]:
        """
        Extract dog knowledge from AI memory with high accuracy
        Handles multiple dogs, partial information, and context
        """
        try:
            if not self.langgraph or not self.langgraph.store:
                return {}
                
            # Get recent AI memories about dogs
            memories = await self.langgraph.store.asearch(
                (f"user_{user_id}", "dogs"),
                query="dog name breed age information",
                limit=20
            )
            
            # Also check general conversation memory for dog references
            general_memories = await self.langgraph.store.asearch(
                (f"user_{user_id}", "general"),
                query="dog pet name breed age",
                limit=10
            )
            
            extracted_dogs = {}
            
            # Extract from dog-specific memories
            for memory in memories:
                if memory.value and isinstance(memory.value, dict):
                    dogs_from_memory = self._parse_memory_for_dogs(memory.value)
                    extracted_dogs.update(dogs_from_memory)
            
            # Extract from general memories
            for memory in general_memories:
                if memory.value and isinstance(memory.value, dict):
                    content = memory.value.get('content', '')
                    if content:
                        dogs_from_content = self._parse_conversation_for_dogs(content)
                        extracted_dogs.update(dogs_from_content)
            
            logger.info(f"🧠 Extracted AI dog knowledge for user {user_id}: {list(extracted_dogs.keys())}")
            return extracted_dogs
            
        except Exception as e:
            logger.error(f"❌ Error extracting AI dog knowledge: {e}")
            return {}

    def _parse_memory_for_dogs(self, memory_value: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse memory value for dog information
        """
        dogs = {}
        
        # Direct dog information stored in memory
        if memory_value.get('name'):
            name = memory_value['name']
            if self._is_valid_dog_name(name):
                dogs[name] = {
                    'name': name,
                    'breed': memory_value.get('breed'),
                    'age': memory_value.get('age'),
                    'weight': memory_value.get('weight'),
                    'health_notes': memory_value.get('health_notes')
                }
        
        return dogs

    def _parse_conversation_for_dogs(self, conversation: str) -> Dict[str, Any]:
        """
        Parse conversation text to extract dog information with high precision
        """
        dogs = {}
        
        for pattern in self.ai_knowledge_patterns:
            matches = re.finditer(pattern, conversation, re.IGNORECASE)
            for match in matches:
                # Extract potential dog name
                groups = match.groups()
                if groups:
                    potential_name = groups[0].title()
                    
                    # Validate it's actually a dog name
                    if self._is_valid_dog_name(potential_name):
                        if potential_name not in dogs:
                            dogs[potential_name] = {"name": potential_name}
                        
                        # Extract additional info if available
                        if len(groups) > 1 and groups[1]:
                            additional_info = groups[1]
                            if additional_info.isdigit():
                                dogs[potential_name]["age"] = additional_info
                            elif not additional_info.lower() in ['dog', 'pet', 'animal']:
                                dogs[potential_name]["breed"] = additional_info.title()
        
        return dogs

    def _is_valid_dog_name(self, name: str) -> bool:
        """
        Ultra-strict validation for dog names with enhanced context awareness
        Uses proven validation logic from DogContextService
        """
        if not name or len(name) < 2:
            return False
        
        name_lower = name.lower()
        
        # Check against expanded false positives
        if name_lower in self.false_positives:
            return False
        
        # Must be capitalized (proper noun)
        if not name[0].isupper():
            return False
        
        # Must be alphabetic only (no numbers, symbols)
        if not name.isalpha():
            return False
        
        # Must be reasonable length (2-15 characters)
        if len(name) < 2 or len(name) > 15:
            return False
        
        # Enhanced rejection patterns for common false positives
        reject_patterns = [
            # Verbs and auxiliaries
            r'^(is|are|was|were|be|been|being|have|has|had)$',
            r'^(can|will|would|could|should|may|might|must|shall)$',
            r'^(do|does|did|done|going|come|came|get|got)$',
            
            # Articles, pronouns, determiners
            r'^(the|that|this|these|those|a|an)$',
            r'^(he|she|it|they|him|her|them|his|hers|its|their)$',
            r'^(you|your|yours|me|my|mine|we|our|ours|us)$',
            
            # Conjunctions and prepositions  
            r'^(and|but|or|if|when|where|why|how|what|which)$',
            r'^(in|on|at|to|for|of|with|by|from|about)$',
            
            # Time and quantity words
            r'^(now|then|here|there|always|never|sometimes)$',
            r'^(all|some|any|many|few|more|most|less|each)$',
            
            # Dog-related context words (not names)
            r'^(dog|dogs|pet|pets|puppy|puppies|canine|animal)$',
            r'^(breed|breeds|training|behavior|exercise|health)$',
            r'^(care|nutrition|food|treat|treats|toy|toys)$',
            
            # Common false positives from our logs
            r'^(connection|pups|elderly|human|companion|friend)$',
            r'^(advice|recommendations|tips|guidance|help)$',
        ]
        
        for pattern in reject_patterns:
            if re.match(pattern, name_lower):
                return False
        
        # Additional context-based validation
        # Reject common English words that might be capitalized
        common_words = {
            'Connection', 'Pups', 'Elderly', 'Human', 'Canine', 'Companion', 'Friend',
            'Training', 'Behavior', 'Exercise', 'Nutrition', 'Health', 'Care', 'Advice',
            'Recommendations', 'Tips', 'Guidance', 'Help', 'Support', 'Information',
            'Details', 'Questions', 'Answers', 'Problems', 'Solutions', 'Issues'
        }
        
        if name in common_words:
            return False
        
        return True

    def _merge_dog_knowledge(self, db_dogs: Dict[str, Any], ai_dogs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge dog knowledge from different sources with conflict resolution
        AI memory takes precedence as it's more recent
        """
        merged = {}
        
        # Start with AI dogs (more recent)
        for name, info in ai_dogs.items():
            merged[name] = info
        
        # Add DB dogs that aren't in AI memory
        for name, dog_info in db_dogs.items():
            if name not in merged:
                merged[name] = {
                    'name': dog_info.name,
                    'breed': dog_info.breed,
                    'age': dog_info.age,
                    'weight': dog_info.weight,
                    'health_notes': dog_info.health_notes
                }
        
        return merged

    async def _sync_to_dog_service(self, user_id: int, dogs: Dict[str, Any]) -> None:
        """
        Sync dog knowledge to dog service database
        """
        try:
            for dog_name, dog_info in dogs.items():
                dog_obj = DogInfo(
                    name=dog_name,
                    breed=dog_info.get("breed"),
                    age=dog_info.get("age"),
                    weight=dog_info.get("weight"),
                    health_notes=dog_info.get("health_notes")
                )
                await self.dog_service.store_dog_information(user_id, dog_obj)
            
            logger.info(f"🔄 Synced {len(dogs)} dogs to service for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error syncing to dog service: {e}")

    def ai_demonstrates_dog_knowledge(self, ai_response: str) -> bool:
        """
        Detect if AI shows specific dog knowledge in response
        """
        for pattern in self.knowledge_indicators:
            matches = re.finditer(pattern, ai_response, re.IGNORECASE)
            for match in matches:
                # Check if the matched name is valid
                groups = match.groups()
                if groups:
                    potential_name = groups[0]
                    if self._is_valid_dog_name(potential_name):
                        logger.info(f"🐕 AI demonstrates knowledge of dog: {potential_name}")
                        return True
        
        return False

    async def extract_and_sync_ai_knowledge(self, user_id: int, ai_response: str) -> None:
        """
        Extract dog knowledge from AI response and sync to all systems
        Ensures knowledge consistency across all components
        """
        try:
            extracted_dogs = self._parse_conversation_for_dogs(ai_response)
            
            if extracted_dogs:
                logger.info(f"🐕 Extracted dog knowledge from AI response: {extracted_dogs}")
                
                # Sync to dog service database
                await self._sync_to_dog_service(user_id, extracted_dogs)
                
                # Also ensure it's in AI memory
                for dog_name, dog_info in extracted_dogs.items():
                    await self.langgraph.store.aput(
                        (f"user_{user_id}", "dogs"),
                        f"dog_{dog_name.lower()}",
                        {
                            "name": dog_name,
                            "breed": dog_info.get("breed"),
                            "age": dog_info.get("age"),
                            "weight": dog_info.get("weight"),
                            "health_notes": dog_info.get("health_notes"),
                            "last_updated": datetime.now().isoformat()
                        }
                    )
                
                logger.info(f"🔄 Synced extracted knowledge across all systems")
                
        except Exception as e:
            logger.error(f"❌ Error extracting and syncing AI knowledge: {e}")

    def detect_knowledge_conflicts(self, ai_response: str, unified_knowledge: Dict[str, Any]) -> List[str]:
        """
        Detect conflicts between AI response and known dog information
        """
        conflicts = []
        
        try:
            # Extract dogs mentioned in AI response
            ai_mentioned_dogs = set()
            for pattern in self.knowledge_indicators:
                matches = re.finditer(pattern, ai_response, re.IGNORECASE)
                for match in matches:
                    groups = match.groups()
                    if groups and groups[0] and self._is_valid_dog_name(groups[0]):
                        # Additional validation to avoid breed words
                        potential_name = groups[0].title()
                        # Skip common breed words that might be extracted
                        breed_words = {'Retriever', 'Shepherd', 'Terrier', 'Spaniel', 'Poodle', 'Bulldog', 'Beagle', 'Boxer', 'Husky', 'Collie'}
                        if potential_name not in breed_words:
                            ai_mentioned_dogs.add(potential_name)
            
            known_dogs = set(unified_knowledge.keys())
            
            # Check for unknown dog mentions
            if ai_mentioned_dogs and known_dogs:
                unknown_mentions = ai_mentioned_dogs - known_dogs
                if unknown_mentions:
                    conflicts.append(f"AI mentions unknown dogs: {unknown_mentions}")
            
            # Check for conflicting information
            for dog_name in ai_mentioned_dogs:
                if dog_name in unified_knowledge:
                    ai_info = self._extract_dog_info_from_text(ai_response, dog_name)
                    known_info = unified_knowledge[dog_name]
                    
                    for key, ai_value in ai_info.items():
                        known_value = known_info.get(key)
                        if known_value and str(known_value).lower() != str(ai_value).lower():
                            conflicts.append(f"{dog_name}'s {key}: AI says {ai_value}, known is {known_value}")
            
            # Also check if response contains age information about known dogs (even without explicit mention)
            for dog_name, known_info in unified_knowledge.items():
                ai_info = self._extract_dog_info_from_text(ai_response, dog_name)
                for key, ai_value in ai_info.items():
                    known_value = known_info.get(key)
                    if known_value and str(known_value).lower() != str(ai_value).lower():
                        conflicts.append(f"{dog_name}'s {key}: AI says {ai_value}, known is {known_value}")
            
        except Exception as e:
            logger.error(f"❌ Error detecting conflicts: {e}")
        
        return conflicts

    def _extract_dog_info_from_text(self, text: str, dog_name: str) -> Dict[str, Any]:
        """
        Extract specific dog information from text for a given dog name
        """
        info = {}
        
        # Age patterns - more comprehensive
        age_patterns = [
            rf"{re.escape(dog_name)}\s+is\s+(?:a\s+)?(\d+)(?:-year-old|\s+years?\s+old)",
            rf"(\d+)(?:-year-old|\s+years?\s+old)\s+{re.escape(dog_name)}",
            rf"{re.escape(dog_name)}\s+is\s+(\d+)",  # Simple "Manku is 8"
            rf"(\d+)\s+years?\s+old\s+{re.escape(dog_name)}",  # "8 years old Manku"
        ]
        
        for pattern in age_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                age_group = 1
                # Find which group has the age
                for i, group in enumerate(match.groups(), 1):
                    if group and group.isdigit():
                        info['age'] = group
                        break
                break
        
        # Breed patterns
        breed_patterns = [
            rf"{re.escape(dog_name)}\s+is\s+a\s+([\w\s]+?)(?:\s+and|\s*,|\s*\.|\s*$)",
        ]
        
        for pattern in breed_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                breed = match.group(1).strip()
                if breed and breed.lower() not in ['dog', 'pet', 'animal']:
                    info['breed'] = breed.title()
                break
        
        return info

    async def _search_conversation_history(self, user_id: int) -> Dict[str, Any]:
        """
        Search conversation history for dog information that might not be in current response
        This catches dogs mentioned in previous interactions
        """
        try:
            if not self.langgraph or not self.langgraph.store:
                return {}
            
            # Search broader conversation memory for dog references
            conversation_memories = await self.langgraph.store.asearch(
                (f"user_{user_id}", "general"),
                query="dog name breed age pet information",
                limit=30  # Look through more history
            )
            
            logger.info(f"🔍 Searching conversation history: found {len(conversation_memories)} memories")
            
            conversation_dogs = {}
            
            # Look for dog information in conversation content
            for memory in conversation_memories:
                if memory.value and isinstance(memory.value, dict):
                    content = memory.value.get('content', '')
                    if content and ('dog' in content.lower() or 'pet' in content.lower()):
                        # Extract dog info from this conversation piece
                        dogs_from_history = self._parse_conversation_for_dogs(content)
                        conversation_dogs.update(dogs_from_history)
                        
                        # Also look for user input patterns (more explicit)
                        user_patterns = [
                            r"my dog (?:name is|is named|is called|is)\s+([A-Z][a-z]+)",
                            r"([A-Z][a-z]+)\s+is\s+my\s+dog",
                            r"([A-Z][a-z]+)\s+(?:is\s+)?(?:a\s+)?(\d+)(?:-year-old|\s+years?\s+old)",
                            r"([A-Z][a-z]+)\s+(?:is\s+)?(?:a\s+)?(bulldog|labrador|retriever|shepherd|terrier|poodle|beagle|husky|collie|boxer)",
                        ]
                        
                        for pattern in user_patterns:
                            matches = re.finditer(pattern, content, re.IGNORECASE)
                            for match in matches:
                                potential_name = match.group(1).title()
                                if self._is_valid_dog_name(potential_name):
                                    if potential_name not in conversation_dogs:
                                        conversation_dogs[potential_name] = {"name": potential_name}
                                    
                                    # Extract additional info from pattern
                                    if len(match.groups()) > 1 and match.group(2):
                                        additional = match.group(2)
                                        if additional.isdigit():
                                            conversation_dogs[potential_name]["age"] = additional
                                        elif additional.lower() in ['bulldog', 'labrador', 'retriever', 'shepherd', 'terrier', 'poodle', 'beagle', 'husky', 'collie', 'boxer']:
                                            conversation_dogs[potential_name]["breed"] = additional.title()
            
            if conversation_dogs:
                logger.info(f"🔍 Found dogs in conversation history: {list(conversation_dogs.keys())}")
            
            return conversation_dogs
            
        except Exception as e:
            logger.error(f"❌ Error searching conversation history: {e}")
            return {}

    def _clean_false_positive_dogs(self, unified_knowledge: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove false positive dog names from unified knowledge
        Clean up corrupted data like "Connection", "Pups", etc.
        """
        # Known false positives from our logs and common context words
        false_positive_names = {
            'Connection', 'Pups', 'Elderly', 'Human', 'Canine', 'Companion', 'Friend',
            'Training', 'Behavior', 'Exercise', 'Nutrition', 'Health', 'Care', 'Advice',
            'Recommendations', 'Tips', 'Guidance', 'Help', 'Support', 'Information',
            'Details', 'Questions', 'Answers', 'Problems', 'Solutions', 'Issues',
            'Years', 'Age', 'Breed', 'Name', 'Names', 'Of', 'To', 'For', 'With', 'The',
            'And', 'Or', 'But', 'If', 'When', 'Where', 'Why', 'How', 'What', 'Which',
            # CRITICAL: Common adverbs falsely detected as dog names
            'Very', 'Quite', 'Really', 'Always', 'Never', 'Sometimes', 'Often',
            'Usually', 'Frequently', 'Rarely', 'Constantly', 'Immediately', 'Suddenly',
            'Eventually', 'Definitely', 'Probably', 'Possibly', 'Certainly', 'Likely'
        }
        
        cleaned_knowledge = {}
        removed_count = 0
        
        for name, info in unified_knowledge.items():
            if name in false_positive_names:
                logger.info(f"🧹 Removing false positive dog name: {name}")
                removed_count += 1
            elif not self._is_valid_dog_name(name):
                logger.info(f"🧹 Removing invalid dog name: {name}")
                removed_count += 1
            else:
                cleaned_knowledge[name] = info
        
        if removed_count > 0:
            logger.info(f"🧹 Cleaned {removed_count} false positive dog names")
        
        return cleaned_knowledge

    def detect_contradictory_response(self, ai_response: str, unified_knowledge: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect if AI response contains contradictory statements about dog knowledge
        Returns analysis and suggested corrections
        """
        analysis = {
            "has_contradiction": False,
            "contradiction_type": None,
            "suggested_correction": None,
            "conflicting_phrases": []
        }
        
        try:
            # Check if AI claims not to know but then demonstrates knowledge
            no_knowledge_phrases = [
                "don't have any specific details",
                "don't have access to personal information",
                "i don't know",
                "i'm not sure about",
                "haven't been told about",
                "i don't have information about",
                "unfortunately, i don't have"
            ]
            
            knowledge_demonstration_phrases = [
                "earlier in our conversation, you mentioned",
                "you mentioned that",
                "as mentioned before",
                "as we discussed",
                "from what you've told me"
            ]
            
            ai_lower = ai_response.lower()
            
            # Check for "no knowledge" claims
            has_no_knowledge_claim = any(phrase in ai_lower for phrase in no_knowledge_phrases)
            
            # Check for knowledge demonstration
            has_knowledge_demonstration = any(phrase in ai_lower for phrase in knowledge_demonstration_phrases)
            
            # Check if AI mentions specific dog names while claiming no knowledge
            mentions_dog_names = False
            for dog_name in unified_knowledge.keys():
                if dog_name.lower() in ai_lower:
                    mentions_dog_names = True
                    break
            
            # Detect contradiction patterns
            if has_no_knowledge_claim and (has_knowledge_demonstration or mentions_dog_names):
                analysis["has_contradiction"] = True
                analysis["contradiction_type"] = "knowledge_denial_vs_demonstration"
                
                # Find conflicting phrases
                for phrase in no_knowledge_phrases:
                    if phrase in ai_lower:
                        analysis["conflicting_phrases"].append(f"Claims no knowledge: '{phrase}'")
                
                if has_knowledge_demonstration:
                    for phrase in knowledge_demonstration_phrases:
                        if phrase in ai_lower:
                            analysis["conflicting_phrases"].append(f"Shows knowledge: '{phrase}'")
                
                if mentions_dog_names:
                    mentioned_dogs = [dog for dog in unified_knowledge.keys() if dog.lower() in ai_lower]
                    analysis["conflicting_phrases"].append(f"Mentions dog names: {mentioned_dogs}")
                
                # Suggest correction
                if unified_knowledge:
                    dog_names = list(unified_knowledge.keys())
                    if len(dog_names) == 1:
                        dog_name = dog_names[0]
                        dog_info = unified_knowledge[dog_name]
                        age_info = f", who is {dog_info.get('age', 'a')} years old" if dog_info.get('age') else ""
                        breed_info = f" {dog_info.get('breed', '')}" if dog_info.get('breed') else ""
                        
                        analysis["suggested_correction"] = (
                            f"I have information about your dog {dog_name}{age_info}. "
                            f"As your trusted dog care expert, I'm happy to provide personalized "
                            f"recommendations and guidance for {dog_name}'s care."
                        )
                    else:
                        analysis["suggested_correction"] = (
                            f"I have information about your dogs: {', '.join(dog_names)}. "
                            f"As your trusted dog care expert, I'm happy to provide personalized "
                            f"recommendations and guidance for their care."
                        )
                else:
                    analysis["suggested_correction"] = (
                        "I'd be happy to learn more about your dog to provide personalized advice. "
                        "Could you tell me about your dog's name, breed, age, and any other details?"
                    )
            
        except Exception as e:
            logger.error(f"❌ Error detecting contradictory response: {e}")
        
        return analysis

    def clean_contradictory_response(self, ai_response: str, unified_knowledge: Dict[str, Any]) -> str:
        """
        Clean contradictory AI responses by removing conflicting statements
        """
        try:
            analysis = self.detect_contradictory_response(ai_response, unified_knowledge)
            
            if not analysis["has_contradiction"]:
                return ai_response
            
            logger.warning(f"🚨 Detected contradictory AI response, cleaning...")
            logger.warning(f"Conflicts: {analysis['conflicting_phrases']}")
            
            # Split response into sentences
            sentences = ai_response.split('.')
            cleaned_sentences = []
            
            # Remove sentences that claim no knowledge when we have knowledge
            no_knowledge_phrases = [
                "don't have any specific details",
                "don't have access to personal information",
                "i don't know",
                "i'm not sure about",
                "haven't been told about",
                "i don't have information about",
                "unfortunately, i don't have"
            ]
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                # Skip sentences that claim no knowledge when we actually have knowledge
                sentence_lower = sentence.lower()
                should_remove = False
                
                if unified_knowledge:  # We have dog knowledge
                    for phrase in no_knowledge_phrases:
                        if phrase in sentence_lower:
                            should_remove = True
                            logger.info(f"🧹 Removing contradictory sentence: {sentence[:50]}...")
                            break
            
                if not should_remove:
                    cleaned_sentences.append(sentence)
            
            # Rebuild response
            cleaned_response = '. '.join(cleaned_sentences)
            
            # Add proper ending if needed
            if not cleaned_response.endswith('.'):
                cleaned_response += '.'
            
            # If response became too short, use suggested correction
            if len(cleaned_response.split()) < 10 and analysis["suggested_correction"]:
                logger.info("🔧 Using suggested correction due to short cleaned response")
                cleaned_response = analysis["suggested_correction"]
            
            logger.info(f"✅ Cleaned contradictory response successfully")
            return cleaned_response
            
        except Exception as e:
            logger.error(f"❌ Error cleaning contradictory response: {e}")
            return ai_response
