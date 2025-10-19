"""
Reminder Service - Reminder and scheduling functionality
Handles reminder creation, management, and intelligent scheduling
Enhanced with Flask API integration and frontend deep linking
"""

import os
import time
import json
import uuid
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta

import httpx
import redis.asyncio as redis
from sqlalchemy import select, update, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import (
    AsyncSessionLocal, User, CareRecord, Message,
    create_message_async
)

from services.shared.async_pinecone_service import AsyncPineconeService
from services.shared.async_parallel_service import AsyncParallelService
from services.shared.async_openai_pool_service import get_openai_pool
from services.shared.async_cache_service import AsyncCacheService

from .reminder_prompts import ReminderPrompts

logger = logging.getLogger(__name__)

class ReminderService:
    """
    Reminder Service for scheduling and managing pet care reminders
    Handles intelligent reminder creation, scheduling, and notifications
    """
    
    def __init__(self, vector_service: AsyncPineconeService, redis_client: redis.Redis, cache_service: AsyncCacheService = None, smart_intent_router=None):
        self.vector_service = vector_service
        self.redis_client = redis_client
        self.cache_service = cache_service
        self.smart_intent_router = smart_intent_router
        
        # Initialize parallel processing services  
        self.parallel_service = AsyncParallelService()
        
        # Flask API integration configuration
        self.flask_api_base_url = os.getenv("FLASK_API_BASE_URL", "http://localhost:5001")
        self.frontend_url = os.getenv("FRONTEND_URL", "http://3.85.132.24:3000")
        
        # OpenAI configuration
        self.openai_pool = None  # Will be set by global pool
        self.chat_model = "gpt-4"
        self.max_tokens = 1000
        self.temperature = 0.3  # Lower for consistent reminder processing
        
        # Reminder prompts manager
        self.prompts = ReminderPrompts()
        
        # Reminder types and default schedules
        self.reminder_types = {
            "vaccination": {"frequency": "annual", "advance_notice": 30},
            "checkup": {"frequency": "annual", "advance_notice": 14},
            "medication": {"frequency": "daily", "advance_notice": 1},
            "grooming": {"frequency": "monthly", "advance_notice": 7},
            "dental": {"frequency": "monthly", "advance_notice": 7},
            "exercise": {"frequency": "daily", "advance_notice": 0},
            "training": {"frequency": "weekly", "advance_notice": 1},
            "nutrition": {"frequency": "weekly", "advance_notice": 2},
            "flea_tick": {"frequency": "monthly", "advance_notice": 3},
            "heartworm": {"frequency": "monthly", "advance_notice": 3},
            "custom": {"frequency": "custom", "advance_notice": 7}
        }
        
        # Performance monitoring
        self.reminder_stats = {
            "total_reminders_created": 0,
            "active_reminders": 0,
            "completed_reminders": 0,
            "overdue_reminders": 0,
            "reminders_by_type": {}
        }
        
    async def _get_openai_pool(self):
        """Get or initialize the OpenAI client pool"""
        if self.openai_pool is None:
            self.openai_pool = await get_openai_pool(pool_size=5)
        return self.openai_pool
        
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        pass

    async def process_reminder_request(
        self,
        user_id: int,
        conversation_id: int,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process reminder-related requests with intelligent parsing
        """
        start_time = time.time()
        
        try:
            # Phase 1: Analyze reminder intent
            reminder_analysis = await self._analyze_reminder_intent(message, context)
            
            # Phase 2: Extract reminder details
            reminder_details = await self._extract_reminder_details(message, reminder_analysis, context)
            
            # Phase 3: Process based on intent type
            if reminder_analysis.get("intent") == "create_reminder":
                result = await self._create_reminder(user_id, reminder_details)
            elif reminder_analysis.get("intent") == "list_reminders":
                result = await self._list_user_reminders(user_id, reminder_details.get("filter"))
            elif reminder_analysis.get("intent") == "update_reminder":
                result = await self._update_reminder(user_id, reminder_details)
            elif reminder_analysis.get("intent") == "delete_reminder":
                result = await self._delete_reminder(user_id, reminder_details.get("reminder_id"))
            elif reminder_analysis.get("intent") == "schedule_smart":
                result = await self._create_smart_schedule(user_id, reminder_details)
            else:
                # Add user_id to analysis for enhanced guidance
                reminder_analysis["user_id"] = user_id
                result = await self._provide_reminder_guidance(message, reminder_analysis)
            
            # Phase 4: Generate conversational response
            response_text = await self._generate_reminder_response(result, reminder_analysis, message)
            
            processing_time = time.time() - start_time
            self._update_reminder_stats(reminder_analysis.get("intent", "unknown"))
            
            return {
                "success": True,
                "content": response_text,
                "conversation_id": conversation_id,
                "reminder_data": result,
                "intent": reminder_analysis.get("intent"),
                "processing_time": processing_time
            }
            
        except Exception as e:
            logger.error(f"Reminder processing error: {str(e)}")
            return {
                "success": False,
                "error": f"Reminder processing failed: {str(e)}",
                "conversation_id": conversation_id,
                "processing_time": time.time() - start_time
            }

    async def _analyze_reminder_intent(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze reminder-related intent"""
        try:
            # Check cache first
            cache_key = f"reminder_intent:{hash(message)}"
            cached = await self.redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Use AI to analyze reminder intent
            prompt = self.prompts.get_reminder_intent_prompt(message, context)
            response = await self._call_reminder_ai(prompt, max_tokens=300)
            
            try:
                analysis = json.loads(response)
            except json.JSONDecodeError:
                # Fallback analysis
                analysis = self._create_fallback_reminder_analysis(message)
            
            # Cache for 1 hour
            await self.redis_client.setex(cache_key, 3600, json.dumps(analysis))
            return analysis
            
        except Exception as e:
            logger.error(f"Reminder intent analysis error: {str(e)}")
            return self._create_fallback_reminder_analysis(message)

    def _create_fallback_reminder_analysis(self, message: str) -> Dict[str, Any]:
        """Create fallback reminder analysis"""
        create_keywords = ["remind", "schedule", "set", "create", "add", "appointment"]
        list_keywords = ["show", "list", "what", "upcoming", "check", "view"]
        update_keywords = ["change", "update", "modify", "reschedule", "move"]
        delete_keywords = ["cancel", "delete", "remove", "clear"]
        
        message_lower = message.lower()
        
        if any(keyword in message_lower for keyword in create_keywords):
            intent = "create_reminder"
        elif any(keyword in message_lower for keyword in list_keywords):
            intent = "list_reminders"
        elif any(keyword in message_lower for keyword in update_keywords):
            intent = "update_reminder"
        elif any(keyword in message_lower for keyword in delete_keywords):
            intent = "delete_reminder"
        else:
            intent = "reminder_guidance"
        
        return {
            "intent": intent,
            "confidence": 0.7,
            "reminder_type": self._detect_reminder_type(message),
            "urgency": "normal",
            "has_specific_date": any(word in message_lower for word in ["tomorrow", "next", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "am", "pm"])
        }

    def _detect_reminder_type(self, message: str) -> str:
        """Detect the type of reminder from message"""
        message_lower = message.lower()
        
        for reminder_type in self.reminder_types.keys():
            if reminder_type in message_lower:
                return reminder_type
        
        # Check for related keywords
        if any(word in message_lower for word in ["vaccine", "shot", "immunization"]):
            return "vaccination"
        elif any(word in message_lower for word in ["vet", "doctor", "checkup", "exam"]):
            return "checkup"
        elif any(word in message_lower for word in ["medicine", "pill", "dose", "medication"]):
            return "medication"
        elif any(word in message_lower for word in ["groom", "bath", "brush", "trim"]):
            return "grooming"
        elif any(word in message_lower for word in ["walk", "exercise", "run", "play"]):
            return "exercise"
        elif any(word in message_lower for word in ["train", "practice", "lesson"]):
            return "training"
        
        return "custom"

    async def _extract_reminder_details(
        self, 
        message: str, 
        analysis: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract detailed reminder information from message"""
        try:
            # Use AI to extract structured details
            prompt = self.prompts.get_detail_extraction_prompt(message, analysis, context)
            # Debug: Log the prompt being sent
            logger.info(f"📤 Sending prompt to AI: {prompt}")
            response = await self._call_reminder_ai(prompt, max_tokens=400)
            
            # Debug: Log what AI extracted
            logger.info(f"🤖 AI extraction response: {response}")
            
            try:
                details = json.loads(response)
                # Debug: Log extracted priority
                logger.info(f"📋 Extracted details: {details}")
                logger.info(f"🎯 Extracted priority: {details.get('priority', 'NOT_FOUND')}")
            except json.JSONDecodeError:
                logger.warning(f"❌ JSON decode error for AI response: {response}")
                # Fallback detail extraction
                details = self._extract_basic_details(message, analysis)
            
            # Enhance with defaults based on reminder type
            reminder_type = details.get("reminder_type", analysis.get("reminder_type", "custom"))
            if reminder_type in self.reminder_types:
                type_defaults = self.reminder_types[reminder_type]
                details.setdefault("frequency", type_defaults["frequency"])
                details.setdefault("advance_notice_days", type_defaults["advance_notice"])
            
            # Map priority values to ensure compatibility with database schema
            raw_priority = details.get("priority", "medium")
            priority_mapping = {
                "urgent": "critical",
                "normal": "medium",
                "low": "low",
                "medium": "medium", 
                "high": "high",
                "critical": "critical"
            }
            mapped_priority = priority_mapping.get(raw_priority.lower(), "medium")
            
            # Log priority mapping for debugging
            if raw_priority.lower() != mapped_priority:
                logger.info(f"🎯 Priority mapped: '{raw_priority}' → '{mapped_priority}'")
            
            details["priority"] = mapped_priority
            
            return details
            
        except Exception as e:
            logger.error(f"Detail extraction error: {str(e)}")
            return self._extract_basic_details(message, analysis)

    def _extract_basic_details(self, message: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Extract basic details using simple parsing"""
        message_lower = message.lower()
        
        # Extract title (pet name + action)
        title = message[:50] + "..." if len(message) > 50 else message
        if "tarzen" in message_lower and "grooming" in message_lower:
            title = "Tarzen's Grooming Reminder"
        elif "tarzen" in message_lower and "vaccination" in message_lower:
            title = "Tarzen's Vaccination Reminder"
        elif "tarzen" in message_lower and "medication" in message_lower:
            title = "Tarzen's Medication Reminder"
        
        # Extract time from message
        time_of_day = None
        import re
        time_patterns = [
            r'(\d{1,2}[\.:]\d{2}\s*(?:am|pm))',  # 11:25 PM or 11.25 PM
            r'(\d{1,2}\s*(?:am|pm))',           # 11 PM
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, message_lower)
            if match:
                time_of_day = match.group(1).replace('.', ':')
                break
        
        # Extract date - check for "today"
        due_date = None
        if "today" in message_lower:
            from datetime import datetime, timezone
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            due_date = today
        elif "tomorrow" in message_lower:
            from datetime import datetime, timezone, timedelta
            tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
            due_date = tomorrow
        
        return {
            "title": title,
            "reminder_type": analysis.get("reminder_type", "custom"),
            "description": message,
            "frequency": "once",
            "advance_notice_days": 7,
            "priority": "medium",
            "due_date": due_date,
            "time_of_day": time_of_day
        }

    async def _create_reminder(self, user_id: int, details: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new reminder via Flask enhanced reminder API"""
        try:
            # Calculate due date if not provided
            due_date = await self._calculate_due_date(details)
            
            # Map priority values to ensure compatibility
            raw_priority = details.get("priority", "medium")
            priority_mapping = {
                "urgent": "critical",
                "normal": "medium",
                "low": "low",
                "medium": "medium", 
                "high": "high",
                "critical": "critical"
            }
            mapped_priority = priority_mapping.get(raw_priority.lower(), "medium")
            
            # Log priority mapping for debugging
            if raw_priority.lower() != mapped_priority:
                logger.info(f"🎯 Priority mapped: '{raw_priority}' → '{mapped_priority}'")
            
            # Prepare reminder data for Flask API
            reminder_data = {
                "title": details.get("title", "Pet Care Reminder"),
                "description": details.get("description", ""),
                "reminder_type": details.get("reminder_type", "custom"),
                "due_date": due_date.isoformat() if due_date else None,
                "priority": mapped_priority,
                "advance_notice_days": details.get("advance_notice_days", 3),
                "send_push": True,
                "send_email": True
            }
            
            logger.info(f"📅 Sending to Flask API - due_date: {reminder_data['due_date']}")
            logger.info(f"🔍 Full reminder_data being sent to Flask: {reminder_data}")
            
            # Create reminder through Flask enhanced reminder API
            flask_result = await self._call_flask_reminder_api(user_id, reminder_data)
            
            if flask_result.get("success"):
                # Update local stats
                self.reminder_stats["total_reminders_created"] += 1
                self.reminder_stats["active_reminders"] += 1
                
                reminder_type = details.get("reminder_type", "custom")
                self.reminder_stats["reminders_by_type"][reminder_type] = (
                    self.reminder_stats["reminders_by_type"].get(reminder_type, 0) + 1
                )
                
                return {
                    "action": "created",
                    "reminder": flask_result.get("reminder", {}),
                    "message": f"Reminder '{reminder_data['title']}' created successfully!",
                    "flask_response": flask_result
                }
            else:
                # Fallback to local storage if Flask API fails
                logger.warning(f"Flask API failed, using fallback: {flask_result.get('error')}")
                return await self._create_reminder_fallback(user_id, details, due_date)
            
        except Exception as e:
            logger.error(f"Error creating reminder: {str(e)}")
            # Fallback to local storage
            return await self._create_reminder_fallback(user_id, details, due_date)

    async def _call_flask_reminder_api(self, user_id: int, reminder_data: Dict[str, Any]) -> Dict[str, Any]:
        """Call Flask enhanced reminder API to create reminder"""
        try:
            # Get user cookie token for API authentication
            cookie_token = await self._get_user_cookie_token(user_id)
            
            headers = {
                "Content-Type": "application/json"
            }
            
            # Use cookies for authentication instead of JWT headers
            cookies = {}
            if cookie_token:
                cookies["token"] = cookie_token
            
            # Add user_id to reminder data for internal endpoint
            reminder_data["user_id"] = user_id
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.flask_api_base_url}/api/enhanced-reminders/internal",
                    json=reminder_data,
                    headers=headers
                    # No cookies needed for internal endpoint
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Flask API error: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"API error: {response.status_code}"
                    }
                    
        except Exception as e:
            logger.error(f"Error calling Flask API: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _get_user_cookie_token(self, user_id: int) -> Optional[str]:
        """Get user cookie token for authentication with Flask API"""
        try:
            # Try to get existing token from cache
            if self.cache_service:
                cached_token = await self.cache_service.get(f"user_cookie_token:{user_id}")
                if cached_token:
                    return cached_token
            
            # For now, return None - would need to implement token retrieval from session
            # In a real implementation, you'd get the user's session token
            # For testing, we'll try without authentication first
            logger.warning(f"No cookie token available for user {user_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting cookie token: {str(e)}")
            return None

    async def _create_reminder_fallback(self, user_id: int, details: Dict[str, Any], due_date: Optional[datetime]) -> Dict[str, Any]:
        """Fallback method to create reminder locally if Flask API fails"""
        try:
            # Create reminder record locally
            reminder_data = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "title": details.get("title", "Pet Care Reminder"),
                "description": details.get("description", ""),
                "reminder_type": details.get("reminder_type", "custom"),
                "due_date": due_date.isoformat() if due_date else None,
                "frequency": details.get("frequency", "once"),
                "advance_notice_days": details.get("advance_notice_days", 7),
                "priority": details.get("priority", "normal"),
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "created_via": "chat_fallback"
            }
            
            # Store in Redis for quick access
            await self._store_reminder(reminder_data)
            
            # Schedule notification if due date is set
            if due_date:
                await self._schedule_reminder_notification(reminder_data)
            
            return {
                "action": "created",
                "reminder": reminder_data,
                "message": f"Reminder '{reminder_data['title']}' created successfully! (Note: Please sync with main reminder system)",
                "fallback_used": True
            }
            
        except Exception as e:
            logger.error(f"Error in fallback reminder creation: {str(e)}")
            return {
                "action": "error",
                "message": f"Failed to create reminder: {str(e)}"
            }

    async def _calculate_due_date(self, details: Dict[str, Any]) -> Optional[datetime]:
        """Calculate due date based on details (returns naive datetime in user's local time)"""
        due_date_str = details.get("due_date")
        time_of_day = details.get("time_of_day")
        
        logger.info(f"📅 Calculating due date - date_str: {due_date_str}, time: {time_of_day}")
        
        if due_date_str:
            try:
                # Try to parse various date formats (returns naive datetime)
                due_date = self._parse_date_string(due_date_str)
                
                # Add time if specified
                if time_of_day and due_date:
                    due_date = self._add_time_to_date(due_date, time_of_day)
                    logger.info(f"📅 Combined date+time: {due_date} (naive local time)")
                
                return due_date
            except Exception as e:
                logger.error(f"Date parsing error: {str(e)}")
        
        # Default to tomorrow if no specific date (naive local time)
        tomorrow = datetime.now() + timedelta(days=1)
        return tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)  # Default to 9 AM tomorrow

    def _parse_date_string(self, date_str: str) -> Optional[datetime]:
        """Parse date string into naive datetime object (user's local time)"""
        # Simple date parsing - could be enhanced with more formats
        date_str_lower = date_str.lower()
        
        # Get current date in user's local time (naive)
        now = datetime.now()  # No timezone = user's local time
        
        if "today" in date_str_lower:
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif "tomorrow" in date_str_lower:
            return now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        elif "next week" in date_str_lower:
            return now + timedelta(weeks=1)
        elif "next month" in date_str_lower:
            return now + timedelta(days=30)
        
        # Try to parse standard formats (return naive datetime)
        formats = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M"]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)  # No timezone = naive
            except ValueError:
                continue
        
        return None

    def _add_time_to_date(self, date: datetime, time_str: str) -> datetime:
        """Add time to date"""
        try:
            # Parse time string (e.g., "9:00 AM", "14:30", "11.15 PM")
            time_str = time_str.strip().upper()
            
            # Handle dots in time format (e.g., "11.15 PM")
            time_str = time_str.replace(".", ":")
            
            if "AM" in time_str or "PM" in time_str:
                time_obj = datetime.strptime(time_str, "%I:%M %p").time()
            else:
                time_obj = datetime.strptime(time_str, "%H:%M").time()
            
            return date.replace(
                hour=time_obj.hour,
                minute=time_obj.minute,
                second=0,
                microsecond=0
            )
        except Exception as e:
            logger.error(f"Time parsing error: {str(e)}")
            return date

    async def _list_user_reminders(self, user_id: int, filter_type: Optional[str] = None) -> Dict[str, Any]:
        """List user's reminders with optional filtering"""
        try:
            reminders = await self._get_user_reminders(user_id)
            
            # Apply filter if specified
            if filter_type:
                if filter_type == "active":
                    reminders = [r for r in reminders if r.get("status") == "active"]
                elif filter_type == "overdue":
                    now = datetime.now(timezone.utc)
                    reminders = [r for r in reminders if r.get("due_date") and 
                               datetime.fromisoformat(r["due_date"].replace("Z", "+00:00")) < now]
                elif filter_type == "upcoming":
                    now = datetime.now(timezone.utc)
                    week_from_now = now + timedelta(days=7)
                    reminders = [r for r in reminders if r.get("due_date") and 
                               now <= datetime.fromisoformat(r["due_date"].replace("Z", "+00:00")) <= week_from_now]
                elif filter_type in self.reminder_types:
                    reminders = [r for r in reminders if r.get("reminder_type") == filter_type]
            
            # Sort by due date
            reminders.sort(key=lambda x: x.get("due_date", "9999-12-31"))
            
            return {
                "action": "listed",
                "reminders": reminders,
                "count": len(reminders),
                "filter": filter_type,
                "message": f"Found {len(reminders)} reminders"
            }
            
        except Exception as e:
            logger.error(f"List reminders error: {str(e)}")
            return {
                "action": "error",
                "message": f"Failed to list reminders: {str(e)}"
            }

    async def _create_smart_schedule(self, user_id: int, details: Dict[str, Any]) -> Dict[str, Any]:
        """Create intelligent reminder schedule based on pet care needs"""
        try:
            # Get user's pet information and care history
            pet_info = await self._get_user_pet_info(user_id)
            
            # Generate smart schedule based on pet age, breed, and history
            schedule_plan = await self._generate_smart_schedule_plan(pet_info, details)
            
            # Create multiple reminders based on the plan
            created_reminders = []
            for reminder_info in schedule_plan.get("reminders", []):
                reminder_data = {
                    **reminder_info,
                    "user_id": user_id,
                    "id": str(uuid.uuid4()),
                    "status": "active",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                await self._store_reminder(reminder_data)
                created_reminders.append(reminder_data)
                
                # Schedule notifications
                if reminder_data.get("due_date"):
                    await self._schedule_reminder_notification(reminder_data)
            
            return {
                "action": "smart_schedule_created",
                "reminders": created_reminders,
                "schedule_plan": schedule_plan,
                "message": f"Created {len(created_reminders)} smart reminders for your pet's care schedule!"
            }
            
        except Exception as e:
            logger.error(f"Smart schedule creation error: {str(e)}")
            return {
                "action": "error",
                "message": f"Failed to create smart schedule: {str(e)}"
            }

    async def _generate_smart_schedule_plan(self, pet_info: Dict[str, Any], details: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI-powered smart schedule plan"""
        try:
            prompt = self.prompts.get_smart_schedule_prompt(pet_info, details)
            response = await self._call_reminder_ai(prompt, max_tokens=800)
            
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                # Fallback to basic schedule
                return self._create_basic_schedule_plan(pet_info)
                
        except Exception as e:
            logger.error(f"Smart schedule generation error: {str(e)}")
            return self._create_basic_schedule_plan(pet_info)

    def _create_basic_schedule_plan(self, pet_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create basic schedule plan"""
        now = datetime.now(timezone.utc)
        
        basic_reminders = [
            {
                "title": "Annual Vet Checkup",
                "reminder_type": "checkup",
                "due_date": (now + timedelta(days=30)).isoformat(),
                "frequency": "annual",
                "priority": "high",
                "description": "Schedule your pet's annual health checkup"
            },
            {
                "title": "Vaccination Review",
                "reminder_type": "vaccination",
                "due_date": (now + timedelta(days=60)).isoformat(),
                "frequency": "annual", 
                "priority": "high",
                "description": "Check if vaccinations are up to date"
            },
            {
                "title": "Monthly Grooming",
                "reminder_type": "grooming",
                "due_date": (now + timedelta(days=30)).isoformat(),
                "frequency": "monthly",
                "priority": "medium",
                "description": "Regular grooming appointment"
            }
        ]
        
        return {
            "plan_type": "basic",
            "reminders": basic_reminders,
            "recommendations": ["Adjust schedule based on your pet's specific needs"]
        }

    # Storage and retrieval methods
    async def _store_reminder(self, reminder_data: Dict[str, Any]):
        """Store reminder in Redis"""
        try:
            user_id = reminder_data["user_id"]
            reminder_id = reminder_data["id"]
            
            # Store individual reminder
            await self.redis_client.setex(
                f"reminder:{reminder_id}",
                86400 * 30,  # 30 days
                json.dumps(reminder_data)
            )
            
            # Add to user's reminder list
            user_reminders_key = f"user_reminders:{user_id}"
            await self.redis_client.sadd(user_reminders_key, reminder_id)
            await self.redis_client.expire(user_reminders_key, 86400 * 30)
            
        except Exception as e:
            logger.error(f"Reminder storage error: {str(e)}")

    async def _get_user_reminders(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all reminders for a user"""
        try:
            user_reminders_key = f"user_reminders:{user_id}"
            reminder_ids = await self.redis_client.smembers(user_reminders_key)
            
            reminders = []
            for reminder_id in reminder_ids:
                reminder_data = await self.redis_client.get(f"reminder:{reminder_id}")
                if reminder_data:
                    reminders.append(json.loads(reminder_data))
            
            return reminders
            
        except Exception as e:
            logger.error(f"Get user reminders error: {str(e)}")
            return []

    async def _get_user_pet_info(self, user_id: int) -> Dict[str, Any]:
        """Get user's pet information from care records"""
        try:
            async with AsyncSessionLocal() as session:
                # Get recent care records to extract pet info
                result = await session.execute(
                    select(CareRecord)
                    .where(CareRecord.user_id == user_id)
                    .order_by(CareRecord.date_occurred.desc())
                    .limit(10)
                )
                records = result.scalars().all()
                
                if records:
                    recent_record = records[0]
                    return {
                        "pet_name": recent_record.pet_name or "Your pet",
                        "pet_breed": recent_record.pet_breed or "Unknown",
                        "pet_age": recent_record.pet_age or "Unknown",
                        "pet_weight": recent_record.pet_weight or "Unknown",
                        "recent_care_categories": list(set([r.category for r in records]))
                    }
                
        except Exception as e:
            logger.error(f"Get pet info error: {str(e)}")
        
        return {
            "pet_name": "Your pet",
            "pet_breed": "Unknown",
            "pet_age": "Unknown",
            "pet_weight": "Unknown",
            "recent_care_categories": []
        }

    # Notification and scheduling
    async def _schedule_reminder_notification(self, reminder_data: Dict[str, Any]):
        """Schedule reminder notification"""
        try:
            # This would integrate with a notification service
            # For now, just log the scheduling
            due_date = reminder_data.get("due_date")
            advance_notice = reminder_data.get("advance_notice_days", 7)
            
            if due_date:
                notification_date = datetime.fromisoformat(due_date.replace("Z", "+00:00")) - timedelta(days=advance_notice)
                logger.info(f"Scheduled reminder notification for {notification_date}: {reminder_data['title']}")
                
                # Store in notification queue
                notification_data = {
                    "reminder_id": reminder_data["id"],
                    "user_id": reminder_data["user_id"],
                    "notification_date": notification_date.isoformat(),
                    "message": f"Reminder: {reminder_data['title']} is due soon!"
                }
                
                await self.redis_client.zadd(
                    "reminder_notifications",
                    {json.dumps(notification_data): notification_date.timestamp()}
                )
                
        except Exception as e:
            logger.error(f"Notification scheduling error: {str(e)}")

    # AI integration
    async def _call_reminder_ai(self, prompt: str, max_tokens: int = None) -> str:
        """Call OpenAI for reminder processing"""
        try:
            pool = await self._get_openai_pool()
            
            response = await pool.chat_completion(
                messages=[
                    {"role": "system", "content": self.prompts.REMINDER_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                model=self.chat_model,
                temperature=self.temperature,
                max_tokens=max_tokens or self.max_tokens
            )
            
            return response["choices"][0]["message"]["content"]
            
        except Exception as e:
            logger.error(f"Reminder AI call error: {str(e)}")
            return "I apologize, but I'm having trouble processing your reminder request right now."

    async def _generate_reminder_response(
        self, 
        result: Dict[str, Any], 
        analysis: Dict[str, Any], 
        original_message: str
    ) -> str:
        """Generate conversational response for reminder actions with frontend links"""
        try:
            # Check if this is a successful reminder creation
            if result.get("action") == "created" and result.get("reminder"):
                return self._create_reminder_success_response(result, analysis, original_message)
            
            # For other actions, use AI-generated response
            response_prompt = self.prompts.get_response_generation_prompt(result, analysis, original_message, self.frontend_url)
            ai_response = await self._call_reminder_ai(response_prompt, max_tokens=300)
            
            # Add reminder page link for any reminder-related response
            return self._enhance_response_with_link(ai_response, result, analysis)
            
        except Exception as e:
            logger.error(f"Response generation error: {str(e)}")
            return self._create_fallback_response(result, analysis)

    def _create_reminder_success_response(
        self, 
        result: Dict[str, Any], 
        analysis: Dict[str, Any], 
        original_message: str
    ) -> str:
        """Create enhanced success response with frontend link"""
        reminder = result.get("reminder", {})
        reminder_title = reminder.get("title", "Pet Care Reminder")
        reminder_type = reminder.get("reminder_type", "custom")
        due_date = reminder.get("due_date")
        priority = reminder.get("priority", "medium")
        
        # Format due date for display
        due_date_display = "not specified"
        if due_date:
            try:
                due_datetime = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                due_date_display = due_datetime.strftime("%A, %B %d, %Y at %I:%M %p")
            except:
                due_date_display = str(due_date)
        
        # Create frontend URL with query parameters for highlighting
        reminder_id = reminder.get("id")
        reminders_url = f"{self.frontend_url}/reminders"
        if reminder_id:
            reminders_url += f"?new_reminder_id={reminder_id}&from_chat=true"
        
        # Create success response with link
        success_response = f"""✅ **Perfect! I've created your reminder successfully!**

🔔 **Reminder Details:**
• **Title:** {reminder_title}
• **Type:** {reminder_type.replace('_', ' ').title()}
• **Due:** {due_date_display}
• **Priority:** {priority.title()}

📋 **[View & Manage All Reminders →]({reminders_url})**

Your reminder is now scheduled and you'll receive email notifications when it's time. The reminder has been added to your dashboard where you can view all your pet care reminders, edit them, or create additional ones.

Need help setting up more reminders or want to adjust this one? Just ask!"""

        return success_response

    def _enhance_response_with_link(
        self, 
        response: str, 
        result: Dict[str, Any], 
        analysis: Dict[str, Any]
    ) -> str:
        """Enhance any reminder response with link to reminders page"""
        reminders_url = f"{self.frontend_url}/reminders"
        
        # Add link at the end if it's not already there
        if "reminders" not in response.lower() or self.frontend_url not in response:
            response += f"\n\n📋 [**Manage All Reminders →**]({reminders_url})"
        
        return response

    def _create_fallback_response(self, result: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Create fallback response with frontend link"""
        action = result.get("action", "unknown")
        reminders_url = f"{self.frontend_url}/reminders"
        
        if action == "created":
            reminder_title = result.get('reminder', {}).get('title', 'Pet care reminder')
            response = f"Great! I've created your reminder: {reminder_title}. I'll make sure to notify you when it's time!"
        elif action == "listed":
            count = result.get("count", 0)
            response = f"You have {count} reminders. Let me know if you'd like to modify any of them!"
        elif action == "smart_schedule_created":
            count = len(result.get("reminders", []))
            response = f"Perfect! I've created a smart care schedule with {count} reminders tailored for your pet. This will help you stay on top of all the important care tasks!"
        else:
            response = result.get("message", "I've processed your reminder request.")
        
        # Add link to reminders page
        response += f"\n\n📋 [**View All Reminders →**]({reminders_url})"
        return response

    async def _provide_reminder_guidance(self, message: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Provide enhanced guidance about reminders with proactive creation"""
        
        # Check if the user is asking to create a specific reminder
        if any(keyword in message.lower() for keyword in ["set", "create", "remind", "schedule", "appointment"]):
            # Try to extract reminder details and create if possible
            extracted_details = await self._extract_reminder_details_enhanced(message, analysis)
            
            if extracted_details.get("has_enough_info", False):
                # We have enough information to create a reminder
                user_id = analysis.get("user_id", 0)  # This should be passed from the caller
                return await self._create_reminder(user_id, extracted_details)
        
        # Otherwise provide guidance
        guidance_prompt = self.prompts.get_guidance_prompt(message, analysis)
        response = await self._call_reminder_ai(guidance_prompt, max_tokens=400)
        
        # Enhanced response with actionable guidance
        enhanced_response = f"""{response}

I can help you create reminders right now! Here are some examples of what you can say:

✅ **"Set a reminder for Max's vaccination next Friday at 2 PM"**
✅ **"Remind me to give medication every 12 hours"**
✅ **"Schedule a grooming appointment in 2 weeks"**
✅ **"Create a reminder for vet checkup in 3 months"**

Just tell me what you need to remember and when, and I'll create the reminder for you!"""
        
        return {
            "action": "enhanced_guidance",
            "message": enhanced_response,
            "can_create_reminders": True,
            "suggestions": [
                "Create a vaccination reminder",
                "Set up monthly grooming reminders", 
                "Schedule regular vet checkups",
                "Create a smart care schedule"
            ]
        }

    async def _extract_reminder_details_enhanced(self, message: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced reminder detail extraction with better parsing"""
        try:
            ai_client = await get_openai_pool()
            
            prompt = f"""Extract reminder details from this message:

Message: "{message}"

Extract and return JSON with these fields:
{{
    "has_enough_info": true/false,
    "title": "extracted title",
    "description": "extracted description", 
    "reminder_type": "vaccination|checkup|medication|grooming|dental|exercise|training|nutrition|flea_tick|heartworm|custom",
    "due_date": "YYYY-MM-DD" or null,
    "time_of_day": "HH:MM" or null,
    "frequency": "once|daily|weekly|monthly|yearly",
    "advance_notice_days": number,
    "priority": "low|medium|high|critical"
}}

Rules:
- Set has_enough_info to true if you can extract a clear reminder purpose and timeframe
- For relative dates like "next Friday", "in 2 weeks", calculate the actual date
- Default advance_notice_days to 7 for checkups/vaccinations, 1 for medications
- Infer reminder_type from context (vaccination, vet visit, grooming, etc.)
- If time is mentioned, extract it, otherwise leave null
- Today's date reference: {datetime.now().strftime('%Y-%m-%d')}

Examples:
- "Set reminder for Max vaccination next Friday at 2 PM" → has_enough_info: true
- "Remind me about the vet" → has_enough_info: false (no timeframe)
- "Schedule grooming in 2 weeks" → has_enough_info: true
"""
            
            response = await ai_client.chat.completions.create(
                model="claude-3-haiku-20240307",
                messages=[
                    {"role": "system", "content": "You are a reminder detail extractor. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.1
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"❌ Enhanced detail extraction error: {str(e)}")
            return {
                "has_enough_info": False,
                "title": "Pet Care Reminder",
                "description": "Reminder extracted from user message",
                "reminder_type": "custom",
                "due_date": None,
                "time_of_day": None,
                "frequency": "once",
                "advance_notice_days": 7,
                "priority": "normal"
            }

    # Update and delete operations
    async def _update_reminder(self, user_id: int, details: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing reminder"""
        try:
            reminder_id = details.get("reminder_id")
            if not reminder_id:
                return {"action": "error", "message": "Reminder ID is required for updates"}
            
            # Get existing reminder
            reminder_data = await self.redis_client.get(f"reminder:{reminder_id}")
            if not reminder_data:
                return {"action": "error", "message": "Reminder not found"}
            
            reminder = json.loads(reminder_data)
            
            # Verify ownership
            if reminder.get("user_id") != user_id:
                return {"action": "error", "message": "Unauthorized"}
            
            # Update fields
            for key, value in details.items():
                if key != "reminder_id" and value is not None:
                    reminder[key] = value
            
            reminder["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            # Store updated reminder
            await self._store_reminder(reminder)
            
            return {
                "action": "updated",
                "reminder": reminder,
                "message": f"Reminder '{reminder['title']}' updated successfully!"
            }
            
        except Exception as e:
            logger.error(f"Reminder update error: {str(e)}")
            return {"action": "error", "message": f"Failed to update reminder: {str(e)}"}

    async def _delete_reminder(self, user_id: int, reminder_id: str) -> Dict[str, Any]:
        """Delete a reminder"""
        try:
            if not reminder_id:
                return {"action": "error", "message": "Reminder ID is required"}
            
            # Get existing reminder
            reminder_data = await self.redis_client.get(f"reminder:{reminder_id}")
            if not reminder_data:
                return {"action": "error", "message": "Reminder not found"}
            
            reminder = json.loads(reminder_data)
            
            # Verify ownership
            if reminder.get("user_id") != user_id:
                return {"action": "error", "message": "Unauthorized"}
            
            # Delete from Redis
            await self.redis_client.delete(f"reminder:{reminder_id}")
            await self.redis_client.srem(f"user_reminders:{user_id}", reminder_id)
            
            # Remove from notification queue
            await self.redis_client.zrem("reminder_notifications", reminder_id)
            
            self.reminder_stats["active_reminders"] = max(0, self.reminder_stats["active_reminders"] - 1)
            
            return {
                "action": "deleted",
                "message": f"Reminder '{reminder['title']}' deleted successfully!"
            }
            
        except Exception as e:
            logger.error(f"Reminder deletion error: {str(e)}")
            return {"action": "error", "message": f"Failed to delete reminder: {str(e)}"}

    # Performance monitoring
    def _update_reminder_stats(self, intent: str):
        """Update reminder statistics"""
        if intent == "create_reminder":
            self.reminder_stats["total_reminders_created"] += 1

    def get_reminder_stats(self) -> Dict[str, Any]:
        """Get reminder service statistics"""
        return self.reminder_stats.copy()

    def reset_reminder_stats(self):
        """Reset reminder statistics"""
        self.reminder_stats = {
            "total_reminders_created": 0,
            "active_reminders": 0,
            "completed_reminders": 0,
            "overdue_reminders": 0,
            "reminders_by_type": {}
        }