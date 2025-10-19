"""
Reminder Query Tool
Allows read-only access to reminders in General Mode
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import text
from models.base import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def query_user_reminders(
    user_id: int,
    dog_name: Optional[str] = None,
    date_filter: Optional[str] = None,  # "today", "this_week", "upcoming", "all"
    status_filter: Optional[str] = None,  # "pending", "completed", "all"
    limit: int = 10
) -> Dict[str, Any]:
    """
    Query reminders from database (read-only)
    
    Args:
        user_id: User ID
        dog_name: Filter by dog name (optional)
        date_filter: "today", "this_week", "upcoming", or "all"
        status_filter: "pending", "completed", or "all"
        limit: Maximum number of reminders to return
    
    Returns:
        Dict with reminders and metadata
    """
    try:
        async with AsyncSessionLocal() as db:
            # Build query
            query = """
                SELECT 
                    r.id,
                    r.title,
                    r.description,
                    r.reminder_datetime,
                    r.recurrence_type,
                    r.is_completed,
                    r.created_at,
                    d.name as dog_name,
                    d.breed as dog_breed
                FROM reminders r
                LEFT JOIN dog_profiles d ON r.dog_profile_id = d.id
                WHERE r.user_id = :user_id
            """
            
            params = {"user_id": user_id}
            
            # Filter by dog name
            if dog_name:
                query += " AND d.name ILIKE :dog_name"
                params["dog_name"] = f"%{dog_name}%"
            
            # Filter by status
            if status_filter == "pending":
                query += " AND r.is_completed = false"
            elif status_filter == "completed":
                query += " AND r.is_completed = true"
            # "all" means no status filter
            
            # Filter by date
            now = datetime.utcnow()
            if date_filter == "today":
                today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                today_end = today_start + timedelta(days=1)
                query += " AND r.reminder_datetime >= :start_date AND r.reminder_datetime < :end_date"
                params["start_date"] = today_start
                params["end_date"] = today_end
            elif date_filter == "this_week":
                week_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                week_end = week_start + timedelta(days=7)
                query += " AND r.reminder_datetime >= :start_date AND r.reminder_datetime < :end_date"
                params["start_date"] = week_start
                params["end_date"] = week_end
            elif date_filter == "upcoming":
                query += " AND r.reminder_datetime >= :now AND r.is_completed = false"
                params["now"] = now
            # "all" means no date filter
            
            # Order by datetime
            query += " ORDER BY r.reminder_datetime ASC LIMIT :limit"
            params["limit"] = limit
            
            # Execute query
            result = await db.execute(text(query), params)
            rows = result.fetchall()
            
            # Format results
            reminders = []
            for row in rows:
                reminder = {
                    "id": row.id,
                    "title": row.title,
                    "description": row.description,
                    "datetime": row.reminder_datetime.isoformat() if row.reminder_datetime else None,
                    "recurrence": row.recurrence_type,
                    "is_completed": row.is_completed,
                    "dog_name": row.dog_name,
                    "dog_breed": row.dog_breed,
                    "created_at": row.created_at.isoformat() if row.created_at else None
                }
                reminders.append(reminder)
            
            logger.info(f"📋 Queried {len(reminders)} reminders for user {user_id}")
            
            return {
                "success": True,
                "count": len(reminders),
                "reminders": reminders,
                "filters": {
                    "dog_name": dog_name,
                    "date_filter": date_filter,
                    "status_filter": status_filter
                }
            }
    
    except Exception as e:
        logger.error(f"❌ Error querying reminders: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "count": 0,
            "reminders": []
        }


# Tool definition for LLM function calling
REMINDER_QUERY_TOOL = {
    "name": "query_user_reminders",
    "description": """Query and view user's reminders from the database (read-only access).
    
Use this tool when the user asks to:
- View their reminders
- Check what reminders they have
- Ask about reminders for a specific dog
- Ask about upcoming reminders
- Check today's or this week's reminders

Examples:
- "What reminders do I have for Max?"
- "Show me today's reminders"
- "Do I have any upcoming reminders?"
- "What did I set reminders for this week?"

IMPORTANT: This tool is for VIEWING only. For creating, editing, or deleting reminders, 
redirect the user to switch to Reminder Mode.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "dog_name": {
                "type": "string",
                "description": "Filter reminders by dog name (optional). Example: 'Max', 'Bella'"
            },
            "date_filter": {
                "type": "string",
                "enum": ["today", "this_week", "upcoming", "all"],
                "description": "Filter by date range. 'today' = today only, 'this_week' = next 7 days, 'upcoming' = all future pending reminders, 'all' = no date filter"
            },
            "status_filter": {
                "type": "string",
                "enum": ["pending", "completed", "all"],
                "description": "Filter by completion status. 'pending' = not completed, 'completed' = completed, 'all' = no status filter"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of reminders to return (default: 10)",
                "default": 10
            }
        },
        "required": []
    }
}

