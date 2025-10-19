#!/usr/bin/env python3
"""
Precision Reminder Scheduler Service
Uses APScheduler to schedule individual reminders at exact times instead of polling
"""

import logging
from datetime import datetime, timedelta, date, time
from typing import List, Dict, Any, Optional
import pytz
from flask import current_app
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import atexit
import os
import json

from app import db
from app.models.health_models import (
    HealthReminder, ReminderStatus, RecurrenceType, 
    ReminderNotification, NotificationStatus
)
from app.models.user import User
from app.services.reminder_notification_service import get_notification_service

logger = logging.getLogger(__name__)

class PrecisionReminderScheduler:
    """
    Precision reminder scheduler using APScheduler
    Schedules individual reminders at exact times
    """
    
    def __init__(self, app=None):
        self.app = app
        self.scheduler = None
        self.notification_service = get_notification_service()
        self.is_running = False
        
        # Ensure jobs directory exists
        jobs_dir = app.config.get('JOB_STORE_DIR', 'jobs') if app else 'jobs'
        os.makedirs(jobs_dir, exist_ok=True)
        
        # Job store configuration - use memory store for simplicity
        self.jobstores = {
            'default': MemoryJobStore()
        }
        
        # Executor configuration
        self.executors = {
            'default': ThreadPoolExecutor(20)
        }
        
        # Job defaults
        self.job_defaults = {
            'coalesce': False,
            'max_instances': 1,
            'misfire_grace_time': 300  # 5 minutes grace time
        }
        
        # Initialize scheduler
        self._init_scheduler()
    
    def _init_scheduler(self):
        """Initialize APScheduler"""
        try:
            self.scheduler = BackgroundScheduler(
                jobstores=self.jobstores,
                executors=self.executors,
                job_defaults=self.job_defaults,
                timezone=pytz.UTC
            )
            
            # Add event listeners
            self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
            self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)
            
            logger.info("✅ Precision reminder scheduler initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize scheduler: {str(e)}")
            raise
    
    def start(self):
        """Start the scheduler"""
        if self.is_running:
            logger.warning("⚠️  Scheduler is already running")
            return
        
        try:
            self.scheduler.start()
            self.is_running = True
            
            # Register cleanup on exit
            atexit.register(self.stop)
            
            # Schedule existing pending reminders
            self._schedule_existing_reminders()
            
            # Schedule recurring maintenance tasks
            self._schedule_maintenance_tasks()
            
            logger.info("🚀 Precision reminder scheduler started")
            
        except Exception as e:
            logger.error(f"❌ Failed to start scheduler: {str(e)}")
            raise
    
    def stop(self):
        """Stop the scheduler"""
        if not self.is_running:
            return
        
        try:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("🛑 Precision reminder scheduler stopped")
            
        except Exception as e:
            logger.error(f"❌ Error stopping scheduler: {str(e)}")
    
    def _job_executed(self, event):
        """Handle job execution events"""
        logger.info(f"✅ Job executed: {event.job_id}")
    
    def _job_error(self, event):
        """Handle job error events"""
        logger.error(f"❌ Job error: {event.job_id} - {event.exception}")
    
    def _schedule_existing_reminders(self):
        """Schedule all existing pending reminders"""
        try:
            with self.app.app_context():
                # Get all pending reminders
                pending_reminders = db.session.query(HealthReminder).filter(
                    HealthReminder.status == ReminderStatus.PENDING
                ).all()
                
                scheduled_count = 0
                skipped_count = 0
                
                for reminder in pending_reminders:
                    if self._schedule_single_reminder(reminder):
                        scheduled_count += 1
                    else:
                        skipped_count += 1
                
                logger.info(f"📅 Scheduled {scheduled_count} reminders, skipped {skipped_count}")
                
        except Exception as e:
            logger.error(f"❌ Error scheduling existing reminders: {str(e)}")
    
    def _schedule_maintenance_tasks(self):
        """
        Schedule recurring maintenance tasks for the scheduler
        """
        try:
            # Daily maintenance at 2 AM
            self.scheduler.add_job(
                func=self._daily_maintenance,
                trigger='cron',
                hour=2,
                minute=0,
                id='daily_maintenance_standalone',
                replace_existing=True,
                max_instances=1
            )
            
            # 🎯 CONTEXT7 ENHANCEMENT: Follow-up notification checks every 5 minutes
            self.scheduler.add_job(
                func=self._check_followup_notifications,
                trigger='interval',
                minutes=5,
                id='followup_notifications_check',
                replace_existing=True,
                max_instances=1
            )
            
            logger.info("🔧 Maintenance tasks scheduled")
            
        except Exception as e:
            logger.error(f"❌ Error scheduling maintenance tasks: {str(e)}")
    
    def _check_followup_notifications(self):
        """
        🎯 CONTEXT7: Check and send follow-up notifications for overdue reminders
        """
        try:
            logger.info("🔔 Starting follow-up notification check...")
            
            # 🎯 CONTEXT7 FIX: Run within Flask application context
            with self.app.app_context():
                from app.services.followup_notification_service import get_followup_notification_service
                followup_service = get_followup_notification_service()
                
                # Run the follow-up check
                results = followup_service.check_and_send_followups()
                
                if results.get('followups_sent', 0) > 0:
                    logger.info(f"📧 Sent {results['followups_sent']} follow-up notifications")
                
                if results.get('errors'):
                    logger.warning(f"⚠️  Follow-up errors: {len(results['errors'])}")
                    for error in results['errors'][:3]:  # Log first 3 errors
                        logger.warning(f"   - {error}")
                
                logger.debug(f"🔔 Follow-up check completed: {results}")
            
        except Exception as e:
            logger.error(f"❌ Error in follow-up notification check: {str(e)}")
    
    def _daily_maintenance(self):
        """
        Daily maintenance tasks for the scheduler
        """
        try:
            logger.info("🔧 Starting daily maintenance...")
            
            # 🎯 CONTEXT7 FIX: Run within Flask application context
            with self.app.app_context():
                # Clean up old completed jobs
                self._cleanup_old_jobs()
                
                # Update overdue reminder statuses
                self._update_overdue_reminders()
                
                # 🎯 CONTEXT7 ENHANCEMENT: Clean up expired completion tokens
                self._cleanup_expired_completion_tokens()
                
                # Generate daily analytics
                self._generate_daily_analytics()
            
            logger.info("✅ Daily maintenance completed")
            
        except Exception as e:
            logger.error(f"❌ Error in daily maintenance: {str(e)}")
    
    def _cleanup_expired_completion_tokens(self):
        """
        🎯 CONTEXT7: Clean up expired email completion tokens from reminders
        """
        try:
            from datetime import datetime, timedelta
            from app.models.health_models import HealthReminder
            
            # Find reminders with expired tokens (older than 7 days)
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            
            reminders_with_tokens = (db.session.query(HealthReminder)
                                   .filter(HealthReminder.extra_data.isnot(None))
                                   .all())
            
            cleaned_count = 0
            
            for reminder in reminders_with_tokens:
                if reminder.extra_data and 'completion_token' in reminder.extra_data:
                    token_created_str = reminder.extra_data.get('completion_token_created')
                    if token_created_str:
                        try:
                            token_created = datetime.fromisoformat(token_created_str)
                            if token_created < cutoff_date:
                                # Remove expired token
                                reminder.extra_data.pop('completion_token', None)
                                reminder.extra_data.pop('completion_token_created', None)
                                cleaned_count += 1
                        except:
                            # Invalid date format, remove token
                            reminder.extra_data.pop('completion_token', None)
                            reminder.extra_data.pop('completion_token_created', None)
                            cleaned_count += 1
            
            if cleaned_count > 0:
                db.session.commit()
                logger.info(f"🧹 Cleaned up {cleaned_count} expired completion tokens")
            
        except Exception as e:
            logger.error(f"Error cleaning up completion tokens: {str(e)}")
    
    def _update_overdue_reminders(self):
        """
        Update the status of overdue reminders
        """
        try:
            from datetime import datetime
            from app.models.health_models import HealthReminder, ReminderStatus
            
            now = datetime.utcnow()
            
            # Find pending reminders that are overdue
            overdue_reminders = (db.session.query(HealthReminder)
                               .filter(
                                   HealthReminder.status == ReminderStatus.PENDING,
                                   HealthReminder.due_date < now.date()
                               )
                               .all())
            
            updated_count = 0
            for reminder in overdue_reminders:
                due_datetime = reminder.get_next_due_datetime()
                if due_datetime and due_datetime < now:
                    reminder.status = ReminderStatus.OVERDUE
                    updated_count += 1
            
            if updated_count > 0:
                db.session.commit()
                logger.info(f"📅 Updated {updated_count} reminders to overdue status")
                
        except Exception as e:
            logger.error(f"Error updating overdue reminders: {str(e)}")
    
    def _generate_daily_analytics(self):
        """
        🎯 CONTEXT7: Generate daily analytics for follow-up notifications and reminder performance
        """
        try:
            from app.services.followup_notification_service import get_followup_notification_service
            
            followup_service = get_followup_notification_service()
            analytics = followup_service.get_followup_analytics(days_back=1)
            
            logger.info(f"📊 Daily Analytics: {analytics}")
            
            # Store analytics in a file or database for reporting
            # This could be expanded to send reports to admins
            
        except Exception as e:
            logger.error(f"Error generating daily analytics: {str(e)}")
    
    def schedule_reminder(self, reminder: HealthReminder) -> bool:
        """
        Schedule a single reminder for precise execution
        """
        return self._schedule_single_reminder(reminder)
    
    def _schedule_single_reminder(self, reminder: HealthReminder) -> bool:
        """
        Schedule a single reminder at its exact time
        """
        try:
            # Calculate exact trigger time
            trigger_datetime = self._calculate_trigger_time(reminder)
            
            if not trigger_datetime:
                logger.warning(f"⚠️  Cannot calculate trigger time for reminder {reminder.id}")
                return False
            
            # Skip if trigger time is in the past
            if trigger_datetime <= datetime.now(pytz.UTC):
                logger.info(f"⏰ Skipping reminder {reminder.id} - trigger time is in the past")
                return False
            
            # Create job ID
            job_id = f"reminder_{reminder.id}"
            
            # Get app config for the standalone function
            app_config = {
                'DATABASE_URL': self.app.config.get('DATABASE_URL'),
                'SECRET_KEY': self.app.config.get('SECRET_KEY')
            }
            
            # Schedule the job using the standalone function
            self.scheduler.add_job(
                func=send_reminder_notification_standalone,
                trigger='date',
                run_date=trigger_datetime,
                args=[reminder.id, app_config],
                id=job_id,
                replace_existing=True
            )
            
            logger.info(f"📅 Scheduled reminder {reminder.id} for {trigger_datetime}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error scheduling reminder {reminder.id}: {str(e)}")
            return False
    
    def _calculate_trigger_time(self, reminder: HealthReminder) -> Optional[datetime]:
        """
        Calculate the exact trigger time for a reminder with enhanced timezone handling
        """
        try:
            # Get user's timezone with comprehensive fallback strategy
            user = db.session.query(User).get(reminder.user_id)
            
            # 🎯 CONTEXT7 ENHANCEMENT: Enhanced timezone detection and validation
            if user and user.timezone:
                try:
                    user_tz = pytz.timezone(user.timezone)
                    logger.debug(f"✅ Using user timezone: {user.timezone}")
                except Exception as tz_error:
                    logger.warning(f"❌ Invalid user timezone {user.timezone}, using UTC: {tz_error}")
                    user_tz = pytz.UTC
                    user.timezone = 'UTC'  # Fix invalid timezone
                    try:
                        db.session.commit()
                    except:
                        db.session.rollback()
            else:
                # Default timezone determination with better logic
                try:
                    import tzlocal
                    system_tz = tzlocal.get_localzone()
                    # Validate system timezone
                    if hasattr(system_tz, 'zone') and system_tz.zone:
                        user_tz = system_tz
                        logger.debug(f"✅ Using system timezone: {system_tz}")
                        
                        # Update user timezone if not set
                        if user and not user.timezone:
                            try:
                                user.timezone = str(system_tz)
                                db.session.commit()
                                logger.info(f"📍 Updated user {user.id} timezone to: {system_tz}")
                            except:
                                db.session.rollback()
                    else:
                        user_tz = pytz.UTC
                        logger.debug("⚠️  System timezone invalid, using UTC")
                except Exception:
                    user_tz = pytz.UTC
                    logger.debug("⚠️  Unable to detect system timezone, using UTC as fallback")
            
            # 🎯 CONTEXT7 ENHANCEMENT: Check for timezone metadata from enhanced creation
            timezone_metadata = None
            if reminder.extra_data:
                try:
                    metadata = json.loads(reminder.extra_data)
                    timezone_metadata = metadata if isinstance(metadata, dict) else None
                    if timezone_metadata and 'user_timezone' in timezone_metadata:
                        # Use timezone from metadata for consistency
                        metadata_tz = timezone_metadata['user_timezone']
                        try:
                            user_tz = pytz.timezone(metadata_tz)
                            logger.info(f"🌍 Using timezone from metadata: {metadata_tz}")
                        except:
                            logger.warning(f"❌ Invalid timezone in metadata: {metadata_tz}")
                except:
                    logger.debug("📋 No valid timezone metadata found")
            
            # Determine trigger date and time with enhanced logic
            if reminder.reminder_date and reminder.reminder_time:
                trigger_date = reminder.reminder_date
                trigger_time = reminder.reminder_time
                logger.debug(f"📅 Using reminder datetime: {trigger_date} {trigger_time}")
            else:
                # Fallback to due_date and due_time
                trigger_date = reminder.due_date
                trigger_time = reminder.due_time or time(9, 0)  # Default to 9 AM
                logger.debug(f"📅 Using due datetime: {trigger_date} {trigger_time}")
            
            # Create naive datetime first
            naive_trigger_datetime = datetime.combine(trigger_date, trigger_time)
            
            # Add a small buffer (30 seconds earlier) to ensure notifications are sent on time
            # This helps prevent notifications from arriving late due to processing delays
            naive_trigger_datetime = naive_trigger_datetime - timedelta(seconds=30)
            
            logger.debug(f"🕐 Naive trigger datetime (with 30s buffer): {naive_trigger_datetime}")
            
            # Get current time in user timezone for comparison
            now_utc = datetime.now(pytz.UTC)
            now_user_tz = now_utc.astimezone(user_tz)
            current_date = now_user_tz.date()
            current_time = now_user_tz.time()
            
            logger.debug(f"🌍 Current time in user TZ ({user_tz}): {now_user_tz}")
            logger.debug(f"📊 Current date: {current_date}, current time: {current_time}")
            
            # 🎯 CONTEXT7 ENHANCEMENT: Smart time validation and adjustment
            # If the reminder is for today but time has passed, move to tomorrow
            if (trigger_date == current_date and trigger_time <= current_time):
                # Add one day if the time has already passed today
                logger.info(f"⏰ Reminder time {trigger_time} has passed today, moving to tomorrow")
                trigger_date = trigger_date + timedelta(days=1)
                naive_trigger_datetime = datetime.combine(trigger_date, trigger_time)
                # Apply the buffer again after recalculating
                naive_trigger_datetime = naive_trigger_datetime - timedelta(seconds=30)
                
                # Update the reminder in database to reflect the change
                try:
                    if reminder.reminder_date and reminder.reminder_time:
                        reminder.reminder_date = trigger_date
                    else:
                        reminder.due_date = trigger_date
                    db.session.commit()
                    logger.info(f"📝 Updated reminder {reminder.id} date to {trigger_date}")
                except:
                    db.session.rollback()
                    logger.warning(f"⚠️  Failed to update reminder {reminder.id} date")
            
            # If the reminder date is in the past, skip it (unless it's a recurring reminder)
            elif trigger_date < current_date:
                if reminder.recurrence_type and reminder.recurrence_type.value != 'none':
                    logger.info(f"🔄 Reminder date {trigger_date} is in the past, but it's recurring - will calculate next occurrence")
                    # Let the recurring reminder handler deal with this
                    return None
                else:
                    logger.info(f"⚠️  Reminder date {trigger_date} is in the past, skipping")
                    return None
            
            # 🎯 CONTEXT7 ENHANCEMENT: Timezone-aware localization with metadata support
            try:
                # Check if we have original timezone information from timezone-aware creation
                if timezone_metadata and 'timezone_aware_creation' in timezone_metadata:
                    # This reminder was created with timezone awareness
                    logger.info(f"🌍 Processing timezone-aware reminder created at: {timezone_metadata.get('extraction_timestamp', 'unknown')}")
                    
                    # The naive_trigger_datetime represents user's local time at creation
                    # We need to localize it properly
                    aware_trigger_datetime = user_tz.localize(naive_trigger_datetime)
                    logger.debug(f"🕐 Localized timezone-aware trigger datetime: {aware_trigger_datetime}")
                else:
                    # Standard localization for non-timezone-aware reminders
                    aware_trigger_datetime = user_tz.localize(naive_trigger_datetime)
                    logger.debug(f"🕐 Localized standard trigger datetime: {aware_trigger_datetime}")
                    
            except Exception as localize_error:
                logger.error(f"❌ Error localizing datetime: {localize_error}")
                # If localization fails, check if it's already timezone-aware
                if naive_trigger_datetime.tzinfo is None:
                    aware_trigger_datetime = pytz.UTC.localize(naive_trigger_datetime)
                    logger.warning("⚠️  Localization failed, using UTC")
                else:
                    aware_trigger_datetime = naive_trigger_datetime
                    logger.warning("⚠️  Using existing timezone info")
            
            # Convert to UTC for APScheduler
            utc_trigger_datetime = aware_trigger_datetime.astimezone(pytz.UTC)
            logger.debug(f"🌐 UTC trigger datetime for scheduler: {utc_trigger_datetime}")
            
            # Final validation - ensure it's in the future
            if utc_trigger_datetime <= now_utc:
                time_diff = (now_utc - utc_trigger_datetime).total_seconds()
                if time_diff < 300:  # Less than 5 minutes in the past - allow it
                    logger.warning(f"⚠️  Trigger time {utc_trigger_datetime} is {time_diff:.0f}s in the past, but allowing")
                else:
                    logger.warning(f"❌ Final check: trigger time {utc_trigger_datetime} is {time_diff:.0f}s in the past (now: {now_utc})")
                    return None
            
            # Log comprehensive timing information
            logger.info(f"✅ Calculated trigger time for reminder {reminder.id}:")
            logger.info(f"   📍 User timezone: {user_tz}")
            logger.info(f"   🕐 Local time: {aware_trigger_datetime}")
            logger.info(f"   🌐 UTC time: {utc_trigger_datetime}")
            if timezone_metadata:
                logger.info(f"   🌍 Timezone-aware: {timezone_metadata.get('timezone_aware_creation', False)}")
            
            return utc_trigger_datetime
            
        except Exception as e:
            logger.error(f"❌ Error calculating trigger time for reminder {reminder.id}: {str(e)}")
            import traceback
            logger.error(f"📊 Traceback: {traceback.format_exc()}")
            return None
    
    def unschedule_reminder(self, reminder_id: int):
        """
        Remove a scheduled reminder
        """
        try:
            job_id = f"reminder_{reminder_id}"
            
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"🗑️  Unscheduled reminder {reminder_id}")
                return True
            else:
                logger.info(f"⚠️  Reminder {reminder_id} was not scheduled")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error unscheduling reminder {reminder_id}: {str(e)}")
            return False
    
    def reschedule_reminder(self, reminder: HealthReminder) -> bool:
        """
        Reschedule an existing reminder with enhanced timezone support
        """
        try:
            # First unschedule the existing job
            job_id = f"reminder_{reminder.id}"
            
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"🗑️  Unscheduled existing job for reminder {reminder.id}")
            
            # Then schedule it again with new timing
            return self._schedule_single_reminder(reminder)
            
        except Exception as e:
            logger.error(f"❌ Error rescheduling reminder {reminder.id}: {str(e)}")
            return False
    
    def _schedule_next_recurrence(self, reminder: HealthReminder):
        """
        Schedule the next occurrence of a recurring reminder
        """
        try:
            # Calculate next due date
            next_due_date = reminder.get_next_recurrence_date()
            if not next_due_date:
                logger.info(f"⏭️  No next recurrence for reminder {reminder.id}")
                return
            
            # Check if we've reached the end date
            if (reminder.recurrence_end_date and 
                next_due_date > reminder.recurrence_end_date):
                logger.info(f"⏭️  Reached end date for reminder {reminder.id}")
                return
            
            # Check if we've reached max occurrences
            if (reminder.max_occurrences and 
                reminder.current_occurrence >= reminder.max_occurrences):
                logger.info(f"⏭️  Reached max occurrences for reminder {reminder.id}")
                return
            
            # Create new reminder instance
            new_reminder = self._create_recurring_reminder(reminder, next_due_date)
            if new_reminder:
                # Schedule the new reminder
                self.schedule_reminder(new_reminder)
                logger.info(f"🔄 Scheduled next recurrence for reminder {reminder.id}")
            
        except Exception as e:
            logger.error(f"❌ Error scheduling next recurrence for reminder {reminder.id}: {str(e)}")
    
    def _create_recurring_reminder(self, original: HealthReminder, next_due_date: date) -> Optional[HealthReminder]:
        """
        Create a new reminder instance for recurring reminders
        """
        try:
            # Calculate reminder date (X days/hours before due date)
            reminder_date = next_due_date - timedelta(days=original.days_before_reminder)
            if original.hours_before_reminder > 0:
                reminder_datetime = datetime.combine(reminder_date, original.reminder_time or time(9, 0))
                reminder_datetime -= timedelta(hours=original.hours_before_reminder)
                reminder_date = reminder_datetime.date()
                reminder_time = reminder_datetime.time()
            else:
                reminder_time = original.reminder_time
            
            # Create new reminder
            new_reminder = HealthReminder(
                user_id=original.user_id,
                pet_id=original.pet_id,
                reminder_type=original.reminder_type,
                title=original.title,
                description=original.description,
                due_date=next_due_date,
                due_time=original.due_time,
                reminder_date=reminder_date,
                reminder_time=reminder_time,
                send_email=original.send_email,
                send_push=original.send_push,
                send_sms=original.send_sms,
                days_before_reminder=original.days_before_reminder,
                hours_before_reminder=original.hours_before_reminder,
                recurrence_type=original.recurrence_type,
                recurrence_interval=original.recurrence_interval,
                recurrence_end_date=original.recurrence_end_date,
                max_occurrences=original.max_occurrences,
                current_occurrence=original.current_occurrence + 1,
                health_record_id=original.health_record_id,
                metadata=original.metadata,
                status=ReminderStatus.PENDING
            )
            
            db.session.add(new_reminder)
            db.session.commit()
            
            return new_reminder
            
        except Exception as e:
            logger.error(f"❌ Error creating recurring reminder: {str(e)}")
            db.session.rollback()
            return None
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status"""
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
                
                # Count scheduled jobs
                scheduled_jobs = len([job for job in self.scheduler.get_jobs() 
                                    if job.id.startswith('reminder_')])
                
                return {
                    'scheduler_running': self.is_running,
                    'scheduler_type': 'precision_apscheduler',
                    'pending_reminders': pending_count,
                    'overdue_reminders': overdue_count,
                    'scheduled_jobs': scheduled_jobs,
                    'total_jobs': len(self.scheduler.get_jobs()),
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"❌ Error getting scheduler status: {str(e)}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def get_scheduled_jobs_info(self) -> Dict[str, Any]:
        """
        Get information about currently scheduled reminder jobs
        """
        try:
            if not self.scheduler or not self.is_running:
                return {"status": "scheduler_not_running", "jobs": []}
            
            jobs = self.scheduler.get_jobs()
            job_info = []
            
            for job in jobs:
                if job.id.startswith("reminder_"):
                    reminder_id = int(job.id.split("_")[1])
                    job_info.append({
                        "job_id": job.id,
                        "reminder_id": reminder_id,
                        "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                        "trigger": str(job.trigger),
                        "args": job.args,
                        "kwargs": job.kwargs
                    })
            
            return {
                "status": "running",
                "total_jobs": len(jobs),
                "reminder_jobs": len(job_info),
                "jobs": job_info
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting scheduled jobs info: {str(e)}")
            return {"status": "error", "error": str(e)}

    def validate_and_fix_timezones(self) -> Dict[str, Any]:
        """
        Validate and fix timezone issues for all users and reminders
        """
        try:
            validation_results = {
                "users_checked": 0,
                "users_fixed": 0,
                "reminders_checked": 0,
                "reminders_rescheduled": 0,
                "errors": []
            }
            
            # Check all users for valid timezones
            users = db.session.query(User).all()
            for user in users:
                validation_results["users_checked"] += 1
                
                if user.timezone:
                    try:
                        pytz.timezone(user.timezone)
                    except:
                        # Fix invalid timezone
                        logger.warning(f"⚠️  Fixing invalid timezone for user {user.id}: {user.timezone}")
                        user.timezone = 'UTC'
                        validation_results["users_fixed"] += 1
                else:
                    # Set default timezone
                    user.timezone = 'UTC'
                    validation_results["users_fixed"] += 1
            
            try:
                db.session.commit()
            except:
                db.session.rollback()
                validation_results["errors"].append("Failed to update user timezones")
            
            # Check and reschedule active reminders
            active_reminders = db.session.query(HealthReminder).filter(
                HealthReminder.status == ReminderStatus.PENDING
            ).all()
            
            for reminder in active_reminders:
                validation_results["reminders_checked"] += 1
                
                # Try to reschedule with improved timezone handling
                if self.reschedule_reminder(reminder):
                    validation_results["reminders_rescheduled"] += 1
                else:
                    validation_results["errors"].append(f"Failed to reschedule reminder {reminder.id}")
            
            logger.info(f"🔧 Timezone validation completed: {validation_results}")
            return validation_results
            
        except Exception as e:
            logger.error(f"❌ Error in timezone validation: {str(e)}")
            return {"status": "error", "error": str(e)}

# ==================== SERVICE INSTANCE ====================

_precision_scheduler_instance = None

def get_precision_scheduler() -> Optional[PrecisionReminderScheduler]:
    """
    Get the global precision scheduler instance
    """
    global _precision_scheduler_instance
    return _precision_scheduler_instance

def initialize_precision_scheduler(app) -> PrecisionReminderScheduler:
    """
    Initialize the global precision scheduler instance
    """
    global _precision_scheduler_instance
    if _precision_scheduler_instance is None:
        _precision_scheduler_instance = PrecisionReminderScheduler(app)
    return _precision_scheduler_instance

def start_precision_scheduler(app=None):
    """
    Start the precision scheduler
    """
    global _precision_scheduler_instance
    if _precision_scheduler_instance is None and app:
        _precision_scheduler_instance = PrecisionReminderScheduler(app)
    
    if _precision_scheduler_instance:
        _precision_scheduler_instance.start()
        logger.info("🚀 Precision reminder scheduler started")
    else:
        logger.warning("⚠️  Cannot start precision scheduler - not initialized")

def stop_precision_scheduler():
    """
    Stop the precision scheduler
    """
    global _precision_scheduler_instance
    if _precision_scheduler_instance:
        _precision_scheduler_instance.stop()
        logger.info("🛑 Precision reminder scheduler stopped")

# Standalone function for sending notifications (can be pickled)
def send_reminder_notification_standalone(reminder_id: int, app_config: dict):
    """
    Standalone function to send reminder notifications
    This function can be properly serialized by APScheduler
    """
    try:
        # Import here to avoid circular imports
        from app import create_app, db
        from app.services.reminder_notification_service import get_notification_service
        
        # Create a minimal app instance with the config
        app = create_app()
        
        with app.app_context():
            # Get reminder
            reminder = db.session.query(HealthReminder).get(reminder_id)
            
            if not reminder:
                logger.warning(f"⚠️  Reminder {reminder_id} not found")
                return
            
            if reminder.status != ReminderStatus.PENDING:
                logger.info(f"⏭️  Skipping reminder {reminder_id} - status is {reminder.status}")
                return
            
            # Check if we should send notification
            if not reminder.should_send_notification():
                logger.info(f"⏭️  Skipping reminder {reminder_id} - should_send_notification returned False")
                return
            
            # Get notification service and send notifications
            notification_service = get_notification_service()
            result = notification_service.send_all_notifications(reminder)
            
            if result['success']:
                logger.info(f"✅ Sent notifications for reminder {reminder_id}: {reminder.title}")
            else:
                logger.error(f"❌ Failed to send notifications for reminder {reminder_id}: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"❌ Error in standalone notification function for reminder {reminder_id}: {str(e)}")

# Standalone function for daily maintenance (can be pickled)
def daily_maintenance_standalone(app_config: dict):
    """
    Standalone function for daily maintenance tasks
    This function can be properly serialized by APScheduler
    """
    try:
        # Import here to avoid circular imports
        from app import create_app, db
        from app.models.health_models import HealthReminder, ReminderStatus, ReminderNotification
        from datetime import datetime, timedelta, date
        
        # Create a minimal app instance with the config
        app = create_app()
        
        with app.app_context():
            logger.info("🧹 Running daily maintenance...")
            
            # Update overdue reminders
            today = date.today()
            
            # Find pending reminders that are past due
            overdue_reminders = db.session.query(HealthReminder).filter(
                HealthReminder.status == ReminderStatus.PENDING,
                HealthReminder.due_date < today
            ).all()
            
            updated_count = 0
            for reminder in overdue_reminders:
                reminder.status = ReminderStatus.OVERDUE
                updated_count += 1
            
            if updated_count > 0:
                db.session.commit()
                logger.info(f"📅 Marked {updated_count} reminders as overdue")
            
            # Clean up old notifications (90 days)
            cutoff_date = datetime.now() - timedelta(days=90)
            
            deleted_count = db.session.query(ReminderNotification).filter(
                ReminderNotification.created_at < cutoff_date
            ).delete()
            
            if deleted_count > 0:
                db.session.commit()
                logger.info(f"🗑️  Cleaned up {deleted_count} old notification records")
            
            logger.info("✅ Daily maintenance completed")
            
    except Exception as e:
        logger.error(f"❌ Error in daily maintenance: {str(e)}") 