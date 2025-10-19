#!/usr/bin/env python3
"""
Recurring Reminder Service
Handles AI-detected recurring patterns by creating multiple separate reminder instances
"""

import logging
from datetime import datetime, timedelta, time, date, timezone
from typing import List, Dict, Any, Optional, Tuple
from flask import current_app
from app import db
from app.models.health_models import HealthReminder, ReminderType, ReminderStatus, RecurrenceType
from app.models.user import User
from app.services.health_service import HealthService
import uuid
import re

logger = logging.getLogger(__name__)

class RecurringReminderService:
    """
    🎯 CONTEXT7 ENHANCEMENT: Advanced recurring reminder system
    
    Features:
    - Detects recurring patterns from natural language ("every 5 hours", "daily", etc.)
    - Creates multiple separate reminder instances
    - Asks clarification questions for missing parameters
    - Handles timezone-aware scheduling
    - Links related reminders in a series
    """
    
    def __init__(self):
        self.health_service = None
    
    def _get_health_service(self):
        """Lazy load health service to avoid circular imports"""
        if self.health_service is None:
            self.health_service = HealthService(db.session)
        return self.health_service
    
    def detect_recurring_pattern(self, message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        🎯 CONTEXT7: Detect recurring patterns in user messages using AI and regex
        """
        try:
            from app.utils.openai_helper import get_openai_response
            
            # AI-powered recurring pattern detection
            ai_prompt = f"""
            Analyze this message for recurring reminder patterns and extract details:
            
            Message: "{message}"
            User timezone: {user_context.get('timezone', 'UTC')}
            Current time: {user_context.get('current_local_time', 'Unknown')}
            
            Look for patterns like:
            - "every X hours/minutes" (e.g., "every 5 hours", "every 30 minutes")
            - "daily", "twice a day", "3 times a day"
            - "weekly", "monthly", "yearly"
            - "every morning/afternoon/evening"
            - "every Monday", "every weekend"
            - Specific intervals like "every 2 weeks", "every 3 months"
            
            Extract:
            1. Is this a recurring reminder request?
            2. What's the recurrence pattern?
            3. What's the interval/frequency?
            4. When should it start?
            5. Are there any end conditions mentioned?
            6. What missing information do we need to ask?
            
            Return JSON:
            {{
                "is_recurring": boolean,
                "confidence": 0.0-1.0,
                "pattern": "hourly/daily/weekly/monthly/yearly/custom",
                "interval": number (e.g., 5 for "every 5 hours"),
                "interval_unit": "minutes/hours/days/weeks/months/years",
                "start_time": "time if mentioned or null",
                "start_date": "date if mentioned or null", 
                "end_condition": "date/count/never",
                "end_value": "end date or max count",
                "missing_info": ["list of what we need to ask"],
                "suggested_questions": ["clarification questions to ask user"],
                "examples": ["example reminders that would be created"]
            }}
            """
            
            result = get_openai_response(ai_prompt, max_tokens=600, temperature=0.3)
            
            if result and result.get("response"):
                try:
                    import json
                    ai_analysis = json.loads(result["response"])
                    current_app.logger.info(f"🔄 AI recurring analysis: {ai_analysis}")
                    
                    # Enhance with regex-based validation
                    regex_analysis = self._regex_pattern_detection(message)
                    
                    # Combine AI and regex results
                    combined_analysis = self._combine_analyses(ai_analysis, regex_analysis, message)
                    
                    return combined_analysis
                    
                except json.JSONDecodeError as e:
                    current_app.logger.warning(f"Failed to parse AI recurring analysis: {str(e)}")
                    return self._regex_pattern_detection(message)
            
            return self._regex_pattern_detection(message)
            
        except Exception as e:
            current_app.logger.error(f"Error detecting recurring pattern: {str(e)}")
            return {"is_recurring": False, "confidence": 0.0}
    
    def _regex_pattern_detection(self, message: str) -> Dict[str, Any]:
        """
        Fallback regex-based recurring pattern detection
        """
        message_lower = message.lower()
        
        patterns = {
            # Hourly patterns
            r'every (\d+) hours?': ('hourly', 'hours'),
            r'every (\d+) hrs?': ('hourly', 'hours'),
            r'hourly': ('hourly', 'hours', 1),
            
            # Daily patterns
            r'every (\d+) days?': ('daily', 'days'),
            r'daily': ('daily', 'days', 1),
            r'every day': ('daily', 'days', 1),
            r'(\d+) times? a day': ('daily', 'times_per_day'),
            r'twice a day': ('daily', 'times_per_day', 2),
            r'three times a day': ('daily', 'times_per_day', 3),
            
            # Weekly patterns
            r'every (\d+) weeks?': ('weekly', 'weeks'),
            r'weekly': ('weekly', 'weeks', 1),
            r'every week': ('weekly', 'weeks', 1),
            
            # Monthly patterns
            r'every (\d+) months?': ('monthly', 'months'),
            r'monthly': ('monthly', 'months', 1),
            r'every month': ('monthly', 'months', 1),
            
            # Minute patterns
            r'every (\d+) minutes?': ('minutely', 'minutes'),
            r'every (\d+) mins?': ('minutely', 'minutes'),
        }
        
        for pattern, details in patterns.items():
            match = re.search(pattern, message_lower)
            if match:
                if len(details) == 3:  # Fixed interval
                    pattern_type, unit, interval = details
                else:  # Variable interval
                    pattern_type, unit = details
                    interval = int(match.group(1)) if match.groups() else 1
                
                return {
                    "is_recurring": True,
                    "confidence": 0.8,
                    "pattern": pattern_type,
                    "interval": interval,
                    "interval_unit": unit,
                    "start_time": None,
                    "start_date": None,
                    "end_condition": "never",
                    "end_value": None,
                    "missing_info": ["end_condition", "duration"],
                    "suggested_questions": [
                        f"When would you like to stop receiving these {pattern_type} reminders?",
                        "Should I create them for a specific duration (e.g., 1 week, 1 month) or until you tell me to stop?"
                    ],
                    "examples": [f"Reminder every {interval} {unit}"]
                }
        
        return {"is_recurring": False, "confidence": 0.0}
    
    def _combine_analyses(self, ai_analysis: Dict, regex_analysis: Dict, message: str) -> Dict[str, Any]:
        """
        Combine AI and regex analyses for best results
        """
        # If AI has high confidence, use it; otherwise use regex
        if ai_analysis.get("confidence", 0) > 0.7:
            return ai_analysis
        elif regex_analysis.get("is_recurring"):
            return regex_analysis
        else:
            return ai_analysis
    
    def generate_clarification_questions(self, recurring_pattern: Dict[str, Any], 
                                       original_message: str) -> Dict[str, Any]:
        """
        🎯 CONTEXT7: Generate clarification questions for missing recurring parameters
        """
        missing_info = recurring_pattern.get("missing_info", [])
        pattern = recurring_pattern.get("pattern", "")
        interval = recurring_pattern.get("interval", 1)
        interval_unit = recurring_pattern.get("interval_unit", "")
        
        questions = []
        
        if "end_condition" in missing_info or "duration" in missing_info:
            questions.append({
                "type": "end_condition",
                "question": f"When should I stop creating these {pattern} reminders?",
                "options": [
                    "After 1 week",
                    "After 1 month", 
                    "After a specific number of reminders",
                    "Until I tell you to stop",
                    "On a specific date"
                ],
                "required": True
            })
        
        if "start_time" in missing_info and not recurring_pattern.get("start_time"):
            questions.append({
                "type": "start_time", 
                "question": f"What time should the {pattern} reminders start?",
                "options": [
                    "9:00 AM",
                    "12:00 PM", 
                    "6:00 PM",
                    "Specify custom time"
                ],
                "required": True
            })
        
        if "start_date" in missing_info and not recurring_pattern.get("start_date"):
            questions.append({
                "type": "start_date",
                "question": "When should the first reminder be?",
                "options": [
                    "Today",
                    "Tomorrow",
                    "Next Monday",
                    "Specify custom date"
                ],
                "required": True
            })
        
        # Generate conversational response
        response = self._generate_clarification_response(recurring_pattern, questions, original_message)
        
        return {
            "needs_clarification": len(questions) > 0,
            "questions": questions,
            "response": response,
            "pattern_detected": recurring_pattern
        }
    
    def _generate_clarification_response(self, pattern: Dict, questions: List[Dict], message: str) -> str:
        """
        Generate a conversational clarification response
        """
        pattern_name = pattern.get("pattern", "recurring")
        interval = pattern.get("interval", 1)
        unit = pattern.get("interval_unit", "")
        
        if interval == 1:
            frequency_desc = f"{pattern_name}"
        else:
            frequency_desc = f"every {interval} {unit}"
        
        intro = f"I understand you want {frequency_desc} reminders for '{pattern.get('title', message)}'! "
        
        if len(questions) == 1:
            question = questions[0]
            if question["type"] == "end_condition":
                return f"{intro}To set this up properly, I need to know: {question['question']}\n\nPlease choose one of these options or tell me your preference:\n" + "\n".join([f"• {opt}" for opt in question['options']])
        else:
            return f"{intro}I need a few more details to set up your {frequency_desc} reminders:\n\n" + "\n\n".join([f"**{q['question']}**\nOptions: {', '.join(q['options'])}" for q in questions])
    
    def create_recurring_reminders(self, user_id: int, base_reminder_data: Dict[str, Any], 
                                 recurring_config: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        🎯 CONTEXT7: Create multiple reminder instances based on recurring configuration
        """
        try:
            current_app.logger.info(f"🔄 Creating recurring reminders for user {user_id}")
            
            # Generate series ID to link all reminders
            series_id = f"series_{user_id}_{int(datetime.utcnow().timestamp())}"
            
            # Calculate reminder schedule
            reminder_schedule = self._calculate_reminder_schedule(recurring_config, user_context)
            
            if not reminder_schedule:
                return {
                    "success": False,
                    "error": "Could not generate reminder schedule"
                }
            
            created_reminders = []
            health_service = self._get_health_service()
            
            for i, reminder_time in enumerate(reminder_schedule):
                try:
                    # Prepare individual reminder data
                    reminder_data = base_reminder_data.copy()
                    
                    # Update with scheduled time
                    reminder_data["due_date"] = reminder_time["due_datetime"]
                    reminder_data["title"] = f"{base_reminder_data.get('title', 'Reminder')} #{i+1}"
                    reminder_data["description"] = f"{base_reminder_data.get('description', '')} (Part of recurring series)"
                    
                    # Add series metadata
                    reminder_data["parent_series_id"] = series_id
                    reminder_data["is_recurring_instance"] = True
                    reminder_data["current_occurrence"] = i + 1
                    reminder_data["_timezone_metadata"] = reminder_time.get("timezone_metadata", {})
                    reminder_data["_timezone_metadata"]["series_id"] = series_id
                    reminder_data["_timezone_metadata"]["series_index"] = i + 1
                    reminder_data["_timezone_metadata"]["total_in_series"] = len(reminder_schedule)
                    
                    # Create the reminder
                    reminder = health_service.create_reminder(user_id, reminder_data)
                    
                    created_reminders.append({
                        "id": reminder.id,
                        "title": reminder.title,
                        "due_date": reminder.due_date.isoformat() if hasattr(reminder.due_date, 'isoformat') else str(reminder.due_date),
                        "occurrence": i + 1
                    })
                    
                    current_app.logger.info(f"✅ Created recurring reminder {reminder.id} (#{i+1})")
                    
                except Exception as e:
                    current_app.logger.error(f"Error creating reminder #{i+1}: {str(e)}")
                    continue
            
            result = {
                "success": True,
                "series_id": series_id,
                "total_created": len(created_reminders),
                "reminders": created_reminders,
                "pattern": recurring_config,
                "schedule_summary": {
                    "frequency": f"Every {recurring_config.get('interval', 1)} {recurring_config.get('interval_unit', '')}",
                    "start_date": reminder_schedule[0]["due_datetime"].date().isoformat() if reminder_schedule else None,
                    "end_date": reminder_schedule[-1]["due_datetime"].date().isoformat() if reminder_schedule else None,
                    "total_reminders": len(created_reminders)
                }
            }
            
            current_app.logger.info(f"🎉 Successfully created {len(created_reminders)} recurring reminders in series {series_id}")
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error creating recurring reminders: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to create recurring reminders: {str(e)}"
            }
    
    def _calculate_reminder_schedule(self, config: Dict[str, Any], user_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Calculate the schedule of reminder times based on configuration
        """
        try:
            schedule = []
            pattern = config.get("pattern", "")
            interval = config.get("interval", 1)
            interval_unit = config.get("interval_unit", "")
            start_time = config.get("start_time", "09:00")
            start_date = config.get("start_date", datetime.now().date().isoformat())
            end_condition = config.get("end_condition", "never")
            end_value = config.get("end_value")
            
            # Parse start datetime
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date() if isinstance(start_date, str) else start_date
            start_time_obj = datetime.strptime(start_time, "%H:%M").time() if isinstance(start_time, str) else start_time
            
            # Get user timezone
            user_timezone = user_context.get('timezone', 'UTC')
            timezone_obj = user_context.get('timezone_obj')
            
            current_datetime = datetime.combine(start_date_obj, start_time_obj)
            
            # Determine how many reminders to create
            max_reminders = self._calculate_max_reminders(end_condition, end_value, interval, interval_unit)
            
            for i in range(max_reminders):
                # Calculate timezone-aware datetime
                if timezone_obj:
                    local_datetime = timezone_obj.localize(current_datetime)
                    utc_datetime = local_datetime.astimezone(timezone.utc)
                else:
                    utc_datetime = current_datetime.replace(tzinfo=timezone.utc)
                    local_datetime = current_datetime
                
                schedule.append({
                    "due_datetime": utc_datetime,
                    "local_datetime": local_datetime,
                    "occurrence": i + 1,
                    "timezone_metadata": {
                        "user_timezone": user_timezone,
                        "original_local_time": local_datetime.isoformat(),
                        "storage_utc_time": utc_datetime.isoformat(),
                        "timezone_aware_creation": True,
                        "recurring_series": True
                    }
                })
                
                # Calculate next occurrence
                current_datetime = self._calculate_next_occurrence(
                    current_datetime, interval, interval_unit
                )
                
                # Check end conditions
                if end_condition == "date" and end_value:
                    end_date = datetime.strptime(end_value, "%Y-%m-%d").date()
                    if current_datetime.date() > end_date:
                        break
            
            current_app.logger.info(f"📅 Generated schedule with {len(schedule)} reminders")
            return schedule
            
        except Exception as e:
            current_app.logger.error(f"Error calculating reminder schedule: {str(e)}")
            return []
    
    def _calculate_max_reminders(self, end_condition: str, end_value: Any, 
                               interval: int, interval_unit: str) -> int:
        """
        Calculate maximum number of reminders based on end condition
        """
        if end_condition == "count" and end_value:
            return min(int(end_value), 100)  # Cap at 100 reminders
        elif end_condition == "date" and end_value:
            # Calculate based on date range
            try:
                end_date = datetime.strptime(end_value, "%Y-%m-%d").date()
                start_date = datetime.now().date()
                days_diff = (end_date - start_date).days
                
                if interval_unit == "days":
                    return min(days_diff // interval, 100)
                elif interval_unit == "hours":
                    return min((days_diff * 24) // interval, 100)
                elif interval_unit == "weeks":
                    return min(days_diff // (interval * 7), 100)
                elif interval_unit == "months":
                    return min(days_diff // (interval * 30), 100)  # Approximate
                else:
                    return 30  # Default
            except:
                return 30
        else:
            # Default limits based on interval
            if interval_unit == "minutes":
                return min(24 * 60 // interval, 50)  # Max 1 day worth or 50
            elif interval_unit == "hours":
                return min(24 * 7 // interval, 50)  # Max 1 week worth or 50  
            elif interval_unit == "days":
                return min(30 // interval, 30)  # Max 1 month worth or 30
            else:
                return 30  # Default
    
    def _calculate_next_occurrence(self, current_dt: datetime, interval: int, unit: str) -> datetime:
        """
        Calculate the next occurrence time
        """
        if unit == "minutes":
            return current_dt + timedelta(minutes=interval)
        elif unit == "hours":
            return current_dt + timedelta(hours=interval)
        elif unit == "days":
            return current_dt + timedelta(days=interval)
        elif unit == "weeks":
            return current_dt + timedelta(weeks=interval)
        elif unit == "months":
            # Approximate monthly calculation
            return current_dt + timedelta(days=interval * 30)
        else:
            return current_dt + timedelta(hours=interval)  # Default to hours


# Global service instance
_recurring_service_instance = None

def get_recurring_reminder_service() -> RecurringReminderService:
    """Get the global recurring reminder service instance"""
    global _recurring_service_instance
    if _recurring_service_instance is None:
        _recurring_service_instance = RecurringReminderService()
    return _recurring_service_instance 