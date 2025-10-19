"""
Food Recommendation Service - Detects food/diet related queries and provides Pawtree recommendations
Follows the same architecture pattern as DogContextService for consistency
"""

import logging
import re
import time
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class FoodRecommendationService:
    """
    Service for detecting food/diet related queries and generating Pawtree recommendations
    Uses pattern matching for fast, reliable detection
    """
    
    def __init__(self, redis_client=None):
        """Initialize the food recommendation service"""
        self.redis_client = redis_client
        self.cooldown_period = 300  
        
        # Primary food and nutrition keywords
        self.food_keywords = {
            'diet', 'food', 'meal', 'nutrition', 'feeding', 'treat', 'snack', 'treats',
            'kibble', 'raw', 'grain', 'protein', 'vitamins', 'supplements', 'supplement',
            'hungry', 'appetite', 'eating', 'feed', 'feeds', 'fed',
            'breakfast', 'dinner', 'lunch', 'portion', 'portions', 'serving',
            'recipe', 'recipes', 'ingredient', 'ingredients', 'nutritional',
            'pawtree', 'options', 'choices'
        }
        
        # Health-related food keywords
        
        self.health_food_keywords = {
            'weight', 'obesity', 'overweight', 'underweight', 'thin', 'fat',
            'allergies', 'allergy', 'sensitive', 'sensitivity', 'intolerance',
            'stomach', 'digestive', 'digestion', 'bland', 'upset',
            'skin', 'coat', 'energy', 'joint', 'joints', 'senior',
            'puppy', 'adult', 'age', 'aging', 'elderly'
        }
        
        # Specific food types and brands
        self.food_types = {
            'dry', 'wet', 'canned', 'freeze-dried', 'dehydrated',
            'organic', 'natural', 'holistic', 'premium', 'high-quality',
            'grain-free', 'gluten-free', 'limited-ingredient', 'single-protein',
            'chicken', 'beef', 'fish', 'salmon', 'lamb', 'turkey', 'duck',
            'vegetable', 'vegetables', 'fruit', 'fruits', 'carrot', 'sweet-potato'
        }
        
        # Explicit advice-seeking phrases (user must be actively seeking food recommendations)
        self.strong_advice_indicators = [
            'recommend', 'recommendation', 'recommendations', 'suggestion', 'suggest', 'advise', 'what should i feed', 'best food', 'which food',
            'food advice', 'nutrition advice', 'what food is good', 'food recommendation',
            'help me choose', 'what to feed', 'looking for food', 'need food suggestions',
            'can you suggest', 'please suggest', 'could you recommend', 'any recommendations',
            'food for my dogs', 'food for my dog', 'what food', 'which food brand',
            'pawtree food', 'pawtree recommendation', 'pawtree recommendations', 'food according to', 'food suggestions',
            'food options', 'food choices', 'tell me some', 'can you tell me some', 'give me some', 'give me',
            'foods items', 'food items', 'best for', 'good for', 'which will be best',
            # CRITICAL FIX: Add "tell me food" patterns for direct food requests
            'tell me food', 'tell me', 'show me food', 'show me', 'prepare', 'prepared', 'quick food', 'fast food'
        ]
        
        # Combine all keywords for comprehensive detection
        self.all_keywords = self.food_keywords.union(
            self.health_food_keywords,
            self.food_types
        )
    
    async def detect_food_query(self, message: str, user_id: int) -> Dict[str, Any]:
        """
        Detect if message is food/diet related and needs Pawtree recommendation
        
        Args:
            message: User's message
            user_id: User ID for context
            
        Returns:
            Dict with detection results and recommendation details
        """
        try:
            logger.info(f"🍽️ FOOD SERVICE CALLED: user_id={user_id}, message='{message[:50]}...'")  # ORCHESTRATOR DEBUG
            message_lower = message.lower()
            
            # Step 1: Fast keyword detection
            detected_keywords = [keyword for keyword in self.all_keywords 
                               if keyword in message_lower]
            
            # Step 1.5: Check for strong advice indicators separately (these are phrases, not single words)
            detected_advice_phrases = [phrase for phrase in self.strong_advice_indicators 
                                     if phrase in message_lower]
            
            has_food_keywords = len(detected_keywords) > 0
            has_advice_indicators = len(detected_advice_phrases) > 0
            
            # Debug logging
            logger.info(f"🍽️ FOOD DEBUG - Message: '{message_lower[:100]}...'")
            logger.info(f"🍽️ FOOD DEBUG - Keywords found: {detected_keywords}")
            logger.info(f"🍽️ FOOD DEBUG - Advice phrases found: {detected_advice_phrases}")
            logger.info(f"🍽️ FOOD DEBUG - Has keywords: {has_food_keywords}, Has advice: {has_advice_indicators}")
            
            if not has_food_keywords and not has_advice_indicators:
                return {
                    "is_food_related": False,
                    "confidence": 0.0,
                    "detected_keywords": [],
                    "recommendation_type": None,
                    "reasoning": "No food-related keywords or advice indicators detected"
                }
            
            # Step 2: Use the advice indicators we already detected
            has_strong_advice_indicators = has_advice_indicators
            
            # Step 3: Determine recommendation type based on keywords
            recommendation_type = self._determine_recommendation_type(detected_keywords)
            
            # Step 4: Calculate confidence based on multiple factors
            confidence = self._calculate_confidence(detected_keywords, has_strong_advice_indicators)
            
            # Recommend if user is explicitly seeking food advice (has advice phrases) with food context
            # OR if user has strong food advice phrases even without explicit food keywords
            is_food_related = (
                (has_strong_advice_indicators and len(detected_keywords) >= 1) or  # Has advice + food keywords
                (len(detected_advice_phrases) >= 2) or  # Has multiple strong advice phrases
                (len(detected_advice_phrases) >= 1 and len(detected_keywords) >= 1)  # Has any advice phrase + food keywords
            )
            
            # Combine detected keywords and advice phrases for return
            all_detected = detected_keywords + detected_advice_phrases
            
            result = {
                "is_food_related": is_food_related,
                "confidence": confidence,
                "detected_keywords": all_detected,
                "recommendation_type": recommendation_type,
                "reasoning": f"Detected {len(detected_keywords)} food keywords + {len(detected_advice_phrases)} advice phrases" + 
                           (f" with explicit advice request" if has_strong_advice_indicators else " (no explicit advice request)")
            }
            
            logger.info(f"🍽️ Food query analysis for user {user_id}: {result['reasoning']}")
            logger.info(f"🍽️ FOOD SERVICE RETURNING: is_food_related={result['is_food_related']}, confidence={result['confidence']}")  # ORCHESTRATOR DEBUG
            return result
            
        except Exception as e:
            logger.error(f"❌ Error detecting food query: {e}")
            return {
                "is_food_related": False,
                "confidence": 0.0,
                "detected_keywords": [],
                "recommendation_type": None,
                "reasoning": f"Error in detection: {str(e)}"
            }
    
    def _determine_recommendation_type(self, detected_keywords: List[str]) -> str:
        """Determine the type of recommendation based on detected keywords"""
        
        # Check for specific categories
        if any(kw in self.health_food_keywords for kw in detected_keywords):
            return "health_nutrition"
        elif any(kw in self.food_types for kw in detected_keywords):
            return "food_types"
        else:
            return "general_nutrition"
    
    def _calculate_confidence(self, detected_keywords: List[str], has_strong_advice_indicators: bool) -> float:
        """Calculate confidence score for food query detection"""
        
        base_confidence = min(0.6, len(detected_keywords) * 0.15)
        
        if has_strong_advice_indicators:
            base_confidence += 0.3
        
        # Boost confidence for health-related keywords
        if any(kw in self.health_food_keywords for kw in detected_keywords):
            base_confidence += 0.1
            
        return min(1.0, base_confidence)
    
    def generate_pawtree_recommendation_from_ai_response(self, ai_response: str, context: Dict[str, Any] = None) -> str:
        """
        Generate smart Pawtree links based on AI's actual food recommendations
        Parses the AI response to extract specific food brands/types and creates targeted Pawtree links
        
        Args:
            ai_response: The AI's response containing food recommendations
            context: Additional context for fallback recommendations
            
        Returns:
            Formatted Pawtree links for specific foods mentioned by AI
        """
        
        if not ai_response:
            return self.generate_pawtree_recommendation(context)
        
        # Extract specific food brands and types from AI response
        extracted_foods = self._extract_foods_from_ai_response(ai_response)
        
        if not extracted_foods:
            # Fallback to generic recommendations if no specific foods found
            return self.generate_pawtree_recommendation(context)
        
        # Create targeted Pawtree links for the foods AI recommended
        search_base_url = "https://pawtree.com/doglove/products/search?query="
        pawtree_links = []
        
        for food in extracted_foods[:8]:  # Increased limit to match extraction and include ingredients
            # Clean and format the food name for URL
            clean_food = food.replace(" ", "+").replace("'", "").replace("®", "")
            search_url = f"{search_base_url}{clean_food}"
            pawtree_links.append(f"🔗 [Find {food} on Pawtree]({search_url})")
        
        # Create the recommendation message
        intro = "💡 **Find these recommended foods on Pawtree:**"
        links_text = "\n".join(pawtree_links)
        
        # Add general link as well
        general_link = f"🔗 [Browse all Pawtree products](https://pawtree.com/doglove)"
        
        return f"{intro}\n{links_text}\n\n{general_link}"

    def generate_pawtree_recommendation(self, context: Dict[str, Any] = None) -> str:
        """
        Generate contextual Pawtree recommendation with clickable link (FALLBACK METHOD)
        Similar to how reminder links are formatted
        
        Args:
            context: Analysis context with detected keywords and recommendation type
            
        Returns:
            Formatted recommendation message with clickable link
        """
        
        if not context:
            context = {"recommendation_type": "general_nutrition", "detected_keywords": []}
        
        recommendation_type = context.get("recommendation_type", "general_nutrition")
        detected_keywords = context.get("detected_keywords", [])
        
        # Enhanced recommendation with specific products
        base_message = "💡 For premium nutrition tailored to your dog's needs, check out Pawtree!"
        
        # Add specific product recommendations based on context
        user_message = context.get("user_message", "")
        product_recommendations = self._get_product_recommendations(recommendation_type, detected_keywords, user_message)
        
        # Create main website link
        website_url = "https://pawtree.com/doglove"
        main_link = f"[Pawtree]({website_url})"
        
        # Build complete recommendation with products
        if product_recommendations:
            full_message = f"{base_message}\n\n**Recommended Products:**\n{product_recommendations}\n\n🔗 Visit {main_link} for more options!"
        else:
            full_message = f"{base_message} 🔗 {main_link}"
        
        return full_message
    
    def _get_product_recommendations(self, recommendation_type: str, detected_keywords: List[str], user_message: str = "") -> str:
        """Generate specific product recommendations with working search query links"""
        
        search_base_url = "https://pawtree.com/doglove/products/search?query="
        products = []
        
        # Extract specific food items mentioned by user
        specific_proteins = self._extract_specific_foods(user_message)
        
        # If user mentioned specific foods, prioritize those
        if specific_proteins:
            for protein in specific_proteins[:2]:  # Limit to 2 specific proteins
                products.append(f"• [{protein.title()} Formula]({search_base_url}{protein}) - As you mentioned, great protein choice")
            
            # Add one general recommendation
            if len(specific_proteins) < 3:
                products.append(f"• [Premium Dog Food]({search_base_url}premium+dog+food) - Complete balanced nutrition")
            
            return "\n".join(products[:3])
        
        
        # Create functional search links based on product types
        if recommendation_type == "health_nutrition":
            if any(kw in ["weight", "obesity", "overweight"] for kw in detected_keywords):
                products = [
                    f"• [Weight Management Formula]({search_base_url}weight+management) - Low-fat, high-protein formula",
                    f"• [Senior Lean Recipe]({search_base_url}senior+lean) - Perfect for weight control in older dogs"
                ]
            elif any(kw in ["allergies", "sensitive", "sensitivity"] for kw in detected_keywords):
                products = [
                    f"• [Limited Ingredient Formula]({search_base_url}limited+ingredient) - Single protein source",
                    f"• [Sensitive Stomach Formula]({search_base_url}sensitive+stomach) - Gentle on sensitive stomachs"
                ]
            elif any(kw in ["puppy", "young"] for kw in detected_keywords):
                products = [
                    f"• [Puppy Growth Formula]({search_base_url}puppy+growth) - Essential nutrients for development",
                    f"• [Small Breed Puppy]({search_base_url}small+breed+puppy) - Perfect kibble size for small mouths"
                ]
            elif any(kw in ["senior", "elderly", "old"] for kw in detected_keywords):
                products = [
                    f"• [Senior Support Formula]({search_base_url}senior+support) - Joint and cognitive support",
                    f"• [Senior Dog Food]({search_base_url}senior+dog+food) - Easy to digest for older dogs"
                ]
            else:
                products = [
                    f"• [Joint Support Formula]({search_base_url}joint+support) - Glucosamine and chondroitin",
                    f"• [Digestive Health]({search_base_url}digestive+health) - Probiotics and prebiotics"
                ]
        
        elif recommendation_type == "food_types":
            if any(kw in ["freeze-dried", "freeze", "dried"] for kw in detected_keywords):
                products = [
                    f"• [Freeze-Dried Treats]({search_base_url}freeze+dried) - Raw nutrition convenience",
                    f"• [Freeze-Dried Duck]({search_base_url}freeze+dried+duck) - High-protein training treats"
                ]
            elif any(kw in ["raw", "natural"] for kw in detected_keywords):
                products = [
                    f"• [Raw Blend Formula]({search_base_url}raw+blend) - Freeze-dried raw mixed with kibble",
                    f"• [Natural Dog Food]({search_base_url}natural+dog+food) - Minimally processed"
                ]
            elif any(kw in ["grain-free", "gluten-free"] for kw in detected_keywords):
                products = [
                    f"• [Grain-Free Formula]({search_base_url}grain+free) - Sweet potato and peas",
                    f"• [Grain-Free Salmon]({search_base_url}grain+free+salmon) - Novel protein source"
                ]
            else:
                products = [
                    f"• [Premium Dry Food]({search_base_url}premium+dry+food) - Balanced daily nutrition",
                    f"• [Wet Food Variety]({search_base_url}wet+food) - Multiple flavors"
                ]
        
        else:  # general_nutrition
            products = [
                f"• [Adult Dog Food]({search_base_url}adult+dog+food) - Complete balanced nutrition",
                f"• [Chicken Recipe]({search_base_url}chicken) - Classic, digestible formula",
                f"• [Training Treats]({search_base_url}training+treats) - High-value rewards for training"
            ]
        
        return "\n".join(products[:3])  # Limit to 3 products for conciseness
    
    def _extract_specific_foods(self, message: str) -> List[str]:
        """Extract specific protein/food items mentioned by the user"""
        if not message:
            return []
        
        message_lower = message.lower()
        
        # Common protein sources and food items
        food_items = [
            'chicken', 'beef', 'salmon', 'fish', 'turkey', 'duck', 'lamb', 
            'pork', 'venison', 'bison', 'rabbit', 'tuna', 'sardines',
            'rice', 'sweet potato', 'potato', 'pumpkin', 'carrots',
            'kibble', 'treats', 'wet food', 'dry food'
        ]
        
        found_foods = []
        for food in food_items:
            if food in message_lower:
                found_foods.append(food)
        
        return found_foods
    
    def _extract_foods_from_ai_response(self, ai_response: str) -> List[str]:
        """
        Extract specific food brands, formulas, and types mentioned in AI's response
        
        Args:
            ai_response: AI's response text containing food recommendations
            
        Returns:
            List of specific food items mentioned by the AI
        """
        if not ai_response:
            return []
        
        import re
        
        # COMPREHENSIVE FOOD TYPE PATTERNS - NO BRAND NAMES (Enhanced for better coverage)
        food_type_patterns = [
            # SPECIFIC INGREDIENTS AND FOODS (NEW - catch individual ingredients AI recommends)
            r"(boiled\s+chicken)",
            r"(cooked\s+chicken)",
            r"(plain\s+chicken)",
            r"(white\s+fish)",
            r"(lean\s+fish)",
            r"(salmon)",
            r"(sweet\s+potatoes?)",
            r"(carrots?)",
            r"(green\s+beans)",
            r"(plain.*yogurt)",
            r"(low[\-\s]fat\s+yogurt)",
            r"(steamed\s+vegetables)",
            r"(roasted\s+vegetables)",
            r"(lean\s+protein)",
            r"(complex\s+carbohydrates)",
            
            # COMPLETE COMBINATIONS - Life Stage + Size + Protein
            r"(senior\s+chicken\s+(?:and|&)\s+rice\s+(?:recipe|formula|food))",
            r"(senior\s+large\s+breed\s+(?:formula|food))",
            r"(small\s+breed\s+senior\s+(?:dog\s+)?food)",
            r"(grain[\-\s]free\s+salmon\s+(?:recipe|formula|food))",
            r"(grain[\-\s]free\s+whitefish\s+(?:recipe|formula|food))",
            r"(whitefish\s+(?:recipe|formula|food))",
            
            # SPECIAL: Handle "adjective + protein1 or protein2 + noun" patterns
            r"(grain[\-\s]free\s+salmon)(?:\s+(?:or|and)\s+[\w\s]+)?\s+(?:recipe|formula|food)",
            r"(grain[\-\s]free\s+whitefish)(?:\s+(?:or|and)\s+[\w\s]+)?\s+(?:recipe|formula|food)",
            
            # SPECIFIC PROTEIN COMBINATIONS
            r"(chicken\s+(?:and|&)\s+rice\s+(?:recipe|formula|food))",
            r"(salmon\s+(?:and|&)\s+sweet\s+potato\s+(?:recipe|formula|food))",
            r"(lamb\s+(?:and|&)\s+rice\s+(?:recipe|formula|food))",
            r"(turkey\s+(?:and|&)\s+oatmeal\s+(?:recipe|formula|food))",
            r"(beef\s+(?:and|&)\s+barley\s+(?:recipe|formula|food))",
            r"(duck\s+(?:and|&)\s+potato\s+(?:recipe|formula|food))",
            r"(salmon\s+(?:recipe|formula|food))",
            r"(whitefish\s+(?:recipe|formula|food))",
            
            # LIFE STAGE + SIZE COMBINATIONS
            r"(senior\s+large\s+breed\s+(?:formula|food))",
            r"(senior\s+small\s+breed\s+(?:formula|food))",
            r"(adult\s+large\s+breed\s+(?:formula|food))",
            r"(adult\s+small\s+breed\s+(?:formula|food))",
            r"(puppy\s+large\s+breed\s+(?:formula|food))",
            r"(puppy\s+small\s+breed\s+(?:formula|food))",
            
            # LIFE STAGE + DIETARY RESTRICTIONS
            r"(senior\s+grain[\-\s]free\s+(?:formula|food))",
            r"(adult\s+grain[\-\s]free\s+(?:formula|food))",
            r"(puppy\s+grain[\-\s]free\s+(?:formula|food))",
            
            # SIZE + DIETARY RESTRICTIONS
            r"(large\s+breed\s+grain[\-\s]free\s+(?:formula|food))",
            r"(small\s+breed\s+grain[\-\s]free\s+(?:formula|food))",
            
            # BASIC LIFE STAGE FORMULAS
            r"(senior\s+(?:dog\s+)?(?:formula|food))",
            r"(adult\s+(?:dog\s+)?(?:formula|food))",
            r"(puppy\s+(?:development|growth)?\s+(?:formula|food))",
            r"(mature\s+(?:dog\s+)?(?:formula|food))",
            
            # BASIC SIZE-SPECIFIC FOODS
            r"(large\s+breed\s+(?:formula|food))",
            r"(small\s+breed\s+(?:formula|food))",
            r"(giant\s+breed\s+(?:formula|food))",
            r"(toy\s+breed\s+(?:formula|food))",
            
            # HEALTH-SPECIFIC FORMULAS
            r"(weight\s+management\s+(?:formula|food))",
            r"(joint\s+support\s+(?:formula|food))",
            r"(sensitive\s+stomach\s+(?:formula|food))",
            r"(digestive\s+health\s+(?:formula|food))",
            r"(skin\s+(?:and|&)\s+coat\s+(?:formula|food))",
            r"(hip\s+(?:and|&)\s+joint\s+(?:formula|food))",
            
            # DIETARY RESTRICTION PATTERNS  
            r"(grain[\-\s]free\s+(?:formula|food))",
            r"(gluten[\-\s]free\s+(?:formula|food))",
            r"(limited\s+ingredient\s+(?:diet|formula|food))",
            r"(hypoallergenic\s+(?:formula|food))",
            r"(natural\s+(?:formula|food))",
            r"(organic\s+(?:formula|food))",
            
            # PROTEIN-SPECIFIC PATTERNS
            r"(high[\-\s]protein\s+(?:formula|food))",
            r"(single[\-\s]protein\s+(?:formula|food))",
            r"(novel\s+protein\s+(?:formula|food))",
            
            # GENERIC PATTERNS FOR BASIC FOODS
            r"((?:dog\s+)?food\s+with\s+[\w\s]+(?:and|&)[\w\s]+)",
            r"(senior\s+(?:dog\s+)?food)",
            r"(adult\s+(?:dog\s+)?food)",
            r"(puppy\s+(?:dog\s+)?food)",
            r"(premium\s+(?:dog\s+)?food)",
            r"(high[\-\s]quality\s+(?:dog\s+)?food)",
        ]
        
        extracted_foods = []
        
        # IMPROVED: Extract ALL matching patterns from the entire response
        # This handles responses with OR without bullet points
        
        all_matches = []
        
        # Search for all patterns in the entire response
        for pattern in food_type_patterns:
            matches = re.findall(pattern, ai_response.lower(), re.IGNORECASE)
            for match in matches:
                clean_match = match.strip()
                if len(clean_match) > 5:  # More lenient minimum length
                    all_matches.append(clean_match)
        
        # Remove duplicates and overlapping matches
        for food in all_matches:
            is_duplicate = False
            
            # Check if this food is already covered by a longer/better match
            for existing_food in extracted_foods:
                # If current food is subset of existing, skip it
                if food.lower() in existing_food.lower():
                    is_duplicate = True
                    break
                # If existing food is subset of current, replace it
                elif existing_food.lower() in food.lower():
                    extracted_foods.remove(existing_food)
                    break
            
            if not is_duplicate:
                # Capitalize properly for display
                clean_match = ' '.join(word.capitalize() for word in food.split())
                extracted_foods.append(clean_match)
        
        # If no specific brands found, look for generic food types
        if not extracted_foods:
            generic_patterns = [
                r"(senior\s+dog\s+food)",
                r"(adult\s+dog\s+food)", 
                r"(puppy\s+food)",
                r"(weight\s+management\s+food)",
                r"(joint\s+support\s+formula)",
                r"(sensitive\s+stomach\s+formula)",
                r"(grain[\-\s]free\s+food)",
                r"(high[\-\s]protein\s+food)",
                r"(limited\s+ingredient\s+diet)",
                r"(large\s+breed\s+food)",
                r"(small\s+breed\s+food)",
            ]
            
            for pattern in generic_patterns:
                matches = re.findall(pattern, ai_response.lower(), re.IGNORECASE)
                for match in matches:
                    clean_match = match.strip()
                    if clean_match not in extracted_foods:
                        # Capitalize properly for display
                        clean_match = ' '.join(word.capitalize() for word in clean_match.split())
                        extracted_foods.append(clean_match)
        
        # Remove duplicates and limit results
        unique_foods = []
        for food in extracted_foods:
            if food not in unique_foods:
                unique_foods.append(food)
        
        return unique_foods[:8]  # Increased limit to accommodate specific ingredients
    
    def _has_food_keywords(self, message: str) -> bool:
        """Quick check for food-related keywords"""
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in self.all_keywords)
    
    async def check_recommendation_cooldown(self, user_id: int, user_message: str = "") -> bool:
        """Check if user is in cooldown period for Pawtree recommendations"""
        # COOLDOWN DISABLED: Always allow recommendations
        logger.info(f"🔄 Cooldown disabled - allowing Pawtree recommendation for user {user_id}")
        return True
    
    async def set_recommendation_cooldown(self, user_id: int):
        """Set cooldown period after showing Pawtree recommendation"""
        if not self.redis_client:
            return
        
        try:
            cooldown_key = f"pawtree_cooldown:{user_id}"
            await self.redis_client.set(cooldown_key, str(time.time()), ex=self.cooldown_period)
            logger.info(f"🕐 Set Pawtree cooldown for user {user_id}")
        except Exception as e:
            logger.error(f"Error setting Pawtree cooldown: {e}")
    
    async def clear_recommendation_cooldown(self, user_id: int):
        """Clear cooldown period for testing purposes"""
        if not self.redis_client:
            return
        
        try:
            cooldown_key = f"pawtree_cooldown:{user_id}"
            await self.redis_client.delete(cooldown_key)
            logger.info(f"🧹 Cleared Pawtree cooldown for user {user_id}")
        except Exception as e:
            logger.error(f"Error clearing Pawtree cooldown: {e}")