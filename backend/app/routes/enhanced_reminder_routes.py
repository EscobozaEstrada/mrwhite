#!/usr/bin/env python3
"""
Enhanced Reminder Routes - API endpoints for the enhanced reminder system with AI time management
"""

from flask import Blueprint, request, jsonify, current_app, g, redirect
from datetime import datetime, date, time, timezone, timedelta
import logging
from app.models.health_models import HealthReminder, ReminderType, ReminderStatus, RecurrenceType, ReminderNotification
from app.models.user import User
from app.services.reminder_scheduler_service import get_scheduler_service
from app.services.ai_time_manager import get_ai_time_manager
from app.middleware.auth import require_auth
from app import db
import pytz
from app.services.followup_notification_service import get_followup_notification_service
from app.services.health_service import HealthService
import json

logger = logging.getLogger(__name__)

# Create the blueprint with the correct name
enhanced_reminder_bp = Blueprint('enhanced_reminders', __name__, url_prefix='/api/enhanced-reminders')

@enhanced_reminder_bp.route('', methods=['GET'])
@require_auth
def get_reminders():
    """Get all reminders for the authenticated user"""
    try:
        user_id = g.user_id
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Get query parameters
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        status = request.args.get('status')
        reminder_type = request.args.get('type')
        
        # Build query
        query = HealthReminder.query.filter_by(user_id=user_id)
        
        if status:
            query = query.filter_by(status=status)
        
        if reminder_type:
            query = query.filter_by(reminder_type=reminder_type)
        
        # Order by due date
        query = query.order_by(HealthReminder.due_date.asc())
        
        # Apply pagination
        reminders = query.offset(offset).limit(limit).all()
        total_count = query.count()
        
        # Get AI time manager for countdown calculations
        ai_time_manager = get_ai_time_manager()
        
        # Get user timezone for proper display conversion
        user_tz = pytz.timezone(user.timezone) if user.timezone else pytz.UTC
        
        # Format reminders with timezone-aware countdown
        formatted_reminders = []
        for reminder in reminders:
            # Combine due_date and due_time (stored as naive UTC in database)
            due_datetime_naive = None
            if reminder.due_date:
                if reminder.due_time:
                    due_datetime_naive = datetime.combine(reminder.due_date, reminder.due_time)
                else:
                    due_datetime_naive = datetime.combine(reminder.due_date, time(9, 0))  # Default to 9 AM
            
            # Convert to timezone-aware UTC, then to user's local timezone for display
            due_datetime_utc = None
            due_datetime_local = None
            if due_datetime_naive:
                due_datetime_utc = pytz.utc.localize(due_datetime_naive)
                due_datetime_local = due_datetime_utc.astimezone(user_tz)
            
            reminder_dict = {
                'id': reminder.id,
                'title': reminder.title,
                'description': reminder.description,
                'reminder_type': reminder.reminder_type.value if reminder.reminder_type else None,
                # Send local timezone datetime for display
                'due_date': due_datetime_local.isoformat() if due_datetime_local else None,
                'status': reminder.status.value if reminder.status else None,
                'recurrence_type': reminder.recurrence_type.value if reminder.recurrence_type else None,
                'recurrence_interval': reminder.recurrence_interval,
                'created_at': reminder.created_at.isoformat() if reminder.created_at else None,
                'updated_at': reminder.updated_at.isoformat() if reminder.updated_at else None,
                'advance_notice_days': reminder.days_before_reminder,
                'send_push': reminder.send_push,
                'send_email': reminder.send_email,
                'is_active': reminder.status == ReminderStatus.PENDING,
                'priority': reminder.priority  # Add priority to the response
            }
            
            # Add real-time countdown information
            if due_datetime_utc:
                countdown_info = ai_time_manager.calculate_time_until_due(
                    due_datetime=due_datetime_utc,
                    user_timezone=user.timezone
                )
                reminder_dict['countdown'] = countdown_info
            
            formatted_reminders.append(reminder_dict)
        
        return jsonify({
            'success': True,
            'reminders': formatted_reminders,
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
            'user_timezone': user.timezone,
            'user_timezone_abbreviation': ai_time_manager.get_timezone_abbreviation(user.timezone),
            'current_user_time': user.get_local_time().strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        logger.error(f"Error in get_reminders: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_reminder_bp.route('', methods=['POST'])
@require_auth
def create_reminder():
    """Create a new reminder with AI time optimization"""
    try:
        user_id = g.user_id
        data = request.json or {}
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Validate required fields
        title = data.get('title')
        if not title:
            return jsonify({
                'success': False,
                'error': 'Title is required'
            }), 400
        
        # Get AI time manager
        ai_time_manager = get_ai_time_manager()
        
        # Parse and validate due date
        due_date_str = data.get('due_date')
        timezone_metadata = {}
        
        if due_date_str:
            try:
                # 🎯 TIMEZONE FIX: Proper handling of user timezone information
                user_tz = user.get_timezone()
                
                if 'T' in due_date_str or ' ' in due_date_str:
                    # User provided specific time - this is already in user's local timezone
                    due_date_local = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                    
                    if due_date_local.tzinfo is None:
                        # This is a naive datetime in user's local timezone
                        logger.info(f"📅 Processing naive datetime as user local time: {due_date_local} in {user.timezone}")
                        
                        # Create timezone metadata for proper scheduling
                        timezone_metadata = {
                            'user_timezone': user.timezone,
                            'timezone_aware_creation': True,
                            'creation_timestamp': datetime.utcnow().isoformat(),
                            'original_local_time': due_date_local.isoformat(),
                            'creation_source': 'frontend_api'
                        }
                        
                        # Store date and time separately as local values
                        due_date = due_date_local.date()
                        due_time = due_date_local.time()
                        
                        logger.info(f"📅 Stored local date/time: {due_date} {due_time} (timezone: {user.timezone})")
                    else:
                        # This is already timezone-aware
                        user_local_datetime = due_date_local.astimezone(user_tz)
                        due_date = user_local_datetime.date()
                        due_time = user_local_datetime.time()
                        
                        timezone_metadata = {
                            'user_timezone': user.timezone,
                            'timezone_aware_creation': True,
                            'creation_timestamp': datetime.utcnow().isoformat(),
                            'original_local_time': user_local_datetime.isoformat(),
                            'creation_source': 'frontend_api_tz_aware'
                        }
                        
                        logger.info(f"📅 Converted timezone-aware datetime to local: {due_date} {due_time} (timezone: {user.timezone})")
                else:
                    # User provided only date, use AI to suggest optimal time
                    due_date_only = datetime.fromisoformat(due_date_str).date()
                    
                    # Get AI time suggestion
                    reminder_type = data.get('reminder_type', 'custom')
                    time_insight = ai_time_manager.suggest_optimal_reminder_time(
                        reminder_type=reminder_type,
                        user_timezone=user.timezone,
                        user_preferences=user.preferred_reminder_times
                    )
                    
                    # Use AI-suggested time as local time
                    due_date = due_date_only
                    due_time = time_insight.optimal_time
                    
                    timezone_metadata = {
                        'user_timezone': user.timezone,
                        'timezone_aware_creation': True,
                        'creation_timestamp': datetime.utcnow().isoformat(),
                        'ai_suggested_time': True,
                        'original_local_time': datetime.combine(due_date, due_time).isoformat(),
                        'creation_source': 'frontend_api_ai_time'
                    }
                    
                    # Learn from this AI suggestion for future improvements
                    ai_time_manager.learn_user_patterns(
                        user_id=user_id,
                        reminder_type=reminder_type,
                        chosen_time=time_insight.optimal_time,
                        user_timezone=user.timezone
                    )
                    
                    logger.info(f"📅 AI-suggested local time: {due_date} {due_time} (timezone: {user.timezone})")
                
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid due date format'
                }), 400
        else:
            due_date = None
            due_time = None
        
        # 🎯 CRITICAL FIX: Calculate reminder_date and reminder_time for notifications
        reminder_date = None
        reminder_time = None
        if due_date:
            advance_notice_days = data.get('advance_notice_days', 1)
            calculated_reminder_date = due_date - timedelta(days=advance_notice_days)
            
            # 🎯 FIX: If calculated reminder date is in the past, set to today
            today = date.today()
            if calculated_reminder_date < today:
                logger.warning(f"⚠️  Calculated reminder date {calculated_reminder_date} is in the past, setting to today ({today})")
                reminder_date = today
            else:
                reminder_date = calculated_reminder_date
            
            # Use the same time as due_time, or default to 9 AM
            reminder_time = due_time or time(9, 0)
        
        # Create reminder with proper timezone metadata
        reminder = HealthReminder(
            user_id=user_id,
            title=title,
            description=data.get('description', ''),
            reminder_type=ReminderType(data.get('reminder_type', 'custom')),
            due_date=due_date,
            due_time=due_time,
            reminder_date=reminder_date,  # 🎯 CRITICAL: Set when to send notification
            reminder_time=reminder_time,  # 🎯 CRITICAL: Set time to send notification
            status=ReminderStatus(data.get('status', 'pending')),
            recurrence_type=RecurrenceType(data.get('recurrence_type')) if data.get('recurrence_type') and data.get('recurrence_type') != 'none' else RecurrenceType.NONE,
            recurrence_interval=data.get('recurrence_interval', 1),
            days_before_reminder=data.get('advance_notice_days', 1),
            send_push=data.get('send_push', True),
            send_email=data.get('send_email', True),
            priority=data.get('priority', 'medium'),  # Add priority field
            extra_data=json.dumps(timezone_metadata) if timezone_metadata else None
        )
        
        db.session.add(reminder)
        db.session.commit()
        
        # 🎯 CRITICAL FIX: Schedule the new reminder for notification
        try:
            from app.services.precision_reminder_scheduler import get_precision_scheduler
            scheduler = get_precision_scheduler()
            if scheduler and scheduler.is_running:
                success = scheduler.schedule_reminder(reminder)
                if success:
                    logger.info(f"✅ Scheduled new reminder {reminder.id} for notification")
                else:
                    logger.warning(f"⚠️  Failed to schedule new reminder {reminder.id}")
            else:
                logger.warning(f"⚠️  Precision scheduler not available - reminder {reminder.id} not scheduled")
        except Exception as e:
            logger.error(f"❌ Error scheduling new reminder {reminder.id}: {str(e)}")
            # Don't fail the request if scheduling fails
        
        # Get countdown information
        countdown_info = None
        # Combine due_date and due_time for proper datetime handling
        due_datetime = None
        if reminder.due_date:
            if reminder.due_time:
                due_datetime = datetime.combine(reminder.due_date, reminder.due_time)
            else:
                due_datetime = datetime.combine(reminder.due_date, time(9, 0))  # Default to 9 AM
        
        if due_datetime:
            countdown_info = ai_time_manager.calculate_time_until_due(
                due_datetime=due_datetime,
                user_timezone=user.timezone
            )
        
        return jsonify({
            'success': True,
            'message': 'Reminder created successfully',
            'reminder': {
                'id': reminder.id,
                'title': reminder.title,
                'description': reminder.description,
                'reminder_type': reminder.reminder_type.value,
                'due_date': due_datetime.isoformat() if due_datetime else None,
                'status': reminder.status.value,
                'countdown': countdown_info,
                'user_timezone': user.timezone
            }
        })
        
    except Exception as e:
        logger.error(f"Error creating reminder: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_reminder_bp.route('/<int:reminder_id>', methods=['GET'])
@require_auth
def get_reminder(reminder_id):
    """Get a specific reminder with real-time countdown"""
    try:
        user_id = g.user_id
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        reminder = HealthReminder.query.filter_by(id=reminder_id, user_id=user_id).first()
        if not reminder:
            return jsonify({
                'success': False,
                'error': 'Reminder not found'
            }), 404
        
        # Get AI time manager
        ai_time_manager = get_ai_time_manager()
        
        # Format reminder with countdown
        # Combine due_date and due_time for proper datetime handling
        due_datetime = None
        if reminder.due_date:
            if reminder.due_time:
                due_datetime = datetime.combine(reminder.due_date, reminder.due_time)
            else:
                due_datetime = datetime.combine(reminder.due_date, time(9, 0))  # Default to 9 AM
        
        reminder_dict = {
            'id': reminder.id,
            'title': reminder.title,
            'description': reminder.description,
            'reminder_type': reminder.reminder_type.value if reminder.reminder_type else None,
            'due_date': due_datetime.isoformat() if due_datetime else None,
            'status': reminder.status.value if reminder.status else None,
            'recurrence_type': reminder.recurrence_type.value if reminder.recurrence_type else None,
            'recurrence_interval': reminder.recurrence_interval,
            'created_at': reminder.created_at.isoformat() if reminder.created_at else None,
            'updated_at': reminder.updated_at.isoformat() if reminder.updated_at else None,
            'advance_notice_days': reminder.days_before_reminder,
            'send_push': reminder.send_push,
            'send_email': reminder.send_email,
            'is_active': reminder.status == ReminderStatus.PENDING,
            'priority': reminder.priority  # Add priority to the response
        }
        
        # Add real-time countdown information
        if due_datetime:
            countdown_info = ai_time_manager.calculate_time_until_due(
                due_datetime=due_datetime,
                user_timezone=user.timezone
            )
            reminder_dict['countdown'] = countdown_info
            
            # Add optimal notification times
            notification_times = ai_time_manager.get_optimal_notification_times(
                due_datetime=due_datetime,
                user_timezone=user.timezone,
                advance_notice_days=reminder.days_before_reminder
            )
            reminder_dict['notification_times'] = [
                nt.isoformat() for nt in notification_times
            ]
        
        return jsonify({
            'success': True,
            'reminder': reminder_dict,
            'user_timezone': user.timezone,
            'user_timezone_abbreviation': ai_time_manager.get_timezone_abbreviation(user.timezone)
        })
        
    except Exception as e:
        logger.error(f"Error getting reminder: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_reminder_bp.route('/<int:reminder_id>', methods=['PUT'])
@require_auth
def update_reminder(reminder_id):
    """Update a reminder with AI time optimization"""
    try:
        user_id = g.user_id
        data = request.json or {}
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        reminder = HealthReminder.query.filter_by(id=reminder_id, user_id=user_id).first()
        if not reminder:
            return jsonify({
                'success': False,
                'error': 'Reminder not found'
            }), 404
        
        # Get AI time manager
        ai_time_manager = get_ai_time_manager()
        
        # Update fields
        if 'title' in data:
            reminder.title = data['title']
        
        if 'description' in data:
            reminder.description = data['description']
        
        if 'reminder_type' in data:
            reminder.reminder_type = ReminderType(data['reminder_type'])
        
        if 'due_date' in data:
            due_date_str = data['due_date']
            if due_date_str:
                try:
                    # Handle timezone conversion
                    if 'T' in due_date_str or ' ' in due_date_str:
                        due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                        if due_date.tzinfo is None:
                            due_date = user.convert_to_utc(due_date)
                    else:
                        # Date only - use AI suggestion or keep existing time
                        due_date_only = datetime.fromisoformat(due_date_str).date()
                        
                        if reminder.due_date:
                            # Keep existing time
                            existing_time = reminder.due_date.time()
                            due_datetime = datetime.combine(due_date_only, existing_time)
                            due_date = due_datetime.replace(tzinfo=timezone.utc)
                        else:
                            # Use AI suggestion
                            time_insight = ai_time_manager.suggest_optimal_reminder_time(
                                reminder_type=reminder.reminder_type.value,
                                user_timezone=user.timezone,
                                user_preferences=user.preferred_reminder_times
                            )
                            due_datetime = datetime.combine(due_date_only, time_insight.optimal_time)
                            due_date = user.convert_to_utc(due_datetime)
                    
                    reminder.due_date = due_date
                    
                    # 🎯 CRITICAL FIX: Update reminder_date and reminder_time when due_date changes
                    if reminder.due_date:
                        advance_notice_days = data.get('advance_notice_days', reminder.days_before_reminder)
                        calculated_reminder_date = reminder.due_date.date() - timedelta(days=advance_notice_days)
                        
                        # 🎯 FIX: If calculated reminder date is in the past, set to today
                        today = date.today()
                        if calculated_reminder_date < today:
                            logger.warning(f"⚠️  Calculated reminder date {calculated_reminder_date} is in the past, setting to today ({today})")
                            reminder.reminder_date = today
                        else:
                            reminder.reminder_date = calculated_reminder_date
                        
                        reminder.reminder_time = reminder.due_date.time() or time(9, 0)
                    
                except ValueError:
                    return jsonify({
                        'success': False,
                        'error': 'Invalid due date format'
                    }), 400
            else:
                reminder.due_date = None
                reminder.reminder_date = None
                reminder.reminder_time = None
        
        if 'status' in data:
            reminder.status = ReminderStatus(data['status'])
        
        if 'recurrence_type' in data:
            reminder.recurrence_type = RecurrenceType(data['recurrence_type']) if data['recurrence_type'] and data['recurrence_type'] != 'none' else RecurrenceType.NONE
        
        if 'recurrence_interval' in data:
            reminder.recurrence_interval = data['recurrence_interval']
        
        if 'advance_notice_days' in data:
            reminder.days_before_reminder = data['advance_notice_days']
            # 🎯 CRITICAL FIX: Recalculate reminder_date when advance notice changes
            if reminder.due_date:
                calculated_reminder_date = reminder.due_date.date() - timedelta(days=reminder.days_before_reminder)
                
                # 🎯 FIX: If calculated reminder date is in the past, set to today
                today = date.today()
                if calculated_reminder_date < today:
                    logger.warning(f"⚠️  Calculated reminder date {calculated_reminder_date} is in the past, setting to today ({today})")
                    reminder.reminder_date = today
                else:
                    reminder.reminder_date = calculated_reminder_date
        
        if 'send_push' in data:
            reminder.send_push = data['send_push']
        
        if 'send_email' in data:
            reminder.send_email = data['send_email']
        
        if 'priority' in data:
            reminder.priority = data['priority']
        
        reminder.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        # 🎯 CRITICAL FIX: Reschedule the updated reminder for notification
        try:
            from app.services.precision_reminder_scheduler import get_precision_scheduler
            scheduler = get_precision_scheduler()
            if scheduler and scheduler.is_running:
                success = scheduler.reschedule_reminder(reminder)
                if success:
                    logger.info(f"✅ Rescheduled updated reminder {reminder.id} for notification")
                else:
                    logger.warning(f"⚠️  Failed to reschedule updated reminder {reminder.id}")
            else:
                logger.warning(f"⚠️  Precision scheduler not available - reminder {reminder.id} not rescheduled")
        except Exception as e:
            logger.error(f"❌ Error rescheduling updated reminder {reminder.id}: {str(e)}")
            # Don't fail the request if scheduling fails
        
        # Get countdown information
        countdown_info = None
        # Combine due_date and due_time for proper datetime handling
        due_datetime = None
        if reminder.due_date:
            if reminder.due_time:
                due_datetime = datetime.combine(reminder.due_date, reminder.due_time)
            else:
                due_datetime = datetime.combine(reminder.due_date, time(9, 0))  # Default to 9 AM
        
        if due_datetime:
            countdown_info = ai_time_manager.calculate_time_until_due(
                due_datetime=due_datetime,
                user_timezone=user.timezone
            )
        
        return jsonify({
            'success': True,
            'message': 'Reminder updated successfully',
            'reminder': {
                'id': reminder.id,
                'title': reminder.title,
                'due_date': due_datetime.isoformat() if due_datetime else None,
                'status': reminder.status.value,
                'countdown': countdown_info
            }
        })
        
    except Exception as e:
        logger.error(f"Error updating reminder: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_reminder_bp.route('/<int:reminder_id>', methods=['DELETE'])
@require_auth
def delete_reminder(reminder_id):
    """Delete a reminder and all its related records"""
    try:
        user_id = g.user_id
        
        reminder = HealthReminder.query.filter_by(id=reminder_id, user_id=user_id).first()
        if not reminder:
            return jsonify({
                'success': False,
                'error': 'Reminder not found'
            }), 404
        
        # First, delete all related notification records to avoid foreign key constraint violation
        related_notifications = ReminderNotification.query.filter_by(reminder_id=reminder_id).all()
        for notification in related_notifications:
            db.session.delete(notification)
        
        # CRITICAL: Flush the session to ensure notifications are deleted first
        db.session.flush()
        
        # Now safely delete the reminder
        db.session.delete(reminder)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Reminder deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()  # Rollback in case of any error
        logger.error(f"Error deleting reminder: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_reminder_bp.route('/ai-suggestions', methods=['GET'])
@require_auth
def get_ai_suggestions():
    """Get AI-powered time suggestions for reminders"""
    try:
        user_id = g.user_id
        reminder_type = request.args.get('reminder_type', 'custom')
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        ai_time_manager = get_ai_time_manager()
        
        # Get optimal time suggestion
        time_insight = ai_time_manager.suggest_optimal_reminder_time(
            reminder_type=reminder_type,
            user_timezone=user.timezone,
            user_preferences=user.preferred_reminder_times
        )
        
        return jsonify({
            'success': True,
            'suggestion': {
                'hour': time_insight.optimal_time.hour,
                'minute': time_insight.optimal_time.minute,
                'formatted_12h': time_insight.optimal_time.strftime('%I:%M %p'),
                'formatted_24h': time_insight.optimal_time.strftime('%H:%M'),
                'confidence': time_insight.confidence,
                'reason': time_insight.reason,
                'user_pattern': time_insight.user_pattern
            },
            'user_timezone': user.timezone,
            'current_time': user.get_local_time().strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        logger.error(f"Error getting AI suggestions: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_reminder_bp.route('/scheduler/status', methods=['GET'])
def get_scheduler_status():
    """Get scheduler status"""
    try:
        scheduler_service = get_scheduler_service()
        status = scheduler_service.get_scheduler_status()
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        logger.error(f"Error getting scheduler status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_reminder_bp.route('/scheduler/trigger', methods=['POST'])
def trigger_scheduler():
    """Manually trigger reminder check"""
    try:
        scheduler_service = get_scheduler_service()
        result = scheduler_service.trigger_immediate_check()
        
        return jsonify({
            'success': True,
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Error triggering scheduler: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_reminder_bp.route('/test', methods=['GET'])
def test_endpoint():
    """Test endpoint to verify the blueprint is working"""
    return jsonify({
        'success': True,
        'message': 'Enhanced reminder system with AI time management is working!',
        'timestamp': datetime.now().isoformat()
    })

@enhanced_reminder_bp.route('/internal', methods=['POST'])
def create_reminder_internal():
    """Create a new reminder for internal FastAPI chat service (no auth required)"""
    try:
        data = request.get_json()
        
        # Debug: Log what Flask receives
        logger.info(f"🔍 Flask received data: {data}")
        
        # Extract user_id from request body for internal calls
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required for internal calls'
            }), 400
        
        # Get user for timezone conversion
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Set g.user_id for the reminder creation process
        g.user_id = user_id
        
        # Use the same logic as the main create_reminder endpoint
        title = data.get('title', 'Pet Care Reminder')
        description = data.get('description', '')
        
        # Map reminder type - handle both enum and string values
        reminder_type_str = data.get('reminder_type', 'custom')
        if reminder_type_str == 'grooming':
            reminder_type = ReminderType.GROOMING
        elif reminder_type_str == 'vaccination':
            reminder_type = ReminderType.VACCINATION
        elif reminder_type_str == 'medication':
            reminder_type = ReminderType.MEDICATION
        elif reminder_type_str == 'checkup':
            reminder_type = ReminderType.CHECKUP
        else:
            reminder_type = ReminderType.CUSTOM
            
        due_date_str = data.get('due_date')
        
        logger.info(f"🔔 Internal reminder creation for user {user_id}: {title}")
        logger.info(f"📅 Raw due_date_str: {due_date_str}")
        logger.info(f"👤 User timezone: {user.timezone}")
        
        # Parse due date with proper timezone handling
        due_date = None
        due_time = None
        
        if due_date_str:
            try:
                # Parse the datetime from FastAPI (should be in user's local time intent)
                parsed_datetime = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                
                # If it's a naive datetime, treat it as user local time
                if parsed_datetime.tzinfo is None:
                    logger.info(f"📅 Treating naive datetime as user local time: {parsed_datetime}")
                    # This is user's local time - store as date/time components
                    due_date = parsed_datetime.date()
                    due_time = parsed_datetime.time()
                    logger.info(f"📅 Stored as date: {due_date}, time: {due_time}")
                else:
                    # Convert to user's timezone first to get the intended local time
                    import pytz
                    user_tz = pytz.timezone(user.timezone)
                    local_datetime = parsed_datetime.astimezone(user_tz)
                    due_date = local_datetime.date()
                    due_time = local_datetime.time()
                    logger.info(f"📅 Converted to user timezone - date: {due_date}, time: {due_time}")
                    
            except (ValueError, AttributeError) as e:
                logger.warning(f"Could not parse due date: {due_date_str}, error: {e}")
                # Fallback: try to parse as just date
                try:
                    due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                except ValueError:
                    logger.error(f"Failed to parse due_date_str: {due_date_str}")
        
        # Debug: Log priority being used
        priority_value = data.get('priority', 'medium')
        logger.info(f"🎯 Using priority for internal reminder creation: {priority_value}")
        
        # Create the reminder with proper timezone handling
        reminder = HealthReminder(
            user_id=user_id,
            title=title,
            description=description,
            reminder_type=reminder_type,
            due_date=due_date,
            due_time=due_time,
            status=ReminderStatus.PENDING,
            send_email=data.get('send_email', True),
            priority=priority_value,  # ADD MISSING PRIORITY FIELD!
            created_at=datetime.now(timezone.utc)
        )
        
        db.session.add(reminder)
        db.session.commit()
        
        # 🎯 CRITICAL FIX: Schedule the new reminder for email notification
        try:
            from app.services.precision_reminder_scheduler import get_precision_scheduler
            scheduler = get_precision_scheduler()
            if scheduler and scheduler.is_running:
                success = scheduler.schedule_reminder(reminder)
                if success:
                    logger.info(f"✅ Scheduled new internal reminder {reminder.id} for email notification")
                else:
                    logger.warning(f"⚠️  Failed to schedule new internal reminder {reminder.id}")
            else:
                logger.warning(f"⚠️  Precision scheduler not available - internal reminder {reminder.id} not scheduled")
        except Exception as e:
            logger.error(f"❌ Error scheduling new internal reminder {reminder.id}: {str(e)}")
            # Don't fail the request if scheduling fails
        
        # Calculate display datetime for response
        display_datetime = None
        if due_date and due_time:
            display_datetime = datetime.combine(due_date, due_time)
        elif due_date:
            display_datetime = datetime.combine(due_date, datetime.min.time())
        
        logger.info(f"✅ Created internal reminder {reminder.id} for user {user_id}")
        logger.info(f"📅 Final reminder - date: {reminder.due_date}, time: {reminder.due_time}")
        
        return jsonify({
            'success': True,
            'reminder': {
                'id': reminder.id,
                'title': reminder.title,
                'description': reminder.description,
                'due_date': display_datetime.isoformat() if display_datetime else None,
                'reminder_type': reminder.reminder_type.value,
                'status': reminder.status.value,
                'priority': reminder.priority,  # ADD PRIORITY TO RESPONSE
                'user_timezone': user.timezone
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Error creating internal reminder: {str(e)}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_reminder_bp.route('/complete/<int:reminder_id>', methods=['POST'])
@require_auth
def mark_reminder_completed(reminder_id):
    """
    🎯 CONTEXT7: Mark a reminder as completed via API
    """
    try:
        user_id = g.user_id
        data = request.json or {}
        
        completion_method = data.get('completion_method', 'web_portal')
        notes = data.get('notes', '')
        
        # Get the reminder
        reminder = (db.session.query(HealthReminder)
                   .filter(HealthReminder.id == reminder_id, 
                          HealthReminder.user_id == user_id)
                   .first())
        
        if not reminder:
            return jsonify({
                'success': False,
                'error': 'Reminder not found or access denied'
            }), 404
        
        if reminder.status != ReminderStatus.PENDING:
            return jsonify({
                'success': False,
                'error': f'Reminder is already {reminder.status.value}'
            }), 400
        
        # Mark as completed
        reminder.mark_completed(
            completed_by='user',
            completion_method=completion_method
        )
        
        # Add completion notes if provided
        if notes:
            if not reminder.extra_data:
                reminder.extra_data = {}
            reminder.extra_data['completion_notes'] = notes
            reminder.extra_data['completed_at_detailed'] = {
                'timestamp': reminder.completed_at.isoformat(),
                'method': completion_method,
                'user_id': user_id
            }
        
        db.session.commit()
        
        current_app.logger.info(f"✅ Reminder {reminder_id} marked as completed by user {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Reminder marked as completed successfully',
            'reminder': {
                'id': reminder.id,
                'title': reminder.title,
                'status': reminder.status.value,
                'completed_at': reminder.completed_at.isoformat(),
                'completion_method': reminder.completion_method,
                'followup_notifications_stopped': reminder.followup_notifications_stopped
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error marking reminder {reminder_id} as completed: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to mark reminder as completed'
        }), 500

@enhanced_reminder_bp.route('/complete/<int:reminder_id>/email', methods=['GET'])
def complete_reminder_via_email(reminder_id):
    """
    🎯 CONTEXT7: Complete reminder via email button click (no auth required)
    """
    try:
        token = request.args.get('token')
        if not token:
            return jsonify({
                'success': False,
                'error': 'Completion token required'
            }), 400
        
        # Use follow-up service to handle token-based completion
        followup_service = get_followup_notification_service()
        result = followup_service.mark_reminder_completed_by_token(
            reminder_id, token, 'email_click'
        )
        
        if result['success']:
            # Redirect to success page with reminder info
            frontend_url = current_app.config.get('FRONTEND_URL')
            return redirect(f"{frontend_url}/reminder/completed?id={reminder_id}&method=email")
        else:
            # Redirect to error page
            frontend_url = current_app.config.get('FRONTEND_URL')
            return redirect(f"{frontend_url}/reminder/error?message={result['error']}")
            
    except Exception as e:
        current_app.logger.error(f"Error completing reminder via email: {str(e)}")
        frontend_url = current_app.config.get('FRONTEND_URL')
        return redirect(f"{frontend_url}/reminder/error?message=Server error")

@enhanced_reminder_bp.route('/complete/<int:reminder_id>/token', methods=['POST'])
def complete_reminder_via_token():
    """
    🎯 CONTEXT7: Complete reminder via API using completion token (for programmatic access)
    """
    try:
        data = request.json or {}
        reminder_id = data.get('reminder_id')
        token = data.get('token')
        completion_method = data.get('completion_method', 'api_token')
        
        if not reminder_id or not token:
            return jsonify({
                'success': False,
                'error': 'reminder_id and token are required'
            }), 400
        
        # Use follow-up service to handle token-based completion
        followup_service = get_followup_notification_service()
        result = followup_service.mark_reminder_completed_by_token(
            reminder_id, token, completion_method
        )
        
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        current_app.logger.error(f"Error completing reminder via token: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to complete reminder'
        }), 500

@enhanced_reminder_bp.route('/<int:reminder_id>/stop-followups', methods=['POST'])
@require_auth
def stop_followup_notifications(reminder_id):
    """
    🎯 CONTEXT7: Stop follow-up notifications for a reminder without marking as completed
    """
    try:
        user_id = g.user_id
        
        # Get the reminder
        reminder = (db.session.query(HealthReminder)
                   .filter(HealthReminder.id == reminder_id, 
                          HealthReminder.user_id == user_id)
                   .first())
        
        if not reminder:
            return jsonify({
                'success': False,
                'error': 'Reminder not found or access denied'
            }), 404
        
        # Stop follow-up notifications
        reminder.followup_notifications_stopped = True
        reminder.next_followup_at = None
        
        # Log the action
        if not reminder.extra_data:
            reminder.extra_data = {}
        reminder.extra_data['followups_stopped_by_user'] = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'followup_count_when_stopped': reminder.current_followup_count
        }
        
        db.session.commit()
        
        current_app.logger.info(f"🔕 Stopped follow-up notifications for reminder {reminder_id}")
        
        return jsonify({
            'success': True,
            'message': 'Follow-up notifications stopped successfully',
            'reminder': {
                'id': reminder.id,
                'title': reminder.title,
                'followup_notifications_stopped': True,
                'current_followup_count': reminder.current_followup_count
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error stopping follow-ups for reminder {reminder_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to stop follow-up notifications'
        }), 500

@enhanced_reminder_bp.route('/followup-analytics', methods=['GET'])
@require_auth
def get_followup_analytics():
    """
    🎯 CONTEXT7: Get follow-up notification analytics for the user
    """
    try:
        user_id = g.user_id
        days_back = request.args.get('days', 30, type=int)
        
        followup_service = get_followup_notification_service()
        analytics = followup_service.get_followup_analytics(user_id, days_back)
        
        return jsonify({
            'success': True,
            'analytics': analytics
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting follow-up analytics: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get analytics'
        }), 500

@enhanced_reminder_bp.route('/batch-complete', methods=['POST'])
@require_auth
def batch_complete_reminders():
    """
    🎯 CONTEXT7: Mark multiple reminders as completed in batch
    """
    try:
        user_id = g.user_id
        data = request.json or {}
        
        reminder_ids = data.get('reminder_ids', [])
        completion_method = data.get('completion_method', 'batch_web_portal')
        notes = data.get('notes', '')
        
        if not reminder_ids:
            return jsonify({
                'success': False,
                'error': 'reminder_ids list is required'
            }), 400
        
        results = {
            'completed': [],
            'failed': [],
            'already_completed': []
        }
        
        for reminder_id in reminder_ids:
            try:
                reminder = (db.session.query(HealthReminder)
                           .filter(HealthReminder.id == reminder_id, 
                                  HealthReminder.user_id == user_id)
                           .first())
                
                if not reminder:
                    results['failed'].append({
                        'id': reminder_id,
                        'error': 'Not found or access denied'
                    })
                    continue
                
                if reminder.status != ReminderStatus.PENDING:
                    results['already_completed'].append({
                        'id': reminder_id,
                        'status': reminder.status.value
                    })
                    continue
                
                # Mark as completed
                reminder.mark_completed(
                    completed_by='user',
                    completion_method=completion_method
                )
                
                # Add batch completion metadata
                if not reminder.extra_data:
                    reminder.extra_data = {}
                reminder.extra_data['batch_completion'] = {
                    'timestamp': reminder.completed_at.isoformat(),
                    'batch_id': f"batch_{user_id}_{int(datetime.utcnow().timestamp())}",
                    'notes': notes
                }
                
                results['completed'].append({
                    'id': reminder_id,
                    'title': reminder.title,
                    'completed_at': reminder.completed_at.isoformat()
                })
                
            except Exception as e:
                results['failed'].append({
                    'id': reminder_id,
                    'error': str(e)
                })
        
        db.session.commit()
        
        current_app.logger.info(f"📋 Batch completed {len(results['completed'])} reminders for user {user_id}")
        
        return jsonify({
            'success': True,
            'message': f"Batch operation completed: {len(results['completed'])} completed, {len(results['failed'])} failed",
            'results': results
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in batch reminder completion: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Batch completion failed'
        }), 500 