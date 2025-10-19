import logging
from datetime import datetime, date, timedelta, time, timezone
from typing import List, Dict, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
import openai
import json
from flask import current_app
from app.models.health_models import (
    HealthRecord, Vaccination, Medication, HealthReminder, 
    PetProfile, HealthInsight, HealthRecordType, ReminderType, ReminderStatus,
    RecurrenceType, ReminderNotification
)
from app.models.user import User

logger = logging.getLogger(__name__)

class HealthService:
    """
    Enhanced health service with advanced reminder management,
    time-based scheduling, and recurring reminders
    """
    
    def __init__(self, db_session: Session, openai_client=None):
        self.db = db_session
        self.openai_client = openai_client or openai
        
    # ==================== HEALTH RECORD MANAGEMENT ====================
    
    def create_health_record(self, user_id: int, record_data: Dict[str, Any]) -> HealthRecord:
        """
        Create a new health record with optional vaccination/medication details
        """
        try:
            # Create main health record
            health_record = HealthRecord(
                user_id=user_id,
                pet_id=record_data.get('pet_id'),
                record_type=HealthRecordType(record_data['record_type']),
                title=record_data['title'],
                description=record_data.get('description'),
                record_date=record_data['record_date'],
                veterinarian_name=record_data.get('veterinarian_name'),
                clinic_name=record_data.get('clinic_name'),
                clinic_address=record_data.get('clinic_address'),
                cost=record_data.get('cost'),
                insurance_covered=record_data.get('insurance_covered', False),
                insurance_amount=record_data.get('insurance_amount'),
                notes=record_data.get('notes'),
                tags=record_data.get('tags')
            )
            
            self.db.add(health_record)
            self.db.flush()  # Get the ID
            
            # Add vaccination details if provided
            if record_data['record_type'] == 'vaccination' and 'vaccination_details' in record_data:
                vaccination = Vaccination(
                    health_record_id=health_record.id,
                    vaccine_name=record_data['vaccination_details']['vaccine_name'],
                    vaccine_type=record_data['vaccination_details'].get('vaccine_type'),
                    batch_number=record_data['vaccination_details'].get('batch_number'),
                    manufacturer=record_data['vaccination_details'].get('manufacturer'),
                    administration_date=record_data['vaccination_details']['administration_date'],
                    next_due_date=record_data['vaccination_details'].get('next_due_date'),
                    adverse_reactions=record_data['vaccination_details'].get('adverse_reactions')
                )
                self.db.add(vaccination)
            
            # Add medication details if provided
            if record_data['record_type'] == 'medication' and 'medication_details' in record_data:
                medication = Medication(
                    health_record_id=health_record.id,
                    medication_name=record_data['medication_details']['medication_name'],
                    dosage=record_data['medication_details'].get('dosage'),
                    frequency=record_data['medication_details'].get('frequency'),
                    start_date=record_data['medication_details']['start_date'],
                    end_date=record_data['medication_details'].get('end_date'),
                    prescribed_by=record_data['medication_details'].get('prescribed_by'),
                    reason=record_data['medication_details'].get('reason'),
                    side_effects=record_data['medication_details'].get('side_effects')
                )
                self.db.add(medication)
            
            self.db.commit()
            logger.info(f"Created health record {health_record.id} for user {user_id}")
            
            # Generate AI insights based on new record
            self._generate_health_insights_async(user_id, health_record.id)
            
            return health_record
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating health record: {str(e)}")
            raise
    
    def get_health_records(self, user_id: int, pet_id: Optional[int] = None, 
                          record_type: Optional[str] = None, 
                          start_date: Optional[date] = None,
                          end_date: Optional[date] = None,
                          limit: int = 100) -> List[HealthRecord]:
        """
        Retrieve health records with filtering options
        """
        try:
            query = self.db.query(HealthRecord).filter(HealthRecord.user_id == user_id)
            
            if pet_id:
                query = query.filter(HealthRecord.pet_id == pet_id)
            
            if record_type:
                query = query.filter(HealthRecord.record_type == HealthRecordType(record_type))
            
            if start_date:
                query = query.filter(HealthRecord.record_date >= start_date)
            
            if end_date:
                query = query.filter(HealthRecord.record_date <= end_date)
            
            records = query.order_by(desc(HealthRecord.record_date)).limit(limit).all()
            
            logger.info(f"Retrieved {len(records)} health records for user {user_id}")
            return records
            
        except Exception as e:
            logger.error(f"Error retrieving health records: {str(e)}")
            raise
    
    def get_health_record_by_id(self, user_id: int, record_id: int) -> Optional[HealthRecord]:
        """
        Get a specific health record by ID
        """
        try:
            record = self.db.query(HealthRecord).filter(
                and_(HealthRecord.id == record_id, HealthRecord.user_id == user_id)
            ).first()
            
            return record
            
        except Exception as e:
            logger.error(f"Error retrieving health record {record_id}: {str(e)}")
            raise
    
    def update_health_record(self, user_id: int, record_id: int, 
                           update_data: Dict[str, Any]) -> Optional[HealthRecord]:
        """
        Update an existing health record
        """
        try:
            record = self.get_health_record_by_id(user_id, record_id)
            if not record:
                return None
            
            # Update fields
            for key, value in update_data.items():
                if hasattr(record, key) and value is not None:
                    setattr(record, key, value)
            
            record.updated_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Updated health record {record_id} for user {user_id}")
            return record
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating health record {record_id}: {str(e)}")
            raise
    
    def delete_health_record(self, user_id: int, record_id: int) -> bool:
        """
        Delete a health record
        """
        try:
            record = self.get_health_record_by_id(user_id, record_id)
            if not record:
                return False
            
            self.db.delete(record)
            self.db.commit()
            
            logger.info(f"Deleted health record {record_id} for user {user_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting health record {record_id}: {str(e)}")
            raise
    
    # ==================== ENHANCED REMINDER MANAGEMENT ====================
    
    def create_reminder(self, user_id: int, reminder_data: Dict[str, Any]) -> HealthReminder:
        """
        Create a new health reminder with enhanced timezone-aware features
        """
        try:
            from datetime import datetime, time, timezone
            import pytz
            
            # 🎯 CONTEXT7 ENHANCEMENT: Handle timezone-aware reminder creation
            
            # Check if this is a timezone-aware reminder (from enhanced chat service)
            is_timezone_aware = reminder_data.get('_timezone_metadata', {}).get('timezone_aware_creation', False)
            
            if is_timezone_aware:
                current_app.logger.info("🌍 Processing timezone-aware reminder creation")
                
                # Handle UTC datetime from timezone-aware creation
                due_datetime_utc = reminder_data.get('due_date')  # This is already a UTC datetime
                
                if isinstance(due_datetime_utc, datetime):
                    # Extract date and time from UTC datetime
                    due_date = due_datetime_utc.date()
                    due_time = due_datetime_utc.time()
                    current_app.logger.info(f"📅 Extracted from UTC datetime: date={due_date}, time={due_time}")
                else:
                    # Fallback to original parsing
                    due_date = reminder_data['due_date']
                    due_time = reminder_data.get('due_time')
            else:
                # Original logic for non-timezone-aware reminders
                due_date = reminder_data['due_date']
                due_time = reminder_data.get('due_time')
            
            # Parse due_time if provided as string
            if due_time and isinstance(due_time, str):
                if ':' in due_time:
                    time_parts = due_time.split(':')
                    due_time = time(int(time_parts[0]), int(time_parts[1]))
                else:
                    due_time = None
            
            # Calculate reminder datetime with timezone awareness
            reminder_date = reminder_data.get('reminder_date')
            reminder_time = reminder_data.get('reminder_time')
            
            # If reminder_date not provided, calculate from due_date and days_before
            if not reminder_date:
                days_before = reminder_data.get('days_before_reminder', 7)
                hours_before = reminder_data.get('hours_before_reminder', 0)
                
                # 🎯 CONTEXT7 FIX: For immediate reminders (same day), use due_date as reminder_date
                if days_before == 0 and hours_before == 0:
                    # This is an immediate reminder - trigger at the same time as due time
                    reminder_date = due_date
                    reminder_time = due_time
                    current_app.logger.info(f"📅 Immediate reminder: due_date={due_date}, reminder_date={reminder_date}")
                else:
                    # This is an advance reminder - calculate based on days/hours before
                    if is_timezone_aware and isinstance(reminder_data.get('due_date'), datetime):
                        # Calculate from UTC datetime
                        due_datetime_utc = reminder_data['due_date']
                        reminder_datetime_utc = due_datetime_utc - timedelta(days=days_before, hours=hours_before)
                        reminder_date = reminder_datetime_utc.date()
                        reminder_time = reminder_datetime_utc.time()
                        current_app.logger.info(f"📅 Timezone-aware advance reminder: due_date={due_date}, reminder_date={reminder_date}, days_before={days_before}")
                    else:
                        # Original calculation for non-timezone-aware
                        if due_time:
                            due_datetime = datetime.combine(due_date, due_time)
                        else:
                            due_datetime = datetime.combine(due_date, time(9, 0))  # Default 9 AM
                        
                        reminder_datetime = due_datetime - timedelta(days=days_before, hours=hours_before)
                        reminder_date = reminder_datetime.date()
                        reminder_time = reminder_datetime.time()
                        current_app.logger.info(f"📅 Standard advance reminder: due_date={due_date}, reminder_date={reminder_date}, days_before={days_before}")
            else:
                current_app.logger.info(f"📅 Explicit reminder_date provided: {reminder_date}")
            
            # If reminder_time not set and we have due_time, use due_time as reminder_time
            if not reminder_time and due_time:
                reminder_time = due_time
                current_app.logger.info(f"🕰️  Using due_time as reminder_time: {reminder_time}")
            
            # Parse reminder_time if provided as string
            if reminder_time and isinstance(reminder_time, str):
                if ':' in reminder_time:
                    time_parts = reminder_time.split(':')
                    reminder_time = time(int(time_parts[0]), int(time_parts[1]))
                else:
                    reminder_time = time(9, 0)  # Default 9 AM
            
            # Handle recurrence settings
            recurrence_type = RecurrenceType(reminder_data.get('recurrence_type', 'none'))
            recurrence_interval = reminder_data.get('recurrence_interval', 1)
            recurrence_end_date = reminder_data.get('recurrence_end_date')
            max_occurrences = reminder_data.get('max_occurrences')
            
            # Parse recurrence_end_date if string
            if recurrence_end_date and isinstance(recurrence_end_date, str):
                recurrence_end_date = datetime.strptime(recurrence_end_date, '%Y-%m-%d').date()
            
            # Store timezone metadata if available
            extra_metadata = reminder_data.get('_timezone_metadata', {})
            if extra_metadata:
                current_app.logger.info(f"🌍 Storing timezone metadata: {extra_metadata}")
            
            # Create reminder with enhanced timezone support
            reminder = HealthReminder(
                user_id=user_id,
                pet_id=reminder_data.get('pet_id'),
                reminder_type=ReminderType(reminder_data['reminder_type']),
                title=reminder_data['title'],
                description=reminder_data.get('description'),
                due_date=due_date,
                due_time=due_time,
                reminder_date=reminder_date,
                reminder_time=reminder_time,
                send_email=reminder_data.get('send_email', True),
                send_push=reminder_data.get('send_push', True),
                send_sms=reminder_data.get('send_sms', False),
                days_before_reminder=reminder_data.get('days_before_reminder', 7),
                hours_before_reminder=reminder_data.get('hours_before_reminder', 0),
                recurrence_type=recurrence_type,
                recurrence_interval=recurrence_interval,
                recurrence_end_date=recurrence_end_date,
                max_occurrences=max_occurrences,
                current_occurrence=reminder_data.get('current_occurrence', 1),
                health_record_id=reminder_data.get('health_record_id'),
                extra_data=json.dumps(extra_metadata) if extra_metadata else None
                )
            
            self.db.add(reminder)
            self.db.commit()
            
            # 🎯 PRECISION SCHEDULING: Schedule the reminder at exact time with timezone awareness
            try:
                from app.services.precision_reminder_scheduler import get_precision_scheduler
                precision_scheduler = get_precision_scheduler()
                
                if precision_scheduler and precision_scheduler.is_running:
                    scheduled = precision_scheduler.schedule_reminder(reminder)
                    if scheduled:
                        current_app.logger.info(f"⏰ Precision scheduled timezone-aware reminder {reminder.id}")
                    else:
                        current_app.logger.warning(f"⚠️  Failed to precision schedule reminder {reminder.id}")
                else:
                    current_app.logger.warning(f"⚠️  Precision scheduler not available for reminder {reminder.id}")
                    
            except Exception as scheduler_error:
                current_app.logger.error(f"❌ Error scheduling reminder {reminder.id} with precision scheduler: {str(scheduler_error)}")
                # Don't fail the reminder creation if scheduling fails
            
            if is_timezone_aware:
                current_app.logger.info(f"✅ Created timezone-aware reminder {reminder.id} for user {user_id}: {reminder.title}")
                current_app.logger.info(f"📅 Stored with timezone metadata: {extra_metadata}")
            else:
                current_app.logger.info(f"✅ Created enhanced reminder {reminder.id} for user {user_id}: {reminder.title}")
            
            return reminder
            
        except Exception as e:
            self.db.rollback()
            current_app.logger.error(f"Error creating enhanced reminder: {str(e)}")
            raise
    
    def update_reminder(self, user_id: int, reminder_id: int, update_data: Dict[str, Any]) -> Optional[HealthReminder]:
        """
        Update an existing reminder with enhanced features
        """
        try:
            reminder = self.db.query(HealthReminder).filter(
                and_(HealthReminder.id == reminder_id, HealthReminder.user_id == user_id)
            ).first()
            
            if not reminder:
                return None
            
            # Update basic fields
            if 'title' in update_data:
                reminder.title = update_data['title']
            if 'description' in update_data:
                reminder.description = update_data['description']
            if 'due_date' in update_data:
                reminder.due_date = update_data['due_date']
            
            # Update time fields
            if 'due_time' in update_data:
                due_time = update_data['due_time']
                if due_time and isinstance(due_time, str) and ':' in due_time:
                    time_parts = due_time.split(':')
                    reminder.due_time = time(int(time_parts[0]), int(time_parts[1]))
                else:
                    reminder.due_time = due_time
            
            if 'reminder_date' in update_data:
                reminder.reminder_date = update_data['reminder_date']
            
            if 'reminder_time' in update_data:
                reminder_time = update_data['reminder_time']
                if reminder_time and isinstance(reminder_time, str) and ':' in reminder_time:
                    time_parts = reminder_time.split(':')
                    reminder.reminder_time = time(int(time_parts[0]), int(time_parts[1]))
                else:
                    reminder.reminder_time = reminder_time
            
            # Update notification settings
            if 'send_email' in update_data:
                reminder.send_email = update_data['send_email']
            if 'send_push' in update_data:
                reminder.send_push = update_data['send_push']
            if 'send_sms' in update_data:
                reminder.send_sms = update_data['send_sms']
            if 'days_before_reminder' in update_data:
                reminder.days_before_reminder = update_data['days_before_reminder']
            if 'hours_before_reminder' in update_data:
                reminder.hours_before_reminder = update_data['hours_before_reminder']
            
            # Update recurrence settings
            if 'recurrence_type' in update_data:
                reminder.recurrence_type = RecurrenceType(update_data['recurrence_type'])
            if 'recurrence_interval' in update_data:
                reminder.recurrence_interval = update_data['recurrence_interval']
            if 'recurrence_end_date' in update_data:
                end_date = update_data['recurrence_end_date']
                if end_date and isinstance(end_date, str):
                    reminder.recurrence_end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                else:
                    reminder.recurrence_end_date = end_date
            if 'max_occurrences' in update_data:
                reminder.max_occurrences = update_data['max_occurrences']
            
            # Update metadata
            if 'metadata' in update_data:
                reminder.metadata = json.dumps(update_data['metadata']) if update_data['metadata'] else None
            
            reminder.updated_at = datetime.utcnow()
            self.db.commit()
            
            # 🎯 PRECISION SCHEDULING: Reschedule the updated reminder
            try:
                from app.services.precision_reminder_scheduler import get_precision_scheduler
                precision_scheduler = get_precision_scheduler()
                
                if precision_scheduler and precision_scheduler.is_running:
                    rescheduled = precision_scheduler.reschedule_reminder(reminder)
                    if rescheduled:
                        logger.info(f"⏰ Precision rescheduled reminder {reminder.id} for exact time")
                    else:
                        logger.warning(f"⚠️  Failed to precision reschedule reminder {reminder.id}")
                else:
                    logger.warning(f"⚠️  Precision scheduler not available for reminder {reminder.id}")
                    
            except Exception as scheduler_error:
                logger.error(f"❌ Error rescheduling reminder {reminder.id} with precision scheduler: {str(scheduler_error)}")
                # Don't fail the reminder update if scheduling fails
            
            logger.info(f"Updated reminder {reminder_id} for user {user_id}")
            return reminder
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating reminder {reminder_id}: {str(e)}")
            raise
    
    def get_active_reminders(self, user_id: int, pet_id: Optional[int] = None) -> List[HealthReminder]:
        """
        Get active reminders for a user with enhanced filtering
        """
        try:
            query = self.db.query(HealthReminder).filter(
                and_(
                    HealthReminder.user_id == user_id,
                    HealthReminder.status == ReminderStatus.PENDING
                )
            )
            
            if pet_id:
                query = query.filter(HealthReminder.pet_id == pet_id)
            
            reminders = query.order_by(HealthReminder.due_date, HealthReminder.due_time).all()
            
            logger.info(f"Retrieved {len(reminders)} active reminders for user {user_id}")
            return reminders
            
        except Exception as e:
            logger.error(f"Error retrieving active reminders: {str(e)}")
            raise
    
    def get_all_reminders(self, user_id: int, pet_id: Optional[int] = None) -> List[HealthReminder]:
        """
        Get all reminders for a user (including completed and overdue) with enhanced sorting
        """
        try:
            query = self.db.query(HealthReminder).filter(
                HealthReminder.user_id == user_id
            )
            
            if pet_id:
                query = query.filter(HealthReminder.pet_id == pet_id)
            
            reminders = query.order_by(
                desc(HealthReminder.due_date), 
                desc(HealthReminder.due_time)
            ).all()
            
            logger.info(f"Retrieved {len(reminders)} total reminders for user {user_id}")
            return reminders
            
        except Exception as e:
            logger.error(f"Error retrieving all reminders: {str(e)}")
            raise
    
    def get_overdue_reminders(self, user_id: int) -> List[HealthReminder]:
        """
        Get overdue reminders for a user with time consideration
        """
        try:
            now = datetime.now()
            today = now.date()
            current_time = now.time()
            
            reminders = self.db.query(HealthReminder).filter(
                and_(
                    HealthReminder.user_id == user_id,
                    HealthReminder.status == ReminderStatus.PENDING,
                    or_(
                        HealthReminder.due_date < today,
                        and_(
                            HealthReminder.due_date == today,
                            HealthReminder.due_time.is_not(None),
                            HealthReminder.due_time < current_time
                        )
                    )
                )
            ).all()
            
            # Update status to overdue
            for reminder in reminders:
                reminder.status = ReminderStatus.OVERDUE
            
            self.db.commit()
            
            logger.info(f"Found {len(reminders)} overdue reminders for user {user_id}")
            return reminders
            
        except Exception as e:
            logger.error(f"Error retrieving overdue reminders: {str(e)}")
            raise
    
    def get_upcoming_reminders(self, user_id: int, days_ahead: int = 7) -> List[HealthReminder]:
        """
        Get upcoming reminders within specified days
        """
        try:
            end_date = date.today() + timedelta(days=days_ahead)
            
            reminders = self.db.query(HealthReminder).filter(
                and_(
                    HealthReminder.user_id == user_id,
                    HealthReminder.status == ReminderStatus.PENDING,
                    HealthReminder.due_date <= end_date,
                    HealthReminder.due_date >= date.today()
                )
            ).order_by(HealthReminder.due_date, HealthReminder.due_time).all()
            
            logger.info(f"Retrieved {len(reminders)} upcoming reminders for user {user_id}")
            return reminders
            
        except Exception as e:
            logger.error(f"Error retrieving upcoming reminders: {str(e)}")
            raise
    
    def get_recurring_reminders(self, user_id: int) -> List[HealthReminder]:
        """
        Get all recurring reminders for a user
        """
        try:
            reminders = self.db.query(HealthReminder).filter(
                and_(
                    HealthReminder.user_id == user_id,
                    HealthReminder.recurrence_type != RecurrenceType.NONE
                )
            ).order_by(HealthReminder.due_date).all()
            
            logger.info(f"Retrieved {len(reminders)} recurring reminders for user {user_id}")
            return reminders
            
        except Exception as e:
            logger.error(f"Error retrieving recurring reminders: {str(e)}")
            raise
    
    def complete_reminder(self, user_id: int, reminder_id: int) -> bool:
        """
        Mark a reminder as completed
        """
        try:
            reminder = self.db.query(HealthReminder).filter(
                and_(HealthReminder.id == reminder_id, HealthReminder.user_id == user_id)
            ).first()
            
            if not reminder:
                return False
            
            reminder.status = ReminderStatus.COMPLETED
            reminder.completed_at = datetime.utcnow()
            reminder.updated_at = datetime.utcnow()
            self.db.commit()
            
            # 🎯 PRECISION SCHEDULING: Unschedule the completed reminder
            try:
                from app.services.precision_reminder_scheduler import get_precision_scheduler
                precision_scheduler = get_precision_scheduler()
                
                if precision_scheduler and precision_scheduler.is_running:
                    unscheduled = precision_scheduler.unschedule_reminder(reminder_id)
                    if unscheduled:
                        logger.info(f"⏰ Precision unscheduled completed reminder {reminder_id}")
                    else:
                        logger.info(f"⏰ Completed reminder {reminder_id} was not scheduled")
                else:
                    logger.warning(f"⚠️  Precision scheduler not available for reminder {reminder_id}")
                    
            except Exception as scheduler_error:
                logger.error(f"❌ Error unscheduling completed reminder {reminder_id}: {str(scheduler_error)}")
                # Don't fail the completion if unscheduling fails
            
            logger.info(f"Completed reminder {reminder_id} for user {user_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error completing reminder {reminder_id}: {str(e)}")
            raise

    def delete_reminder(self, user_id: int, reminder_id: int) -> bool:
        """
        Delete a reminder
        """
        try:
            reminder = self.db.query(HealthReminder).filter(
                and_(HealthReminder.id == reminder_id, HealthReminder.user_id == user_id)
            ).first()
            
            if not reminder:
                return False
            
            # 🎯 PRECISION SCHEDULING: Unschedule the reminder before deletion
            try:
                from app.services.precision_reminder_scheduler import get_precision_scheduler
                precision_scheduler = get_precision_scheduler()
                
                if precision_scheduler and precision_scheduler.is_running:
                    unscheduled = precision_scheduler.unschedule_reminder(reminder_id)
                    if unscheduled:
                        logger.info(f"⏰ Precision unscheduled reminder {reminder_id}")
                    else:
                        logger.info(f"⏰ Reminder {reminder_id} was not scheduled")
                else:
                    logger.warning(f"⚠️  Precision scheduler not available for reminder {reminder_id}")
                    
            except Exception as scheduler_error:
                logger.error(f"❌ Error unscheduling reminder {reminder_id}: {str(scheduler_error)}")
                # Continue with deletion even if unscheduling fails
            
            # 🎯 FIX: Delete related notification records first to avoid foreign key constraint violation
            try:
                related_notifications = self.db.query(ReminderNotification).filter(
                    ReminderNotification.reminder_id == reminder_id
                ).all()
                
                for notification in related_notifications:
                    self.db.delete(notification)
                
                # Flush to ensure notifications are deleted first
                self.db.flush()
                
                logger.info(f"🧹 Deleted {len(related_notifications)} related notification records for reminder {reminder_id}")
                
            except Exception as cleanup_error:
                logger.error(f"❌ Error cleaning up notifications for reminder {reminder_id}: {str(cleanup_error)}")
                # Continue with reminder deletion anyway
            
            # Now safely delete the reminder
            self.db.delete(reminder)
            self.db.commit()
            
            logger.info(f"Deleted reminder {reminder_id} for user {user_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting reminder {reminder_id}: {str(e)}")
            raise
    
    # ==================== NOTIFICATION HISTORY ====================
    
    def get_reminder_notifications(self, user_id: int, reminder_id: Optional[int] = None) -> List[ReminderNotification]:
        """
        Get notification history for reminders
        """
        try:
            query = self.db.query(ReminderNotification).filter(
                ReminderNotification.user_id == user_id
            )
            
            if reminder_id:
                query = query.filter(ReminderNotification.reminder_id == reminder_id)
            
            notifications = query.order_by(desc(ReminderNotification.created_at)).all()
            
            logger.info(f"Retrieved {len(notifications)} notification records for user {user_id}")
            return notifications
            
        except Exception as e:
            logger.error(f"Error retrieving notification history: {str(e)}")
            raise
    
    # ==================== ANALYTICS AND INSIGHTS ====================
    
    def get_reminder_analytics(self, user_id: int, days_back: int = 30) -> Dict[str, Any]:
        """
        Get reminder analytics and insights
        """
        try:
            start_date = date.today() - timedelta(days=days_back)
            
            # Get all reminders in date range
            reminders = self.db.query(HealthReminder).filter(
                and_(
                    HealthReminder.user_id == user_id,
                    HealthReminder.created_at >= start_date
                )
            ).all()
            
            # Calculate analytics
            total_reminders = len(reminders)
            completed_reminders = len([r for r in reminders if r.status == ReminderStatus.COMPLETED])
            overdue_reminders = len([r for r in reminders if r.status == ReminderStatus.OVERDUE])
            pending_reminders = len([r for r in reminders if r.status == ReminderStatus.PENDING])
            
            # Group by type
            type_breakdown = {}
            for reminder in reminders:
                reminder_type = reminder.reminder_type.value
                if reminder_type not in type_breakdown:
                    type_breakdown[reminder_type] = {'total': 0, 'completed': 0, 'overdue': 0, 'pending': 0}
                
                type_breakdown[reminder_type]['total'] += 1
                type_breakdown[reminder_type][reminder.status.value] += 1
            
            # Calculate completion rate
            completion_rate = (completed_reminders / total_reminders * 100) if total_reminders > 0 else 0
            
            # Get notification statistics
            notifications = self.db.query(ReminderNotification).filter(
                and_(
                    ReminderNotification.user_id == user_id,
                    ReminderNotification.created_at >= start_date
                )
            ).all()
            
            notification_stats = {
                'total_sent': len([n for n in notifications if n.status.value == 'sent']),
                'total_failed': len([n for n in notifications if n.status.value == 'failed']),
                'email_sent': len([n for n in notifications if n.notification_type == 'email' and n.status.value == 'sent']),
                'push_sent': len([n for n in notifications if n.notification_type == 'push' and n.status.value == 'sent']),
                'sms_sent': len([n for n in notifications if n.notification_type == 'sms' and n.status.value == 'sent'])
            }
            
            return {
                'summary': {
                    'total_reminders': total_reminders,
                    'completed_reminders': completed_reminders,
                    'overdue_reminders': overdue_reminders,
                    'pending_reminders': pending_reminders,
                    'completion_rate': round(completion_rate, 2)
                },
                'type_breakdown': type_breakdown,
                'notification_stats': notification_stats,
                'date_range': {
                    'start_date': start_date.isoformat(),
                    'end_date': date.today().isoformat(),
                    'days': days_back
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting reminder analytics: {str(e)}")
            raise
    
    # ==================== AI INSIGHTS GENERATION ====================
    
    def generate_health_insights(self, user_id: int, pet_id: Optional[int] = None) -> List[HealthInsight]:
        """
        Generate AI-powered health insights based on health history
        """
        try:
            # Get recent health records
            recent_records = self.get_health_records(
                user_id=user_id,
                pet_id=pet_id,
                start_date=date.today() - timedelta(days=365),
                limit=50
            )
            
            if not recent_records:
                logger.info(f"No recent health records found for user {user_id}")
                return []
            
            # Get pet profile for context
            pet_profile = None
            if pet_id:
                pet_profile = self.db.query(PetProfile).filter(
                    and_(PetProfile.user_id == user_id, PetProfile.id == pet_id)
                ).first()
            
            # Generate insights using AI
            insights = self._generate_ai_insights(recent_records, pet_profile)
            
            # Save insights to database
            saved_insights = []
            for insight_data in insights:
                insight = HealthInsight(
                    user_id=user_id,
                    pet_id=pet_id,
                    insight_type=insight_data['type'],
                    title=insight_data['title'],
                    content=insight_data['content'],
                    confidence_score=insight_data.get('confidence', 0.8),
                    generated_by='gpt-4',
                    based_on_records=','.join([str(r.id) for r in recent_records]),
                    expiry_date=date.today() + timedelta(days=30)
                )
                self.db.add(insight)
                saved_insights.append(insight)
            
            self.db.commit()
            
            logger.info(f"Generated {len(saved_insights)} health insights for user {user_id}")
            return saved_insights
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error generating health insights: {str(e)}")
            raise
    
    def _generate_ai_insights(self, health_records: List[HealthRecord], 
                            pet_profile: Optional[PetProfile] = None) -> List[Dict[str, Any]]:
        """
        Use OpenAI to generate health insights from health records
        """
        try:
            # Prepare context for AI
            context = self._prepare_health_context(health_records, pet_profile)
            
            prompt = f"""
            As a veterinary health expert, analyze the following pet health data and provide 3-5 personalized insights:

            {context}

            Please provide insights in the following categories:
            1. Care recommendations based on breed and age
            2. Vaccination schedule optimization
            3. Preventive care suggestions
            4. Cost-saving opportunities
            5. Health trend analysis

            Format your response as a JSON array with objects containing:
            - type: "care_tip", "warning", or "recommendation"
            - title: Brief descriptive title
            - content: Detailed explanation (2-3 sentences)
            - confidence: Float between 0.0 and 1.0
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1500
            )
            
            # Parse AI response
            import json
            insights = json.loads(response.choices[0].message.content)
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating AI insights: {str(e)}")
            # Return fallback insights
            return [
                {
                    "type": "care_tip",
                    "title": "Regular Health Checkups",
                    "content": "Schedule regular veterinary checkups to maintain your pet's health and catch any issues early.",
                    "confidence": 0.9
                }
            ]
    
    def _prepare_health_context(self, health_records: List[HealthRecord], 
                              pet_profile: Optional[PetProfile] = None) -> str:
        """
        Prepare health context for AI analysis
        """
        context_parts = []
        
        # Pet profile information
        if pet_profile:
            context_parts.append(f"""
            Pet Profile:
            - Name: {pet_profile.name}
            - Breed: {pet_profile.breed}
            - Age: {pet_profile.age} years
            - Weight: {pet_profile.weight} lbs
            - Known Allergies: {pet_profile.known_allergies or 'None'}
            - Medical Conditions: {pet_profile.medical_conditions or 'None'}
            """)
        
        # Health records summary
        if health_records:
            context_parts.append("Recent Health Records:")
            for record in health_records[:10]:  # Limit to recent records
                context_parts.append(f"""
                - {record.record_date}: {record.record_type.value.title()} - {record.title}
                  Cost: ${record.cost or 0}, Notes: {record.notes or 'None'}
                """)
        
        return "\n".join(context_parts)
    
    def get_health_insights(self, user_id: int, pet_id: Optional[int] = None) -> List[HealthInsight]:
        """
        Get existing health insights for a user
        """
        try:
            query = self.db.query(HealthInsight).filter(HealthInsight.user_id == user_id)
            
            if pet_id:
                query = query.filter(HealthInsight.pet_id == pet_id)
            
            # Filter out expired insights
            today = date.today()
            insights = query.filter(
                or_(HealthInsight.expiry_date.is_(None), HealthInsight.expiry_date >= today)
            ).order_by(desc(HealthInsight.created_at)).all()
            
            return insights
            
        except Exception as e:
            logger.error(f"Error retrieving health insights: {str(e)}")
            raise
    
    def _generate_health_insights_async(self, user_id: int, health_record_id: int):
        """
        Placeholder for async insight generation
        TODO: Implement with Celery or similar task queue
        """
        logger.info(f"Scheduled async insight generation for user {user_id}, record {health_record_id}")
    
    # ==================== HEALTH ANALYTICS ====================
    
    def get_health_summary(self, user_id: int, pet_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get comprehensive health summary for dashboard
        """
        try:
            # Get counts by record type
            query = self.db.query(HealthRecord).filter(HealthRecord.user_id == user_id)
            if pet_id:
                query = query.filter(HealthRecord.pet_id == pet_id)
            
            records = query.all()
            
            # Calculate summary statistics
            summary = {
                'total_records': len(records),
                'total_cost': sum(r.cost or 0 for r in records),
                'insurance_savings': sum(r.insurance_amount or 0 for r in records),
                'record_types': {},
                'recent_records': len([r for r in records if r.record_date >= date.today() - timedelta(days=30)]),
                'upcoming_reminders': len(self.get_active_reminders(user_id, pet_id)),
                'overdue_reminders': len(self.get_overdue_reminders(user_id))
            }
            
            # Count by type
            for record in records:
                record_type = record.record_type.value
                summary['record_types'][record_type] = summary['record_types'].get(record_type, 0) + 1
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating health summary: {str(e)}")
            raise
    
    def search_health_records(self, user_id: int, query: str, 
                            pet_id: Optional[int] = None) -> List[HealthRecord]:
        """
        Search health records by text query
        """
        try:
            db_query = self.db.query(HealthRecord).filter(HealthRecord.user_id == user_id)
            
            if pet_id:
                db_query = db_query.filter(HealthRecord.pet_id == pet_id)
            
            # Search in title, description, notes, and tags
            search_filter = or_(
                HealthRecord.title.ilike(f'%{query}%'),
                HealthRecord.description.ilike(f'%{query}%'),
                HealthRecord.notes.ilike(f'%{query}%'),
                HealthRecord.tags.ilike(f'%{query}%')
            )
            
            records = db_query.filter(search_filter).order_by(desc(HealthRecord.record_date)).all()
            
            logger.info(f"Found {len(records)} records matching query '{query}' for user {user_id}")
            return records
            
        except Exception as e:
            logger.error(f"Error searching health records: {str(e)}")
            raise 