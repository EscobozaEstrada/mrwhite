"""
Reminders API routes
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import pytz

from models.base import get_db
from middleware.auth import require_auth

router = APIRouter(prefix="/api", tags=["reminders"])


@router.get("/enhanced-reminders")
async def get_enhanced_reminders(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Get enhanced reminders for the current user.
    Returns reminders from health_reminders table with countdown and formatting.
    """
    try:
        user_id = current_user["user_id"]
        
        # Get user's timezone
        user_query = text("SELECT timezone FROM users WHERE id = :user_id")
        user_result = await db.execute(user_query, {"user_id": user_id})
        user_row = user_result.fetchone()
        user_tz_str = user_row[0] if user_row and user_row[0] else "UTC"
        user_tz = pytz.timezone(user_tz_str)
        
        # Query health_reminders table
        query = text("""
            SELECT 
                hr.id,
                hr.user_id,
                hr.pet_id,
                hr.reminder_type,
                hr.title,
                hr.description,
                hr.due_date,
                hr.due_time,
                hr.reminder_date,
                hr.reminder_time,
                hr.status,
                hr.completed_at,
                hr.created_at,
                hr.updated_at,
                hr.recurrence_type,
                hr.recurrence_interval,
                pp.name as pet_name
            FROM health_reminders hr
            LEFT JOIN pet_profiles pp ON hr.pet_id = pp.id
            WHERE hr.user_id = :user_id
            ORDER BY hr.due_date ASC, hr.due_time ASC
            LIMIT :limit OFFSET :offset
        """)
        
        result = await db.execute(query, {
            "user_id": user_id,
            "limit": limit,
            "offset": offset
        })
        
        rows = result.fetchall()
        
        reminders = []
        now_utc = datetime.now(pytz.UTC)
        
        for row in rows:
            # Combine due_date and due_time (stored as naive UTC in database)
            due_datetime_naive = None
            if row.due_date:
                due_datetime_naive = datetime.combine(row.due_date, row.due_time or datetime.min.time())
            
            # Convert to timezone-aware UTC, then to user's timezone for display
            due_datetime_utc = None
            due_datetime_local = None
            if due_datetime_naive:
                due_datetime_utc = pytz.utc.localize(due_datetime_naive)
                due_datetime_local = due_datetime_utc.astimezone(user_tz)
            
            # Calculate countdown using UTC times
            countdown = None
            is_overdue = False
            if due_datetime_utc:
                time_diff = due_datetime_utc - now_utc
                total_seconds = int(time_diff.total_seconds())
                
                if total_seconds < 0:
                    is_overdue = True
                    total_seconds = abs(total_seconds)
                
                days = total_seconds // 86400
                hours = (total_seconds % 86400) // 3600
                minutes = (total_seconds % 3600) // 60
                
                countdown = {
                    "days": days,
                    "hours": hours,
                    "minutes": minutes,
                    "total_seconds": total_seconds if not is_overdue else -total_seconds,
                    "is_overdue": is_overdue
                }
            
            reminders.append({
                "id": row.id,
                "user_id": row.user_id,
                "pet_id": row.pet_id,
                "pet_name": row.pet_name,
                "reminder_type": row.reminder_type,
                "title": row.title,
                "description": row.description,
                # Send local timezone date/time for display
                "due_date": due_datetime_local.date().isoformat() if due_datetime_local else (row.due_date.isoformat() if row.due_date else None),
                "due_time": due_datetime_local.time().isoformat() if due_datetime_local else (row.due_time.isoformat() if row.due_time else None),
                "reminder_date": row.reminder_date.isoformat() if row.reminder_date else None,
                "reminder_time": row.reminder_time.isoformat() if row.reminder_time else None,
                "status": row.status,
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                "recurrence_type": row.recurrence_type,
                "recurrence_interval": row.recurrence_interval,
                "countdown": countdown
            })
        
        return {
            "success": True,
            "reminders": reminders,
            "total": len(reminders),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        import traceback
        print(f"❌ Error fetching reminders: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to fetch reminders: {str(e)}")

