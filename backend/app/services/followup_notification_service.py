#!/usr/bin/env python3
"""
Follow-up Notification Service
Handles sending follow-up notifications for overdue reminders every 30 minutes for 5 times
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from flask import current_app
from app import db
from app.models.health_models import HealthReminder, ReminderStatus, ReminderNotification, NotificationStatus
from app.models.user import User
from app.services.email_service import EmailService
from app.services.reminder_notification_service import ReminderNotificationService
import uuid
import json

logger = logging.getLogger(__name__)

class FollowupNotificationService:
    """
    🎯 CONTEXT7 ENHANCEMENT: Advanced follow-up notification system
    
    Features:
    - Sends follow-up notifications every 30 minutes for 5 times after due time
    - Stops notifications when reminder is marked as completed
    - Email completion buttons for easy marking
    - Timezone-aware scheduling
    - Comprehensive tracking and analytics
    """
    
    def __init__(self):
        self.email_service = EmailService()
        self.notification_service = ReminderNotificationService()
    
    def check_and_send_followups(self) -> Dict[str, Any]:
        """
        Main method to check for overdue reminders and send follow-up notifications
        Should be called by scheduler every 5 minutes
        """
        try:
            current_app.logger.info("🔔 Starting follow-up notification check...")
            
            # Get all reminders that need follow-up notifications
            overdue_reminders = self._get_reminders_needing_followup()
            
            results = {
                'total_checked': len(overdue_reminders),
                'followups_sent': 0,
                'completed_series': 0,
                'errors': []
            }
            
            for reminder in overdue_reminders:
                try:
                    if self._send_followup_notification(reminder):
                        results['followups_sent'] += 1
                        
                        # Check if this was the last follow-up
                        if reminder.current_followup_count >= reminder.max_followup_count:
                            results['completed_series'] += 1
                            current_app.logger.info(f"📋 Completed follow-up series for reminder {reminder.id}")
                    
                except Exception as e:
                    error_msg = f"Error sending follow-up for reminder {reminder.id}: {str(e)}"
                    current_app.logger.error(error_msg)
                    results['errors'].append(error_msg)
            
            current_app.logger.info(f"✅ Follow-up check completed: {results}")
            return results
            
        except Exception as e:
            current_app.logger.error(f"❌ Follow-up notification check failed: {str(e)}")
            return {'error': str(e)}
    
    def _get_reminders_needing_followup(self) -> List[HealthReminder]:
        """
        Get all reminders that need follow-up notifications
        """
        try:
            now = datetime.utcnow()
            
            # Query reminders that need follow-up
            reminders = (db.session.query(HealthReminder)
                        .filter(
                            HealthReminder.status == ReminderStatus.PENDING,
                            HealthReminder.enable_followup_notifications == True,
                            HealthReminder.followup_notifications_stopped == False,
                            HealthReminder.current_followup_count < HealthReminder.max_followup_count
                        )
                        .all())
            
            # Filter reminders that should send follow-up now
            reminders_to_followup = []
            for reminder in reminders:
                if reminder.should_send_followup():
                    reminders_to_followup.append(reminder)
            
            current_app.logger.info(f"📋 Found {len(reminders_to_followup)} reminders needing follow-up")
            return reminders_to_followup
            
        except Exception as e:
            current_app.logger.error(f"Error getting reminders for follow-up: {str(e)}")
            return []
    
    def _send_followup_notification(self, reminder: HealthReminder) -> bool:
        """
        Send a follow-up notification for an overdue reminder
        """
        try:
            user = db.session.query(User).get(reminder.user_id)
            if not user:
                current_app.logger.warning(f"User {reminder.user_id} not found for reminder {reminder.id}")
                return False
            
            # Generate completion token for email buttons
            completion_token = reminder.generate_completion_token()
            
            # 🎯 CONTEXT7 FIX: Store completion token in extra_data with defensive handling
            if not reminder.extra_data or not isinstance(reminder.extra_data, dict):
                reminder.extra_data = {}
            
            # Ensure extra_data is a dictionary
            try:
                if isinstance(reminder.extra_data, str):
                    reminder.extra_data = json.loads(reminder.extra_data)
                elif not isinstance(reminder.extra_data, dict):
                    reminder.extra_data = {}
            except (json.JSONDecodeError, TypeError):
                # If we can't parse the existing data, start fresh
                reminder.extra_data = {}
            
            reminder.extra_data['completion_token'] = completion_token
            reminder.extra_data['completion_token_created'] = datetime.utcnow().isoformat()
            
            # Increment follow-up count
            reminder.current_followup_count += 1
            reminder.last_followup_sent_at = datetime.utcnow()
            
            # Calculate next follow-up time if not max reached
            if reminder.current_followup_count < reminder.max_followup_count:
                reminder.next_followup_at = reminder.calculate_next_followup_time()
            else:
                reminder.next_followup_at = None  # No more follow-ups
            
            # Send email notification with completion button
            if reminder.send_email and user.email:
                self._send_followup_email(reminder, user, completion_token)
            
            # Send push notification
            if reminder.send_push:
                self._send_followup_push(reminder, user)
            
            # Update database
            db.session.commit()
            
            current_app.logger.info(f"✅ Sent follow-up #{reminder.current_followup_count} for reminder {reminder.id}")
            return True
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error sending follow-up for reminder {reminder.id}: {str(e)}")
            return False
    
    def _send_followup_email(self, reminder: HealthReminder, user: User, completion_token: str):
        """
        Send follow-up email with completion button
        """
        try:
            # Get user's timezone for proper formatting
            user_timezone = user.timezone or 'UTC'
            
            # Calculate overdue time
            due_datetime = reminder.get_next_due_datetime()
            now = datetime.utcnow()
            overdue_hours = int((now - due_datetime).total_seconds() / 3600)
            
            # Create completion URL
            completion_url = f"{current_app.config.get('FRONTEND_URL', 'http://localhost:3000')}/reminder/complete/{reminder.id}?token={completion_token}"
            
            # Email subject
            subject = f"⏰ Follow-up #{reminder.current_followup_count}: {reminder.title} - Still Pending"
            
            # Create email content
            email_content = self._generate_followup_email_content(
                reminder, user, overdue_hours, completion_url, user_timezone
            )
            
            # 🎯 CONTEXT7 FIX: Use ReminderNotificationService for sending emails
            success, message = self.notification_service.send_reminder_email(reminder, user)
            
            if not success:
                current_app.logger.error(f"Failed to send follow-up email: {message}")
            
            # Log notification
            self._log_notification(reminder, user, 'email', subject, 'follow_up')
            
            current_app.logger.info(f"📧 Sent follow-up email for reminder {reminder.id}")
            
        except Exception as e:
            current_app.logger.error(f"Error sending follow-up email for reminder {reminder.id}: {str(e)}")
    
    def _send_followup_push(self, reminder: HealthReminder, user: User):
        """
        Send follow-up push notification
        """
        try:
            # Calculate overdue time
            due_datetime = reminder.get_next_due_datetime()
            now = datetime.utcnow()
            overdue_hours = int((now - due_datetime).total_seconds() / 3600)
            
            # Create push notification data
            push_data = {
                'title': f"⏰ Reminder Overdue: {reminder.title}",
                'body': f"This reminder is {overdue_hours}h overdue. Follow-up #{reminder.current_followup_count}/{reminder.max_followup_count}",
                'icon': '/assets/reminder-icon.png',
                'data': {
                    'reminder_id': reminder.id,
                    'type': 'followup_notification',
                    'followup_count': reminder.current_followup_count,
                    'overdue_hours': overdue_hours,
                    'url': f"/reminders/{reminder.id}"
                }
            }
            
            # 🎯 CONTEXT7 FIX: Use the correct push notification method
            success, message = self.notification_service.send_push_notification(reminder, user)
            
            if not success:
                current_app.logger.error(f"Failed to send follow-up push: {message}")
            
            # Log notification
            self._log_notification(reminder, user, 'push', push_data['title'], 'follow_up')
            
            current_app.logger.info(f"📱 Sent follow-up push for reminder {reminder.id}")
            
        except Exception as e:
            current_app.logger.error(f"Error sending follow-up push for reminder {reminder.id}: {str(e)}")
    
    def _generate_followup_email_content(self, reminder: HealthReminder, user: User, 
                                       overdue_hours: int, completion_url: str, 
                                       user_timezone: str) -> str:
        """
        Generate HTML content for follow-up email with completion button
        """
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #ff6b6b, #ffa726); padding: 20px; border-radius: 10px 10px 0 0;">
                <h2 style="color: white; margin: 0;">⏰ Reminder Follow-up #{reminder.current_followup_count}</h2>
            </div>
            
            <div style="background: #fff; padding: 30px; border: 1px solid #e0e0e0; border-radius: 0 0 10px 10px;">
                <h3 style="color: #333; margin-top: 0;">Hi {user.username},</h3>
                
                <p style="color: #666; font-size: 16px;">
                    Your reminder "<strong>{reminder.title}</strong>" was due <strong>{overdue_hours} hours ago</strong> 
                    and is still marked as pending.
                </p>
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h4 style="color: #333; margin-top: 0;">📋 Reminder Details:</h4>
                    <p><strong>Task:</strong> {reminder.title}</p>
                    <p><strong>Description:</strong> {reminder.description or 'No description'}</p>
                    <p><strong>Due:</strong> {reminder.due_date} at {reminder.due_time or 'Not specified'} ({user_timezone})</p>
                    <p><strong>Overdue by:</strong> {overdue_hours} hours</p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{completion_url}" 
                       style="background: #4CAF50; color: white; padding: 15px 30px; text-decoration: none; 
                              border-radius: 25px; font-weight: bold; font-size: 16px; display: inline-block;
                              box-shadow: 0 3px 10px rgba(76, 175, 80, 0.3);">
                        ✅ Mark as Completed
                    </a>
                </div>
                
                <div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0; color: #856404;">
                        <strong>📬 Follow-up #{reminder.current_followup_count} of {reminder.max_followup_count}</strong><br>
                        You'll receive {reminder.max_followup_count - reminder.current_followup_count} more reminders 
                        every 30 minutes if this task remains incomplete.
                    </p>
                </div>
                
                <p style="color: #666; font-size: 14px; margin-top: 30px;">
                    Click the button above to mark this reminder as completed and stop receiving follow-up notifications.
                    You can also complete this reminder from your 
                    <a href="{current_app.config.get('FRONTEND_URL', 'http://localhost:3000')}/reminders">dashboard</a>.
                </p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                
                <p style="color: #999; font-size: 12px; text-align: center;">
                    This is an automated follow-up from Mr. White's Pet Care Assistant.<br>
                    If you believe this is an error, please contact support.
                </p>
            </div>
        </div>
        """
    
    def _log_notification(self, reminder: HealthReminder, user: User, 
                         notification_type: str, subject: str, category: str):
        """
        Log notification attempt in the database
        """
        try:
            notification = ReminderNotification(
                reminder_id=reminder.id,
                user_id=user.id,
                notification_type=notification_type,
                status=NotificationStatus.SENT,
                scheduled_at=datetime.utcnow(),
                sent_at=datetime.utcnow(),
                subject=subject,
                message=f"{category} notification #{reminder.current_followup_count}",
                recipient=user.email if notification_type == 'email' else 'push_device'
            )
            
            db.session.add(notification)
            db.session.commit()
            
        except Exception as e:
            current_app.logger.error(f"Error logging notification: {str(e)}")
    
    def mark_reminder_completed_by_token(self, reminder_id: int, token: str, 
                                       completion_method: str = 'email_click') -> Dict[str, Any]:
        """
        Mark reminder as completed using email completion token
        """
        try:
            reminder = db.session.query(HealthReminder).get(reminder_id)
            if not reminder:
                return {'success': False, 'error': 'Reminder not found'}
            
            # Verify token
            if not reminder.extra_data or reminder.extra_data.get('completion_token') != token:
                return {'success': False, 'error': 'Invalid completion token'}
            
            # Check token age (expire after 7 days)
            token_created = reminder.extra_data.get('completion_token_created')
            if token_created:
                token_age = datetime.utcnow() - datetime.fromisoformat(token_created)
                if token_age.days > 7:
                    return {'success': False, 'error': 'Completion token expired'}
            
            # Mark as completed
            reminder.mark_completed(
                completed_by='email_button',
                completion_method=completion_method
            )
            
            # Clear completion token
            if reminder.extra_data:
                reminder.extra_data.pop('completion_token', None)
                reminder.extra_data.pop('completion_token_created', None)
            
            db.session.commit()
            
            current_app.logger.info(f"✅ Reminder {reminder_id} marked as completed via {completion_method}")
            
            return {
                'success': True,
                'message': 'Reminder marked as completed successfully',
                'reminder': {
                    'id': reminder.id,
                    'title': reminder.title,
                    'completed_at': reminder.completed_at.isoformat(),
                    'completion_method': reminder.completion_method
                }
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error marking reminder completed by token: {str(e)}")
            return {'success': False, 'error': f'Failed to complete reminder: {str(e)}'}
    
    def get_followup_analytics(self, user_id: Optional[int] = None, 
                             days_back: int = 30) -> Dict[str, Any]:
        """
        Get analytics about follow-up notifications
        """
        try:
            from datetime import datetime, timedelta
            from sqlalchemy import func
            
            start_date = datetime.utcnow() - timedelta(days=days_back)
            
            # Base query
            base_query = db.session.query(HealthReminder)
            if user_id:
                base_query = base_query.filter(HealthReminder.user_id == user_id)
            
            # Analytics data
            analytics = {
                'period_days': days_back,
                'total_reminders': base_query.filter(
                    HealthReminder.created_at >= start_date
                ).count(),
                'reminders_with_followups': base_query.filter(
                    HealthReminder.current_followup_count > 0,
                    HealthReminder.created_at >= start_date
                ).count(),
                'completed_via_email': base_query.filter(
                    HealthReminder.completion_method == 'email_click',
                    HealthReminder.completed_at >= start_date
                ).count(),
                'total_followups_sent': db.session.query(
                    func.sum(HealthReminder.current_followup_count)
                ).filter(
                    HealthReminder.created_at >= start_date
                ).scalar() or 0,
                'average_followups_per_reminder': 0,
                'completion_rate_after_followup': 0
            }
            
            # Calculate averages
            if analytics['reminders_with_followups'] > 0:
                analytics['average_followups_per_reminder'] = round(
                    analytics['total_followups_sent'] / analytics['reminders_with_followups'], 2
                )
            
            # Completion rate after follow-up
            followup_reminders = analytics['reminders_with_followups']
            completed_after_followup = base_query.filter(
                HealthReminder.current_followup_count > 0,
                HealthReminder.status == ReminderStatus.COMPLETED,
                HealthReminder.created_at >= start_date
            ).count()
            
            if followup_reminders > 0:
                analytics['completion_rate_after_followup'] = round(
                    (completed_after_followup / followup_reminders) * 100, 2
                )
            
            return analytics
            
        except Exception as e:
            current_app.logger.error(f"Error getting follow-up analytics: {str(e)}")
            return {'error': str(e)}


# Global service instance
_followup_service_instance = None

def get_followup_notification_service() -> FollowupNotificationService:
    """Get the global follow-up notification service instance"""
    global _followup_service_instance
    if _followup_service_instance is None:
        _followup_service_instance = FollowupNotificationService()
    return _followup_service_instance 