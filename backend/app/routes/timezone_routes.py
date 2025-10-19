#!/usr/bin/env python3
"""
Timezone Management Routes
AI-powered timezone detection and user preference management
"""

from flask import Blueprint, request, jsonify, current_app, g
from app.middleware.auth import require_auth
from app.services.ai_time_manager import get_ai_time_manager
from app.models.user import User
from app import db
import pytz
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

timezone_bp = Blueprint('timezone', __name__)

@timezone_bp.route('/detect', methods=['POST'])
@require_auth
def detect_timezone():
    """
    Intelligent timezone detection using multiple sources
    """
    try:
        user_id = g.user_id
        data = request.json or {}
        
        ai_time_manager = get_ai_time_manager()
        
        # Get detection sources
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', ''))
        browser_timezone = data.get('browser_timezone')
        browser_offset = data.get('browser_offset')  # Minutes from UTC
        user_input = data.get('user_input', '')  # Manual city/country input
        
        timezone_suggestions = []
        
        # 1. Browser detection (highest priority)
        if browser_timezone:
            browser_info = ai_time_manager.detect_timezone_from_browser(
                browser_timezone, 
                -browser_offset // 60 if browser_offset else 0
            )
            if browser_info:
                timezone_suggestions.append({
                    'source': 'browser',
                    'timezone': browser_info.timezone,
                    'city': browser_info.city,
                    'country': browser_info.country,
                    'offset': browser_info.offset,
                    'is_dst': browser_info.is_dst,
                    'confidence': browser_info.confidence,
                    'display_name': f"{browser_info.timezone} (Auto-detected)",
                    'recommended': True
                })
        
        # 2. IP-based detection (fallback)
        if ip_address and ip_address != '127.0.0.1':
            ip_info = ai_time_manager.detect_timezone_from_ip(ip_address)
            if ip_info:
                timezone_suggestions.append({
                    'source': 'ip',
                    'timezone': ip_info.timezone,
                    'city': ip_info.city,
                    'country': ip_info.country,
                    'offset': ip_info.offset,
                    'is_dst': ip_info.is_dst,
                    'confidence': ip_info.confidence,
                    'display_name': f"{ip_info.timezone} (Location-based)",
                    'recommended': len(timezone_suggestions) == 0
                })
        
        # 3. Manual input processing
        if user_input:
            manual_suggestions = ai_time_manager.suggest_timezones_from_input(user_input)
            for suggestion in manual_suggestions[:3]:  # Top 3 suggestions
                timezone_suggestions.append({
                    'source': 'manual',
                    'timezone': suggestion.timezone,
                    'city': suggestion.city,
                    'country': suggestion.country,
                    'offset': suggestion.offset,
                    'is_dst': suggestion.is_dst,
                    'confidence': suggestion.confidence,
                    'display_name': f"{suggestion.city}, {suggestion.country}",
                    'recommended': False
                })
        
        # 4. User's current preference as fallback
        user = User.query.get(user_id)
        if user and user.timezone and not timezone_suggestions:
            current_tz = pytz.timezone(user.timezone)
            now = datetime.now(current_tz)
            timezone_suggestions.append({
                'source': 'current',
                'timezone': user.timezone,
                'city': user.location_city or 'Unknown',
                'country': user.location_country or 'Unknown',
                'offset': now.utcoffset().total_seconds() / 3600,
                'is_dst': now.dst() is not None and now.dst().total_seconds() > 0,
                'confidence': 0.8,
                'display_name': f"{user.timezone} (Current setting)",
                'recommended': False
            })
        
        return jsonify({
            'success': True,
            'suggestions': timezone_suggestions,
            'user_id': user_id,
            'detection_sources': {
                'browser_timezone': browser_timezone,
                'ip_address': ip_address != '127.0.0.1',
                'user_input': bool(user_input)
            }
        })
        
    except Exception as e:
        logger.error(f"Timezone detection error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to detect timezone'
        }), 500

@timezone_bp.route('/set', methods=['POST'])
@require_auth
def set_timezone():
    """
    Set user's timezone preference with AI optimization
    """
    try:
        user_id = g.user_id
        data = request.json or {}
        
        timezone_str = data.get('timezone')
        location_city = data.get('location_city', '')
        location_country = data.get('location_country', '')
        auto_detect = data.get('auto_detect_timezone', True)
        
        if not timezone_str:
            return jsonify({
                'success': False,
                'error': 'Timezone is required'
            }), 400
        
        # Validate timezone
        try:
            pytz.timezone(timezone_str)
        except pytz.exceptions.UnknownTimeZoneError:
            return jsonify({
                'success': False,
                'error': 'Invalid timezone'
            }), 400
        
        # Update user's timezone preferences
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        user.timezone = timezone_str
        user.location_city = location_city
        user.location_country = location_country
        user.auto_detect_timezone = auto_detect
        
        # AI time manager optimizations
        ai_time_manager = get_ai_time_manager()
        
        # Get optimal reminder times for this timezone
        optimal_times = ai_time_manager.get_optimal_reminder_times(timezone_str)
        user.preferred_reminder_times = optimal_times
        
        # Store timezone change for learning
        ai_time_manager.learn_user_preference(user_id, 'timezone_change', {
            'from_timezone': user.timezone,
            'to_timezone': timezone_str,
            'manual_selection': not auto_detect,
            'city': location_city,
            'country': location_country
        })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Timezone updated successfully',
            'settings': {
                'timezone': user.timezone,
                'location_city': user.location_city,
                'location_country': user.location_country,
                'auto_detect_timezone': user.auto_detect_timezone,
                'preferred_reminder_times': user.preferred_reminder_times,
                'time_format_24h': user.time_format_24h,
                'current_local_time': datetime.now(pytz.timezone(timezone_str)).isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Set timezone error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to set timezone'
        }), 500

@timezone_bp.route('/user-settings', methods=['GET'])
@require_auth
def get_timezone_settings():
    """
    Get user's current timezone settings
    """
    try:
        user_id = g.user_id
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Default timezone if not set
        user_timezone = user.timezone or 'UTC'
        
        try:
            tz = pytz.timezone(user_timezone)
            now = datetime.now(tz)
            timezone_abbreviation = now.strftime('%Z')
        except:
            tz = pytz.UTC
            now = datetime.now(tz)
            timezone_abbreviation = 'UTC'
            user_timezone = 'UTC'
        
        settings = {
            'timezone': user_timezone,
            'location_city': user.location_city,
            'location_country': user.location_country,
            'auto_detect_timezone': user.auto_detect_timezone,
            'preferred_reminder_times': user.preferred_reminder_times,
            'time_format_24h': user.time_format_24h,
            'timezone_abbreviation': timezone_abbreviation,
            'current_local_time': now.isoformat(),
            'utc_offset': now.utcoffset().total_seconds() / 3600 if now.utcoffset() else 0
        }
        
        return jsonify({
            'success': True,
            'settings': settings
        })
        
    except Exception as e:
        logger.error(f"Get timezone settings error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get settings'
        }), 500

@timezone_bp.route('/user-settings', methods=['PUT'])
@require_auth
def update_timezone_settings():
    """
    Update user's timezone settings
    """
    try:
        user_id = g.user_id
        data = request.json or {}
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # Update provided fields
        if 'timezone' in data:
            try:
                pytz.timezone(data['timezone'])
                user.timezone = data['timezone']
            except pytz.exceptions.UnknownTimeZoneError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid timezone'
                }), 400
        
        if 'location_city' in data:
            user.location_city = data['location_city']
        
        if 'location_country' in data:
            user.location_country = data['location_country']
        
        if 'auto_detect_timezone' in data:
            user.auto_detect_timezone = data['auto_detect_timezone']
        
        if 'time_format_24h' in data:
            user.time_format_24h = data['time_format_24h']
        
        if 'preferred_reminder_times' in data:
            user.preferred_reminder_times = data['preferred_reminder_times']
        
        db.session.commit()
        
        # Return updated settings
        user_timezone = user.timezone or 'UTC'
        tz = pytz.timezone(user_timezone)
        now = datetime.now(tz)
        
        settings = {
            'timezone': user_timezone,
            'location_city': user.location_city,
            'location_country': user.location_country,
            'auto_detect_timezone': user.auto_detect_timezone,
            'preferred_reminder_times': user.preferred_reminder_times,
            'time_format_24h': user.time_format_24h,
            'timezone_abbreviation': now.strftime('%Z'),
            'current_local_time': now.isoformat(),
            'utc_offset': now.utcoffset().total_seconds() / 3600 if now.utcoffset() else 0
        }
        
        return jsonify({
            'success': True,
            'message': 'Settings updated successfully',
            'settings': settings
        })
        
    except Exception as e:
        logger.error(f"Update timezone settings error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to update settings'
        }), 500

@timezone_bp.route('/time-until-due', methods=['POST'])
@require_auth
def calculate_time_until_due():
    """
    Calculate real-time countdown until due date
    """
    try:
        user_id = g.user_id
        data = request.json or {}
        
        due_datetime_str = data.get('due_datetime')
        if not due_datetime_str:
            return jsonify({
                'success': False,
                'error': 'due_datetime is required'
            }), 400
        
        # Parse datetime string to datetime object
        try:
            # Handle ISO format: 2025-07-03T00:00:00.000Z
            if due_datetime_str.endswith('Z'):
                due_datetime_str = due_datetime_str[:-1] + '+00:00'
            
            due_datetime = datetime.fromisoformat(due_datetime_str)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid datetime format. Use ISO format: YYYY-MM-DDTHH:MM:SS.sssZ'
            }), 400
        
        user = User.query.get(user_id)
        user_timezone = user.timezone if user else 'UTC'
        
        ai_time_manager = get_ai_time_manager()
        countdown_info = ai_time_manager.calculate_time_until_due(
            due_datetime, user_timezone
        )
        
        return jsonify({
            'success': True,
            'countdown': countdown_info
        })
        
    except Exception as e:
        logger.error(f"Calculate time until due error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to calculate time until due'
        }), 500

@timezone_bp.route('/learn-preference', methods=['POST'])
@require_auth
def learn_user_preference():
    """
    Learn from user's time preferences for AI optimization
    """
    try:
        user_id = g.user_id
        data = request.json or {}
        
        preference_type = data.get('type')  # 'reminder_time', 'timezone_change', etc.
        preference_data = data.get('data', {})
        
        if not preference_type:
            return jsonify({
                'success': False,
                'error': 'Preference type is required'
            }), 400
        
        ai_time_manager = get_ai_time_manager()
        ai_time_manager.learn_user_preference(user_id, preference_type, preference_data)
        
        return jsonify({
            'success': True,
            'message': 'Preference learned successfully'
        })
        
    except Exception as e:
        logger.error(f"Learn preference error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to learn preference'
        }), 500 