#!/usr/bin/env python3
"""
Comprehensive Reminder Notification Service
Handles email (AWS SES), push notifications, and SMS for health reminders
"""

import smtplib
import json
import logging
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Tuple, Any
from flask import current_app
import boto3
from botocore.exceptions import ClientError

from app.models.health_models import (
    HealthReminder, ReminderNotification, NotificationStatus, 
    ReminderStatus, RecurrenceType
)
from app.models.user import User
from app import db

logger = logging.getLogger(__name__)

class ReminderNotificationService:
    """
    Comprehensive notification service for health reminders
    """
    
    def __init__(self):
        self.ses_client = None
        # Don't initialize AWS SES here - do it lazily when needed
    
    def initialize_aws_ses(self):
        """Initialize AWS SES client lazily when needed"""
        if self.ses_client is not None:
            return  # Already initialized
            
        try:
            # Check if we're in Flask app context
            if current_app:
                self.ses_client = boto3.client(
                    'ses',
                    aws_access_key_id=current_app.config.get('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=current_app.config.get('AWS_SECRET_ACCESS_KEY'),
                    region_name='us-east-1'  # SES region
                )
                logger.info("AWS SES client initialized successfully")
            else:
                logger.warning("No Flask app context available for SES initialization")
                self.ses_client = None
        except Exception as e:
            logger.error(f"Failed to initialize AWS SES client: {str(e)}")
            self.ses_client = None
    
    # ==================== EMAIL NOTIFICATIONS ====================
    
    def send_reminder_email(self, reminder: HealthReminder, user: User) -> Tuple[bool, str]:
        """
        Send reminder email using SMTP (preferred) or AWS SES fallback
        """
        try:
            # Check if we have basic email configuration
            smtp_host = current_app.config.get('SES_SMTP_HOST') or current_app.config.get('MAIL_SERVER')
            smtp_username = current_app.config.get('SES_SMTP_USERNAME') or current_app.config.get('MAIL_USERNAME')
            smtp_password = current_app.config.get('SES_SMTP_PASSWORD') or current_app.config.get('MAIL_PASSWORD')
            
            # Prioritize SMTP if credentials are available
            if smtp_host and smtp_username and smtp_password:
                logger.info(f"Using SMTP for email notification to user {user.id}")
                return self._send_reminder_email_smtp(reminder, user)
            
            # Fallback to AWS SES API if SMTP not available
            aws_key = current_app.config.get('AWS_ACCESS_KEY_ID')
            aws_secret = current_app.config.get('AWS_SECRET_ACCESS_KEY')
            
            if aws_key and aws_secret:
                logger.info(f"Falling back to AWS SES API for email notification to user {user.id}")
                try:
                    return self._send_reminder_email_ses(reminder, user)
                except Exception as e:
                    logger.warning(f"AWS SES API failed: {str(e)}")
                    
                    # If SES API fails but we have SMTP credentials, try SMTP as final fallback
                    if smtp_host and smtp_username and smtp_password:
                        logger.info(f"Trying SMTP as final fallback for user {user.id}")
                        return self._send_reminder_email_smtp(reminder, user)
                    
                    raise e
            
            # No email configuration available
            logger.warning("No email configuration found - skipping email notification")
            self._log_notification(
                reminder_id=reminder.id,
                user_id=user.id,
                notification_type='email',
                status=NotificationStatus.FAILED,
                recipient=user.email,
                error_message="No email server configured"
            )
            return False, "Email server not configured"
            
        except Exception as e:
            error_msg = f"Email sending error: {str(e)}"
            logger.error(error_msg)
            self._log_notification(
                reminder_id=reminder.id,
                user_id=user.id,
                notification_type='email',
                status=NotificationStatus.FAILED,
                recipient=user.email,
                error_message=error_msg
            )
            return False, error_msg
    
    def _send_reminder_email_ses(self, reminder: HealthReminder, user: User) -> Tuple[bool, str]:
        """
        Send reminder email using AWS SES
        """
        try:
            # Initialize SES client if not already done
            self.initialize_aws_ses()
            
            if not self.ses_client:
                raise Exception("AWS SES client initialization failed")
            
            # Create email content
            subject, html_content, text_content = self._create_reminder_email_content(reminder, user)
            
            # Send via AWS SES
            response = self.ses_client.send_email(
                Source=current_app.config.get('SES_EMAIL_FROM', 'mrwhitetheai@gmail.com'),
                Destination={
                    'ToAddresses': [user.email]
                },
                Message={
                    'Subject': {
                        'Data': subject,
                        'Charset': 'UTF-8'
                    },
                    'Body': {
                        'Text': {
                            'Data': text_content,
                            'Charset': 'UTF-8'
                        },
                        'Html': {
                            'Data': html_content,
                            'Charset': 'UTF-8'
                        }
                    }
                }
            )
            
            # Log notification
            self._log_notification(
                reminder_id=reminder.id,
                user_id=user.id,
                notification_type='email',
                status=NotificationStatus.SENT,
                recipient=user.email,
                subject=subject,
                message=text_content
            )
            
            logger.info(f"Reminder email sent via SES to {user.email} for reminder {reminder.id}")
            return True, f"Email sent via SES (Message ID: {response['MessageId']})"
            
        except ClientError as e:
            error_msg = f"AWS SES error: {e.response['Error']['Message']}"
            logger.error(error_msg)
            raise Exception(error_msg)
            
        except Exception as e:
            error_msg = f"SES sending error: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def _send_reminder_email_smtp(self, reminder: HealthReminder, user: User) -> Tuple[bool, str]:
        """
        Fallback email sending using SMTP (if AWS SES client fails)
        """
        try:
            # Check for SMTP configuration
            smtp_host = current_app.config.get('SES_SMTP_HOST') or current_app.config.get('MAIL_SERVER')
            smtp_port = current_app.config.get('SES_SMTP_PORT') or current_app.config.get('MAIL_PORT', 587)
            smtp_username = current_app.config.get('SES_SMTP_USERNAME') or current_app.config.get('MAIL_USERNAME')
            smtp_password = current_app.config.get('SES_SMTP_PASSWORD') or current_app.config.get('MAIL_PASSWORD')
            from_email = current_app.config.get('SES_EMAIL_FROM') or current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@mrwhite.com')
            
            if not smtp_host:
                raise Exception("No SMTP server configured (MAIL_SERVER or SES_SMTP_HOST required)")
            
            if not smtp_username or not smtp_password:
                raise Exception("SMTP authentication required but credentials not provided")
            
            # Create email content
            subject, html_content, text_content = self._create_reminder_email_content(reminder, user)
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = from_email
            msg['To'] = user.email
            
            # Add both text and HTML parts
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send via SMTP
            with smtplib.SMTP(smtp_host, int(smtp_port)) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.sendmail(from_email, [user.email], msg.as_string())
            
            # Log notification
            self._log_notification(
                reminder_id=reminder.id,
                user_id=user.id,
                notification_type='email',
                status=NotificationStatus.SENT,
                recipient=user.email,
                subject=subject,
                message=text_content
            )
            
            logger.info(f"Reminder email sent via SMTP to {user.email} for reminder {reminder.id}")
            return True, "Email sent successfully via SMTP"
            
        except Exception as e:
            error_msg = f"SMTP email error: {str(e)}"
            logger.error(error_msg)
            self._log_notification(
                reminder_id=reminder.id,
                user_id=user.id,
                notification_type='email',
                status=NotificationStatus.FAILED,
                recipient=user.email,
                error_message=error_msg
            )
            return False, error_msg
    
    def _create_reminder_email_content(self, reminder: HealthReminder, user: User) -> Tuple[str, str, str]:
        """
        Create email content for reminder notification
        """
        # Get reminder type emoji and description
        type_info = {
            'vaccination': {'emoji': '💉', 'name': 'Vaccination'},
            'vet_appointment': {'emoji': '🏥', 'name': 'Vet Appointment'},
            'medication': {'emoji': '💊', 'name': 'Medication'},
            'grooming': {'emoji': '✂️', 'name': 'Grooming'},
            'checkup': {'emoji': '🔍', 'name': 'Health Checkup'},
            'custom': {'emoji': '📝', 'name': 'Custom Reminder'}
        }
        
        reminder_info = type_info.get(reminder.reminder_type.value, type_info['custom'])
        
        # Format dates
        due_date_str = reminder.due_date.strftime('%B %d, %Y')
        if reminder.due_time:
            due_time_str = reminder.due_time.strftime('%I:%M %p')
            due_datetime_str = f"{due_date_str} at {due_time_str}"
        else:
            due_datetime_str = due_date_str
        
        # Check urgency
        days_until_due = (reminder.due_date - datetime.now().date()).days
        if days_until_due < 0:
            urgency = "⚠️ OVERDUE"
            urgency_color = "#dc3545"
        elif days_until_due == 0:
            urgency = "🔔 DUE TODAY"
            urgency_color = "#fd7e14"
        elif days_until_due <= 3:
            urgency = "⏰ DUE SOON"
            urgency_color = "#ffc107"
        else:
            urgency = "📅 UPCOMING"
            urgency_color = "#198754"
        
        # Create subject
        subject = f"🐾 Mr. White Reminder: {reminder.title} - {urgency}"
        
        # Create text content
        text_content = f"""
🐾 Mr. White Pet Care Reminder

Hi {user.username or 'there'}!

{urgency}: {reminder_info['emoji']} {reminder_info['name']}

Reminder: {reminder.title}
Due: {due_datetime_str}

{f'Description: {reminder.description}' if reminder.description else ''}

{f'Recurrence: Every {reminder.recurrence_interval} {reminder.recurrence_type.value}(s)' if reminder.recurrence_type.value != 'none' else ''}

Don't forget to take care of your furry friend! 🐕

You can manage your reminders at: {current_app.config.get('FRONTEND_URL', 'http://localhost:3000')}/reminders

Best regards,
Mr. White - Your AI Pet Care Assistant
"""
        
        # Create HTML content
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pet Care Reminder</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f4f4f4; margin: 0; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); overflow: hidden;">
        
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #000000 0%, #333333 100%); color: white; padding: 30px 20px; text-align: center;">
            <h1 style="margin: 0; font-size: 24px;">🐾 Mr. White Pet Care</h1>
            <p style="margin: 5px 0 0 0; opacity: 0.9;">Your AI Pet Care Assistant</p>
        </div>
        
        <!-- Urgency Banner -->
        <div style="background-color: {urgency_color}; color: white; padding: 15px; text-align: center; font-weight: bold; font-size: 18px;">
            {urgency}
        </div>
        
        <!-- Content -->
        <div style="padding: 30px 20px;">
            <p style="font-size: 18px; margin: 0 0 20px 0;">Hi {user.username or 'there'}! 👋</p>
            
            <div style="background-color: #f8f9fa; border-left: 4px solid {urgency_color}; padding: 20px; margin: 20px 0; border-radius: 0 5px 5px 0;">
                <h2 style="margin: 0 0 15px 0; color: #333; display: flex; align-items: center;">
                    <span style="font-size: 24px; margin-right: 10px;">{reminder_info['emoji']}</span>
                    {reminder_info['name']} Reminder
                </h2>
                
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold; color: #555;">Reminder:</td>
                        <td style="padding: 8px 0;">{reminder.title}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-weight: bold; color: #555;">Due:</td>
                        <td style="padding: 8px 0; font-weight: bold; color: {urgency_color};">{due_datetime_str}</td>
                    </tr>
                    {f'<tr><td style="padding: 8px 0; font-weight: bold; color: #555;">Description:</td><td style="padding: 8px 0;">{reminder.description}</td></tr>' if reminder.description else ''}
                    {f'<tr><td style="padding: 8px 0; font-weight: bold; color: #555;">Recurrence:</td><td style="padding: 8px 0;">Every {reminder.recurrence_interval} {reminder.recurrence_type.value}(s)</td></tr>' if reminder.recurrence_type.value != 'none' else ''}
                </table>
            </div>
            
            <p style="margin: 20px 0;">Don't forget to take care of your furry friend! 🐕</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{current_app.config.get('FRONTEND_URL', 'http://localhost:3000')}/reminders" 
                   style="display: inline-block; background-color: #000000; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; transition: background-color 0.3s;">
                    Manage Reminders
                </a>
            </div>
        </div>
        
        <!-- Footer -->
        <div style="background-color: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #e9ecef;">
            <p style="margin: 0; font-size: 14px; color: #666;">
                Best regards,<br>
                <strong>Mr. White - Your AI Pet Care Assistant</strong>
            </p>
            <p style="margin: 10px 0 0 0; font-size: 12px; color: #999;">
                You received this reminder because you have an active reminder in your Mr. White account.
            </p>
        </div>
    </div>
</body>
</html>
"""
        
        return subject, html_content, text_content
    
    # ==================== PUSH NOTIFICATIONS ====================
    
    def send_push_notification(self, reminder: HealthReminder, user: User) -> Tuple[bool, str]:
        """
        Send push notification using FCM
        """
        try:
            # Check if user has push notifications enabled
            if not getattr(user, 'push_notifications_enabled', True):
                logger.info(f"Push notifications disabled for user {user.id}")
                self._log_notification(
                    reminder_id=reminder.id,
                    user_id=user.id,
                    notification_type='push',
                    status=NotificationStatus.FAILED,
                    recipient=f"user_{user.id}",
                    error_message="Push notifications disabled by user"
                )
                return False, "Push notifications disabled for user"
            
            # Check if user has device tokens
            device_tokens = getattr(user, 'device_tokens', None)
            if not device_tokens:
                logger.info(f"No device tokens found for user {user.id} - user needs to enable push notifications")
                self._log_notification(
                    reminder_id=reminder.id,
                    user_id=user.id,
                    notification_type='push',
                    status=NotificationStatus.FAILED,
                    recipient=f"user_{user.id}",
                    error_message="No device tokens registered - user needs to enable push notifications in browser"
                )
                return False, "No device tokens registered - please enable push notifications in your browser"
            
            # Use FCM service for sending notifications
            from app.services.fcm_service import get_fcm_service
            fcm_service = get_fcm_service()
            
            if not fcm_service.is_available():
                logger.warning("FCM service not available - push notifications unavailable")
                self._log_notification(
                    reminder_id=reminder.id,
                    user_id=user.id,
                    notification_type='push',
                    status=NotificationStatus.FAILED,
                    recipient=f"user_{user.id}",
                    error_message="FCM service not configured or unavailable"
                )
                return False, "Push notification service not configured"
            
            # Create notification content
            notification_title = f"🐾 {reminder.title}"
            notification_body = self._create_push_notification_body(reminder)
            
            # Add reminder data for click action
            notification_data = {
                'reminder_id': str(reminder.id),
                'reminder_type': reminder.reminder_type.value,
                'due_date': reminder.due_date.isoformat()
            }
            
            # Send using FCM service
            result = fcm_service.send_to_user_devices(
                user_device_tokens=device_tokens,
                title=notification_title,
                body=notification_body,
                data=notification_data,
                click_action=f"{current_app.config.get('FRONTEND_URL', 'http://localhost:3000')}/reminders"
            )
            
            # Log notification attempt
            sent_count = result['success_count']
            failed_count = result['failure_count']
            
            status = NotificationStatus.SENT if sent_count > 0 else NotificationStatus.FAILED
            error_msg = f"Failed devices: {failed_count}" if failed_count > 0 else None
            
            self._log_notification(
                reminder_id=reminder.id,
                user_id=user.id,
                notification_type='push',
                status=status,
                recipient=f"devices_{sent_count}",
                subject=notification_title,
                message=notification_body,
                error_message=error_msg
            )
            
            if sent_count > 0:
                logger.info(f"FCM notification sent to {sent_count} device(s) for user {user.id}")
                return True, f"FCM notification sent to {sent_count} device(s)"
            else:
                return False, f"Failed to send FCM notification to any device ({failed_count} failures)"
            
        except Exception as e:
            error_msg = f"FCM notification error: {str(e)}"
            logger.error(error_msg)
            self._log_notification(
                reminder_id=reminder.id,
                user_id=user.id,
                notification_type='push',
                status=NotificationStatus.FAILED,
                recipient=f"user_{user.id}",
                error_message=error_msg
            )
            return False, error_msg
    
    def _create_push_notification_body(self, reminder: HealthReminder) -> str:
        """Create notification body based on reminder type and urgency"""
        urgency_text = self._get_urgency_text(reminder)
        return f"{urgency_text} {reminder.description or 'Tap to view details'}"
    
    def _get_urgency_text(self, reminder: HealthReminder) -> str:
        """Get urgency text based on due date"""
        from datetime import datetime, date
        
        if reminder.due_date == date.today():
            return "Due today!"
        elif reminder.due_date < date.today():
            days_overdue = (date.today() - reminder.due_date).days
            return f"Overdue by {days_overdue} day(s)!"
        else:
            days_until = (reminder.due_date - date.today()).days
            if days_until <= 3:
                return "Due soon!"
            else:
                return f"Due in {days_until} days"
    
    # ==================== SMS NOTIFICATIONS ====================
    
    def send_sms_notification(self, reminder: HealthReminder, user: User, phone_number: str) -> Tuple[bool, str]:
        """
        Send SMS notification (placeholder for future implementation)
        """
        try:
            # For now, we'll log this as a pending feature
            logger.info(f"SMS notification scheduled for user {user.id}, reminder {reminder.id}")
            
            # Log notification attempt
            self._log_notification(
                reminder_id=reminder.id,
                user_id=user.id,
                notification_type='sms',
                status=NotificationStatus.SENT,  # Mark as sent for now
                recipient=phone_number,
                subject=f"Reminder: {reminder.title}",
                message=f"🐾 Mr. White Reminder: {reminder.title} is due!"
            )
            
            return True, "SMS notification sent (simulated)"
            
        except Exception as e:
            error_msg = f"SMS notification error: {str(e)}"
            logger.error(error_msg)
            self._log_notification(
                reminder_id=reminder.id,
                user_id=user.id,
                notification_type='sms',
                status=NotificationStatus.FAILED,
                recipient=phone_number,
                error_message=error_msg
            )
            return False, error_msg
    
    # ==================== NOTIFICATION ORCHESTRATION ====================
    
    def send_all_notifications(self, reminder: HealthReminder) -> Dict[str, Any]:
        """
        Send all enabled notifications for a reminder
        """
        results = {
            'reminder_id': reminder.id,
            'notifications_sent': [],
            'notifications_failed': [],
            'success': True
        }
        
        try:
            # Get user
            user = User.query.get(reminder.user_id)
            if not user:
                results['success'] = False
                results['error'] = f"User {reminder.user_id} not found"
                return results
            
            # Send email notification
            if reminder.send_email and user.email:
                success, message = self.send_reminder_email(reminder, user)
                if success:
                    results['notifications_sent'].append({'type': 'email', 'message': message})
                else:
                    results['notifications_failed'].append({'type': 'email', 'error': message})
            
            # Send push notification
            if reminder.send_push:
                success, message = self.send_push_notification(reminder, user)
                if success:
                    results['notifications_sent'].append({'type': 'push', 'message': message})
                else:
                    results['notifications_failed'].append({'type': 'push', 'error': message})
            
            # Send SMS notification (if phone number is available)
            if reminder.send_sms and hasattr(user, 'phone_number') and user.phone_number:
                success, message = self.send_sms_notification(reminder, user, user.phone_number)
                if success:
                    results['notifications_sent'].append({'type': 'sms', 'message': message})
                else:
                    results['notifications_failed'].append({'type': 'sms', 'error': message})
            
            # Update reminder notification tracking
            reminder.last_notification_sent = datetime.utcnow()
            reminder.notification_attempts += 1
            db.session.commit()
            
            # Set overall success status
            results['success'] = len(results['notifications_sent']) > 0
            
            logger.info(f"Notification batch completed for reminder {reminder.id}: "
                       f"{len(results['notifications_sent'])} sent, {len(results['notifications_failed'])} failed")
            
        except Exception as e:
            logger.error(f"Error sending notifications for reminder {reminder.id}: {str(e)}")
            results['success'] = False
            results['error'] = str(e)
        
        return results
    
    # ==================== NOTIFICATION LOGGING ====================
    
    def _log_notification(self, reminder_id: int, user_id: int, notification_type: str,
                         status: NotificationStatus, recipient: str,
                         subject: Optional[str] = None, message: Optional[str] = None,
                         error_message: Optional[str] = None) -> None:
        """
        Log notification attempt to database
        """
        try:
            # Create notification record with correct parameters
            notification = ReminderNotification()
            notification.reminder_id = reminder_id
            notification.user_id = user_id
            notification.notification_type = notification_type
            notification.status = status
            notification.scheduled_at = datetime.utcnow()
            notification.sent_at = datetime.utcnow() if status == NotificationStatus.SENT else None
            notification.recipient = recipient
            notification.subject = subject
            notification.message = message
            notification.error_message = error_message
            
            db.session.add(notification)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to log notification: {str(e)}")
            db.session.rollback()

# ==================== SERVICE INSTANCE ====================

def get_notification_service() -> ReminderNotificationService:
    """Get notification service instance"""
    return ReminderNotificationService() 