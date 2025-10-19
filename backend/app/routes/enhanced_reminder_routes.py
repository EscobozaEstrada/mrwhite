#!/usr/bin/env python3
"""
Enhanced Reminder Routes - API endpoints for the enhanced reminder system with AI time management
"""

from flask import Blueprint, request, jsonify, current_app, g, redirect
from datetime import datetime, date, time, timezone
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
        
        # Format reminders with timezone-aware countdown
        formatted_reminders = []
        for reminder in reminders:
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
                'is_active': reminder.status == ReminderStatus.PENDING
            }
            
            # Add real-time countdown information
            if due_datetime:
                countdown_info = ai_time_manager.calculate_time_until_due(
                    due_datetime=due_datetime,
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
        if due_date_str:
            try:
                # If user provides time, use it; otherwise use AI suggestion
                if 'T' in due_date_str or ' ' in due_date_str:
                    # User provided specific time
                    due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                    if due_date.tzinfo is None:
                        # Assume user's local time
                        due_date = user.convert_to_utc(due_date)
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
                    
                    # Combine date with AI-suggested time
                    due_datetime = datetime.combine(due_date_only, time_insight.optimal_time)
                    due_date = user.convert_to_utc(due_datetime)
                    
                    # Learn from this AI suggestion for future improvements
                    ai_time_manager.learn_user_patterns(
                        user_id=user_id,
                        reminder_type=reminder_type,
                        chosen_time=time_insight.optimal_time,
                        user_timezone=user.timezone
                    )
                
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid due date format'
                }), 400
        else:
            due_date = None
        
        # Create reminder
        reminder = HealthReminder(
            user_id=user_id,
            title=title,
            description=data.get('description', ''),
            reminder_type=ReminderType(data.get('reminder_type', 'custom')),
            due_date=due_date,
            status=ReminderStatus(data.get('status', 'pending')),
            recurrence_type=RecurrenceType(data.get('recurrence_type', 'none')) if data.get('recurrence_type') else None,
            recurrence_interval=data.get('recurrence_interval', 1),
            days_before_reminder=data.get('advance_notice_days', 1),
            send_push=data.get('send_push', True),
            send_email=data.get('send_email', False),
        )
        
        db.session.add(reminder)
        db.session.commit()
        
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
            'is_active': reminder.status == ReminderStatus.PENDING
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
                    
                except ValueError:
                    return jsonify({
                        'success': False,
                        'error': 'Invalid due date format'
                    }), 400
            else:
                reminder.due_date = None
        
        if 'status' in data:
            reminder.status = ReminderStatus(data['status'])
        
        if 'recurrence_type' in data:
            reminder.recurrence_type = RecurrenceType(data['recurrence_type']) if data['recurrence_type'] else None
        
        if 'recurrence_interval' in data:
            reminder.recurrence_interval = data['recurrence_interval']
        
        if 'advance_notice_days' in data:
            reminder.days_before_reminder = data['advance_notice_days']
        
        if 'send_push' in data:
            reminder.send_push = data['send_push']
        
        if 'send_email' in data:
            reminder.send_email = data['send_email']
        
        reminder.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
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
            frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:3000')
            return redirect(f"{frontend_url}/reminder/completed?id={reminder_id}&method=email")
        else:
            # Redirect to error page
            frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:3000')
            return redirect(f"{frontend_url}/reminder/error?message={result['error']}")
            
    except Exception as e:
        current_app.logger.error(f"Error completing reminder via email: {str(e)}")
        frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:3000')
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