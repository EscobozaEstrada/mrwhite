"""
Simple LLM-Based Pet Information Extractor
Focus on accuracy and reliability over complexity
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, date

logger = logging.getLogger(__name__)

class PetExtractionResult:
    """Enhanced extraction result with comprehensive profile support"""
    
    def __init__(self, extracted_fields: Dict[str, Any], confidence_score: float, raw_message: str, comprehensive_json: Dict[str, Any] = None):
        self.extracted_fields = extracted_fields
        self.confidence_score = confidence_score
        self.raw_message = raw_message
        self.comprehensive_json = comprehensive_json or {}

class SimplePetExtractor:
    """
    Simple, reliable LLM-based pet information extraction
    """
    
    def __init__(self, openai_client=None):
        self.openai_client = openai_client
        
        # All possible pet fields
        self.PET_FIELDS = {
            "name": "Pet's name (e.g., 'Buddy', 'Luna')",
            "breed": "Dog breed (e.g., 'Golden Retriever', 'Labrador')",
            "age": "Age in years (integer, e.g., 3)",
            "weight": "Weight in pounds (number, e.g., 45.5)",
            "gender": "Gender ('Male' or 'Female')",
            "date_of_birth": "Birth date (YYYY-MM-DD format)",
            "microchip_id": "Microchip ID number",
            "spayed_neutered": "Whether spayed/neutered (true/false)",
            "known_allergies": "Known allergies or food sensitivities",
            "medical_conditions": "Any medical conditions or health issues",
            "emergency_vet_name": "Veterinarian or clinic name",
            "emergency_vet_phone": "Vet phone number"
        }
    
    async def extract_pet_information(self, user_message: str, existing_pet_context: Dict[str, Any] = None) -> PetExtractionResult:
        """
        Extract pet information using LLM with structured prompt
        """
        try:
            # Clean the message first
            clean_message = self._clean_message(user_message)
            if not clean_message:
                return PetExtractionResult({}, 0.0, user_message)
            
            # CRITICAL: Skip Anahata-related queries entirely - these are book/author queries, not pet queries
            message_lower = clean_message.lower()
            anahata_keywords = [
                "anahata", "anahta", "anahata graceland", "anahta graceland", 
                "way of dog", "way of the dog", "interspecies culture", "intuitive bonding",
                "what does anahata say", "anahata says", "according to anahata", "anahata approach",
                "anahata philosophy", "anahata method", "anahata book", "anahata wisdom",
                "poem by anahata", "poem by anahta", "archive this poem",
                "dance of souls", "tribute to the dog", "dog–human bond", "dog-human bond"
            ]
            is_anahata_query = any(keyword in message_lower for keyword in anahata_keywords)
            
            if is_anahata_query:
                logger.info(f"📚 Anahata book/author query detected, not extracting pet info: '{clean_message}'")
                return PetExtractionResult({}, 0.0, user_message)
            
            # CRITICAL: Skip document/archive-related queries entirely - these are document queries, not pet queries
            document_keywords = [
                "archive this", "store this", "save this", "keep this",
                "do you remember", "remember the", "recall the", "what about the",
                "the poem", "the article", "the story", "the document", "the text",
                "here it is:", "here is the", "here's the", "i'd like you to archive"
            ]
            is_document_query = any(keyword in message_lower for keyword in document_keywords)
            
            if is_document_query:
                logger.info(f"📄 Document/archive query detected, not extracting pet info: '{clean_message}'")
                return PetExtractionResult({}, 0.0, user_message)
            
            # INFORMATION: Veterinarian context detection for logging purposes
            # Note: We allow vet information extraction into correct fields (emergency_vet_name, emergency_vet_phone)
            # The invalid names list and validation logic will prevent vet names from being extracted as pet names
            veterinarian_keywords = [
                "as his vet", "as her vet", "as my vet", "as their vet", "as the vet",
                "is his vet", "is her vet", "is my vet", "is their vet", "is the vet",  
                "vet is", "veterinarian is", "doctor is", "my veterinarian", "my doctor",
                "our vet", "our veterinarian", "our doctor", "the veterinarian", "vet named",
                "veterinarian named", "doctor named", "see the vet", "visit the vet"
            ]
            is_veterinarian_query = any(keyword in message_lower for keyword in veterinarian_keywords)
            
            if is_veterinarian_query:
                logger.info(f"🏥 Veterinarian context detected - will extract vet info into correct fields: '{clean_message}'")
            
            # Check if user is asking hypothetical or general questions
            hypothetical_keywords = [
                "getting", "thinking of getting", "planning to", "want to get", "considering", 
                "new dog", "future dog", "coming home", "arriving", "joining",
                "adopting", "bringing home", "will get", "going to get", "introducing",
                "integration", "integrate", "suggestions", "advice for new", "best way"
            ]
            
            # More specific hypothetical patterns for "another dog" to avoid false positives
            hypothetical_another_dog_patterns = [
                "getting another dog", "want another dog", "thinking of another dog", 
                "considering another dog", "planning.*another dog"
            ]
            
            # Check basic hypothetical keywords
            is_hypothetical = any(keyword in message_lower for keyword in hypothetical_keywords)
            
            # Check for hypothetical "another dog" patterns but allow "I have another dog"
            if not is_hypothetical:
                is_hypothetical = any(pattern in message_lower for pattern in hypothetical_another_dog_patterns)
            
            # Override: If user says "I have another dog" or similar, treat as pet info not hypothetical
            present_tense_indicators = ["i have another", "my other", "we have another", "our other"]
            if any(indicator in message_lower for indicator in present_tense_indicators):
                is_hypothetical = False
            
            # Override: If user is sharing actual pet information/reports, treat as real data not hypothetical
            information_sharing_patterns = [
                "i am sharing", "here is", "sharing my", "my dog's", "my cat's", "my pet's",
                "health report", "medical report", "vet report", "veterinary report",
                "test results", "lab results", "examination", "checkup report",
                "vaccination record", "medical history", "health history", "vet visit",
                "diagnosis", "blood work", "x-ray", "scan results", "assessment",
                "here are the details", "here's the information", "the report shows",
                "according to the vet", "the veterinarian said", "medical findings"
            ]
            is_sharing_pet_info = any(pattern in message_lower for pattern in information_sharing_patterns)
            
            # Additional check for integration/introduction scenarios
            integration_patterns = [
                "integrate", "introduction", "introducing", "join", "joining", "new.*to.*pack",
                "suggestions.*new", "advice.*new", "best way.*new"
            ]
            is_integration_question = any(keyword in message_lower for keyword in integration_patterns)
            
            # Override both hypothetical AND integration detection when sharing pet info
            if is_sharing_pet_info:
                is_hypothetical = False
                is_integration_question = False  # Also override integration detection
                logger.info(f"📋 Detected information sharing - overriding detection to allow extraction")
            
            # Check if user is asking about FOOD - prevent food extraction as pet names
            # FIX: Don't treat pet profile information as food questions
            food_question_patterns = [
                "can my dog eat", "can dogs eat", "should i feed", "what to feed", "safe to eat",
                "toxic", "poisonous", "what should i give", "how much to feed",
                "is it safe", "can they have", "food good for dogs", "food bad for dogs",
                "daily portion", "how much food", "feeding schedule", "food recommendation"
            ]
            # Only treat as food question if it's actually asking about food safety/recommendations
            # NOT when providing pet profile information that includes diet details
            is_food_question = any(pattern in message_lower for pattern in food_question_patterns)
            
            # CRITICAL FIX: Don't treat exercise questions as food questions
            exercise_keywords = ["exercise", "excercise", "walk", "walking", "activity", "physical", "movement", "play", "training"]
            is_exercise_question = any(keyword in message_lower for keyword in exercise_keywords)
            if is_exercise_question:
                is_food_question = False  # Override food question detection for exercise
            
            # Don't treat pet profile information as food questions
            profile_indicators = [
                "information", "details", "profile", "about", "data", "my pet",
                "my dog information", "my cat information", "pet details"
            ]
            is_profile_info = any(indicator in message_lower for indicator in profile_indicators)
            
            # If it's profile information, don't skip extraction even if it mentions food
            if is_profile_info:
                is_food_question = False
            
            if is_hypothetical or is_integration_question or is_food_question:
                if is_food_question:
                    logger.info(f"🍖 Food/diet question detected, not extracting pet info: '{clean_message}'")
                else:
                    logger.info(f"🤔 Hypothetical/advice question detected, not extracting pet info: '{clean_message}'")
                return PetExtractionResult({}, 0.0, user_message)
            
            if not self.openai_client:
                logger.warning("No OpenAI client available for extraction")
                return PetExtractionResult({}, 0.0, user_message)
            
            # Create structured extraction prompt
            extraction_prompt = self._create_extraction_prompt(clean_message, existing_pet_context)
            
            # Get LLM response
            response = await self._get_llm_response(extraction_prompt)
            
            # Parse and validate response with comprehensive data support
            extracted_data, comprehensive_data = self._parse_llm_response_enhanced(response)
            
            # DEBUG: Log what was extracted after parsing
            logger.info(f"🔍 EXTRACTED DATA: {extracted_data}")
            logger.info(f"🔍 COMPREHENSIVE DATA: {comprehensive_data}")
            
            # 🆕 CRITICAL FIX: If comprehensive data is empty but we have vet/medical content, use fallback extraction
            if not comprehensive_data and self._is_vet_or_medical_content(clean_message):
                logger.info("🏥 COMPREHENSIVE FIX: JSON parsing succeeded but comprehensive data is empty - using fallback vet extraction")
                fallback_comprehensive = self._extract_vet_report_data(clean_message)
                if fallback_comprehensive:
                    comprehensive_data = fallback_comprehensive
                    logger.info(f"🏥 FALLBACK SUCCESS: Extracted {len(comprehensive_data)} comprehensive fields from vet content")
            
            # Calculate confidence based on extraction quality
            confidence = self._calculate_confidence(extracted_data, clean_message)
            
            logger.info(f"🔍 Enhanced extraction complete: Structured: {len(extracted_data)} fields, Comprehensive: {len(comprehensive_data)} fields, confidence: {confidence:.2f}")
            
            # 🔍 DEBUG: Log just before PetExtractionResult creation
            logger.info(f"🔍 ABOUT TO CREATE PetExtractionResult with: extracted_fields={extracted_data}, confidence={confidence}")
            
            try:
                result = PetExtractionResult(
                    extracted_fields=extracted_data,
                    confidence_score=confidence,
                    raw_message=user_message,
                    comprehensive_json=comprehensive_data
                )
                logger.info(f"🔍 PetExtractionResult created successfully: confidence={result.confidence_score}, fields={result.extracted_fields}")
                return result
            except Exception as e:
                logger.error(f"❌ Simple extraction error: {e}")
                return PetExtractionResult({}, 0.0, user_message)
        except Exception as e:
            logger.error(f"❌ Simple extraction error: {e}")
            return PetExtractionResult({}, 0.0, user_message)
    
    def _clean_message(self, message: str) -> str:
        """Clean and filter the user message"""
        # Remove AI response indicators
        ai_indicators = [
            "I'd be happy to", "Let me help", "I recommend", "I suggest",
            "As an AI", "As your", "Here's what", "*wags tail*", "*nods*",
            "Mr. White:", "Assistant:", "AI:"
        ]
        
        # Check if this looks like an AI response
        for indicator in ai_indicators:
            if indicator in message:
                return ""
        
        # Handle conversation format (User: ... Assistant: ...)
        if "User:" in message and "Assistant:" in message:
            lines = message.split('\n')
            user_parts = []
            current_speaker = None
            
            for line in lines:
                line = line.strip()
                if line.startswith("User:"):
                    current_speaker = "user"
                    user_parts.append(line[5:].strip())
                elif line.startswith(("Assistant:", "AI:", "Mr. White:")):
                    current_speaker = "ai"
                elif current_speaker == "user" and line:
                    user_parts.append(line)
            
            return " ".join(user_parts)
        
        return message.strip()
    
    def _get_comprehensive_invalid_names(self) -> list:
        """Get comprehensive list of invalid pet names"""
        return [
            # Titles and honorifics
            "Dr.", "Mr.", "Mrs.", "Ms.", "Professor", "Doctor", "Sir", "Madam",
            
            # Generic animal terms
            "Dog", "Cat", "Pet", "Animal", "Puppy", "Kitten", "Doggy", "Doggie",
            "Canine", "Feline", "Beast", "Creature", "Pup", "Kitty",
            "The Dog", "My Dog", "Our Pet", "The Cat", "A Dog", "A Cat",
            
            # CRITICAL: English pronouns and articles (major source of fake names)
            "My", "Your", "His", "Her", "Their", "Its", "Our", "Mine", "Yours",
            "The", "A", "An", "This", "That", "These", "Those", "Some", "Any",
            "All", "Both", "Each", "Every", "No", "None", "Nothing", "Something",
            
            # Possessive forms (common LLM mistakes)
            "My Dog'S", "His Dog'S", "Her Cat'S", "Their Pet'S", "Dog'S", "Cat'S",
            
            # Common verbs (especially past tense - frequently misextracted)
            "Adapted", "Trained", "Learned", "Walked", "Fed", "Played", "Ran",
            "Jumped", "Barked", "Meowed", "Slept", "Ate", "Drank", "Grew",
            "Changed", "Moved", "Lived", "Stayed", "Came", "Went", "Got", "Had",
            "Was", "Were", "Been", "Being", "Have", "Has", "Will", "Would",
            "Could", "Should", "Might", "Must", "Can", "Cannot", "Do", "Does",
            "Did", "Done", "Make", "Made", "Take", "Took", "Give", "Gave",
            
            # Adjectives and descriptors (NOT names)
            "Beautiful", "Cute", "Smart", "Clever", "Funny", "Sweet", "Gentle",
            "Hyper", "Active", "Calm", "Quiet", "Lazy", "Energetic", "Playful",
            "Aggressive", "Shy", "Friendly", "Mean", "Nice", "Good", "Bad",
            "Smart", "Stupid", "Fast", "Slow", "Strong", "Weak", "Healthy",
            "Sick", "Young", "Old", "New", "Big", "Small", "Large", "Tiny",
            "Huge", "Little", "Happy", "Sad", "Excited", "Nervous", "Scared",
            
            # Behavioral terms
            "Hyper", "Active", "Calm", "Quiet", "Lazy", "Energetic",
            "Playful", "Aggressive", "Shy", "Friendly", "Mean", "Nice",
            "Good", "Bad", "Smart", "Stupid", "Fast", "Slow",
            
            # Location and direction words
            "Here", "There", "Where", "Everywhere", "Nowhere", "Somewhere",
            "Up", "Down", "Left", "Right", "Front", "Back", "Inside", "Outside",
            "Near", "Far", "Close", "Away", "Home", "House", "Yard", "Park",
            
            # Time-related words
            "Now", "Then", "Today", "Yesterday", "Tomorrow", "Always", "Never",
            "Sometimes", "Often", "Usually", "Rarely", "When", "While", "Before",
            "After", "During", "Since", "Until", "Morning", "Evening", "Night",
            
            # Question words and conjunctions
            "What", "Who", "When", "Where", "Why", "How", "Which", "Whose",
            "And", "Or", "But", "So", "If", "Because", "Although", "However",
            "Therefore", "Moreover", "Furthermore", "Nevertheless",
            
            # Numbers and quantities
            "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight",
            "Nine", "Ten", "First", "Second", "Third", "Many", "Few", "Several",
            "More", "Less", "Most", "Least", "Enough", "Too", "Very", "Much",
            
            # Hypothetical/Future pets (NOT real names)
            "New Dog", "New Cat", "New Pet", "New Puppy", "New Kitten",
            "Another Cat", "Another Pet", "Second Dog",
            "Third Dog", "Other Dog", "Different Dog", "Extra Dog",
            "Future Dog", "Coming Dog", "Incoming Dog", "Next Dog",
            "Next Pet", "Additional Pet", "More Dogs", "More Cats",
            
            # Common words that aren't names
            "Help", "Problem", "Issue", "Question", "Training", "Behavior",
            "Listening", "Teaching", "Learn", "Know", "Think", "Feel", "Want",
            "Need", "Like", "Love", "Hate", "Enjoy", "Prefer", "Choose",
            "Decide", "Remember", "Forget", "Understand", "Explain", "Tell",
            "Say", "Speak", "Talk", "Listen", "Hear", "See", "Look", "Watch",
            
            # FOOD ITEMS - CRITICAL: Prevent food names from being extracted as pets
            "Chicken", "Beef", "Pork", "Fish", "Salmon", "Tuna", "Turkey",
            "Lamb", "Duck", "Venison", "Rabbit", "Egg", "Eggs", "Boiled Egg",
            "Scrambled Egg", "Fried Egg", "Raw Egg", "Cheese", "Milk",
            "Rice", "Pasta", "Bread", "Carrot", "Broccoli", "Spinach",
            "Potato", "Sweet Potato", "Pumpkin", "Apple", "Banana",
            "Blueberry", "Strawberry", "Orange", "Watermelon", "Grape",
            "Kibble", "Treats", "Food", "Meat", "Bones", "Bone",
            "Raw Food", "Dry Food", "Wet Food", "Canned Food",
            "Dog Food", "Cat Food", "Pet Food", "Biscuit", "Cookie",
            "Liver", "Heart", "Kidney", "Organ", "Vegetables", "Fruits",
            
            # Medical/Health terms
            "Vet", "Veterinarian", "Doctor", "Medicine", "Treatment", "Surgery",
            "Vaccine", "Shot", "Pill", "Medication", "Therapy", "Examination",
            
        # Authors and Professionals (NOT pet names) - including name variations
        "Anahata", "Anahta", "Anahata Graceland", "Anahta Graceland", 
        # CRITICAL: Veterinarian name variations (Dr Anatha/Anahata)
        "Dr Anatha", "Dr. Anatha", "Doctor Anatha", "Dr Anahata", "Dr. Anahata", "Doctor Anahata",
        "dr anatha", "dr. anatha", "doctor anatha", "dr anahata", "dr. anahata", "doctor anahata",
        "Author", "Writer", "Expert", "Trainer", "Professional",
            
            # Colors (when used alone, not proper names)
            "Black", "White", "Brown", "Gray", "Grey", "Red", "Blue", "Green",
            "Yellow", "Orange", "Pink", "Purple", "Golden", "Silver",
            
            # CRITICAL: Dog breeds (should be extracted as breed, NOT as pet names)
            "Labrador", "Golden Retriever", "German Shepherd", "Bulldog", "Poodle",
            "Beagle", "Rottweiler", "Yorkshire Terrier", "Dachshund", "Siberian Husky",
            "Shih Tzu", "Boston Terrier", "Pomeranian", "Australian Shepherd", 
            "Border Collie", "Cocker Spaniel", "French Bulldog", "Mastiff", "Chihuahua",
            "Great Dane", "Boxer", "Pit Bull", "Jack Russell", "Bernese Mountain Dog",
            "Saint Bernard", "Newfoundland", "Bloodhound", "Greyhound", "Whippet",
            "Doberman", "Akita", "Basset Hound", "Maltese", "Cavalier King Charles",
            "English Springer Spaniel", "Weimaraner", "Rhodesian Ridgeback", "Vizsla",
            "Irish Setter", "Scottish Terrier", "West Highland Terrier", "Papillon",
            "Bichon Frise", "Havanese", "Portuguese Water Dog", "Afghan Hound",
            "Alaskan Malamute", "American Eskimo Dog", "Australian Cattle Dog",
            "Belgian Malinois", "Brittany", "Cairn Terrier", "Chinese Crested",
            "Chow Chow", "Dalmatian", "English Bulldog", "Finnish Spitz", "Great Pyrenees",
            "Irish Wolfhound", "Italian Greyhound", "Japanese Chin", "Keeshond",
            "Lhasa Apso", "Norwegian Elkhound", "Old English Sheepdog", "Pekingese",
            "Pharaoh Hound", "Pointer", "Pug", "Saluki", "Samoyed", "Schnauzer",
            "Shetland Sheepdog", "Staffordshire Terrier", "Standard Poodle", "Toy Poodle",
            "Miniature Poodle", "Welsh Corgi", "Wire Fox Terrier", "Mixed Breed", "Mutt",
            "Crossbreed", "Hybrid", "Designer Dog", "Rescue", "Shelter Dog",
            
            # Dog-related terms (NOT pet names)
            "Training", "Obedience", "Agility", "Grooming", "Brushing", "Bathing",
            "Walking", "Exercise", "Fetch", "Sit", "Stay", "Come", "Down", "Heel",
            "Roll Over", "Shake", "Speak", "Quiet", "Drop It", "Leave It",
            "Leash", "Collar", "Harness", "Crate", "Kennel", "Bed", "Toy", "Ball",
            "Rope", "Chew", "Bone", "Treat", "Reward", "Praise", "Good Boy", "Good Girl",
            
            # Single letters and very short words (except valid short names)
            "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M",
            "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
            "It", "Is", "Be", "To", "Of", "In", "On", "At", "By", "For",
            "As", "Or", "An", "No", "So", "Up", "We", "He", "Me", "Us",
            "Am", "Are", "Was", "Were", "Been", "Being", "Have", "Has", "Had",
            "Do", "Does", "Did", "Will", "Would", "Should", "Could", "May",
            "Might", "Must", "Can", "Get", "Got", "Go", "Went", "Come", "Came"
        ]
    
    def _is_valid_pet_name(self, name: str) -> bool:
        """Smart linguistic validation for pet names"""
        import re
        
        # Basic length check (allow some valid short names like "Bo", "Lu", etc.)
        if len(name) < 2:
            return False
        
        # Check for all lowercase (proper names should be capitalized)
        if name.islower() and len(name) > 2:
            return False
            
        # Check for possessive forms (major source of errors)
        if "'s" in name.lower() or "'S" in name:
            return False
            
        # Check for common non-name patterns
        # All caps (likely acronyms, not names)
        if name.isupper() and len(name) > 2:
            return False
            
        # Contains numbers (unusual for pet names)
        if re.search(r'\d', name):
            return False
            
        # Contains special characters (except apostrophes in valid names like O'Malley)
        if re.search(r'[^a-zA-Z\'\s\-]', name):
            return False
            
        # Starts with common English articles/pronouns
        if re.match(r'^(My|The|A|An|His|Her|Their|This|That)\s', name, re.IGNORECASE):
            return False
            
        # Common English stop words (basic check)
        english_stop_words = {
            'my', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'among', 'along', 'across',
            'it', 'he', 'she', 'they', 'we', 'you', 'me', 'him', 'her', 'them', 'us',
            'his', 'her', 'its', 'their', 'our', 'your', 'this', 'that', 'these', 'those',
            'what', 'who', 'when', 'where', 'why', 'how', 'which', 'whose'
        }
        
        if name.lower() in english_stop_words:
            return False
            
        return True
    
    def _contains_invalid_patterns(self, name: str) -> bool:
        """Check for additional invalid patterns"""
        import re
        
        # Check for verb endings (past tense -ed, present -ing, etc.)
        if re.search(r'(ed|ing|tion|sion|ness|ment|able|ible)$', name.lower()):
            # Allow some exceptions that could be legitimate names
            exceptions = {'Ted', 'Ed', 'Reed', 'Fred', 'Ned', 'Red', 'Bing', 'King', 'Ring'}
            if name not in exceptions:
                return True
                
        # Check for multiple consecutive uppercase letters (not typical for names)
        if re.search(r'[A-Z]{3,}', name):
            return True
            
        # Check for common sentence patterns
        if re.search(r'\b(is|was|has|have|had|will|can|could|should|would|may|might)\b', name.lower()):
            return True
            
        return False
    
    def _create_extraction_prompt(self, message: str, existing_context: Dict[str, Any] = None) -> str:
        """Create structured prompt for LLM extraction"""
        
        existing_info = ""
        if existing_context and existing_context.get("pets"):
            pets_summary = []
            for pet in existing_context["pets"]:
                pet_info = f"Name: {pet.get('name', 'Unknown')}"
                if pet.get('breed'):
                    pet_info += f", Breed: {pet['breed']}"
                if pet.get('age'):
                    pet_info += f", Age: {pet['age']}"
                pets_summary.append(pet_info)
            existing_info = f"\n\nExisting pets in database: {' | '.join(pets_summary)}"
        
        prompt = f"""Extract pet/dog information from this user message. Be very careful to extract the exact names and details mentioned.
User message: "{message}"{existing_info}

🚨 CRITICAL DATA QUALITY RULES - PREVENT HALLUCINATION:
- ONLY extract information that is EXPLICITLY mentioned in the user's current message
- NEVER infer, assume, or complete missing information for existing pets
- NEVER add breed/age/details unless the user EXPLICITLY states them in THIS message
- If existing pets are shown below, DO NOT extract them unless NEW info is provided about them
- If user says "my dog" without specifying details, extract NOTHING for that pet
- DO NOT fill in missing fields - incomplete data is better than wrong/hallucinated data
- CRITICAL: Existing pets are for context only - don't re-extract them unless user provides NEW details

Extract information into TWO categories:
1. STRUCTURED DATA: Basic pet info that fits standard database fields
2. COMPREHENSIVE DETAILS: Colors, food preferences, personality, habits, and other descriptive info
CRITICAL EXTRACTION RULES:
- Extract EXACT VALUES mentioned, not pet names or other words
- If user says "Luna is pink", extract color as "pink" NOT "luna"
- If user says "Jemmy loves chicken", extract favorite_food as "chicken" NOT "jemmy"
- Be extremely precise with value extraction
- IMPORTANT: If multiple pets are mentioned, extract ALL pets into a "pets" array. If only one pet, still use the pets array format.

🚨 RELATIONSHIP INFORMATION RULES:
- If user mentions PARENT names, SIBLING names, or FAMILY relationships, store them in comprehensive_details, NOT as separate pets
- Keywords indicating relationships: "parent", "parents", "father", "mother", "dad", "mom", "sire", "dam", "sibling", "brother", "sister", "offspring", "child", "puppy of", "son of", "daughter of"
- PATTERN: "PetName's parents are X and Y" → Extract PetName as main pet, store X and Y as parents in comprehensive_details
- PATTERN: "PetName's father is X" → Extract PetName as main pet, store X as father in comprehensive_details
- Example: "Roody's parents are Max and Luna" → Extract {{"pets": [{{"name": "Roody", "comprehensive_details": {{"parents": "Max (father), Luna (mother)"}}}}]}}
- Example: "Buddy's father is Rex" → Extract {{"pets": [{{"name": "Buddy", "comprehensive_details": {{"father": "Rex"}}}}]}}
- Example: "Roody's parent names are Jonnes and Jemini" → Extract {{"pets": [{{"name": "Roody", "comprehensive_details": {{"parents": "Jonnes (father), Jemini (mother)"}}}}]}}
- NEVER create separate pet entries for family members unless they are described as actual pets owned by the user

🚨 MEDICAL/HEALTH INFORMATION RULES:
- If user shares HEALTH REPORTS, MEDICAL RECORDS, VET REPORTS, or MEDICAL INFORMATION, extract ALL relevant details into comprehensive_details
- Medical keywords: "health report", "medical report", "vet report", "examination", "diagnosis", "medications", "supplements", "vaccinations", "medical history", "test results"
- Extract medical findings, treatments, recommendations, medications, health conditions, examination results
- Example: Health report with medications → Extract {{"pets": [{{"name": "Whimsey", "comprehensive_details": {{"medications": "Joint supplement (glucosamine)", "health_conditions": "Mild tartar, slight hind limb stiffness", "vaccinations": "Up to date, rabies booster due in 6 months"}}}}]}}
- Store diet information, activity level, medical history, examination findings, veterinary recommendations
- NEVER ignore medical information - it's valuable for pet care

Return a JSON object in this exact format:
{{
  "pets": [
    {{
      "name": "Pet's actual name",
      "breed": "SPECIFIC breed ONLY if explicitly mentioned (e.g., 'Labrador', 'Poodle', 'Golden Retriever') - NEVER use generic 'Dog'", 
      "age": age_number,
      "weight": weight_number,
      "gender": "Male or Female",
      "date_of_birth": "YYYY-MM-DD if mentioned",
      "microchip_id": "Microchip number if mentioned",
      "spayed_neutered": true_or_false,
      "known_allergies": "Allergies if mentioned",
      "medical_conditions": "Health issues if mentioned",
      "emergency_vet_name": "Vet name if mentioned (e.g., 'Dr. Smith', 'James Veterinary Clinic')",
      "emergency_vet_phone": "Vet phone/contact if mentioned",
      "vet_name": "Alternative vet name field",
      "vet_phone": "Alternative vet phone field",
      "vet_contact": "Vet contact information",
      "vet_experience": "Vet experience if mentioned",
      "comprehensive_details": {{
        // Extract ANY relevant pet information mentioned by the user into appropriate field names
        // Create field names that clearly describe the information (e.g., "grooming_schedule", "training_status", "behavioral_notes", "exercise_routine", etc.)
        // Use descriptive, snake_case field names based on the content
        // Example: {{"color": "golden", "favorite_food": "chicken", "parents": "Max (father), Luna (mother)", "medications": "Joint supplement", "grooming_frequency": "weekly", "training_level": "intermediate"}}
        // If no additional details mentioned, use: {{}}
      }}
    }}
  ]
}}
CRITICAL RULES - PREVENT DATA HALLUCINATION:
1. ALWAYS use the "pets" array format, even for one pet
2. Extract the EXACT name mentioned, not the word "name"
3. BREED field: Only SPECIFIC breeds when explicitly stated (Labrador, Poodle, etc.) - NEVER generic "Dog" - OMIT if not mentioned
4. COLORS go in comprehensive_details.color, NOT in breed field
5. FOOD preferences go in comprehensive_details, NOT in structured fields
6. Only include fields explicitly mentioned for each pet
7. Return {{"pets": []}} if no pet information is mentioned
8. Use exact values from the message, don't paraphrase
9. If multiple pets mentioned, include ALL of them in the array


✅ CORRECT: User says "my dogs need food" → Return {{"pets": []}} (no specific new details)
✅ CORRECT: User says "Buddy is 5 years old" → Extract {{"pets": [{{"name": "Buddy", "age": 5}}]}}
✅ CORRECT: User says "Charlie loves treats" → Extract {{"pets": [{{"name": "Charlie", "comprehensive_details": {{"favorite_food": "treats"}}}}]}}
VET INFORMATION RULES:
- If user mentions VET INFORMATION (vet name, vet phone, vet experience), DO NOT create a new pet
- Vet names like "Dr. James", "Dr. Smith" are VET INFORMATION, not pet names
- Put vet info in structured fields: emergency_vet_name, emergency_vet_phone, vet_experience
- If no specific pet is mentioned with vet info, return ONLY the vet fields without pet array
- Example: "My vet is Dr. Smith" → {{"emergency_vet_name": "Dr. Smith", "pets": []}}
CRITICAL NAME VALIDATION RULES:
- NEVER extract generic words as pet names: "Dog", "Cat", "Pet", "Animal"
- NEVER extract titles as pet names: "Dr.", "Mr.", "Mrs.", "Professor" 
- NEVER extract vet names as pet names: Names starting with "Dr." are VETS, not pets
- NEVER extract behavioral adjectives as pet names: "Hyper", "Active", "Calm", "Playful", "Aggressive"
- NEVER extract descriptive words as pet names: "Small", "Big", "Young", "Old", "Good", "Bad"
- NEVER extract hypothetical pets without names: "New Dog", "Future Dog", "Coming Dog", "Second Dog"
- "Another dog" is REAL if a specific name is provided: "I have another dog named Max" → Extract "Max"
🚨 NEVER EXTRACT FOOD ITEMS AS PET NAMES:
- NEVER extract food names as pet names: "Chicken", "Beef", "Fish", "Egg", "Boiled Egg", "Scrambled Egg"
- NEVER extract food adjectives: "Raw", "Cooked", "Boiled", "Fried", "Baked", "Grilled"
- NEVER extract ingredients: "Rice", "Pasta", "Vegetables", "Fruits", "Meat", "Bones"
- NEVER extract treats/snacks: "Treats", "Kibble", "Biscuit", "Cookie"
- If user asks "Can my dogs eat X?" - X is FOOD, not a pet name
- If user asks "What should I feed my dogs?" - this is about DIET, extract NOTHING
- ONLY extract ACTUAL SPECIFIC pet names mentioned by the user
- If user says "my dog", "the dog", "our pet" - these are NOT pet names, ignore them
🚨 HYPOTHETICAL vs REAL PET DETECTION:
- "I'm getting another dog" → HYPOTHETICAL (Extract NOTHING - future tense, no name)
- "I want to adopt a dog" → HYPOTHETICAL (Extract NOTHING - desire, no name)
- "I have another dog named Buster" → REAL (Extract "Buster" - present tense with specific name)
- "My new puppy Max arrives tomorrow" → REAL (Extract "Max" - specific name given)
- "My dog Buddy needs training" → REAL (Extract "Buddy" - specific existing pet)
Examples:
  * "How can I help my dog feel better?" → Extract NOTHING (no specific pet name)
  * "My dog is very hyper" → Extract NOTHING ("hyper" is behavior, NOT a name)
  * "I have a new dog coming home" → Extract NOTHING (hypothetical scenario)
  * "My vet is Dr. James" → Extract vet info, NOT a pet named "Dr. James"
  * "Luna is very playful" → Extract "Luna" as name, "playful" goes to comprehensive details
🚨 FOOD QUESTION EXAMPLES:
  * "Can my dogs eat boiled egg daily?" → Extract NOTHING ("boiled egg" is FOOD, not a pet name)
  * "Should I feed my dog chicken?" → Extract NOTHING ("chicken" is FOOD, not a pet name)
  * "What treats are safe for dogs?" → Extract NOTHING (about FOOD/TREATS, not pet names)
  * "My dog Luna loves chicken" → Extract "Luna" as name, "chicken" as favorite_food
  * "Is raw meat good for dogs?" → Extract NOTHING ("raw meat" is FOOD, not a pet name)
EXTRACTION ACCURACY EXAMPLES:
✅ CORRECT: "Luna is pink color" → "color": "pink"
❌ WRONG: "Luna is pink color" → "color": "luna"
✅ CORRECT: "Jemmy loves chicken rice" → "favorite_food": "chicken rice"  
❌ WRONG: "Jemmy loves chicken rice" → "favorite_food": "jemmy"
✅ CORRECT: "My dog weighs 25 pounds" → "weight": 25
❌ WRONG: "My dog weighs 25 pounds" → "weight": "dog"
ADDITIVE INFORMATION HANDLING:
- Detect additive keywords: "also", "too", "as well", "in addition", "and", "plus"
- When user says "Luna ALSO likes balls" or "Jemmy TOO enjoys running":
  * Extract the COMPLETE new information
  * Mark it as ADDITIVE by including "ADDITIVE:" prefix in comprehensive_details
  * Example: "comprehensive_details": {{"likes": "ADDITIVE:playing with balls"}}
- For complete information like "Luna loves toy cars and balls", extract the full phrase
- NEVER extract incomplete fragments like "to play" or "to play with"
- Always extract complete, meaningful phrases
Examples:
- Color + breed: {{"pets": [{{"name": "Max", "breed": "Golden Retriever", "comprehensive_details": {{"color": "golden"}}}}]}}
- Food preference: {{"pets": [{{"name": "Luna", "breed": "Poodle", "comprehensive_details": {{"favorite_food": "chicken and rice"}}}}]}}
- Multiple details: {{"pets": [{{"name": "Buddy", "breed": "Labrador", "age": 3, "comprehensive_details": {{"color": "black", "favorite_treat": "peanut butter"}}}}]}}
- Parent information: {{"pets": [{{"name": "Roody", "breed": "German Shepherd", "comprehensive_details": {{"parents": "Jonnes (father, German Shepherd), Jemini (mother, German Shepherd)"}}}}]}}
- Single parent: {{"pets": [{{"name": "Max", "comprehensive_details": {{"father": "Rex (Golden Retriever)"}}}}]}}
- Medical information: {{"pets": [{{"name": "Whimsey", "breed": "Royal Frenchel", "age": 7, "gender": "Female", "comprehensive_details": {{"medications": "Joint supplement (glucosamine)", "health_conditions": "Mild tartar, slight hind limb stiffness", "vaccinations": "Up to date, rabies booster due in 6 months", "diet_details": "Commercial dry kibble, occasional treats", "activity_level": "Moderate daily exercise", "veterinary_recommendations": "Professional dental cleaning within 12 months, annual bloodwork"}}}}]}}
- Training info: {{"pets": [{{"name": "Rex", "comprehensive_details": {{"training_level": "advanced obedience", "known_commands": "sit, stay, heel, come", "training_school": "PetSmart training program"}}}}]}}
- Grooming info: {{"pets": [{{"name": "Fluffy", "comprehensive_details": {{"grooming_frequency": "every 6 weeks", "grooming_salon": "Happy Paws", "coat_type": "double coat", "brushing_routine": "daily"}}}}]}}
- No pet info: {{"pets": []}}

IMPORTANT: Create new field names dynamically based on the information provided. Don't limit yourself to predefined fields.
JSON response:"""

        return prompt
    
    async def _get_llm_response(self, prompt: str) -> str:
        """Get response from LLM"""
        try:
            # Use AWS Bedrock Claude via chat completion
            messages = [
                {"role": "system", "content": "You are a precise data extraction assistant. Return only valid JSON objects with the requested pet information."},
                {"role": "user", "content": prompt}
            ]
            
            response = await self.openai_client.chat_completion(
                messages=messages,
                model="claude-3-sonnet-20240229-v1:0",
                temperature=0.1,  # Low temperature for consistency
                max_tokens=500
            )
            
            # Extract content from response
            if isinstance(response, dict) and 'choices' in response:
                content = response['choices'][0]['message']['content']
            elif hasattr(response, 'content'):
                content = response.content
            else:
                content = str(response)
            
            return content
            
        except Exception as e:
            logger.error(f"❌ LLM response error: {e}")
            return "{}"
    
    def _parse_llm_response_enhanced(self, response: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Parse and validate LLM response with new pets array format"""
        try:
            # Extract JSON from response
            response_clean = response.strip()
            
            # 🔍 DEBUG: Log raw response for vet extraction debugging
            logger.debug(f"🔍 VET DEBUG - Raw LLM response: {response}")
            
            # Find JSON object in response
            start_idx = response_clean.find('{')
            end_idx = response_clean.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                logger.warning(f"🔍 VET DEBUG - No JSON found in response: {response}")
                return {}, {}
            
            json_str = response_clean[start_idx:end_idx]
            logger.debug(f"🔍 VET DEBUG - Extracted JSON: {json_str}")
            
            response_data = json.loads(json_str)
            logger.debug(f"🔍 VET DEBUG - Parsed response data: {response_data}")
            
            # Handle new "pets" array format - treat all pets equally
            if "pets" in response_data and isinstance(response_data["pets"], list):
                pets_array = response_data["pets"]
                
                if pets_array and len(pets_array) > 0:
                    # Process all pets equally - no primary/additional distinction
                    all_pets = []
                    all_comprehensive_data = {}
                    
                    for i, pet in enumerate(pets_array):
                        cleaned_pet = self._clean_single_pet_data(pet)
                        
                        # Handle comprehensive details for each pet individually - FILTER OUT NULL VALUES
                        if "comprehensive_details" in pet and pet["comprehensive_details"]:
                            # Filter out null, empty, and meaningless values
                            comprehensive_data = {}
                            for key, value in pet["comprehensive_details"].items():
                                if self._is_meaningful_value(value):
                                    comprehensive_data[key] = value
                            
                            # Only store if there's actual meaningful data
                            if comprehensive_data:
                                cleaned_pet["comprehensive_profile"] = comprehensive_data
                        
                        all_pets.append(cleaned_pet)
                        
                        # Aggregate all comprehensive data for backward compatibility - FILTER NULLS
                        if "comprehensive_details" in pet and pet["comprehensive_details"]:
                            # Apply same filtering for aggregated data
                            filtered_comprehensive = {}
                            for key, value in pet["comprehensive_details"].items():
                                if self._is_meaningful_value(value):
                                    filtered_comprehensive[key] = value
                            
                            if filtered_comprehensive:
                                pet_name = cleaned_pet.get("name", f"pet_{i+1}")
                                all_comprehensive_data[pet_name] = filtered_comprehensive
                    
                    # Return structure that treats all pets equally
                    if len(all_pets) == 1:
                        # Single pet - return directly
                        return all_pets[0], all_pets[0].get("comprehensive_profile", {})
                    else:
                        # Multiple pets - return as equal list
                        result_data = {"all_pets": all_pets}
                        logger.info(f"🐕 Enhanced extraction: {len(pets_array)} pets, all treated equally")
                        return result_data, all_comprehensive_data
                else:
                    # Empty pets array
                    return {}, {}
            
            # Fallback: Handle old single-pet format (backward compatibility)
            cleaned_data = self._clean_single_pet_data(response_data)
            
            # Apply null filtering to comprehensive data in fallback case
            raw_comprehensive = response_data.get("comprehensive_details", {}) if isinstance(response_data, dict) else {}
            comprehensive_data = {}
            if raw_comprehensive:
                for key, value in raw_comprehensive.items():
                    if self._is_meaningful_value(value):
                        comprehensive_data[key] = value
            
            # 🔍 DEBUG: Log final extraction results
            logger.debug(f"🔍 VET DEBUG - Final cleaned data: {cleaned_data}")
            logger.debug(f"🔍 VET DEBUG - Final comprehensive data: {comprehensive_data}")
            
            return cleaned_data, comprehensive_data
            
        except json.JSONDecodeError as json_error:
            logger.warning(f"Failed to parse JSON from LLM response: {response}")
            logger.warning(f"JSON Error details: {str(json_error)}")
            
            # 🆕 CRITICAL FIX: Try to extract basic pet info even if JSON parsing fails
            # This handles cases where the response is valid but has formatting issues
            return self._fallback_text_extraction(response)
            
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            # Try fallback extraction for any other errors too
            return self._fallback_text_extraction(response)
    
    def _fallback_text_extraction(self, response: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """
        🆕 CRITICAL FIX: Fallback text extraction for when JSON parsing fails
        Extracts pet information from vet reports and other structured text
        """
        try:
            logger.info("🔧 FALLBACK: Attempting text-based extraction from failed JSON response")
            
            # Initialize extracted data
            extracted_data = {}
            comprehensive_data = {}
            
            # Convert response to lowercase for easier searching
            text = response.lower()
            
            # Extract basic pet information using text patterns
            
            # 1. Extract pet name (look for name patterns)
            name_patterns = [
                r"name[\"\':\s]*([a-zA-Z]+)",
                r"patient\s*name[\"\':\s]*([a-zA-Z]+)", 
                r"pet\s*name[\"\':\s]*([a-zA-Z]+)"
            ]
            for pattern in name_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    extracted_data["name"] = match.group(1).title()
                    break
            
            # 2. Extract breed
            breed_patterns = [
                r"breed[\"\':\s]*([a-zA-Z\s]+)",
                r"species\s*/\s*breed[\"\':\s]*dog\s*[—-]\s*([a-zA-Z\s]+)",
                r"labrador|golden retriever|german shepherd|beagle|bulldog|poodle|husky"
            ]
            for pattern in breed_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    breed = match.group(1) if match.lastindex else match.group(0)
                    extracted_data["breed"] = breed.title().strip()
                    break
            
            # 3. Extract age
            age_patterns = [
                r"age[\"\':\s]*(\d+)",
                r"(\d+)\s*years?\s*old",
                r"(\d+)\s*years?"
            ]
            for pattern in age_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    extracted_data["age"] = int(match.group(1))
                    break
            
            # 4. Extract weight
            weight_patterns = [
                r"weight[\"\':\s]*(\d+(?:\.\d+)?)\s*(?:lb|kg|pounds?|kilograms?)",
                r"(\d+(?:\.\d+)?)\s*lb",
                r"(\d+(?:\.\d+)?)\s*kg"
            ]
            for pattern in weight_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    extracted_data["weight"] = float(match.group(1))
                    break
            
            # 5. Extract gender and spay/neuter status
            if re.search(r"male.*neutered|neutered.*male", text, re.IGNORECASE):
                extracted_data["gender"] = "Male"
                extracted_data["spayed_neutered"] = True
            elif re.search(r"female.*spayed|spayed.*female", text, re.IGNORECASE):
                extracted_data["gender"] = "Female"
                extracted_data["spayed_neutered"] = True
            elif re.search(r"\bmale\b", text, re.IGNORECASE):
                extracted_data["gender"] = "Male"
            elif re.search(r"\bfemale\b", text, re.IGNORECASE):
                extracted_data["gender"] = "Female"
            
            # 6. Extract comprehensive medical data for vet reports
            comprehensive_data = self._extract_vet_report_data(response)
            
            logger.info(f"🔧 FALLBACK EXTRACTION: {len(extracted_data)} basic fields, {len(comprehensive_data)} comprehensive fields")
            return extracted_data, comprehensive_data
            
        except Exception as e:
            logger.error(f"❌ Fallback extraction failed: {e}")
            return {}, {}
    
    def _extract_vet_report_data(self, text: str) -> Dict[str, Any]:
        """Extract comprehensive veterinary report data from text"""
        try:
            comprehensive_data = {}
            text_lower = text.lower()
            
            # Extract clinic and vet information
            clinic_match = re.search(r"clinic[\"\':\s]*([a-zA-Z\s]+)", text_lower)
            if clinic_match:
                comprehensive_data["clinic"] = clinic_match.group(1).title().strip()
            
            vet_match = re.search(r"(?:examining\s*)?veterinarian[\"\':\s]*([^,\n]+)", text_lower)
            if vet_match:
                comprehensive_data["veterinarian"] = vet_match.group(1).title().strip()
            
            # Extract medical conditions and findings
            conditions = []
            condition_patterns = [
                r"otitis\s+externa",
                r"ear\s+infection",
                r"overweight",
                r"liver\s+enzyme\s+elevation",
                r"yeast\s+overgrowth"
            ]
            for pattern in condition_patterns:
                if re.search(pattern, text_lower):
                    conditions.append(pattern.replace(r"\s+", " "))
            
            if conditions:
                comprehensive_data["medical_conditions"] = ", ".join(conditions)
            
            # Extract medications and treatments
            medications = []
            if re.search(r"otic\s+suspension", text_lower):
                medications.append("Otic suspension (ear medication)")
            if re.search(r"flea.*tick.*heartworm", text_lower):
                medications.append("Monthly flea/tick and heartworm prevention")
            
            if medications:
                comprehensive_data["medications"] = ", ".join(medications)
            
            # Extract diet information
            diet_match = re.search(r"diet[\"\':\s]*([^.\n]+)", text_lower)
            if diet_match:
                comprehensive_data["diet"] = diet_match.group(1).strip()
            
            # Extract vaccination status
            vaccines = []
            if re.search(r"rabies.*current", text_lower):
                vaccines.append("Rabies (current)")
            if re.search(r"dhpp.*current", text_lower):
                vaccines.append("DHPP (current)")
            if re.search(r"bordetella", text_lower):
                vaccines.append("Bordetella")
            
            if vaccines:
                comprehensive_data["vaccinations"] = ", ".join(vaccines)
            
            # Extract exam findings
            findings = []
            if re.search(r"temperature.*(\d+(?:\.\d+)?)", text_lower):
                temp_match = re.search(r"temperature.*(\d+(?:\.\d+)?)", text_lower)
                if temp_match:
                    findings.append(f"Temperature: {temp_match.group(1)}°F")
            
            if re.search(r"heart\s+rate.*(\d+)", text_lower):
                hr_match = re.search(r"heart\s+rate.*(\d+)", text_lower)
                if hr_match:
                    findings.append(f"Heart rate: {hr_match.group(1)} bpm")
            
            if findings:
                comprehensive_data["exam_findings"] = ", ".join(findings)
            
            # Extract recommendations/plan
            if re.search(r"reduce.*food.*portion", text_lower):
                comprehensive_data["dietary_recommendations"] = "Reduce food portion by ~10%"
            
            if re.search(r"dental.*cleaning.*recommended", text_lower):
                comprehensive_data["dental_care"] = "Dental cleaning recommended within 12 months"
            
            logger.info(f"🏥 VET REPORT: Extracted {len(comprehensive_data)} medical data fields")
            return comprehensive_data
            
        except Exception as e:
            logger.error(f"❌ Vet report extraction failed: {e}")
            return {}
    
    def _is_vet_or_medical_content(self, text: str) -> bool:
        """Check if text contains veterinary or medical report content"""
        text_lower = text.lower()
        
        # Look for veterinary/medical indicators
        vet_indicators = [
            "veterinary", "vet report", "medical report", "clinic", "veterinarian", "dvm", 
            "examination", "exam", "diagnosis", "physical exam", "blood work", "lab results",
            "vaccination", "medication", "prescription", "treatment", "symptoms", 
            "temperature", "heart rate", "respiratory rate", "blood pressure",
            "otitis", "infection", "condition", "assessment", "prognosis", "follow-up",
            "patient name", "record id", "examining", "preventatives", "rabies", "dhpp"
        ]
        
        # Count how many indicators are present
        indicator_count = sum(1 for indicator in vet_indicators if indicator in text_lower)
        
        # If we have 3+ medical indicators, it's likely a vet report
        is_medical = indicator_count >= 3
        
        if is_medical:
            logger.info(f"🏥 MEDICAL CONTENT DETECTED: {indicator_count} medical indicators found")
        
        return is_medical
    
    def _clean_single_pet_data(self, pet_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and validate data for a single pet"""
        cleaned_data = {}
        
        for field, value in pet_data.items():
            if field in self.PET_FIELDS and value is not None:
                # Type validation and cleaning
                if field == "name" and isinstance(value, str) and len(value.strip()) > 1:
                    name = value.strip().title()
                    
                    # CRITICAL: Comprehensive validation to prevent invalid pet name extraction
                    invalid_names = self._get_comprehensive_invalid_names()
                    
                    # Check if name starts with title (indicates vet/person)
                    if any(name.startswith(title) for title in ["Dr. ", "Mr. ", "Mrs. ", "Prof"]):
                        logger.warning(f"🚫 BLOCKED: Attempted to create pet with vet/person name: {name}")
                        continue
                        
                    # TRIPLE-LAYER VALIDATION SYSTEM
                    # Layer 1: Smart linguistic validation
                    if not self._is_valid_pet_name(name):
                        logger.warning(f"🚫 BLOCKED: Invalid pet name pattern detected: {name}")
                        continue
                        
                    # Layer 2: Comprehensive invalid names list
                    if name in invalid_names or name.lower() in [n.lower() for n in invalid_names]:
                        logger.warning(f"🚫 BLOCKED: Name found in invalid names database: {name}")
                        continue
                        
                    # Layer 3: Advanced pattern detection
                    if self._contains_invalid_patterns(name):
                        logger.warning(f"🚫 BLOCKED: Invalid name pattern detected: {name}")
                        continue
                        
                    # Only accept validated pet names
                    logger.info(f"✅ VALIDATED: Accepting pet name: {name}")
                    cleaned_data[field] = name
                elif field == "age" and isinstance(value, (int, str)):
                    try:
                        age = int(value)
                        if 0 <= age <= 25:
                            cleaned_data[field] = age
                    except:
                        pass
                elif field == "weight" and isinstance(value, (int, float, str)):
                    try:
                        weight = float(value)
                        if 0 < weight <= 200:
                            cleaned_data[field] = weight
                    except:
                        pass
                elif field == "gender" and str(value).lower() in ["male", "female"]:
                    cleaned_data[field] = str(value).title()
                elif field == "breed" and isinstance(value, str) and len(value.strip()) > 1:
                    cleaned_data[field] = value.strip().title()
                elif field == "spayed_neutered" and isinstance(value, bool):
                    cleaned_data[field] = value
                elif field in ["known_allergies", "medical_conditions", "emergency_vet_name", "emergency_vet_phone", "microchip_id"]:
                    if isinstance(value, str) and len(value.strip()) > 0:
                        cleaned_data[field] = value.strip()
                elif field == "date_of_birth" and isinstance(value, str):
                    # Validate date format
                    try:
                        datetime.strptime(value, "%Y-%m-%d")
                        cleaned_data[field] = value
                    except:
                        pass
        
        return cleaned_data
    
    def _is_meaningful_value(self, value: Any) -> bool:
        """Check if a value is meaningful (not null, empty, or meaningless)"""
        return (value is not None and 
                value != "" and 
                value != "null" and
                str(value).strip() != "" and
                str(value).lower() not in ["none", "unknown", "not mentioned"])
    
    def _calculate_confidence(self, extracted_data: Dict[str, Any], original_message: str) -> float:
        """Calculate confidence score based on extraction quality"""
        if not extracted_data:
            return 0.0
        
        confidence = 0.0
        total_fields = len(extracted_data)
        
        # Base confidence from successful extraction
        confidence += 0.5
        
        # Bonus for high-value fields
        high_value_fields = ["name", "breed", "age"]
        for field in high_value_fields:
            if field in extracted_data:
                confidence += 0.15
        
        # Penalty for suspicious extractions
        message_lower = original_message.lower()
        for field, value in extracted_data.items():
            if field == "name":
                # Make sure the name actually appears in the message
                if str(value).lower() in message_lower:
                    confidence += 0.1
                else:
                    confidence -= 0.3  # Big penalty for incorrect names
        
        # Normalize confidence
        return min(1.0, max(0.0, confidence))
    
    def generate_follow_up_questions(self, extracted_data: Dict[str, Any], existing_pets: List[Dict] = None, extraction_result=None, question_tracker=None, user_id: int = None) -> List[str]:
        """Generate follow-up questions for all pets, prioritizing missing critical info (tracking handled by PetContextManager)"""
        questions = []
        
        # Collect all pets to ask about - handle new equal treatment structure
        all_pets = []
        
        # Check for new "all_pets" structure (equal treatment)
        if "all_pets" in extracted_data:
            all_pets = extracted_data["all_pets"]
        else:
            # Handle legacy structure
            if extracted_data.get("name"):
                primary_pet = {k: v for k, v in extracted_data.items() if k not in ["_additional_pets", "all_pets"]}
                all_pets.append(primary_pet)
            
            # Add legacy additional pets
            if "_additional_pets" in extracted_data:
                all_pets.extend(extracted_data["_additional_pets"])
        
        # If no pets extracted but we have existing pets, ask about them
        if not all_pets and existing_pets:
            all_pets = existing_pets[:2]  # Limit to 2 pets to avoid too many questions
        
        # Critical fields we always want
        critical_fields = ["age", "breed", "weight", "emergency_vet_name", "known_allergies"]
        
        # Generate questions for each pet
        for pet in all_pets:
            if len(questions) >= 2:  # Limit total questions to avoid overwhelming
                break
                
            pet_name = pet.get("name", "your dog")
            
            # Find existing pet data from database if available
            existing_pet_data = {}
            if existing_pets:
                for existing_pet in existing_pets:
                    if existing_pet.get("name", "").lower() == pet_name.lower():
                        existing_pet_data = existing_pet
                        break
            
            # Question templates for this pet
        question_map = {
            "age": f"How old is {pet_name}?",
            "breed": f"What breed is {pet_name}?", 
            "weight": f"What's {pet_name}'s weight?",
            "emergency_vet_name": f"Do you have a vet for {pet_name}?",
            "known_allergies": f"Does {pet_name} have any allergies?"
        }
        
            # Add questions for missing critical fields for this pet
        for field in critical_fields:
                # Check if field exists in current extraction OR in existing database data
                field_exists_in_extraction = field in pet
                field_exists_in_db = existing_pet_data.get(field) is not None
                
                # Also check comprehensive profile for some fields
                if field in ["color", "favorite_food"] and existing_pet_data.get("comprehensive_profile"):
                    field_exists_in_db = field_exists_in_db or existing_pet_data["comprehensive_profile"].get(field) is not None
                
                # Special handling for vet fields - check if ANY vet info was provided in current extraction
                if field == "emergency_vet_name" and extraction_result:
                    vet_info_provided = any([
                        extraction_result.extracted_fields.get("emergency_vet_name"),
                        extraction_result.extracted_fields.get("vet_name"), 
                        extraction_result.extracted_fields.get("emergency_vet_phone"),
                        extraction_result.extracted_fields.get("vet_phone")
                    ])
                    if vet_info_provided:
                        field_exists_in_extraction = True  # Don't ask about vet if any vet info was just provided
                
                # Only ask if field is missing from both extraction and database
                if not field_exists_in_extraction and not field_exists_in_db and len(questions) < 2:
                    # Note: Question tracking is handled in PetContextManager to avoid async complexity here
                    # This method just generates the questions, tracking happens at a higher level
                    questions.append(question_map[field])
                    break  # Only one question per pet to keep it manageable
        
        # If no specific questions, ask general questions
        if not questions and not all_pets:
            questions = [
                "What's your dog's name?",
                "What breed is your dog?"
            ]
        
        return questions
