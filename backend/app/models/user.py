from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
import pytz

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), index=True)
    reset_token = db.Column(db.String(100), nullable=True, index=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)
    
    # Subscription related fields
    is_premium = db.Column(db.Boolean, default=False)
    stripe_customer_id = db.Column(db.String(100), nullable=True, unique=True, index=True)
    stripe_subscription_id = db.Column(db.String(100), nullable=True, unique=True)
    subscription_status = db.Column(db.String(50), nullable=True)
    subscription_start_date = db.Column(db.DateTime, nullable=True)
    subscription_end_date = db.Column(db.DateTime, nullable=True)
    last_payment_date = db.Column(db.DateTime, nullable=True)
    payment_failed = db.Column(db.Boolean, default=False)
    
    # Credit System fields
    credits_balance = db.Column(db.Integer, default=0)  # Current credit balance
    total_credits_purchased = db.Column(db.Integer, default=0)  # Lifetime credits purchased
    credits_used_today = db.Column(db.Integer, default=0)  # Credits used today
    credits_used_this_month = db.Column(db.Integer, default=0)  # Credits used this month
    last_credit_reset_date = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())  # For daily/monthly resets
    last_monthly_refill_date = db.Column(db.Date, nullable=True)  # Track last monthly credit refill date
    
    # Usage Analytics
    lifetime_usage_stats = db.Column(db.JSON, default=dict)  # Store usage analytics
    subscription_tier = db.Column(db.String(50), default='free')
    
    # Free Credits & Bonuses
    daily_free_credits_claimed = db.Column(db.Boolean, default=False)  # Daily free credits
    signup_bonus_claimed = db.Column(db.Boolean, default=False)  # Signup bonus
    referral_credits = db.Column(db.Integer, default=0)  # Credits from referrals
    
    # Push Notification Support
    device_tokens = db.Column(db.JSON, default=dict)  # Store multiple device tokens
    push_notifications_enabled = db.Column(db.Boolean, default=True)  # Global push setting
    last_device_token_update = db.Column(db.DateTime, nullable=True)  # Track last update
    
    # Advanced Time Management
    timezone = db.Column(db.String(50), default='UTC')  # User's timezone (e.g., 'America/New_York')
    location_city = db.Column(db.String(100), nullable=True)  # User's city
    location_country = db.Column(db.String(100), nullable=True)  # User's country
    auto_detect_timezone = db.Column(db.Boolean, default=True)  # Auto-detect timezone
    preferred_reminder_times = db.Column(db.JSON, default=dict)  # AI-learned preferences
    time_format_24h = db.Column(db.Boolean, default=False)  # 24-hour vs 12-hour format
    
    # Dog Image
    dog_image = db.Column(db.String(255), nullable=True)  # S3 URL of uploaded dog image
    
    # Relationship with conversations
    conversations = db.relationship('Conversation', backref='user', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<User {self.username}>"
    
    def get_timezone(self):
        """Get user's timezone as pytz timezone object"""
        try:
            return pytz.timezone(self.timezone)
        except:
            return pytz.UTC
    
    def get_local_time(self, utc_datetime=None):
        """Convert UTC datetime to user's local time"""
        if utc_datetime is None:
            utc_datetime = datetime.now(timezone.utc)
        
        user_tz = self.get_timezone()
        if utc_datetime.tzinfo is None:
            utc_datetime = utc_datetime.replace(tzinfo=timezone.utc)
        
        return utc_datetime.astimezone(user_tz)
    
    def convert_to_utc(self, local_datetime):
        """Convert user's local time to UTC"""
        user_tz = self.get_timezone()
        if local_datetime.tzinfo is None:
            local_datetime = user_tz.localize(local_datetime)
        
        return local_datetime.astimezone(timezone.utc)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat(),
            'is_premium': self.is_premium,
            'subscription_status': self.subscription_status,
            'subscription_start_date': self.subscription_start_date.isoformat() if self.subscription_start_date else None,
            'subscription_end_date': self.subscription_end_date.isoformat() if self.subscription_end_date else None,
            'last_payment_date': self.last_payment_date.isoformat() if self.last_payment_date else None,
            'payment_failed': self.payment_failed,
            'stripe_customer_id': self.stripe_customer_id,
            'stripe_subscription_id': self.stripe_subscription_id,
            'credits_balance': self.credits_balance,
            'subscription_tier': self.subscription_tier,
            'daily_free_credits_claimed': self.daily_free_credits_claimed,
            'push_notifications_enabled': self.push_notifications_enabled,
            'device_tokens': self.device_tokens or {},
            'timezone': self.timezone,
            'location_city': self.location_city,
            'location_country': self.location_country,
            'time_format_24h': self.time_format_24h,
            'preferred_reminder_times': self.preferred_reminder_times or {},
            'dog_image': self.dog_image
        }
