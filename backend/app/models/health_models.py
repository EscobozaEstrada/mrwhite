from app import db
from datetime import datetime, date, time
import enum
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Boolean, ForeignKey, Enum, Float, Time, JSON

class HealthRecordType(enum.Enum):
    VACCINATION = "vaccination"
    VET_VISIT = "vet_visit"
    MEDICATION = "medication"
    ALLERGY = "allergy"
    SURGERY = "surgery"
    INJURY = "injury"
    CHECKUP = "checkup"
    EMERGENCY = "emergency"
    DENTAL = "dental"
    GROOMING = "grooming"
    OTHER = "other"

class ReminderType(enum.Enum):
    VACCINATION = "vaccination"
    VET_APPOINTMENT = "vet_appointment"
    MEDICATION = "medication"
    GROOMING = "grooming"
    CHECKUP = "checkup"
    CUSTOM = "custom"

class ReminderStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"

class RecurrenceType(enum.Enum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"

class NotificationStatus(enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"

class HealthRecord(db.Model):
    """
    Comprehensive health record model for storing all health-related information
    """
    __tablename__ = 'health_records'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    pet_id = db.Column(db.Integer, nullable=True)  # Optional pet association
    
    # Record metadata
    record_type = db.Column(db.Enum(HealthRecordType), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Date information
    record_date = db.Column(db.Date, nullable=False)  # When the event occurred
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Provider information
    veterinarian_name = db.Column(db.String(100))
    clinic_name = db.Column(db.String(100))
    clinic_address = db.Column(db.Text)
    
    # Cost tracking
    cost = db.Column(db.Numeric(10, 2))
    insurance_covered = db.Column(db.Boolean, default=False)
    insurance_amount = db.Column(db.Numeric(10, 2))
    
    # Additional metadata
    notes = db.Column(db.Text)
    tags = db.Column(db.String(500))  # Comma-separated tags
    
    # Relationships
    vaccinations = db.relationship("Vaccination", back_populates="health_record", cascade="all, delete-orphan")
    medications = db.relationship("Medication", back_populates="health_record", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<HealthRecord(id={self.id}, type={self.record_type.value}, title='{self.title}')>"

class Vaccination(db.Model):
    """
    Detailed vaccination records
    """
    __tablename__ = 'vaccinations'
    
    id = db.Column(db.Integer, primary_key=True)
    health_record_id = db.Column(db.Integer, db.ForeignKey('health_records.id'), nullable=False)
    
    # Vaccination details
    vaccine_name = db.Column(db.String(100), nullable=False)
    vaccine_type = db.Column(db.String(50))  # Core, Non-core, etc.
    batch_number = db.Column(db.String(50))
    manufacturer = db.Column(db.String(100))
    
    # Scheduling
    administration_date = db.Column(db.Date, nullable=False)
    next_due_date = db.Column(db.Date)
    
    # Status
    completed = db.Column(db.Boolean, default=True)
    adverse_reactions = db.Column(db.Text)
    
    # Relationship
    health_record = db.relationship("HealthRecord", back_populates="vaccinations")
    
    def __repr__(self):
        return f"<Vaccination(id={self.id}, vaccine='{self.vaccine_name}', date={self.administration_date})>"

class Medication(db.Model):
    """
    Medication tracking and history
    """
    __tablename__ = 'medications'
    
    id = db.Column(db.Integer, primary_key=True)
    health_record_id = db.Column(db.Integer, db.ForeignKey('health_records.id'), nullable=False)
    
    # Medication details
    medication_name = db.Column(db.String(100), nullable=False)
    dosage = db.Column(db.String(50))
    frequency = db.Column(db.String(50))  # Daily, Twice daily, etc.
    
    # Duration
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    
    # Status
    active = db.Column(db.Boolean, default=True)
    prescribed_by = db.Column(db.String(100))
    reason = db.Column(db.Text)
    side_effects = db.Column(db.Text)
    
    # Relationship
    health_record = db.relationship("HealthRecord", back_populates="medications")
    
    def __repr__(self):
        return f"<Medication(id={self.id}, name='{self.medication_name}', active={self.active})>"

class HealthReminder(db.Model):
    """
    Enhanced health reminder system with time-based scheduling, recurring reminders,
    and follow-up notifications for incomplete tasks
    """
    __tablename__ = 'health_reminders'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    pet_id = db.Column(db.Integer, nullable=True)
    
    # Reminder details
    reminder_type = db.Column(db.Enum(ReminderType), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Enhanced scheduling with time support
    due_date = db.Column(db.Date, nullable=False)
    due_time = db.Column(db.Time, nullable=True)  # Specific time for reminder
    reminder_date = db.Column(db.Date)  # When to send reminder
    reminder_time = db.Column(db.Time)  # Specific time to send reminder
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Status tracking
    status = db.Column(db.Enum(ReminderStatus), default=ReminderStatus.PENDING)
    completed_at = db.Column(db.DateTime)
    completed_by = db.Column(db.String(50))  # 'user', 'email_button', 'auto'
    completion_method = db.Column(db.String(50))  # 'web_portal', 'email_click', 'api'
    
    # 🎯 CONTEXT7 ENHANCEMENT: Follow-up notification system
    enable_followup_notifications = db.Column(db.Boolean, default=True)
    followup_interval_minutes = db.Column(db.Integer, default=30)  # Every 30 minutes
    max_followup_count = db.Column(db.Integer, default=5)  # Maximum 5 follow-ups
    current_followup_count = db.Column(db.Integer, default=0)  # Current follow-up count
    next_followup_at = db.Column(db.DateTime, nullable=True)  # When to send next follow-up
    last_followup_sent_at = db.Column(db.DateTime, nullable=True)  # Last follow-up timestamp
    followup_notifications_stopped = db.Column(db.Boolean, default=False)  # Manual stop
    
    # Notification settings
    send_email = db.Column(db.Boolean, default=True)
    send_push = db.Column(db.Boolean, default=True)
    send_sms = db.Column(db.Boolean, default=False)
    days_before_reminder = db.Column(db.Integer, default=7)
    hours_before_reminder = db.Column(db.Integer, default=0)
    
    # Recurring reminder settings (for AI-created series)
    recurrence_type = db.Column(db.Enum(RecurrenceType), default=RecurrenceType.NONE)
    recurrence_interval = db.Column(db.Integer, default=1)  # Every X days/weeks/months
    recurrence_end_date = db.Column(db.Date, nullable=True)
    max_occurrences = db.Column(db.Integer, nullable=True)
    current_occurrence = db.Column(db.Integer, default=1)
    parent_series_id = db.Column(db.String(50), nullable=True)  # Link related reminders
    is_recurring_instance = db.Column(db.Boolean, default=False)  # Part of a series
    
    # Notification tracking
    last_notification_sent = db.Column(db.DateTime, nullable=True)
    notification_attempts = db.Column(db.Integer, default=0)
    
    # Related health record
    health_record_id = db.Column(db.Integer, nullable=True)
    
    # Extra data for timezone and follow-up metadata
    extra_data = db.Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<HealthReminder(id={self.id}, type={self.reminder_type.value}, due={self.due_date} {self.due_time or ''})>"
    
    def get_next_due_datetime(self):
        """Get the next due datetime combining date and time"""
        if self.due_time:
            return datetime.combine(self.due_date, self.due_time)
        return datetime.combine(self.due_date, time(9, 0))  # Default to 9 AM
    
    def get_reminder_datetime(self):
        """Get the reminder datetime when notification should be sent"""
        if self.reminder_date and self.reminder_time:
            return datetime.combine(self.reminder_date, self.reminder_time)
        elif self.reminder_date:
            return datetime.combine(self.reminder_date, time(9, 0))
        return None
    
    def should_send_notification(self):
        """Check if notification should be sent now"""
        reminder_datetime = self.get_reminder_datetime()
        if not reminder_datetime:
            return False
        
        now = datetime.now()
        return (now >= reminder_datetime and 
                self.status == ReminderStatus.PENDING and
                (not self.last_notification_sent or 
                 (now - self.last_notification_sent).total_seconds() > 3600))  # At least 1 hour gap
    
    def should_send_followup(self):
        """
        🎯 CONTEXT7: Check if follow-up notification should be sent
        """
        if not self.enable_followup_notifications or self.followup_notifications_stopped:
            return False
        
        if self.status != ReminderStatus.PENDING:
            return False  # Already completed or cancelled
        
        if self.current_followup_count >= self.max_followup_count:
            return False  # Max follow-ups reached
        
        # Check if due time has passed
        due_datetime = self.get_next_due_datetime()
        now = datetime.now()
        
        if now < due_datetime:
            return False  # Not due yet
        
        # Check if it's time for next follow-up
        if self.next_followup_at and now >= self.next_followup_at:
            return True
        
        # If no follow-ups sent yet and due time passed, send first follow-up
        if self.current_followup_count == 0 and now >= due_datetime:
            return True
        
        return False
    
    def calculate_next_followup_time(self):
        """
        🎯 CONTEXT7: Calculate when the next follow-up should be sent
        """
        from datetime import timedelta
        
        if self.last_followup_sent_at:
            # Next follow-up is interval minutes after last one
            return self.last_followup_sent_at + timedelta(minutes=self.followup_interval_minutes)
        else:
            # First follow-up is interval minutes after due time
            due_datetime = self.get_next_due_datetime()
            return due_datetime + timedelta(minutes=self.followup_interval_minutes)
    
    def mark_completed(self, completed_by='user', completion_method='web_portal'):
        """
        🎯 CONTEXT7: Mark reminder as completed and stop follow-ups
        """
        self.status = ReminderStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.completed_by = completed_by
        self.completion_method = completion_method
        self.followup_notifications_stopped = True
        self.next_followup_at = None
    
    def generate_completion_token(self):
        """
        🎯 CONTEXT7: Generate secure token for email completion links
        """
        import uuid
        import hashlib
        
        # Create unique token based on reminder ID and timestamp
        token_data = f"{self.id}_{self.user_id}_{datetime.utcnow().timestamp()}"
        return hashlib.sha256(token_data.encode()).hexdigest()[:32]
    
    def get_next_recurrence_date(self):
        """Calculate next recurrence date based on recurrence settings"""
        if self.recurrence_type == RecurrenceType.NONE:
            return None
        
        from dateutil.relativedelta import relativedelta
        
        if self.recurrence_type == RecurrenceType.DAILY:
            return self.due_date + relativedelta(days=self.recurrence_interval)
        elif self.recurrence_type == RecurrenceType.WEEKLY:
            return self.due_date + relativedelta(weeks=self.recurrence_interval)
        elif self.recurrence_type == RecurrenceType.MONTHLY:
            return self.due_date + relativedelta(months=self.recurrence_interval)
        elif self.recurrence_type == RecurrenceType.YEARLY:
            return self.due_date + relativedelta(years=self.recurrence_interval)
        
        return None

class ReminderNotification(db.Model):
    """
    Track individual notification attempts for reminders
    """
    __tablename__ = 'reminder_notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    reminder_id = db.Column(db.Integer, db.ForeignKey('health_reminders.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Notification details
    notification_type = db.Column(db.String(20), nullable=False)  # email, push, sms
    status = db.Column(db.Enum(NotificationStatus), default=NotificationStatus.PENDING)
    
    # Timing
    scheduled_at = db.Column(db.DateTime, nullable=False)
    sent_at = db.Column(db.DateTime, nullable=True)
    delivered_at = db.Column(db.DateTime, nullable=True)
    
    # Message details
    subject = db.Column(db.String(255), nullable=True)
    message = db.Column(db.Text, nullable=True)
    recipient = db.Column(db.String(255), nullable=False)  # email or phone
    
    # Error tracking
    error_message = db.Column(db.Text, nullable=True)
    retry_count = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<ReminderNotification(id={self.id}, type={self.notification_type}, status={self.status.value})>"

class PetProfile(db.Model):
    """
    Enhanced pet profile with health-specific information
    """
    __tablename__ = 'pet_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Basic information
    name = db.Column(db.String(100), nullable=False)
    breed = db.Column(db.String(100))
    age = db.Column(db.Integer)
    weight = db.Column(db.Numeric(5, 2))
    gender = db.Column(db.String(10))
    
    # Health information
    microchip_id = db.Column(db.String(50))
    spayed_neutered = db.Column(db.Boolean)
    known_allergies = db.Column(db.Text)
    medical_conditions = db.Column(db.Text)
    
    # Emergency contacts
    emergency_vet_name = db.Column(db.String(100))
    emergency_vet_phone = db.Column(db.String(20))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<PetProfile(id={self.id}, name='{self.name}', breed='{self.breed}')>"

class HealthInsight(db.Model):
    """
    AI-generated health insights and recommendations
    """
    __tablename__ = 'health_insights'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    pet_id = db.Column(db.Integer, nullable=True)
    
    # Insight details
    insight_type = db.Column(db.String(50))  # care_tip, warning, recommendation
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    
    # AI metadata
    confidence_score = db.Column(db.Numeric(3, 2))  # 0.00 to 1.00
    generated_by = db.Column(db.String(50))  # AI model used
    
    # Relevance
    based_on_records = db.Column(db.Text)  # IDs of health records used
    expiry_date = db.Column(db.Date)  # When insight becomes outdated
    
    # Status
    shown_to_user = db.Column(db.Boolean, default=False)
    user_feedback = db.Column(db.String(20))  # helpful, not_helpful, etc.
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<HealthInsight(id={self.id}, type='{self.insight_type}', title='{self.title}')>" 