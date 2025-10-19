from typing import Dict, Any, List, Optional
from flask import request, jsonify
import re
from functools import wraps


class ValidationMiddleware:
    """Middleware for request validation and sanitization"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_password(password: str) -> tuple[bool, str]:
        """Validate password strength"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if not re.search(r'[A-Za-z]', password):
            return False, "Password must contain at least one letter"
        
        if not re.search(r'\d', password):
            return False, "Password must contain at least one number"
        
        return True, "Password is valid"
    
    @staticmethod
    def validate_username(username: str) -> tuple[bool, str]:
        """Validate username format"""
        if len(username) < 3:
            return False, "Username must be at least 3 characters long"
        
        if len(username) > 50:
            return False, "Username must be less than 50 characters"
        
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            return False, "Username can only contain letters, numbers, underscores, and hyphens"
        
        return True, "Username is valid"
    
    @staticmethod
    def sanitize_string(text: str, max_length: Optional[int] = None) -> str:
        """Sanitize string input by removing harmful characters"""
        if not text:
            return ""
        
        # Remove potential XSS characters
        sanitized = re.sub(r'[<>"\']', '', text.strip())
        
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized
    
    @staticmethod
    def validate_file_upload(file) -> tuple[bool, str]:
        """Validate uploaded file"""
        if not file or not file.filename:
            return False, "No file provided"
        
        # Check file size (limit to 10MB)
        if hasattr(file, 'content_length') and file.content_length > 10 * 1024 * 1024:
            return False, "File size exceeds 10MB limit"
        
        # Check file extension
        allowed_extensions = {'.pdf', '.txt', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.gif'}
        file_ext = '.' + file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        
        if file_ext not in allowed_extensions:
            return False, f"File type {file_ext} not allowed"
        
        return True, "File is valid"
    
    @staticmethod
    def validate_json_schema(data: Dict[str, Any], required_fields: List[str], 
                           optional_fields: Optional[List[str]] = None) -> tuple[bool, str]:
        """Validate JSON data against schema"""
        if not isinstance(data, dict):
            return False, "Request body must be valid JSON"
        
        # Check required fields
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"
        
        # Check for unexpected fields
        allowed_fields = set(required_fields + (optional_fields or []))
        unexpected_fields = set(data.keys()) - allowed_fields
        if unexpected_fields:
            return False, f"Unexpected fields: {', '.join(unexpected_fields)}"
        
        return True, "JSON schema is valid"


def validate_signup_data(f):
    """Decorator to validate signup request data"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        data = request.get_json()
        
        # Validate JSON schema - confirm_password and timezone are optional
        required_fields = ['username', 'email', 'password']
        optional_fields = ['confirm_password', 'timezone']
        valid, message = ValidationMiddleware.validate_json_schema(data, required_fields, optional_fields)
        if not valid:
            return jsonify({'message': message}), 400
        
        # If confirm_password not provided, set it to same as password
        if 'confirm_password' not in data:
            data['confirm_password'] = data['password']
        
        # Validate email
        if not ValidationMiddleware.validate_email(data['email']):
            return jsonify({'message': 'Invalid email format'}), 400
        
        # Validate username
        valid, message = ValidationMiddleware.validate_username(data['username'])
        if not valid:
            return jsonify({'message': message}), 400
        
        # Validate password
        valid, message = ValidationMiddleware.validate_password(data['password'])
        if not valid:
            return jsonify({'message': message}), 400
        
        # Sanitize inputs
        data['username'] = ValidationMiddleware.sanitize_string(data['username'], 50)
        data['email'] = ValidationMiddleware.sanitize_string(data['email'], 100)
        
        return f(*args, **kwargs)
    return decorated_function


def validate_login_data(f):
    """Decorator to validate login request data"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        data = request.get_json()
        
        # Validate JSON schema
        required_fields = ['username', 'password']
        valid, message = ValidationMiddleware.validate_json_schema(data, required_fields)
        if not valid:
            return jsonify({'message': message}), 400
        
        # Sanitize inputs
        data['username'] = ValidationMiddleware.sanitize_string(data['username'], 50)
        
        return f(*args, **kwargs)
    return decorated_function


def validate_contact_data(f):
    """Decorator to validate contact form data"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        data = request.get_json()
        
        # Validate JSON schema
        required_fields = ['name', 'email', 'message']
        optional_fields = ['phone', 'subject']
        valid, message = ValidationMiddleware.validate_json_schema(data, required_fields, optional_fields)
        if not valid:
            return jsonify({'message': message}), 400
        
        # Validate email
        if not ValidationMiddleware.validate_email(data['email']):
            return jsonify({'message': 'Invalid email format'}), 400
        
        # Validate message length
        if len(data['message']) < 10:
            return jsonify({'message': 'Message must be at least 10 characters long'}), 400
        
        if len(data['message']) > 2000:
            return jsonify({'message': 'Message must be less than 2000 characters'}), 400
        
        # Sanitize inputs
        data['name'] = ValidationMiddleware.sanitize_string(data['name'], 100)
        data['email'] = ValidationMiddleware.sanitize_string(data['email'], 100)
        data['message'] = ValidationMiddleware.sanitize_string(data['message'], 2000)
        if data.get('phone'):
            data['phone'] = ValidationMiddleware.sanitize_string(data['phone'], 20)
        if data.get('subject'):
            data['subject'] = ValidationMiddleware.sanitize_string(data['subject'], 200)
        
        return f(*args, **kwargs)
    return decorated_function


def validate_chat_data(f):
    """Decorator to validate chat message data"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get message from form data
        message = request.form.get('message', '').strip()
        
        if not message:
            return jsonify({'message': 'Message cannot be empty'}), 400
        
        if len(message) > 5001:
            return jsonify({'message': 'Message must be less than 5001 characters'}), 400
        
        # Validate files if any
        files = request.files.getlist('attachments')
        for file in files:
            if file.filename:
                valid, error_message = ValidationMiddleware.validate_file_upload(file)
                if not valid:
                    return jsonify({'message': error_message}), 400
        
        return f(*args, **kwargs)
    return decorated_function


def validate_json_content(f):
    """Generic decorator to validate JSON request content"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip validation for OPTIONS requests
        if request.method == 'OPTIONS':
            return f(*args, **kwargs)
        
        # Check if request has JSON content
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Request must contain JSON data'}), 400
        
        try:
            data = request.get_json()
            if data is None:
                return jsonify({'success': False, 'message': 'Invalid JSON data'}), 400
        except Exception as e:
            return jsonify({'success': False, 'message': f'Failed to parse JSON: {str(e)}'}), 400
        
        return f(*args, **kwargs)
    return decorated_function 