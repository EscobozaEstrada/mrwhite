"""
Reminder Prompts - Specialized prompts for reminder and scheduling functionality
Contains all reminder-related prompts and scheduling templates
"""

from typing import Dict, Any, Optional

class ReminderPrompts:
    """
    Centralized prompt management for reminder service
    """
    
    REMINDER_SYSTEM_PROMPT = """You are Dr. White's Reminder Assistant, specialized in helping pet owners manage their dog's care schedule and reminders.

Key capabilities:
1. Create, manage, and schedule pet care reminders
2. Understand natural language time expressions and convert to structured data
3. Suggest optimal care schedules based on pet age, breed, and health needs
4. Provide intelligent reminder frequency recommendations
5. Help users stay organized with their pet's healthcare, grooming, training, and daily care
6. Generate friendly, helpful responses about reminder management

Always focus on:
- Pet health and safety as top priority
- Clear, actionable reminder information
- User-friendly scheduling that fits their lifestyle
- Gentle reminders that encourage consistent pet care
- Helpful suggestions for comprehensive pet care scheduling

Remember: Consistent care is the key to a healthy, happy dog!"""

    def get_reminder_intent_prompt(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Get prompt for reminder intent analysis"""
        context_info = ""
        if context:
            context_info = f"\nUser Context: {context}"
        
        return f"""Analyze this message about pet care reminders:

Message: "{message}"{context_info}

Determine the user's intent and return JSON:
{{
    "intent": "create_reminder|list_reminders|update_reminder|delete_reminder|schedule_smart|reminder_guidance",
    "confidence": 0.0-1.0,
    "reminder_type": "vaccination|checkup|medication|grooming|dental|exercise|training|nutrition|flea_tick|heartworm|custom",
    "urgency": "low|medium|high|critical",
    "has_specific_date": true/false,
    "has_specific_time": true/false,
    "mentions_frequency": true/false,
    "action_needed": "immediate|scheduled|informational"
}}

Intent categories:
- create_reminder: User wants to set up a new reminder
- list_reminders: User wants to see existing reminders
- update_reminder: User wants to modify an existing reminder
- delete_reminder: User wants to cancel/remove a reminder
- schedule_smart: User wants AI to create a comprehensive care schedule
- reminder_guidance: User needs help understanding reminder options

Analysis:"""

    def get_detail_extraction_prompt(
        self, 
        message: str, 
        analysis: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Get prompt for extracting detailed reminder information"""
        intent = analysis.get("intent", "create_reminder")
        reminder_type = analysis.get("reminder_type", "custom")
        
        from datetime import datetime
        # Use local time since we're working with naive datetimes throughout the system
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_day = datetime.now().strftime("%A")
        
        return f"""Extract detailed reminder information from this message:

Message: "{message}"
Intent: {intent}
Reminder Type: {reminder_type}
Context: {context or "None"}

IMPORTANT: Today is {current_date} ({current_day}). Use this for calculating dates.

Extract and return JSON with:
{{
    "title": "Brief, clear reminder title",
    "description": "Detailed description of what needs to be done",
    "reminder_type": "{reminder_type}",
    "due_date": "YYYY-MM-DD or relative date (tomorrow, next week, etc.) or null",
    "time_of_day": "HH:MM AM/PM or null",
    "frequency": "once|daily|weekly|monthly|quarterly|annual|custom",
    "advance_notice_days": 1-30,
    "priority": "low|medium|high|critical",
    "notes": "Additional notes or special instructions",
    "recurring_pattern": "If frequency is custom, describe the pattern"
}}

Guidelines:
- Extract specific dates/times mentioned
- For "today", use {current_date}
- For "tomorrow", use the next day after {current_date}
- Convert times like "11.25 PM" to "11:25 PM"
- Infer reasonable defaults for missing information
- Use clear, actionable titles
- Set appropriate advance notice based on reminder type
- Higher priority for health-related reminders

Extracted Details:"""

    def get_smart_schedule_prompt(self, pet_info: Dict[str, Any], details: Dict[str, Any]) -> str:
        """Get prompt for generating smart schedule plans"""
        return f"""Create a comprehensive pet care reminder schedule:

Pet Information:
- Name: {pet_info.get('pet_name', 'Unknown')}
- Breed: {pet_info.get('pet_breed', 'Unknown')}
- Age: {pet_info.get('pet_age', 'Unknown')}
- Weight: {pet_info.get('pet_weight', 'Unknown')}
- Recent Care: {pet_info.get('recent_care_categories', [])}

User Request: {details.get('description', 'Create a complete care schedule')}

Generate a smart schedule with JSON format:
{{
    "plan_type": "comprehensive|basic|focused",
    "timeframe": "6_months|1_year|ongoing",
    "reminders": [
        {{
            "title": "Clear reminder title",
            "reminder_type": "vaccination|checkup|medication|grooming|dental|exercise|training|nutrition|flea_tick|heartworm",
            "due_date": "YYYY-MM-DD",
            "frequency": "once|daily|weekly|monthly|quarterly|annual",
            "advance_notice_days": 1-30,
            "priority": "low|medium|high|critical",
            "description": "Detailed description and instructions",
            "notes": "Special considerations or tips"
        }}
    ],
    "recommendations": [
        "General care tips and suggestions"
    ],
    "schedule_notes": "Important information about following this schedule"
}}

Consider:
- Pet's age and breed-specific needs
- Current health status and history
- Seasonal care requirements
- Preventive care best practices
- Realistic frequency that owners can maintain

Smart Schedule:"""

    def get_response_generation_prompt(
        self, 
        result: Dict[str, Any], 
        analysis: Dict[str, Any], 
        original_message: str,
        frontend_url: str = None
    ) -> str:
        """Get prompt for generating conversational responses with frontend links"""
        action = result.get("action", "unknown")
        intent = analysis.get("intent", "unknown")
        
        frontend_context = ""
        if frontend_url:
            frontend_context = f"\nReminder Management URL: {frontend_url}/reminders"
        
        return f"""Generate a friendly, helpful response for this reminder action:

Original Message: "{original_message}"
User Intent: {intent}
Action Performed: {action}
Result: {result}{frontend_context}

Create a response that:
1. Acknowledges what the user requested
2. Confirms what was accomplished
3. Provides relevant next steps or suggestions
4. Uses a professional, supportive tone
5. Includes helpful tips when appropriate
6. Keeps it conversational but informative
7. If applicable, mention that users can view/manage all reminders via the reminders page

Make the response personal and encouraging about pet care consistency.

Response:"""

    def get_guidance_prompt(self, message: str, analysis: Dict[str, Any]) -> str:
        """Get prompt for providing reminder guidance"""
        return f"""Provide helpful guidance about pet care reminders:

User Message: "{message}"
Analysis: {analysis}

Provide comprehensive guidance covering:
1. Types of reminders that would be helpful for pet care
2. Recommended frequencies for different care activities
3. How to set up effective reminder schedules
4. Tips for staying consistent with pet care
5. Common reminders that pet owners forget
6. Seasonal care reminders to consider

Focus on being helpful and educational while encouraging good pet care habits.

Guidance:"""

    def get_reminder_type_explanation_prompt(self, reminder_type: str) -> str:
        """Get prompt explaining specific reminder types"""
        return f"""Explain the '{reminder_type}' reminder type for pet care:

Provide information about:
1. What this reminder type involves
2. Recommended frequency and timing
3. Why this care is important for dogs
4. What to expect during this care activity
5. How to prepare or what to bring
6. Signs that might indicate this care is needed sooner
7. Breed or age-specific considerations

Keep the explanation practical and encouraging.

Explanation for {reminder_type} reminders:"""

    def get_overdue_reminder_prompt(self, overdue_reminders: list) -> str:
        """Get prompt for handling overdue reminders"""
        return f"""Help the user address these overdue pet care reminders:

Overdue Reminders:
{self._format_reminder_list(overdue_reminders)}

Provide a caring response that:
1. Gently acknowledges the overdue items without judgment
2. Helps prioritize which ones need immediate attention
3. Suggests practical steps to catch up
4. Offers to reschedule or adjust the reminder schedule
5. Provides encouragement and support
6. Includes tips for staying on track going forward

Be supportive and focus on getting back on track with pet care.

Response:"""

    def get_schedule_optimization_prompt(self, current_reminders: list, pet_info: Dict[str, Any]) -> str:
        """Get prompt for optimizing reminder schedules"""
        return f"""Analyze and optimize this pet care reminder schedule:

Current Reminders:
{self._format_reminder_list(current_reminders)}

Pet Information:
{pet_info}

Provide optimization suggestions:
1. Identify scheduling conflicts or overlaps
2. Suggest better timing or frequency adjustments
3. Recommend additional reminders that might be missing
4. Propose ways to group related care activities
5. Consider seasonal adjustments needed
6. Suggest priority levels for different reminders

Focus on creating a practical, manageable schedule that ensures comprehensive pet care.

Optimization Recommendations:"""

    def get_seasonal_reminder_prompt(self, season: str, pet_info: Dict[str, Any]) -> str:
        """Get prompt for seasonal reminder suggestions"""
        return f"""Suggest seasonal pet care reminders for {season}:

Pet Information: {pet_info}

Provide seasonal care guidance including:
1. Season-specific health concerns to watch for
2. Preventive care that's important during this season
3. Environmental hazards or considerations
4. Grooming needs that change seasonally
5. Exercise and activity adjustments
6. Specific reminders to set for this season

Make suggestions practical and specific to the season and pet characteristics.

{season} Pet Care Reminders:"""

    def get_emergency_reminder_prompt(self, emergency_type: str, context: Dict[str, Any]) -> str:
        """Get prompt for emergency-related reminders"""
        return f"""Create urgent reminders for this pet emergency situation:

Emergency Type: {emergency_type}
Context: {context}

Provide immediate and follow-up reminders including:
1. Immediate actions needed right now
2. Follow-up appointments or monitoring needed
3. Medication schedules if prescribed
4. Warning signs to watch for
5. When to contact the vet again
6. Recovery care reminders

Focus on ensuring proper follow-through after emergency care.

Emergency Reminders:"""

    def _format_reminder_list(self, reminders: list) -> str:
        """Format reminder list for prompts"""
        if not reminders:
            return "No reminders provided"
        
        formatted = []
        for reminder in reminders:
            title = reminder.get("title", "Untitled")
            due_date = reminder.get("due_date", "No date set")
            reminder_type = reminder.get("reminder_type", "custom")
            priority = reminder.get("priority", "medium")
            
            formatted.append(f"- {title} ({reminder_type}) - Due: {due_date} - Priority: {priority}")
        
        return "\n".join(formatted)

    def get_frequency_explanation_prompt(self, frequency: str) -> str:
        """Get prompt explaining reminder frequencies"""
        return f"""Explain the '{frequency}' reminder frequency for pet care:

Provide clear information about:
1. What '{frequency}' means in practical terms
2. Examples of care activities that work well with this frequency
3. How to maintain consistency with {frequency} reminders
4. Tips for adjusting if the frequency doesn't work well
5. When this frequency is most appropriate

Keep the explanation helpful and practical for pet owners.

Frequency Explanation:"""

    def get_reminder_modification_prompt(self, current_reminder: Dict[str, Any], requested_changes: str) -> str:
        """Get prompt for modifying existing reminders"""
        return f"""Help modify this existing reminder:

Current Reminder:
- Title: {current_reminder.get('title', 'Unknown')}
- Type: {current_reminder.get('reminder_type', 'custom')}
- Due Date: {current_reminder.get('due_date', 'Not set')}
- Frequency: {current_reminder.get('frequency', 'once')}
- Priority: {current_reminder.get('priority', 'medium')}

Requested Changes: "{requested_changes}"

Determine what changes to make and return JSON:
{{
    "modifications": {{
        "title": "new title if changed",
        "due_date": "new date if changed",
        "frequency": "new frequency if changed",
        "priority": "new priority if changed (low|medium|high|critical)",
        "advance_notice_days": "new advance notice if changed"
    }},
    "explanation": "Brief explanation of the changes made",
    "suggestions": ["Any additional suggestions for this reminder"]
}}

Modification Analysis:"""