"""
Health AI Prompts - Specialized prompts for health and medical functionality
Contains all health-related prompts and medical response templates
"""

from typing import Dict, Any, Optional

class HealthPrompts:
    """
    Centralized prompt management for health AI service
    """
    
    HEALTH_SYSTEM_PROMPT = """You are Dr. White, a specialized AI veterinary assistant with expertise in dog health and medical care. You provide professional, accurate, and compassionate health guidance for dogs.

Key principles:
1. ALWAYS prioritize the animal's safety and well-being
2. Provide clear, actionable medical guidance within appropriate scope
3. ALWAYS recommend veterinary consultation for serious conditions
4. Be empathetic and understanding of pet owners' concerns
5. Use medical knowledge responsibly - never diagnose, but guide toward proper care
6. Explain medical concepts in understandable terms
7. Consider emergency situations with appropriate urgency

IMPORTANT DISCLAIMERS:
- You provide guidance but cannot replace professional veterinary diagnosis
- For emergencies, always direct to immediate veterinary care
- Medication advice should always include veterinary consultation
- When in doubt, recommend professional evaluation

Remember: You're helping concerned pet parents make informed decisions about their dog's health and when to seek professional care."""

    EMERGENCY_SYSTEM_PROMPT = """🚨 EMERGENCY VETERINARY ASSISTANT MODE 🚨

You are Dr. White in EMERGENCY mode. A pet owner has described what appears to be an urgent veterinary situation.

EMERGENCY PROTOCOL:
1. IMMEDIATELY assess if this requires emergency veterinary care
2. Provide CLEAR, DIRECT instructions for immediate care if safe to do so
3. STRONGLY emphasize the need for immediate veterinary attention
4. Provide comfort and guidance while directing to professional care
5. Do NOT attempt to diagnose - focus on immediate safety and next steps

CRITICAL: Always prioritize getting the animal to professional veterinary care for any serious symptoms."""

    def get_health_intent_prompt(self, message: str) -> str:
        """Get prompt for health intent analysis"""
        return f"""Analyze this pet health message and classify the medical intent:

Message: "{message}"

Analyze and return JSON with:
{{
    "intent": "emergency|symptoms|behavioral|preventive|medication|nutrition|general_health",
    "is_emergency": true/false,
    "severity": "low|medium|high|critical",
    "confidence": 0.0-1.0,
    "keywords": ["key", "medical", "terms"],
    "requires_vet": true/false,
    "category": "emergency|acute_care|chronic_care|preventive|behavioral|nutritional",
    "urgency_level": "immediate|same_day|within_week|routine"
}}

Emergency indicators: bleeding, collapse, seizure, unconscious, severe pain, toxin ingestion, difficulty breathing, severe vomiting/diarrhea

Analysis:"""

    def build_health_response_prompt(
        self, 
        message: str, 
        context: Dict[str, Any], 
        analysis: Dict[str, Any]
    ) -> str:
        """Build comprehensive health response prompt"""
        pet_info = context.get("pet_information", {})
        medical_history = context.get("medical_history", [])
        recent_interactions = context.get("recent_interactions", [])
        medical_documents = context.get("medical_documents", "")
        
        prompt = f"""Patient Information:
Pet Name: {pet_info.get('name', 'Unknown')}
Breed: {pet_info.get('breed', 'Unknown')}
Age: {pet_info.get('age', 'Unknown')}
Weight: {pet_info.get('weight', 'Unknown')}

Medical History Summary:
{self._format_medical_history(medical_history)}

Recent Health Interactions:
{self._format_recent_interactions(recent_interactions)}

Medical Documents:
{medical_documents or "No medical documents provided"}

Current Health Query: "{message}"

Health Analysis: {analysis.get('intent', 'general_health')} (Severity: {analysis.get('severity', 'unknown')})

Please provide a comprehensive health response that:
1. Addresses the specific concern raised
2. Considers the pet's medical history and context
3. Provides actionable guidance appropriate for the severity level
4. Recommends appropriate next steps (home care, monitoring, or veterinary visit)
5. Explains any medical concepts in understandable terms
6. Includes relevant safety considerations

Response:"""
        
        return prompt

    def get_emergency_response_prompt(self, message: str, context: Dict[str, Any]) -> str:
        """Get prompt for emergency health situations"""
        pet_info = context.get("pet_information", {})
        
        return f"""🚨 EMERGENCY VETERINARY SITUATION 🚨

Pet Information:
- Name: {pet_info.get('name', 'Unknown')}
- Breed: {pet_info.get('breed', 'Unknown')}
- Age: {pet_info.get('age', 'Unknown')}
- Weight: {pet_info.get('weight', 'Unknown')}

EMERGENCY SITUATION: "{message}"

Provide IMMEDIATE guidance that includes:
1. FIRST: Clear assessment of urgency (immediate veterinary care needed?)
2. Immediate steps the owner can safely take RIGHT NOW
3. What to tell the emergency vet when calling
4. What NOT to do (common mistakes in emergencies)
5. How to safely transport if needed
6. What information to gather for the vet

Keep response focused, clear, and actionable. Lead with the most critical information.

EMERGENCY RESPONSE:"""

    def get_health_fallback_response(self, analysis: Dict[str, Any]) -> str:
        """Get fallback response for health service errors"""
        if analysis.get("is_emergency", False):
            return """I apologize, but I'm experiencing technical difficulties processing your urgent health question. 

🚨 Since this appears to be an urgent situation, please:
1. Contact your veterinarian immediately
2. Call an emergency animal hospital if your vet is unavailable
3. If it's after hours, look up the nearest 24-hour emergency vet clinic

Your pet's safety is the priority. Don't wait for technical issues to be resolved - seek professional veterinary care now."""
        
        severity = analysis.get("severity", "unknown")
        
        if severity in ["high", "medium"]:
            return """I apologize for the technical difficulty in processing your health question. Since this appears to involve your pet's health, I recommend:

1. Contact your veterinarian for proper medical guidance
2. Monitor your pet closely for any changes
3. Keep a record of symptoms, timing, and behaviors to share with your vet

For any concerns about your pet's health, professional veterinary advice is always the best approach."""
        
        return """I apologize for the technical issue. For any health-related questions about your pet, I always recommend consulting with your veterinarian who can provide personalized medical guidance based on a proper examination.

Feel free to try your question again, or contact your vet directly for immediate assistance."""

    def _format_medical_history(self, medical_history: list) -> str:
        """Format medical history for prompt"""
        if not medical_history:
            return "No medical history available"
        
        formatted = []
        for record in medical_history[:5]:  # Last 5 records
            date = record.get("date_occurred", "Unknown date")
            title = record.get("title", "Medical record")
            category = record.get("category", "general")
            description = record.get("description", "No details")
            
            formatted.append(f"• {date}: {title} ({category}) - {description[:100]}...")
        
        return "\n".join(formatted)

    def _format_recent_interactions(self, interactions: list) -> str:
        """Format recent health interactions for prompt"""
        if not interactions:
            return "No recent health interactions"
        
        formatted = []
        for interaction in interactions[:3]:  # Last 3 interactions
            timestamp = interaction.get("timestamp", "Unknown time")
            message = interaction.get("message", "No message")
            insights = interaction.get("insights", [])
            
            formatted.append(f"• {timestamp}: {message[:100]}... (Insights: {', '.join(insights)})")
        
        return "\n".join(formatted)

    def get_medication_guidance_prompt(self, medication: str, pet_info: Dict[str, Any]) -> str:
        """Get prompt for medication guidance"""
        return f"""Provide guidance about {medication} for dogs:

Pet Information:
- Breed: {pet_info.get('breed', 'Unknown')}
- Age: {pet_info.get('age', 'Unknown')}
- Weight: {pet_info.get('weight', 'Unknown')}

Please provide information about:
1. General safety considerations for {medication} in dogs
2. Common uses and indications
3. Important warnings or contraindications
4. Why veterinary consultation is essential for this medication
5. What questions to ask the veterinarian

ALWAYS emphasize that medication should only be given under veterinary supervision.

Guidance:"""

    def get_symptom_assessment_prompt(self, symptoms: str, duration: str, pet_info: Dict[str, Any]) -> str:
        """Get prompt for symptom assessment"""
        return f"""Assess these symptoms in a dog:

Symptoms: {symptoms}
Duration: {duration}

Pet Information:
- Breed: {pet_info.get('breed', 'Unknown')}
- Age: {pet_info.get('age', 'Unknown')}
- Weight: {pet_info.get('weight', 'Unknown')}

Provide assessment covering:
1. Possible significance of these symptoms
2. Warning signs that would require immediate veterinary care
3. What information to gather for the veterinarian
4. General monitoring guidelines
5. When to schedule a veterinary appointment

Assessment:"""

    def get_preventive_care_prompt(self, care_type: str, pet_info: Dict[str, Any]) -> str:
        """Get prompt for preventive care guidance"""
        return f"""Provide preventive care guidance about {care_type} for dogs:

Pet Information:
- Breed: {pet_info.get('breed', 'Unknown')}
- Age: {pet_info.get('age', 'Unknown')}
- Current Health Status: {pet_info.get('health_status', 'Unknown')}

Cover:
1. Importance of {care_type} for dogs
2. Recommended schedule/frequency
3. What to expect during {care_type}
4. Breed-specific considerations if applicable
5. Questions to discuss with veterinarian

Guidance:"""

    def get_nutritional_guidance_prompt(self, nutrition_question: str, pet_info: Dict[str, Any]) -> str:
        """Get prompt for nutritional guidance"""
        return f"""Provide nutritional guidance for this question: {nutrition_question}

Pet Information:
- Breed: {pet_info.get('breed', 'Unknown')}
- Age: {pet_info.get('age', 'Unknown')}
- Weight: {pet_info.get('weight', 'Unknown')}
- Activity Level: {pet_info.get('activity_level', 'Unknown')}

Address:
1. General nutritional principles for dogs
2. Breed and age-specific considerations
3. Safe vs. unsafe foods if relevant
4. When to consult with veterinarian about diet
5. Signs of nutritional issues to watch for

Nutritional Guidance:"""

    def get_behavioral_health_prompt(self, behavior_issue: str, pet_info: Dict[str, Any]) -> str:
        """Get prompt for behavioral health issues"""
        return f"""Address this behavioral health concern: {behavior_issue}

Pet Information:
- Breed: {pet_info.get('breed', 'Unknown')}
- Age: {pet_info.get('age', 'Unknown')}
- Medical History: {pet_info.get('medical_history_summary', 'No known issues')}

Consider:
1. Possible medical causes for this behavior
2. When behavioral changes warrant veterinary examination
3. How stress, pain, or illness can affect behavior
4. Recommended approach (veterinary check first, then behavior work)
5. Warning signs of medical issues presenting as behavioral problems

Behavioral Health Assessment:"""