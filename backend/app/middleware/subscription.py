from functools import wraps
from flask import jsonify, g
from app.models.user import User

def premium_required(f):
    """Decorator to require premium subscription"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'user_id') or not g.user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        user = User.query.get(g.user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        if not user.is_premium or user.subscription_status != 'active':
            return jsonify({
                'error': 'Premium subscription required',
                'premium_required': True
            }), 403
            
        return f(*args, **kwargs)
    return decorated_function

def subscription_status_check(f):
    """Decorator to add subscription info to response"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if hasattr(g, 'user_id') and g.user_id:
            user = User.query.get(g.user_id)
            if user:
                g.user_subscription = {
                    'is_premium': user.is_premium,
                    'subscription_status': user.subscription_status,
                    'payment_failed': user.payment_failed
                }
        return f(*args, **kwargs)
    return decorated_function 