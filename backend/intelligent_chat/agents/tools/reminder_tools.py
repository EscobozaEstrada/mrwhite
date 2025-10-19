"""
Tools for Reminder Agent.
"""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from langchain_core.tools import tool
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
import pytz

from models.base import AsyncSessionLocal
from models import Reminder, DogProfile
from config.settings import Settings

settings = Settings()


async def get_user_timezone(user_id: int) -> str:
    """
    Get user's timezone from database.
    
    Args:
        user_id: User ID
        
    Returns:
        Timezone string (e.g., 'America/New_York', 'Asia/Kolkata')
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("SELECT timezone FROM users WHERE id = :user_id"),
                {"user_id": user_id}
            )
            row = result.fetchone()
            return row[0] if row and row[0] else 'UTC'
    except Exception as e:
        print(f"❌ Failed to get user timezone: {e}")
        return 'UTC'


@tool
async def extract_reminder_info(message: str, user_id: int, available_dogs: List[Dict]) -> Dict[str, Any]:
    """
    Extract reminder information from user message using Claude.
    
    Args:
        message: User's message
        user_id: User ID
        available_dogs: List of user's dogs with id and name
        
    Returns:
        Dictionary with extracted fields: title, datetime, type, dog_name, recurrence
    """
    import boto3
    
    # Get user's timezone
    user_tz_str = await get_user_timezone(user_id)
    user_tz = pytz.timezone(user_tz_str)
    
    # Get current time in user's timezone
    current_time_utc = datetime.now(pytz.UTC)
    current_time_user = current_time_utc.astimezone(user_tz)
    
    bedrock = boto3.client(
        service_name='bedrock-runtime',
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
    )
    
    dog_list = "\n".join([f"- {dog['name']} (ID: {dog['id']})" for dog in available_dogs])
    
    prompt = f"""Extract reminder information from THIS SINGLE MESSAGE ONLY. DO NOT use context from previous messages!

⚠️ CRITICAL INSTRUCTION: If title or datetime are NOT in THIS message, return null for those fields. DO NOT guess!

**CURRENT DATE AND TIME:**
Current time in user's timezone ({user_tz_str}): {current_time_user.strftime("%Y-%m-%d %H:%M:%S %Z")}
Current year: {current_time_user.year}
Current month: {current_time_user.strftime("%B")}
Current day: {current_time_user.day}

User's dogs:
{dog_list}

User's CURRENT message: "{message}"

Extract and return JSON with these fields:
{{
  "title": "brief title IF mentioned in THIS message (e.g. 'take max for walk' → 'walk', 'vet appointment for bella' → 'vet appointment'). If message is just 'set a reminder' or 'set another reminder' with NO action, return null.",
  "description": "optional longer description, or null",
  "reminder_datetime": "ISO datetime string in user's timezone (YYYY-MM-DDTHH:MM:SS), or null if no time info provided",
  "reminder_type": "medication|vet_appointment|grooming|feeding|training|walking|playtime|other, or null",
  "dog_name": "exact dog name from list above, or null if not specified, or 'all' for all dogs",
  "recurrence": "once|daily|weekly|monthly, default to 'once'",
  "confidence": "high|medium|low"
}}

CRITICAL DATETIME RULES:
- **NEVER GUESS OR INFER** a datetime if the user doesn't explicitly provide one
- **ONLY** extract datetime if user explicitly mentions a time (like "tomorrow", "3pm", "next week", "today at 10:50 PM", "15 oct", "at 12 pm")
- If user just says "set a reminder" or "set another reminder" with NO time info, set reminder_datetime to **null**
- DO NOT default to any datetime from context or previous messages
- DO NOT make up dates like "tomorrow" or "next week" unless user says so
- **CURRENT YEAR IS {current_time_user.year}** - Always use this year unless user explicitly says "next year"
- If time is relative ("tomorrow", "in 2 hours", "next week"), convert to absolute datetime IN THE USER'S TIMEZONE
- If only time given (no date like "10:50 PM"), assume TODAY if that time hasn't passed yet, or TOMORROW if it has
- If date is given without year (like "15 oct", "october 15"), use CURRENT YEAR {current_time_user.year}
- All datetimes should be in the user's timezone ({user_tz_str})

TITLE EXTRACTION RULES (CRITICAL):
- **ONLY infer a title** if the current message contains actionable information
- **DO NOT use titles from previous messages or context** - only look at the CURRENT message
- Examples of inference FROM CURRENT MESSAGE:
  * "take bella to vet at 3pm" → title: "take to vet" or "vet visit"
  * "i want to take max for walk at 12pm" → title: "walk" or "dog walk"
  * "give her medicine tomorrow" → title: "medication" or "give medicine"
  * "groom max next week" → title: "grooming"
- If user says "set a reminder" or "set another reminder" with NO action info, set title to **null**
- Examples of NO title:
  * "set a reminder" → title: null
  * "set another reminder for bella" → title: null (no action specified)
  * "remind me about bella" → title: null (too vague)
- Prefer short, actionable titles (2-4 words)

DOG SELECTION RULES (IMPORTANT):
- If user says "for ALL dogs", "for BOTH dogs", "for all my dogs" → set dog_name to "all"
- If user says "for my dog" (singular), "for the dog", or a specific dog name → extract that specific dog's name
- If user says nothing about dogs → set dog_name to null
- DO NOT set dog_name to "all" unless explicitly stated

OTHER RULES:
- If reminder type not clear, set to null
- Set confidence based on how much information is present

Return ONLY valid JSON, nothing else."""

    try:
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1
        }
        
        response = bedrock.invoke_model(
            modelId=settings.BEDROCK_MODEL_ID,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            extracted = json.loads(json_match.group())
            
            # DEBUG LOGGING
            print(f"🔍 EXTRACTION DEBUG:")
            print(f"  User timezone: {user_tz_str}")
            print(f"  Raw datetime from Claude: {extracted.get('reminder_datetime')}")
            
            # Convert datetime string to datetime object (assume user's timezone, convert to UTC)
            if extracted.get('reminder_datetime'):
                try:
                    dt_str = extracted['reminder_datetime']
                    
                    # Remove 'Z' if present
                    dt_str = dt_str.replace('Z', '')
                    
                    # Parse the datetime
                    dt_parsed = datetime.fromisoformat(dt_str)
                    
                    # Check if already timezone-aware
                    if dt_parsed.tzinfo is not None:
                        # Already has timezone, convert to UTC
                        dt_utc = dt_parsed.astimezone(pytz.UTC)
                        print(f"  Parsed (with tz): {dt_parsed} → UTC: {dt_utc}")
                    else:
                        # Naive datetime, assume it's in user's timezone
                        dt_user = user_tz.localize(dt_parsed)
                        dt_utc = dt_user.astimezone(pytz.UTC)
                        print(f"  Parsed (user tz): {dt_user} → UTC: {dt_utc}")
                    
                    # Store as naive UTC (database expects naive datetime, but it's actually UTC)
                    extracted['reminder_datetime'] = dt_utc.replace(tzinfo=None)
                    print(f"  Stored: {extracted['reminder_datetime']}")
                    
                except Exception as e:
                    print(f"  ❌ Failed to parse: {e}")
                    extracted['reminder_datetime'] = None
            
            return extracted
        
        return {"error": "Could not extract information"}
        
    except Exception as e:
        return {"error": f"Extraction failed: {str(e)}"}


@tool
async def validate_reminder_datetime(dt: Optional[datetime]) -> Dict[str, Any]:
    """
    Validate reminder datetime (expected in UTC).
    
    Args:
        dt: Datetime to validate (can be None if not provided yet) - should be naive UTC
        
    Returns:
        Dictionary with valid (bool) and error (str) if invalid
    """
    if not dt:
        # This is OK - user hasn't provided datetime yet, we'll ask for it
        return {"valid": True, "missing": True}
    
    # Compare in UTC (both should be naive UTC for consistency)
    now_utc = datetime.utcnow()
    
    # DEBUG LOGGING
    print(f"🔍 VALIDATION DEBUG:")
    print(f"  Reminder datetime (UTC): {dt}")
    print(f"  Current time (UTC): {now_utc}")
    print(f"  Difference: {(dt - now_utc).total_seconds()} seconds ({(dt - now_utc).total_seconds() / 3600:.1f} hours)")
    print(f"  Is past?: {dt < now_utc}")
    
    if dt < now_utc:
        return {"valid": False, "error": "Cannot set reminder in the past"}
    
    if dt > now_utc + timedelta(days=365):
        return {"valid": False, "error": "Cannot set reminder more than 1 year ahead"}
    
    return {"valid": True, "missing": False}


@tool
async def create_reminder(
    user_id: int,
    title: str,
    reminder_datetime: datetime,
    reminder_type: str,
    dog_profile_id: Optional[int] = None,
    description: Optional[str] = None,
    recurrence: str = "once"
) -> Dict[str, Any]:
    """
    Create reminder in database (both ic_reminders and health_reminders tables).
    
    Args:
        user_id: User ID
        title: Reminder title
        reminder_datetime: When to remind
        reminder_type: Type of reminder
        dog_profile_id: Optional dog ID
        description: Optional description
        recurrence: once, daily, weekly, monthly
        
    Returns:
        Dictionary with success (bool) and reminder_id (int)
    """
    try:
        print(f"🔧 CREATE_REMINDER TOOL:")
        print(f"  user_id={user_id}, dog_profile_id={dog_profile_id}")
        print(f"  title='{title}', type={reminder_type}")
        print(f"  datetime={reminder_datetime}, recurrence={recurrence}")
        
        async with AsyncSessionLocal() as session:
            # 1. Create in ic_reminders (intelligent_chat system)
            ic_reminder = Reminder(
                user_id=user_id,
                title=title,
                description=description,
                reminder_datetime=reminder_datetime,
                reminder_type=reminder_type,
                dog_profile_id=dog_profile_id,
                recurrence=recurrence,
                status='pending',
                created_from_message=True,
                created_at=datetime.now()
            )
            session.add(ic_reminder)
            await session.flush()
            
            reminder_id = ic_reminder.id
            print(f"  ✅ Created ic_reminder with ID: {reminder_id}")
            
            # 2. ALSO create in health_reminders (legacy system for UI compatibility)
            # Map reminder types to legacy enum values (UPPERCASE)
            type_mapping = {
                'medication': 'MEDICATION',
                'vet_appointment': 'VET_APPOINTMENT',
                'vaccination': 'VACCINATION',
                'grooming': 'GROOMING',
                'checkup': 'CHECKUP',
                'feeding': 'CUSTOM',
                'training': 'CUSTOM',
                'walking': 'CUSTOM',
                'playtime': 'CUSTOM',
                'other': 'CUSTOM'
            }
            legacy_type = type_mapping.get(reminder_type.lower(), 'CUSTOM')
            
            # Map recurrence to legacy recurrence_type (UPPERCASE)
            recurrence_mapping = {
                'once': 'NONE',
                'daily': 'DAILY',
                'weekly': 'WEEKLY',
                'monthly': 'MONTHLY'
            }
            legacy_recurrence = recurrence_mapping.get(recurrence.lower(), 'NONE')
            
            # Extract date and time from reminder_datetime
            due_date = reminder_datetime.date()
            due_time = reminder_datetime.time()
            
            legacy_sql = text("""
                INSERT INTO health_reminders (
                    user_id, 
                    title, 
                    description, 
                    reminder_type, 
                    due_date,
                    due_time,
                    recurrence_type,
                    status, 
                    created_at,
                    pet_id
                ) VALUES (
                    :user_id, 
                    :title, 
                    :description, 
                    :reminder_type,
                    :due_date,
                    :due_time,
                    :recurrence_type,
                    'PENDING', 
                    NOW(),
                    :pet_id
                )
            """)
            
            await session.execute(legacy_sql, {
                'user_id': user_id,
                'title': title,
                'description': description,
                'reminder_type': legacy_type,
                'due_date': due_date,
                'due_time': due_time,
                'recurrence_type': legacy_recurrence,
                'pet_id': dog_profile_id
            })
            
            await session.commit()
            
            print(f"  ✅ Committed both reminders successfully")
            
            return {
                "success": True,
                "reminder_id": reminder_id,
                "message": f"Reminder created successfully (ID: {reminder_id})"
            }
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"  ❌ CREATE_REMINDER FAILED: {str(e)}")
        print(f"  Stack trace:\n{error_details}")
        return {
            "success": False,
            "error": f"Failed to create reminder: {str(e)}"
        }


@tool
async def get_user_dogs(user_id: int) -> List[Dict[str, Any]]:
    """
    Get list of user's dogs.
    
    Args:
        user_id: User ID
        
    Returns:
        List of dogs with id, name, breed
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(DogProfile).where(DogProfile.user_id == user_id)
            )
            dogs = result.scalars().all()
            
            return [
                {
                    "id": dog.id,
                    "name": dog.name,
                    "breed": dog.breed,
                    "age": dog.age
                }
                for dog in dogs
            ]
    except Exception as e:
        return []


@tool
async def search_existing_reminders(user_id: int, query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search user's existing reminders.
    
    Args:
        user_id: User ID
        query: Search query
        limit: Max results
        
    Returns:
        List of matching reminders
    """
    try:
        async with AsyncSessionLocal() as session:
            sql = text("""
                SELECT id, title, description, reminder_datetime, reminder_type, status
                FROM ic_reminders
                WHERE user_id = :user_id
                AND (
                    title ILIKE :query 
                    OR description ILIKE :query
                    OR reminder_type ILIKE :query
                )
                ORDER BY reminder_datetime DESC
                LIMIT :limit
            """)
            
            result = await session.execute(sql, {
                'user_id': user_id,
                'query': f'%{query}%',
                'limit': limit
            })
            
            reminders = []
            for row in result:
                reminders.append({
                    "id": row[0],
                    "title": row[1],
                    "description": row[2],
                    "datetime": row[3].isoformat() if row[3] else None,
                    "type": row[4],
                    "status": row[5]
                })
            
            return reminders
            
    except Exception as e:
        return []



