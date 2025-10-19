from functools import wraps
from flask import request, jsonify, g
from app.utils.jwt import decode_token


def require_auth(f):
    """
    Decorator that requires authentication for a route.
    Extracts user information from JWT token and adds it to request.current_user
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip authentication for OPTIONS requests
        if request.method == 'OPTIONS':
            return f(*args, **kwargs)

        token = request.cookies.get('token')
        if not token:
            return jsonify({"message": "Unauthorized"}), 401
        
        try:
            user_data = decode_token(token)
            g.user_id = user_data.get('id')
            g.user_email = user_data.get('email')
            g.user_name = user_data.get('name', 'User')
            
            # Make user data available as request.current_user for compatibility
            request.current_user = {
                'id': g.user_id,
                'email': g.user_email,
                'name': g.user_name
            }
            
        except Exception as e:
            return jsonify({"message": "Invalid or expired token"}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function 