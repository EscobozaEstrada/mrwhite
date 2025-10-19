#!/usr/bin/env python3
"""
AI Time Management Service
Intelligent timezone detection, time optimization, and reminder scheduling
"""

import pytz
import requests
import logging
from datetime import datetime, timedelta, time, timezone
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from flask import current_app

logger = logging.getLogger(__name__)

@dataclass
class TimeInsight:
    """Data class for time-related insights"""
    optimal_time: time
    confidence: float
    reason: str
    user_pattern: Dict[str, Any]

@dataclass
class TimezoneInfo:
    """Data class for timezone information"""
    timezone: str
    city: str
    country: str
    offset: str
    is_dst: bool
    confidence: float

class AITimeManager:
    """
    AI-powered time management system with:
    - Intelligent timezone detection
    - Optimal reminder time suggestions
    - User behavior pattern learning
    - Real-time countdown calculations
    """
    
    def __init__(self):
        self.timezone_cache = {}
        self.geolocation_api_key = current_app.config.get('GEOLOCATION_API_KEY') if current_app else None
    
    # ==================== TIMEZONE INTELLIGENCE ====================
    
    def detect_timezone_from_ip(self, ip_address: str) -> Optional[TimezoneInfo]:
        """
        Detect timezone from IP address using geolocation API
        """
        try:
            # Use ipapi.co as it's free and reliable
            response = requests.get(f"http://ipapi.co/{ip_address}/json/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                return TimezoneInfo(
                    timezone=data.get('timezone', 'UTC'),
                    city=data.get('city', ''),
                    country=data.get('country_name', ''),
                    offset=data.get('utc_offset', '+00:00'),
                    is_dst=data.get('dst', False),
                    confidence=0.9  # High confidence for IP-based detection
                )
        except Exception as e:
            logger.warning(f"IP timezone detection failed: {str(e)}")
        
        return None
    
    def detect_timezone_from_browser(self, browser_timezone: str, browser_offset: int) -> Optional[TimezoneInfo]:
        """
        Process timezone information from browser JavaScript
        """
        try:
            # Validate timezone
            tz = pytz.timezone(browser_timezone)
            now = datetime.now(tz)
            
            return TimezoneInfo(
                timezone=browser_timezone,
                city='',  # Browser doesn't provide city
                country='',  # Browser doesn't provide country
                offset=f"{browser_offset:+03d}:00",
                is_dst=bool(now.dst()),
                confidence=0.95  # Very high confidence for browser-reported timezone
            )
        except Exception as e:
            logger.warning(f"Browser timezone validation failed: {str(e)}")
        
        return None
    
    def get_smart_timezone_suggestions(self, user_input: str) -> List[TimezoneInfo]:
        """
        Get timezone suggestions based on user input (city, country, etc.)
        """
        suggestions = []
        user_input = user_input.lower().strip()
        
        # Common timezone mappings
        timezone_mappings = {
            'new york': 'America/New_York',
            'nyc': 'America/New_York',
            'los angeles': 'America/Los_Angeles',
            'la': 'America/Los_Angeles',
            'chicago': 'America/Chicago',
            'denver': 'America/Denver',
            'phoenix': 'America/Phoenix',
            'london': 'Europe/London',
            'paris': 'Europe/Paris',
            'berlin': 'Europe/Berlin',
            'tokyo': 'Asia/Tokyo',
            'sydney': 'Australia/Sydney',
            'mumbai': 'Asia/Kolkata',
            'dubai': 'Asia/Dubai',
            'toronto': 'America/Toronto',
            'vancouver': 'America/Vancouver',
        }
        
        # Check direct mappings
        if user_input in timezone_mappings:
            tz_name = timezone_mappings[user_input]
            try:
                tz = pytz.timezone(tz_name)
                now = datetime.now(tz)
                suggestions.append(TimezoneInfo(
                    timezone=tz_name,
                    city=user_input.title(),
                    country='',
                    offset=f"{now.utcoffset().total_seconds()/3600:+03.0f}:00",
                    is_dst=bool(now.dst()),
                    confidence=0.8
                ))
            except:
                pass
        
        # Search through all timezones for partial matches
        for tz_name in pytz.all_timezones:
            if user_input in tz_name.lower():
                try:
                    tz = pytz.timezone(tz_name)
                    now = datetime.now(tz)
                    
                    # Extract city from timezone name
                    city = tz_name.split('/')[-1].replace('_', ' ')
                    
                    suggestions.append(TimezoneInfo(
                        timezone=tz_name,
                        city=city,
                        country=tz_name.split('/')[0] if '/' in tz_name else '',
                        offset=f"{now.utcoffset().total_seconds()/3600:+03.0f}:00",
                        is_dst=bool(now.dst()),
                        confidence=0.6
                    ))
                    
                    if len(suggestions) >= 5:  # Limit suggestions
                        break
                except:
                    continue
        
        # Sort by confidence
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        return suggestions[:5]
    
    def suggest_timezones_from_input(self, user_input: str) -> List[TimezoneInfo]:
        """
        Wrapper for get_smart_timezone_suggestions for backward compatibility
        """
        return self.get_smart_timezone_suggestions(user_input)
    
    def get_optimal_reminder_times(self, timezone_str: str) -> Dict[str, Any]:
        """
        Get optimal reminder times for a given timezone
        """
        try:
            tz = pytz.timezone(timezone_str)
            now = datetime.now(tz)
            
            # Default optimal times for different reminder types
            optimal_times = {
                'vaccination': {
                    'hour': 9,
                    'minute': 0,
                    'reason': 'Morning appointments are typically available'
                },
                'medication': {
                    'hour': 20,
                    'minute': 0,
                    'reason': 'Evening routine for consistency'
                },
                'grooming': {
                    'hour': 10,
                    'minute': 0,
                    'reason': 'Late morning when pets are alert'
                },
                'checkup': {
                    'hour': 9,
                    'minute': 30,
                    'reason': 'Morning appointment slots'
                },
                'custom': {
                    'hour': 12,
                    'minute': 0,
                    'reason': 'Midday default'
                }
            }
            
            # Adjust for timezone-specific cultural patterns
            if 'Asia/' in timezone_str:
                # Asian timezones often prefer earlier times
                for reminder_type in optimal_times:
                    optimal_times[reminder_type]['hour'] = max(8, optimal_times[reminder_type]['hour'] - 1)
                    optimal_times[reminder_type]['reason'] += ' (adjusted for Asian timezone)'
            elif 'America/' in timezone_str:
                # American timezones often prefer later times
                for reminder_type in optimal_times:
                    optimal_times[reminder_type]['hour'] = min(22, optimal_times[reminder_type]['hour'] + 1)
                    optimal_times[reminder_type]['reason'] += ' (adjusted for American timezone)'
            
            return optimal_times
            
        except Exception as e:
            logger.error(f"Error getting optimal reminder times: {str(e)}")
            return {}
    
    def learn_user_preference(self, user_id: int, preference_type: str, preference_data: Dict[str, Any]):
        """
        Learn from user preferences to improve future suggestions
        """
        try:
            from app.models.user import User
            from app import db
            
            user = User.query.get(user_id)
            if not user:
                return
            
            # Initialize preferences if needed
            if not user.preferred_reminder_times:
                user.preferred_reminder_times = {}
            
            preferences = user.preferred_reminder_times
            
            # Handle different preference types
            if preference_type == 'timezone_change':
                # Learn from timezone changes
                if 'timezone_history' not in preferences:
                    preferences['timezone_history'] = []
                
                preferences['timezone_history'].append({
                    'timestamp': datetime.now().isoformat(),
                    'from_timezone': preference_data.get('from_timezone'),
                    'to_timezone': preference_data.get('to_timezone'),
                    'manual_selection': preference_data.get('manual_selection', False),
                    'city': preference_data.get('city'),
                    'country': preference_data.get('country')
                })
                
                # Keep only last 10 changes
                preferences['timezone_history'] = preferences['timezone_history'][-10:]
                
            elif preference_type == 'reminder_time':
                # Learn from reminder time selections
                reminder_type = preference_data.get('reminder_type', 'custom')
                chosen_time = preference_data.get('chosen_time')
                
                if reminder_type not in preferences:
                    preferences[reminder_type] = {
                        'count': 0,
                        'total_hour': 0,
                        'preferred_hour': 12,
                        'last_updated': datetime.now().isoformat()
                    }
                
                pattern = preferences[reminder_type]
                if chosen_time:
                    hour = chosen_time.get('hour', 12)
                    pattern['count'] += 1
                    pattern['total_hour'] += hour
                    pattern['preferred_hour'] = pattern['total_hour'] // pattern['count']
                    pattern['last_updated'] = datetime.now().isoformat()
            
            user.preferred_reminder_times = preferences
            db.session.commit()
            
            logger.info(f"Learned preference for user {user_id}: {preference_type}")
            
        except Exception as e:
            logger.error(f"Error learning user preference: {str(e)}")
    
    # ==================== AI OPTIMAL TIME SUGGESTIONS ====================
    
    def suggest_optimal_reminder_time(self, reminder_type: str, user_timezone: str, 
                                    user_preferences: Dict[str, Any] = None) -> TimeInsight:
        """
        AI-powered optimal time suggestion based on reminder type and user patterns
        """
        user_tz = pytz.timezone(user_timezone)
        user_preferences = user_preferences or {}
        
        # Default optimal times by reminder type
        optimal_times = {
            'vaccination': time(9, 0),   # Morning for vet appointments
            'vet_appointment': time(8, 30),  # Early morning for appointments
            'medication': time(20, 0),   # Evening for consistency
            'grooming': time(10, 0),     # Late morning
            'checkup': time(9, 30),      # Morning
            'custom': time(12, 0)        # Noon default
        }
        
        base_time = optimal_times.get(reminder_type, time(12, 0))
        confidence = 0.7
        reason = "AI-optimized based on reminder type"
        
        # Adjust based on user preferences
        if user_preferences:
            # Check for learned patterns
            if reminder_type in user_preferences:
                pattern = user_preferences[reminder_type]
                if 'preferred_hour' in pattern:
                    base_time = time(pattern['preferred_hour'], 0)
                    confidence = 0.9
                    reason = "Based on your historical preferences"
            
            # Check for general morning/evening preference
            if 'general_preference' in user_preferences:
                pref = user_preferences['general_preference']
                if pref == 'morning' and base_time.hour > 12:
                    base_time = time(9, 0)
                    reason = "Adjusted for morning preference"
                elif pref == 'evening' and base_time.hour < 12:
                    base_time = time(19, 0)
                    reason = "Adjusted for evening preference"
        
        # Adjust for timezone-specific cultural patterns
        now_local = datetime.now(user_tz)
        if 'Asia/' in user_timezone:
            # Asian timezones often prefer slightly earlier times
            base_time = time(max(8, base_time.hour - 1), base_time.minute)
            reason += " (optimized for Asian timezone)"
        elif 'America/' in user_timezone:
            # American timezones often prefer later times
            base_time = time(min(22, base_time.hour + 1), base_time.minute)
            reason += " (optimized for American timezone)"
        
        return TimeInsight(
            optimal_time=base_time,
            confidence=confidence,
            reason=reason,
            user_pattern=user_preferences.get(reminder_type, {})
        )
    
    def learn_user_patterns(self, user_id: int, reminder_type: str, 
                          chosen_time: time, user_timezone: str):
        """
        Learn from user's time choices to improve future suggestions
        """
        from app.models.user import User
        from app import db
        
        try:
            user = User.query.get(user_id)
            if not user:
                return
            
            # Initialize preferences if needed
            if not user.preferred_reminder_times:
                user.preferred_reminder_times = {}
            
            preferences = user.preferred_reminder_times
            
            # Update pattern for this reminder type
            if reminder_type not in preferences:
                preferences[reminder_type] = {
                    'count': 0,
                    'total_hour': 0,
                    'preferred_hour': chosen_time.hour,
                    'last_updated': datetime.now().isoformat()
                }
            
            pattern = preferences[reminder_type]
            pattern['count'] += 1
            pattern['total_hour'] += chosen_time.hour
            pattern['preferred_hour'] = pattern['total_hour'] // pattern['count']
            pattern['last_updated'] = datetime.now().isoformat()
            
            # Update general preference
            if 'general_preference' not in preferences:
                preferences['general_preference'] = 'neutral'
            
            # Determine if user prefers morning or evening
            if chosen_time.hour < 12:
                morning_count = preferences.get('morning_count', 0) + 1
                preferences['morning_count'] = morning_count
            else:
                evening_count = preferences.get('evening_count', 0) + 1
                preferences['evening_count'] = evening_count
            
            morning_total = preferences.get('morning_count', 0)
            evening_total = preferences.get('evening_count', 0)
            
            if morning_total > evening_total * 1.5:
                preferences['general_preference'] = 'morning'
            elif evening_total > morning_total * 1.5:
                preferences['general_preference'] = 'evening'
            
            user.preferred_reminder_times = preferences
            db.session.commit()
            
            logger.info(f"Learned time preference for user {user_id}: {reminder_type} at {chosen_time}")
            
        except Exception as e:
            logger.error(f"Error learning user patterns: {str(e)}")
    
    # ==================== REAL-TIME CALCULATIONS ====================
    
    def calculate_time_until_due(self, due_datetime: datetime, user_timezone: str) -> Dict[str, Any]:
        """
        Calculate real-time countdown until due date with intelligent formatting
        """
        try:
            user_tz = pytz.timezone(user_timezone)
            now_utc = datetime.now(timezone.utc)
            now_local = now_utc.astimezone(user_tz)
            
            # Ensure due_datetime is timezone-aware
            if due_datetime.tzinfo is None:
                due_datetime = due_datetime.replace(tzinfo=timezone.utc)
            
            due_local = due_datetime.astimezone(user_tz)
            
            # Calculate time difference
            time_diff = due_local - now_local
            
            # Extract components
            total_seconds = int(time_diff.total_seconds())
            is_overdue = total_seconds < 0
            
            if is_overdue:
                total_seconds = abs(total_seconds)
            
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            minutes = (total_seconds % 3600) // 60
            
            # Create human-readable format
            if is_overdue:
                if days > 0:
                    formatted = f"Overdue by {days} day{'s' if days != 1 else ''}"
                elif hours > 0:
                    formatted = f"Overdue by {hours} hour{'s' if hours != 1 else ''}"
                else:
                    formatted = f"Overdue by {minutes} minute{'s' if minutes != 1 else ''}"
                urgency = "critical"
                color = "#dc3545"
            elif days > 7:
                formatted = f"Due in {days} days"
                urgency = "low"
                color = "#28a745"
            elif days > 1:
                formatted = f"Due in {days} days, {hours} hours"
                urgency = "medium"
                color = "#ffc107"
            elif days == 1:
                formatted = f"Due tomorrow at {due_local.strftime('%I:%M %p')}"
                urgency = "high"
                color = "#fd7e14"
            elif hours > 2:
                formatted = f"Due in {hours} hours, {minutes} minutes"
                urgency = "high"
                color = "#fd7e14"
            elif hours > 0:
                formatted = f"Due in {hours}h {minutes}m"
                urgency = "critical"
                color = "#dc3545"
            else:
                formatted = f"Due in {minutes} minutes"
                urgency = "critical"
                color = "#dc3545"
            
            return {
                'total_seconds': total_seconds if not is_overdue else -total_seconds,
                'days': days,
                'hours': hours,
                'minutes': minutes,
                'formatted': formatted,
                'urgency': urgency,
                'color': color,
                'is_overdue': is_overdue,
                'due_local_time': due_local.strftime('%Y-%m-%d %I:%M %p %Z'),
                'due_local_date': due_local.strftime('%B %d, %Y'),
                'due_local_time_only': due_local.strftime('%I:%M %p')
            }
            
        except Exception as e:
            logger.error(f"Error calculating time until due: {str(e)}")
            return {
                'formatted': 'Time calculation error',
                'urgency': 'unknown',
                'color': '#6c757d',
                'is_overdue': False
            }
    
    def get_next_business_day(self, user_timezone: str, days_ahead: int = 1) -> datetime:
        """
        Get next business day in user's timezone (skipping weekends)
        """
        user_tz = pytz.timezone(user_timezone)
        current_date = datetime.now(user_tz).date()
        
        target_date = current_date + timedelta(days=days_ahead)
        
        # Skip weekends
        while target_date.weekday() >= 5:  # 5=Saturday, 6=Sunday
            target_date += timedelta(days=1)
        
        return datetime.combine(target_date, time(9, 0))
    
    def get_optimal_notification_times(self, due_datetime: datetime, user_timezone: str,
                                     advance_notice_days: int = 3) -> List[datetime]:
        """
        Calculate optimal notification times leading up to due date
        """
        user_tz = pytz.timezone(user_timezone)
        
        if due_datetime.tzinfo is None:
            due_datetime = due_datetime.replace(tzinfo=timezone.utc)
        
        due_local = due_datetime.astimezone(user_tz)
        notification_times = []
        
        # 1 week before (if enough time)
        one_week_before = due_local - timedelta(days=7)
        if one_week_before > datetime.now(user_tz):
            notification_times.append(one_week_before.replace(hour=9, minute=0, second=0))
        
        # Custom advance notice
        advance_before = due_local - timedelta(days=advance_notice_days)
        if advance_before > datetime.now(user_tz):
            notification_times.append(advance_before.replace(hour=9, minute=0, second=0))
        
        # Day before at 6 PM
        day_before = due_local - timedelta(days=1)
        if day_before > datetime.now(user_tz):
            notification_times.append(day_before.replace(hour=18, minute=0, second=0))
        
        # Day of at optimal time (2 hours before)
        day_of = due_local - timedelta(hours=2)
        if day_of > datetime.now(user_tz):
            notification_times.append(day_of)
        
        return notification_times
    
    # ==================== TIMEZONE UTILITIES ====================
    
    def format_time_for_user(self, dt: datetime, user_timezone: str, 
                           use_24h_format: bool = False) -> str:
        """
        Format datetime according to user's timezone and preferences
        """
        try:
            user_tz = pytz.timezone(user_timezone)
            
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            
            local_dt = dt.astimezone(user_tz)
            
            if use_24h_format:
                return local_dt.strftime('%Y-%m-%d %H:%M %Z')
            else:
                return local_dt.strftime('%Y-%m-%d %I:%M %p %Z')
                
        except Exception as e:
            logger.error(f"Error formatting time: {str(e)}")
            return dt.strftime('%Y-%m-%d %H:%M UTC')
    
    def get_timezone_abbreviation(self, timezone_name: str) -> str:
        """
        Get timezone abbreviation (e.g., EST, PST, GMT)
        """
        try:
            tz = pytz.timezone(timezone_name)
            now = datetime.now(tz)
            return now.strftime('%Z')
        except:
            return 'UTC'

# ==================== SERVICE INSTANCE ====================

def get_ai_time_manager() -> AITimeManager:
    """Get AI time manager instance"""
    return AITimeManager() 