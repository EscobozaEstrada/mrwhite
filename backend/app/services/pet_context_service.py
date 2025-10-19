"""
Pet Context Service

This service specializes in proactively retrieving and managing pet information
from the user's knowledge base for Context7 enhanced responses.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from flask import current_app

from app.services.ai_service import AIService
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import json
import re

logger = logging.getLogger(__name__)

class PetContextService:
    """Service for proactive pet information retrieval and context building"""
    
    def __init__(self):
        self.ai_service = AIService()
        self.chat_model = ChatOpenAI(model="gpt-4", temperature=0.1)
        
        # Pet-related query patterns
        self.pet_care_keywords = [
            'diet', 'food', 'feeding', 'nutrition', 'meal', 'eat', 'eating',
            'exercise', 'walk', 'training', 'behavior', 'health', 'vet',
            'grooming', 'bath', 'care', 'weight', 'breed', 'age'
        ]
        
        # Query types that typically need pet context
        self.context_requiring_queries = [
            'diet_advice', 'feeding_schedule', 'exercise_plan', 'health_advice',
            'training_tips', 'breed_specific_care', 'age_specific_care'
        ]
    
    def analyze_query_for_pet_context(self, query: str) -> Dict[str, Any]:
        """
        Analyze if a query requires pet context and what type of context
        
        Args:
            query: User's query
            
        Returns:
            Dictionary with context analysis
        """
        try:
            query_lower = query.lower().strip()
            
            # Check for document-related queries first - these should never trigger pet context
            document_keywords = [
                "document", "pdf", "file", "upload", "uploaded", "summarize", "summary",
                "analyze document", "extract from document", "information in document", 
                "content of document", "what's in the document", "what does the document say", 
                "read the document", "tell me about the document", "explain the document",
                "document summary", "summarize this document", "summarize the pdf",
                "summarize this pdf", "summarize this file", "summarize the file"
            ]
            
            # Strong document request indicators - if these are present, skip pet context entirely
            strong_doc_indicators = ["summarize this", "summarize the", "what's in this document", 
                                  "what does this document", "tell me about this document",
                                  "document summary", "document content", "document analysis"]
                                  
            for indicator in strong_doc_indicators:
                if indicator in query_lower:
                    current_app.logger.info(f"📄 Strong document query detected: '{indicator}' in '{query}'")
                    return {
                        "needs_pet_context": False,
                        "confidence": 0.0,
                        "query_type": "document_request",
                        "context_requirements": [],
                        "debug": f"Strong document query detected: '{indicator}'"
                    }
            
            # If it's clearly a document-related query, skip pet context entirely
            if any(keyword in query_lower for keyword in document_keywords):
                current_app.logger.info(f"🔍 Document-related query detected: '{query_lower}'")
                return {
                    "needs_pet_context": False,
                    "confidence": 0.0,
                    "query_type": "document_request",
                    "context_requirements": [],
                    "debug": f"Document-related query detected: '{query_lower}'"
                }
            
            # IMPROVED: Better general knowledge pattern matching
            general_knowledge_patterns = [
                r"^what is a\b",
                r"^what is an\b",
                r"^what is\b",
                r"^what are\b",
                r"^define\b",
                r"^tell me about\b",
                r"^explain\b",
                r"^how does\b",
                r"^why do\b",
                r"^who is\b",
                r"^when was\b",
                r"^where is\b"
            ]
            
            # Special case for "what is dog" and similar questions
            if query_lower == "what is dog" or query_lower == "what is dog?" or query_lower == "what is a dog" or query_lower == "what is a dog?":
                current_app.logger.info(f"🔍 Direct general knowledge question detected: '{query_lower}'")
                return {
                    "needs_pet_context": False,
                    "confidence": 0.0,
                    "query_type": "general_knowledge",
                    "context_requirements": [],
                    "debug": f"Direct general knowledge question detected: '{query_lower}'"
                }
            
            # If it matches general knowledge patterns, skip pet context
            if any(re.match(pattern, query_lower) for pattern in general_knowledge_patterns):
                current_app.logger.info(f"🔍 General knowledge question detected: '{query_lower}'")
                return {
                    "needs_pet_context": False,
                    "confidence": 0.0,
                    "query_type": "general_knowledge",
                    "context_requirements": [],
                    "debug": f"General knowledge question detected: '{query_lower}'"
                }
            
            # Expanded pet-related keywords to catch more variations
            expanded_pet_keywords = [
                # Basic care
                'diet', 'food', 'feeding', 'nutrition', 'meal', 'eat', 'eating', 'feed',
                'exercise', 'walk', 'training', 'behavior', 'health', 'vet',
                'grooming', 'bath', 'care', 'weight', 'breed', 'age',
                
                # Feeding specific (important for the user's query)
                'how often', 'how much', 'how many times', 'frequency',
                'schedule', 'times a day', 'feeding schedule',
                
                # Pet references - REMOVED standalone 'dog', 'pet', 'puppy' to avoid false positives
                'my dog', 'my pet', 'my puppy', 'his dog', 'her dog', 'their dog',
                
                # Health and care
                'sick', 'symptoms', 'medication', 'vaccine', 'checkup',
                'treats', 'snacks', 'supplements', 'vitamins'
            ]
            
            # Direct animal definition questions that should NEVER trigger pet context
            direct_animal_questions = [
                "what is dog", "what is a dog", "what is dog?", "what is a dog?",
                "what are dogs", "what are dogs?", "what is puppy", "what is a puppy",
                "define dog", "explain dog", "tell me about dog", "tell me about dogs",
                "what is pet", "what is a pet", "what are pets"
            ]
            
            # Skip pet context for direct animal questions
            if query_lower in direct_animal_questions:
                current_app.logger.info(f"🔍 Direct animal question detected: '{query_lower}'")
                return {
                    "needs_pet_context": False,
                    "confidence": 0.0,
                    "query_type": "general_knowledge",
                    "context_requirements": [],
                    "debug": f"Direct animal question detected: '{query_lower}'"
                }
            
            # MODIFIED: Remove 'dog', 'pet', 'puppy' from keywords for general questions
            if any(query_lower.startswith(pattern.replace('^', '')) for pattern in general_knowledge_patterns):
                current_app.logger.info(f"🔍 General knowledge question pattern detected - removing animal keywords")
                # Filter out standalone animal keywords to avoid false positives
                expanded_pet_keywords = [kw for kw in expanded_pet_keywords if kw not in ['dog', 'pet', 'puppy', 'animal']]
            
            # Check if query is pet-related with higher sensitivity
            is_pet_related = any(keyword in query_lower for keyword in expanded_pet_keywords)
            
            # Special handling for possessive references that definitely need context
            possessive_indicators = ['my dog', 'my pet', 'my puppy', 'his', 'her', 'him']
            has_possessive = any(indicator in query_lower for indicator in possessive_indicators)
            
            if not is_pet_related and not has_possessive:
                return {
                    "needs_pet_context": False,
                    "confidence": 0.0,
                    "query_type": "general",
                    "context_requirements": [],
                    "debug": f"No pet keywords found in: '{query_lower}'"
                }
            
            # Determine specific query type with better classification
            query_type = self._classify_pet_query_type(query_lower)
            
            # Determine context requirements
            context_requirements = self._determine_context_requirements(query_type, query_lower)
            
            # Calculate confidence with higher sensitivity for feeding questions
            confidence = self._calculate_context_confidence(query_lower, query_type)
            
            # Boost confidence for possessive references
            if has_possessive:
                confidence = min(1.0, confidence + 0.3)
            
            result = {
                "needs_pet_context": True,
                "confidence": confidence,
                "query_type": query_type,
                "context_requirements": context_requirements,
                "keywords_found": [kw for kw in expanded_pet_keywords if kw in query_lower],
                "has_possessive": has_possessive,
                "debug": f"Pet query detected: type={query_type}, confidence={confidence:.2f}"
            }
            
            current_app.logger.info(f"🔍 Pet context analysis: {result['debug']}")
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error analyzing query for pet context: {str(e)}")
            return {
                "needs_pet_context": False,
                "confidence": 0.0,
                "query_type": "error",
                "context_requirements": [],
                "error": str(e)
            }
    
    def retrieve_pet_information(self, user_id: int, query: str) -> Dict[str, Any]:
        """
        Proactively retrieve pet information from user's knowledge base
        
        Args:
            user_id: User ID
            query: Original query for context
            
        Returns:
            Dictionary with pet information and context
        """
        try:
            current_app.logger.info(f"🐕 Retrieving pet information for user {user_id}")
            
            # OPTIMIZED: Consolidate 33+ searches into just 3 targeted searches
            pet_info_queries = [
                # Single comprehensive query instead of many small ones
                "my dog pet information name breed age weight size health",
                
                # Query with current context
                f"{query} dog pet",
                
                # Possessive query for personal pet references
                "my dog my pet"
            ]
            
            all_pet_info = []
            unique_messages = set()  # Avoid duplicates
            
            # Search each pet info query with better error handling
            for pet_query in pet_info_queries:
                try:
                    current_app.logger.info(f"🔍 Searching with query: '{pet_query}'")
                    chat_docs = self.ai_service.search_chat_history(pet_query, user_id, top_k=8)
                    
                    # Add unique messages only
                    for doc in chat_docs:
                        message_id = doc.metadata.get("message_id", "")
                        if message_id and message_id not in unique_messages:
                            all_pet_info.append(doc)
                            unique_messages.add(message_id)
                            
                except Exception as e:
                    current_app.logger.warning(f"Error searching for pet info with query '{pet_query}': {str(e)}")
                    continue
            
            current_app.logger.info(f"🔍 Found {len(all_pet_info)} total messages to analyze for pet information")
            
            if not all_pet_info:
                current_app.logger.warning("❌ No chat history found - user might not have previous conversations")
                return {
                    "pets_found": [],
                    "primary_pet": None,
                    "context_available": False,
                    "recommendation": "ask_for_details",
                    "debug_info": "No chat history found"
                }
            
            # Extract structured pet information with better processing
            pets_found = self._extract_pet_information_from_messages(all_pet_info)
            current_app.logger.info(f"🐕 Extracted information for {len(pets_found)} pets")
            
            # Determine primary pet
            primary_pet = self._determine_primary_pet(pets_found, query)
            
            result = {
                "pets_found": pets_found,
                "primary_pet": primary_pet,
                "context_available": len(pets_found) > 0,
                "total_messages_analyzed": len(all_pet_info),
                "recommendation": self._get_context_recommendation(pets_found),
                "debug_info": f"Analyzed {len(all_pet_info)} messages, found {len(pets_found)} pets"
            }
            
            if primary_pet:
                current_app.logger.info(f"✅ Found primary pet: {primary_pet.get('name', 'Unknown')} - {primary_pet.get('breed', 'Unknown breed')}")
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error retrieving pet information: {str(e)}")
            return {
                "pets_found": [],
                "primary_pet": None,
                "context_available": False,
                "recommendation": "error",
                "error": str(e),
                "debug_info": f"Error occurred: {str(e)}"
            }
    
    def _classify_pet_query_type(self, query_lower: str) -> str:
        """Classify the type of pet-related query"""
        
        if any(word in query_lower for word in ['diet', 'food', 'feeding', 'nutrition', 'meal', 'eat']):
            return "diet_advice"
        elif any(word in query_lower for word in ['exercise', 'walk', 'activity', 'play']):
            return "exercise_plan"
        elif any(word in query_lower for word in ['training', 'behavior', 'command', 'obedience']):
            return "training_tips"
        elif any(word in query_lower for word in ['health', 'vet', 'medical', 'sick', 'symptoms']):
            return "health_advice"
        elif any(word in query_lower for word in ['grooming', 'bath', 'cleaning', 'hygiene']):
            return "grooming_care"
        elif any(word in query_lower for word in ['breed', 'type', 'species']):
            return "breed_specific_care"
        elif any(word in query_lower for word in ['age', 'puppy', 'senior', 'old']):
            return "age_specific_care"
        else:
            return "general_pet_care"
    
    def _determine_context_requirements(self, query_type: str, query_lower: str) -> List[str]:
        """Determine what pet information is needed for the query"""
        
        requirements = ["pet_name"]  # Always helpful to have name
        
        if query_type == "diet_advice":
            requirements.extend(["breed", "age", "weight", "size", "health_conditions"])
        elif query_type == "exercise_plan":
            requirements.extend(["breed", "age", "size", "energy_level"])
        elif query_type == "health_advice":
            requirements.extend(["breed", "age", "weight", "health_history", "medications"])
        elif query_type == "training_tips":
            requirements.extend(["breed", "age", "temperament", "current_training"])
        elif query_type == "breed_specific_care":
            requirements.extend(["breed", "age", "specific_needs"])
        elif query_type == "age_specific_care":
            requirements.extend(["age", "breed", "life_stage", "health_status"])
        else:
            requirements.extend(["breed", "age"])
        
        return requirements
    
    def _calculate_context_confidence(self, query_lower: str, query_type: str) -> float:
        """Calculate confidence that pet context is needed"""
        
        base_confidence = 0.5
        
        # High confidence queries
        high_confidence_phrases = [
            "best diet for my dog",
            "what should I feed",
            "how much food",
            "exercise for my",
            "training my dog"
        ]
        
        if any(phrase in query_lower for phrase in high_confidence_phrases):
            base_confidence = 0.9
        
        # Medium confidence queries
        medium_confidence_words = ['best', 'should', 'how', 'what', 'recommend']
        if any(word in query_lower for word in medium_confidence_words):
            base_confidence += 0.2
        
        # Query type bonus
        if query_type in ['diet_advice', 'health_advice']:
            base_confidence += 0.1
        
        return min(1.0, base_confidence)
    
    def _extract_pet_information_from_messages(self, chat_docs: List) -> List[Dict[str, Any]]:
        """Extract structured pet information from chat messages using AI"""
        
        try:
            # Combine message content for analysis with better processing
            message_texts = []
            for doc in chat_docs[:15]:  # Analyze more messages but limit to avoid token limits
                content = doc.page_content
                # Add timestamp context if available
                timestamp = doc.metadata.get("timestamp", "")
                if timestamp:
                    content = f"[{timestamp}] {content}"
                message_texts.append(content)
            
            combined_text = "\n".join(message_texts)
            
            if not combined_text.strip():
                return []
            
            current_app.logger.info(f"🤖 Analyzing {len(message_texts)} messages for pet information (total chars: {len(combined_text)})")
            
            # Enhanced AI prompt for better pet extraction
            extraction_prompt = f"""
            You are an expert at extracting pet information from chat conversations. 
            
            Analyze these chat messages and extract ALL pet information mentioned. Look carefully for:
            - Pet names (e.g., "Ben", "Max", "Luna") 
            - Breeds (e.g., "Bulldog", "Golden Retriever", "mixed breed")
            - Ages (e.g., "3 years old", "puppy", "2 year old")
            - Weights (e.g., "65 pounds", "2 pond", "30 kg")
            - Sizes (e.g., "large", "small", "medium")
            - Health conditions or special needs
            - Any other relevant pet details
            
            Messages to analyze:
            {combined_text}
            
            Extract every pet mentioned and return ONLY a JSON array with this exact format:
            [
                {{
                    "name": "pet_name_or_unknown",
                    "breed": "breed_name_or_unknown", 
                    "age": "age_info_or_unknown",
                    "weight": "weight_info_or_unknown",
                    "size": "size_info_or_unknown",
                    "health_conditions": ["condition1", "condition2"],
                    "other_details": "additional_relevant_info",
                    "confidence": 0.85,
                    "source_context": "brief_context_where_this_info_was_found"
                }}
            ]
            
            Important: 
            - If you find ANY pet information, include it
            - Use "unknown" only if truly no information is available
            - Be thorough - check every message carefully
            - Return empty array [] only if absolutely no pet information exists
            """
            
            response = self.chat_model.invoke([
                SystemMessage(content="You are Mr. White, an expert at extracting pet information. Always return valid JSON only."),
                HumanMessage(content=extraction_prompt)
            ])
            
            try:
                pets_info = json.loads(response.content)
                if isinstance(pets_info, list):
                    current_app.logger.info(f"✅ Successfully extracted information for {len(pets_info)} pets")
                    # Log what was found for debugging
                    for pet in pets_info:
                        current_app.logger.info(f"   Pet: {pet.get('name', 'Unknown')} - {pet.get('breed', 'Unknown')} - {pet.get('age', 'Unknown')}")
                    return pets_info
                else:
                    current_app.logger.warning("❌ AI returned non-list format")
                    return []
            except json.JSONDecodeError as je:
                current_app.logger.warning(f"❌ Failed to parse pet information JSON: {str(je)}")
                current_app.logger.info(f"Raw AI response: {response.content[:500]}...")
                return self._fallback_pet_extraction(combined_text)
                
        except Exception as e:
            current_app.logger.error(f"Error extracting pet information: {str(e)}")
            return []
    
    def _fallback_pet_extraction(self, text: str) -> List[Dict[str, Any]]:
        """Fallback method using regex patterns to extract pet info"""
        
        pets = []
        text_lower = text.lower()
        
        current_app.logger.info(f"Running fallback pet extraction on text: {text[:100]}...")
        
        # Special pattern for the format "my dog name is X and his breed is Y and age is Z"
        special_pattern = r"my dog name is (\w+)(?:\s+and|\s*,)\s+(?:his|her|its)?\s*breed is (\w+)(?:\s+and|\s*,)?\s+(?:his|her|its)?\s*age is (\d+)\s*(months|years|month|year)"
        special_match = re.search(special_pattern, text_lower)
        if special_match:
            name = special_match.group(1).capitalize()
            breed = special_match.group(2).capitalize()
            age = f"{special_match.group(3)} {special_match.group(4)}"
            
            current_app.logger.info(f"✅ Special pattern matched! Found dog: {name}, {breed}, {age}")
            
            # Extract weight if present
            weight = "unknown"
            weight_match = re.search(r"(?:his|her|its)?\s*weight is (\d+)\s*(kg|pounds|lbs|pound|lb)", text_lower)
            if weight_match:
                weight = f"{weight_match.group(1)} {weight_match.group(2)}"
            
            return [{
                "name": name,
                "breed": breed,
                "age": age,
                "weight": weight,
                "size": "unknown",
                "health_conditions": [],
                "other_details": "",
                "confidence": 0.9,
                "source_context": "Extracted from direct user statement"
            }]
        
        # Look for pet names
        name_patterns = [
            r"my dog (?:name is |is )?(\w+)",
            r"(?:his|her) name is (\w+)",
            r"(\w+) is my (?:dog|pet)",
            r"my dog name is (\w+)",
            r"dog name is (\w+)",
            r"dog(?:'s)? name is (\w+)"
        ]
        
        names = []
        for pattern in name_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                for match in matches:
                    if isinstance(match, str) and len(match) > 1:
                        name = match.capitalize()
                        if name.lower() not in ["dog", "pet", "name", "the", "my", "is", "his", "her", "its"]:
                            names.append(name)
                            current_app.logger.info(f"Found dog name: {name}")
        
        # Look for breeds
        breed_patterns = [
            r"(?:breed is|is a) (\w+\s*\w*)",
            r"(\w+) breed",
            r"(\w+) dog"
        ]
        
        breeds = []
        for pattern in breed_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                for match in matches:
                    if isinstance(match, str) and len(match) > 1:
                        breed = match.strip().capitalize()
                        if breed.lower() not in ["dog", "pet", "breed", "the", "my", "is", "his", "her", "its"]:
                            breeds.append(breed)
                            current_app.logger.info(f"Found dog breed: {breed}")
        
        # Look for ages
        age_patterns = [
            r"(\d+)\s*(year|years|month|months) old",
            r"age is (\d+)\s*(year|years|month|months)",
            r"(\d+)\s*(year|years|month|months) of age"
        ]
        
        ages = []
        for pattern in age_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                for match in matches:
                    if isinstance(match, tuple) and len(match) >= 2:
                        age = f"{match[0]} {match[1]}"
                        ages.append(age)
                        current_app.logger.info(f"Found dog age: {age}")
        
        # Look for weights
        weight_patterns = [
            r"(\d+)\s*(kg|pound|pounds|lb|lbs)",
            r"weight is (\d+)\s*(kg|pound|pounds|lb|lbs)",
            r"weighs (\d+)\s*(kg|pound|pounds|lb|lbs)"
        ]
        
        weights = []
        for pattern in weight_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                for match in matches:
                    if isinstance(match, tuple) and len(match) >= 2:
                        weight = f"{match[0]} {match[1]}"
                        weights.append(weight)
                        current_app.logger.info(f"Found dog weight: {weight}")
        
        # Create pet entries
        if names:
            for i, name in enumerate(names):
                pet = {
                    "name": name,
                    "breed": breeds[i] if i < len(breeds) else "unknown",
                    "age": ages[i] if i < len(ages) else "unknown",
                    "weight": weights[i] if i < len(weights) else "unknown",
                    "size": "unknown",
                    "health_conditions": [],
                    "other_details": "",
                    "confidence": 0.7,
                    "source_context": "Extracted using fallback pattern matching"
                }
                pets.append(pet)
        elif breeds:  # Create entry even if no name found
            pet = {
                "name": "unknown",
                "breed": breeds[0],
                "age": ages[0] if ages else "unknown",
                "weight": weights[0] if weights else "unknown",
                "size": "unknown",
                "health_conditions": [],
                "other_details": "",
                "confidence": 0.6,
                "source_context": "Partial information extracted"
            }
            pets.append(pet)
        
        current_app.logger.info(f"Fallback extraction found {len(pets)} pets")
        return pets
    
    def _determine_primary_pet(self, pets_found: List[Dict[str, Any]], query: str) -> Optional[Dict[str, Any]]:
        """Determine which pet is most relevant to the current query"""
        
        if not pets_found:
            return None
        
        if len(pets_found) == 1:
            return pets_found[0]
        
        # If multiple pets, try to determine from query context
        query_lower = query.lower()
        
        for pet in pets_found:
            pet_name = pet.get("name", "").lower()
            if pet_name != "unknown" and pet_name in query_lower:
                return pet
        
        # Default to first pet (highest confidence or most recent)
        return pets_found[0]
    
    def _get_context_recommendation(self, pets_found: List[Dict[str, Any]]) -> str:
        """Get recommendation based on found pet information"""
        
        if not pets_found:
            return "ask_for_details"
        
        if len(pets_found) == 1:
            pet = pets_found[0]
            # Check completeness of information
            unknown_fields = sum(1 for key in ["breed", "age", "weight"] 
                               if pet.get(key, "Unknown").lower() == "unknown")
            
            if unknown_fields > 1:
                return "ask_for_missing_details"
            else:
                return "use_available_context"
        
        else:  # Multiple pets
            return "clarify_which_pet"
    
    def generate_contextual_pet_response_prefix(
        self, 
        pet_context: Dict[str, Any], 
        query: str, 
        query_analysis: Dict[str, Any]
    ) -> str:
        """
        Generate a context-aware prefix for responses that includes pet information
        
        Args:
            pet_context: Pet information retrieved
            query: Original query
            query_analysis: Query analysis results
            
        Returns:
            Contextual prefix for the AI response
        """
        try:
            if not pet_context.get("context_available", False):
                return ""
            
            pets_found = pet_context.get("pets_found", [])
            primary_pet = pet_context.get("primary_pet")
            recommendation = pet_context.get("recommendation", "")
            
            if recommendation == "use_available_context" and primary_pet:
                # Generate rich context prefix
                pet_name = primary_pet.get("name", "your dog")
                breed = primary_pet.get("breed", "Unknown")
                age = primary_pet.get("age", "Unknown")
                weight = primary_pet.get("weight", "Unknown")
                
                context_prefix = f"Based on the information I have about {pet_name}"
                
                details = []
                if breed != "Unknown":
                    details.append(f"breed: {breed}")
                if age != "Unknown":
                    details.append(f"age: {age}")
                if weight != "Unknown":
                    details.append(f"weight: {weight}")
                
                if details:
                    context_prefix += f" ({', '.join(details)})"
                
                context_prefix += ", here's my recommendation:\n\n"
                return context_prefix
                
            elif recommendation == "clarify_which_pet" and len(pets_found) > 1:
                pet_names = [pet.get("name", "Unknown") for pet in pets_found if pet.get("name", "Unknown") != "Unknown"]
                if pet_names:
                    return f"I see you have information about {', '.join(pet_names)}. Which dog are you asking about for this {query_analysis.get('query_type', 'question')}?\n\n"
                else:
                    return f"I found information about {len(pets_found)} pets in our previous conversations. Which one are you asking about?\n\n"
                    
            elif recommendation == "ask_for_missing_details" and primary_pet:
                pet_name = primary_pet.get("name", "your dog")
                missing_info = []
                
                if primary_pet.get("breed", "Unknown") == "Unknown":
                    missing_info.append("breed")
                if primary_pet.get("age", "Unknown") == "Unknown":
                    missing_info.append("age")
                if primary_pet.get("weight", "Unknown") == "Unknown":
                    missing_info.append("weight")
                
                if missing_info:
                    return f"I have some information about {pet_name}, but could you please tell me {pet_name}'s {' and '.join(missing_info)} for more personalized advice?\n\n"
                    
            return ""
            
        except Exception as e:
            current_app.logger.error(f"Error generating contextual prefix: {str(e)}")
            return ""

    def generate_pawtree_diet_recommendation(
        self, 
        pet_info: Optional[Dict[str, Any]], 
        query: str
    ) -> str:
        """
        Generate Paw Tree diet recommendation based on pet information
        
        Args:
            pet_info: Pet information dictionary
            query: Original diet-related query
            
        Returns:
            Formatted Paw Tree recommendation text
        """
        try:
            if not pet_info:
                # Generic recommendation when no pet info available
                return """💡 **Also Consider**: For premium, personalized nutrition, check out **Paw Tree** (https://pawtree.com/doglove/) - they create custom diet plans based on your dog's specific needs."""
                
            else:
                # Personalized recommendation with pet context
                pet_name = pet_info.get("name", "your dog")
                
                return f"""💡 **Also Consider**: For {pet_name}'s specific needs, **Paw Tree** (https://pawtree.com/doglove/) offers personalized nutrition plans tailored to breed, age, and health requirements."""
            
        except Exception as e:
            current_app.logger.error(f"Error generating Paw Tree recommendation: {str(e)}")
            # Fallback to basic recommendation
            return """💡 **Also Consider**: For personalized nutrition, check out **Paw Tree** (https://pawtree.com/doglove/)"""
    
    def is_diet_related_query(self, query: str) -> bool:
        """
        Check if query is specifically related to diet/food/nutrition
        
        Args:
            query: User's query
            
        Returns:
            True if diet-related, False otherwise
        """
        diet_keywords = [
            'diet', 'food', 'feeding', 'nutrition', 'meal', 'eat', 'eating',
            'feed', 'kibble', 'treats', 'snacks', 'supplements', 'vitamins',
            'hungry', 'appetite', 'calories', 'protein', 'carbs', 'fat',
            'ingredients', 'grain free', 'raw diet', 'dry food', 'wet food',
            'puppy food', 'senior food', 'weight management', 'digestive',
            'allergies', 'sensitive stomach', 'premium food', 'organic',
            'natural', 'holistic nutrition'
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in diet_keywords)

    def get_pet_context(self, user_id: int, message: str) -> Dict[str, Any]:
        """
        Get pet context for a user and message
        
        This is a wrapper around the analyze_query_for_pet_context and retrieve_pet_information methods
        that provides a simplified interface for the enhanced chat service.
        
        Args:
            user_id: User ID
            message: User's message
            
        Returns:
            Dictionary with pet context
        """
        try:
            # First analyze if the query needs pet context
            query_analysis = self.analyze_query_for_pet_context(message)
            
            # If the query needs pet context with sufficient confidence, retrieve it
            if query_analysis.get("needs_pet_context", False) and query_analysis.get("confidence", 0) >= 0.7:
                current_app.logger.info(f"🐕 Pet context required (confidence: {query_analysis.get('confidence', 0):.2f})")
                pet_context = self.retrieve_pet_information(user_id, message)
                
                # Check what we found
                if pet_context.get("context_available", False):
                    pets_found = pet_context.get("pets_found", [])
                    current_app.logger.info(f"✅ Retrieved context for {len(pets_found)} pet(s)")
                    return pet_context
                else:
                    current_app.logger.info("ℹ️ No pet context found - will ask for details if needed")
                    return {}
            else:
                current_app.logger.info(f"🔍 Skipping pet context retrieval (confidence: {query_analysis.get('confidence', 0):.2f})")
                return {}
        except Exception as e:
            current_app.logger.error(f"❌ Error getting pet context: {str(e)}")
            return {}
    
    def analyze_pet_query(self, message: str) -> Dict[str, Any]:
        """
        Analyze a query for pet-related information
        
        This is a wrapper around analyze_query_for_pet_context that provides
        a simplified interface for the enhanced chat service.
        
        Args:
            message: User's message
            
        Returns:
            Dictionary with query analysis
        """
        try:
            return self.analyze_query_for_pet_context(message)
        except Exception as e:
            current_app.logger.error(f"❌ Error analyzing pet query: {str(e)}")
            return {
                "needs_pet_context": False,
                "confidence": 0.0,
                "query_type": "general_knowledge",
                "context_requirements": [],
                "error": str(e)
            }


# Global service instance
_pet_context_service = None

def get_pet_context_service() -> PetContextService:
    """Get singleton instance of pet context service"""
    global _pet_context_service
    if _pet_context_service is None:
        _pet_context_service = PetContextService()
    return _pet_context_service 