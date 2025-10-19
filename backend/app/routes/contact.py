from flask import Blueprint, request, jsonify
from app.utils.jwt import decode_token
from app.services.email_service import EmailService
from app.middleware.validation import validate_contact_data

contact_bp = Blueprint('contact', __name__)

@contact_bp.route('/', methods=['POST'])
@validate_contact_data
def submit_contact_form():
    data = request.json
    
    # Get user_id from token if available
    user_id = None
    token = request.cookies.get('token')
    if token:
        try:
            user_data = decode_token(token)
            user_id = user_data.get('id')
        except:
            # If token is invalid, continue without user_id
            pass
    
    # Use EmailService to handle contact form submission
    success, message, contact_data = EmailService.submit_contact_form(
        name=data.get('name', ''),
        email=data.get('email', ''),
        message=data.get('message', ''),
        phone=data.get('phone'),
        user_id=user_id,
        subject=data.get('subject')
    )
    
    if not success:
        return jsonify({'message': message}), 400
    
    status_code = 201 if 'successfully' in message else 200
    return jsonify({
        'message': message,
        'contact': contact_data
    }), status_code 