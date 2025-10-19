#!/usr/bin/env python3
"""
Reminder Scheduler Service
Handles scheduled checking and processing of reminders, recurring reminders, and notification dispatch
"""

import logging
import threading
import time
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
from flask import current_app
from sqlalchemy import and_, or_
import schedule
import json

from app import db
from app.models.health_models import (
    HealthReminder, ReminderStatus, RecurrenceType, 
    ReminderNotification, NotificationStatus
)
from app.models.user import User
from app.services.reminder_notification_service import get_notification_service

logger = logging.getLogger(__name__)

class ReminderSchedulerService:
    """
    Comprehensive reminder scheduler service
    """
    
    def __init__(self, app=None):
        self.notification_service = get_notification_service()
        self.is_running = False
        self.scheduler_thread = None
        self.last_check = None
        self.app = app
    
    def set_app(self, app):
        """Set the Flask app instance"""
        self.app = app
        self.app = app
    
    def set_app(self, app):
        """Set the Flask app instance"""
        self.app = app
    
    def set_app(self, app):
        """Set the Flask app instance for context management"""
        self.app = app
    
    def set_app(self, app):
        """Set the Flask app instance"""
        self.app = app
    
    # ==================== MAIN SCHEDULER FUNCTIONS ====================
    
    def start_scheduler(self):
        """Start the reminder scheduler"""
        if self.is_running:
            logger.warning("Reminder scheduler is already running")
            return
        
        try:
            # Schedule jobs
            schedule.every(5).minutes.do(self.check_and_send_reminders)  # Check every 5 minutes
            schedule.every().hour.do(self.update_overdue_reminders)     # Update overdue status hourly
            schedule.every().day.at("09:00").do(self.process_recurring_reminders)  # Process recurring daily at 9 AM
            schedule.every().day.at("02:00").do(self.cleanup_old_notifications)   # Cleanup at 2 AM
            
            # Start scheduler thread
            self.is_running = True
            self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.scheduler_thread.start()
            
            logger.info("Reminder scheduler started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start reminder scheduler: {str(e)}")
            self.is_running = False
    
    def stop_scheduler(self):
        """Stop the reminder scheduler"""
        try:
            self.is_running = False
            schedule.clear()
            
            if self.scheduler_thread and self.scheduler_thread.is_alive():
                self.scheduler_thread.join(timeout=10)
            
            logger.info("Reminder scheduler stopped")
            
        except Exception as e:
            logger.error(f"Error stopping reminder scheduler: {str(e)}")
    
    def _run_scheduler(self):
        """Internal scheduler loop"""
        logger.info("Reminder scheduler thread started")
        
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                time.sleep(60)  # Wait longer on error
        
        logger.info("Reminder scheduler thread stopped")
    
    # ==================== REMINDER CHECKING AND SENDING ====================
    
    def check_and_send_reminders(self):
        """
        Check for due reminders and send notifications
        """
        try:
            logger.info("🔍 Checking for due reminders...")
            
            with self.app.app_context():
                # Get current datetime
                now = datetime.now()
                
                # Find reminders that should send notifications
                due_reminders = db.session.query(HealthReminder).filter(
                    and_(
                        HealthReminder.status == ReminderStatus.PENDING,
                        HealthReminder.reminder_date <= now.date(),
                        or_(
                            HealthReminder.reminder_time.is_(None),
                            and_(
                                HealthReminder.reminder_date == now.date(),
                                HealthReminder.reminder_time <= now.time()
                            ),
                            HealthReminder.reminder_date < now.date()
                        ),
                        or_(
                            HealthReminder.last_notification_sent.is_(None),
                            HealthReminder.last_notification_sent < (now - timedelta(hours=1))
                        )
                    )
                ).all()
                
                if not due_reminders:
                    logger.info("No due reminders found")
                    return
                
                logger.info(f"Found {len(due_reminders)} due reminders")
                
                # Process each reminder
                sent_count = 0
                failed_count = 0
                
                for reminder in due_reminders:
                    try:
                        # Check if reminder should actually send notification
                        if not reminder.should_send_notification():
                            continue
                        
                        # Send notifications
                        result = self.notification_service.send_all_notifications(reminder)
                        
                        if result['success']:
                            sent_count += 1
                            logger.info(f"✅ Notifications sent for reminder {reminder.id}: {reminder.title}")
                        else:
                            failed_count += 1
                            logger.warning(f"❌ Failed to send notifications for reminder {reminder.id}: {result.get('error', 'Unknown error')}")
                    
                    except Exception as e:
                        failed_count += 1
                        logger.error(f"Error processing reminder {reminder.id}: {str(e)}")
                
                logger.info(f"Reminder processing completed: {sent_count} sent, {failed_count} failed")
                self.last_check = now
        
        except Exception as e:
            logger.error(f"Error in check_and_send_reminders: {str(e)}")
    
    # ==================== OVERDUE REMINDER MANAGEMENT ====================
    
    def update_overdue_reminders(self):
        """
        Update reminders that are past due to overdue status
        """
        try:
            logger.info("🔍 Updating overdue reminders...")
            
            with self.app.app_context():
                today = date.today()
                
                # Find pending reminders that are past due
                overdue_reminders = db.session.query(HealthReminder).filter(
                    and_(
                        HealthReminder.status == ReminderStatus.PENDING,
                        HealthReminder.due_date < today
                    )
                ).all()
                
                if not overdue_reminders:
                    logger.info("No reminders to mark as overdue")
                    return
                
                # Update status to overdue
                updated_count = 0
                for reminder in overdue_reminders:
                    reminder.status = ReminderStatus.OVERDUE
                    updated_count += 1
                
                db.session.commit()
                logger.info(f"✅ Marked {updated_count} reminders as overdue")
        
        except Exception as e:
            logger.error(f"Error updating overdue reminders: {str(e)}")
            db.session.rollback()
    
    # ==================== RECURRING REMINDER MANAGEMENT ====================
    
    def process_recurring_reminders(self):
        """
        Process recurring reminders and create next occurrences
        """
        try:
            logger.info("🔄 Processing recurring reminders...")
            
            with self.app.app_context():
                # Find completed recurring reminders that need next occurrence
                completed_recurring = db.session.query(HealthReminder).filter(
                    and_(
                        HealthReminder.status == ReminderStatus.COMPLETED,
                        HealthReminder.recurrence_type != RecurrenceType.NONE,
                        or_(
                            HealthReminder.recurrence_end_date.is_(None),
                            HealthReminder.recurrence_end_date >= date.today()
                        ),
                        or_(
                            HealthReminder.max_occurrences.is_(None),
                            HealthReminder.current_occurrence < HealthReminder.max_occurrences
                        )
                    )
                ).all()
                
                if not completed_recurring:
                    logger.info("No recurring reminders to process")
                    return
                
                created_count = 0
                for reminder in completed_recurring:
                    try:
                        new_reminder = self._create_next_recurrence(reminder)
                        if new_reminder:
                            created_count += 1
                            logger.info(f"✅ Created next occurrence for reminder {reminder.id}")
                    except Exception as e:
                        logger.error(f"Error creating recurrence for reminder {reminder.id}: {str(e)}")
                
                logger.info(f"Created {created_count} recurring reminder occurrences")
        
        except Exception as e:
            logger.error(f"Error processing recurring reminders: {str(e)}")
    
    def _create_next_recurrence(self, original_reminder: HealthReminder) -> Optional[HealthReminder]:
        """
        Create the next occurrence of a recurring reminder
        """
        try:
            # Calculate next due date
            next_due_date = original_reminder.get_next_recurrence_date()
            if not next_due_date:
                return None
            
            # Check if we've reached the end date
            if (original_reminder.recurrence_end_date and 
                next_due_date > original_reminder.recurrence_end_date):
                return None
            
            # Check if we've reached max occurrences
            if (original_reminder.max_occurrences and 
                original_reminder.current_occurrence >= original_reminder.max_occurrences):
                return None
            
            # Calculate reminder date (X days/hours before due date)
            reminder_date = next_due_date - timedelta(days=original_reminder.days_before_reminder)
            if original_reminder.hours_before_reminder > 0:
                reminder_datetime = datetime.combine(reminder_date, original_reminder.reminder_time or datetime.min.time())
                reminder_datetime -= timedelta(hours=original_reminder.hours_before_reminder)
                reminder_date = reminder_datetime.date()
                reminder_time = reminder_datetime.time()
            else:
                reminder_time = original_reminder.reminder_time
            
            # Create new reminder
            new_reminder = HealthReminder(
                user_id=original_reminder.user_id,
                pet_id=original_reminder.pet_id,
                reminder_type=original_reminder.reminder_type,
                title=original_reminder.title,
                description=original_reminder.description,
                due_date=next_due_date,
                due_time=original_reminder.due_time,
                reminder_date=reminder_date,
                reminder_time=reminder_time,
                send_email=original_reminder.send_email,
                send_push=original_reminder.send_push,
                send_sms=original_reminder.send_sms,
                days_before_reminder=original_reminder.days_before_reminder,
                hours_before_reminder=original_reminder.hours_before_reminder,
                recurrence_type=original_reminder.recurrence_type,
                recurrence_interval=original_reminder.recurrence_interval,
                recurrence_end_date=original_reminder.recurrence_end_date,
                max_occurrences=original_reminder.max_occurrences,
                current_occurrence=original_reminder.current_occurrence + 1,
                health_record_id=original_reminder.health_record_id,
                metadata=original_reminder.metadata,
                status=ReminderStatus.PENDING
            )
            
            db.session.add(new_reminder)
            db.session.commit()
            
            logger.info(f"Created recurring reminder {new_reminder.id} (occurrence {new_reminder.current_occurrence}) "
                       f"for original reminder {original_reminder.id}")
            
            return new_reminder
        
        except Exception as e:
            logger.error(f"Error creating next recurrence: {str(e)}")
            db.session.rollback()
            return None
    
    # ==================== CLEANUP AND MAINTENANCE ====================
    
    def cleanup_old_notifications(self, days_to_keep: int = 90):
        """
        Clean up old notification records
        """
        try:
            logger.info("🧹 Cleaning up old notification records...")
            
            with self.app.app_context():
                cutoff_date = datetime.now() - timedelta(days=days_to_keep)
                
                # Delete old notification records
                deleted_count = db.session.query(ReminderNotification).filter(
                    ReminderNotification.created_at < cutoff_date
                ).delete()
                
                db.session.commit()
                logger.info(f"✅ Cleaned up {deleted_count} old notification records")
        
        except Exception as e:
            logger.error(f"Error cleaning up notifications: {str(e)}")
            db.session.rollback()
    
    # ==================== MANUAL TRIGGER FUNCTIONS ====================
    
    def trigger_immediate_check(self) -> Dict[str, Any]:
        """
        Manually trigger immediate reminder check
        """
        try:
            logger.info("🚀 Manual trigger: immediate reminder check")
            self.check_and_send_reminders()
            
            return {
                'success': True,
                'message': 'Immediate reminder check completed',
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error in manual trigger: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """
        Get current scheduler status
        """
        try:
            with self.app.app_context():
                # Count pending reminders
                pending_count = db.session.query(HealthReminder).filter(
                    HealthReminder.status == ReminderStatus.PENDING
                ).count()
                
                # Count overdue reminders
                overdue_count = db.session.query(HealthReminder).filter(
                    HealthReminder.status == ReminderStatus.OVERDUE
                ).count()
                
                # Count recent notifications (last 24 hours)
                recent_notifications = db.session.query(ReminderNotification).filter(
                    ReminderNotification.created_at >= datetime.now() - timedelta(hours=24)
                ).count()
                
                return {
                    'scheduler_running': self.is_running,
                    'last_check': self.last_check.isoformat() if self.last_check else None,
                    'pending_reminders': pending_count,
                    'overdue_reminders': overdue_count,
                    'recent_notifications_24h': recent_notifications,
                    'scheduled_jobs': len(schedule.jobs),
                    'timestamp': datetime.now().isoformat()
                }
        
        except Exception as e:
            logger.error(f"Error getting scheduler status: {str(e)}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

# ==================== SERVICE INSTANCE ====================

# Global scheduler instance
_scheduler_instance = None

def get_scheduler_service(app=None) -> ReminderSchedulerService:
    """Get scheduler service instance (singleton)"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = ReminderSchedulerService(app)
    elif app and not _scheduler_instance.app:
        _scheduler_instance.set_app(app)
    return _scheduler_instance

def start_reminder_scheduler(app=None):
    """Start the global reminder scheduler"""
    scheduler = get_scheduler_service(app)
    scheduler.start_scheduler()

def stop_reminder_scheduler():
    """Stop the global reminder scheduler"""
    scheduler = get_scheduler_service(app)
    scheduler.stop_scheduler()

# ==================== COMMAND LINE INTERFACE ====================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "start":
            print("Starting reminder scheduler...")
            start_reminder_scheduler()
            
            # Keep running
            try:
                while True:
                    time.sleep(60)
            except KeyboardInterrupt:
                print("\nStopping scheduler...")
                stop_reminder_scheduler()
        
        elif command == "check":
            print("Running immediate reminder check...")
            scheduler = get_scheduler_service(app)
            result = scheduler.trigger_immediate_check()
            print(f"Result: {result}")
        
        elif command == "status":
            print("Getting scheduler status...")
            scheduler = get_scheduler_service(app)
            status = scheduler.get_scheduler_status()
            print(json.dumps(status, indent=2))
        
        else:
            print("Usage: python reminder_scheduler_service.py [start|check|status]")
    else:
        print("Usage: python reminder_scheduler_service.py [start|check|status]") 