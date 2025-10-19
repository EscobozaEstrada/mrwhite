from functools import wraps
from flask import jsonify, g, request
from app.services.usage_tracking_service import UsageTrackingService

def check_chat_usage(f):
    """Decorator to check chat usage limits"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'user_id') or not g.user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        usage_service = UsageTrackingService()
        can_chat, message = usage_service.check_chat_limit(g.user_id)
        
        if not can_chat:
            return jsonify({
                'error': message,
                'usage_limit_reached': True,
                'upgrade_required': True
            }), 429  # Too Many Requests
        
        return f(*args, **kwargs)
    return decorated_function

def check_document_usage(f):
    """Decorator to check document upload limits"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'user_id') or not g.user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        usage_service = UsageTrackingService()
        can_upload, message = usage_service.check_document_limit(g.user_id)
        
        if not can_upload:
            return jsonify({
                'error': message,
                'usage_limit_reached': True,
                'upgrade_required': True
            }), 429
        
        return f(*args, **kwargs)
    return decorated_function

def check_care_record_usage(f):
    """Decorator to check care record creation limits"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'user_id') or not g.user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        usage_service = UsageTrackingService()
        can_create, message = usage_service.check_care_record_limit(g.user_id)
        
        if not can_create:
            return jsonify({
                'error': message,
                'usage_limit_reached': True,
                'upgrade_required': True
            }), 429
        
        return f(*args, **kwargs)
    return decorated_function

def check_conversation_usage(f):
    """Decorator to check conversation creation limits"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'user_id') or not g.user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        usage_service = UsageTrackingService()
        can_create, message = usage_service.check_conversation_limit(g.user_id)
        
        if not can_create:
            return jsonify({
                'error': message,
                'usage_limit_reached': True,
                'upgrade_required': True
            }), 429
        
        return f(*args, **kwargs)
    return decorated_function 