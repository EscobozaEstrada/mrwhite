from functools import wraps
from flask import jsonify, g, request
from app.services.credit_system_service import CreditSystemService
import logging

def require_credits(action: str, dynamic_cost_fn=None):
    """
    Decorator to require credits for an action
    Works for both Free and Elite users with different logic
    
    Args:
        action: The action type that costs credits
        dynamic_cost_fn: Optional function to calculate dynamic cost based on request
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'user_id') or not g.user_id:
                return jsonify({'error': 'Authentication required'}), 401
            
            try:
                credit_service = CreditSystemService()
                
                # Calculate metadata for dynamic pricing
                metadata = {}
                if dynamic_cost_fn:
                    metadata = dynamic_cost_fn(request)
                
                # Check and deduct credits
                can_perform, message, cost = credit_service.check_and_deduct_credits(
                    g.user_id, action, metadata
                )
                
                if not can_perform:
                    return jsonify({
                        'error': 'Access denied',
                        'message': message,
                        'required_credits': cost,
                        'credit_required': True
                    }), 402  # Payment Required
                
                # Store credit info in g for response
                g.credits_used = cost
                g.credit_action = action
                
                # Call the original function
                result = f(*args, **kwargs)
                
                # Add credit info to successful responses
                if isinstance(result, tuple) and len(result) == 2:
                    response_data, status_code = result
                    if isinstance(response_data, dict) and status_code == 200:
                        response_data['credits_used'] = cost
                        response_data['credit_action'] = action
                        response_data['cost_usd'] = f"${cost/100:.2f}"
                
                return result
                
            except Exception as e:
                logging.error(f"Credit middleware error: {str(e)}")
                return jsonify({'error': 'Credit system error'}), 500
        
        return decorated_function
    return decorator

def elite_feature_required(f):
    """
    Decorator for features that require Elite subscription
    (but still use credits once you have Elite)
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'user_id') or not g.user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        try:
            from app.models.user import User
            user = User.query.get(g.user_id)
            
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Check if user has Elite subscription
            if not (user.is_premium and user.subscription_status == 'active'):
                return jsonify({
                    'error': 'Elite subscription required',
                    'message': 'This feature requires an Elite subscription. Upgrade to access all premium features and get 3,000 monthly credits.',
                    'upgrade_required': True
                }), 403
            
            # User has Elite, now check credits via the credit system
            # This will be handled by the route's credit middleware
            return f(*args, **kwargs)
            
        except Exception as e:
            logging.error(f"Elite feature middleware error: {str(e)}")
            return jsonify({'error': 'Authorization system error'}), 500
    
    return decorated_function

def check_credits_only(action: str, dynamic_cost_fn=None):
    """
    Decorator to check credits without deducting (for cost estimation)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'user_id') or not g.user_id:
                return jsonify({'error': 'Authentication required'}), 401
            
            try:
                credit_service = CreditSystemService()
                
                # Calculate metadata for dynamic pricing
                metadata = {}
                if dynamic_cost_fn:
                    metadata = dynamic_cost_fn(request)
                
                # Estimate cost without deducting
                estimate = credit_service.estimate_action_cost(action, metadata)
                
                # Store estimate in g for the route to use
                g.credit_estimate = estimate
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logging.error(f"Credit check error: {str(e)}")
                return jsonify({'error': 'Credit system error'}), 500
        
        return decorated_function
    return decorator

# Specific credit decorators for common actions

def require_chat_credits(f):
    """Require credits for basic chat messages"""
    
    def calculate_chat_cost(request):
        """Calculate dynamic cost for chat based on complexity"""
        try:
            data = request.get_json() or {}
            form_data = request.form or {}
            metadata = {}
            
            # Get message from either JSON or form data
            message = data.get('message', '') or form_data.get('message', '')
            
            # Factor in message length
            if len(message) > 500:
                metadata['long_message'] = True
            
            # Factor in context usage
            if data.get('conversation_id') or form_data.get('conversationId'):
                metadata['has_context'] = True
                
            # Factor in file attachments
            if hasattr(request, 'files') and request.files:
                metadata['has_attachments'] = True
                
            return metadata
        except:
            return {}
    
    return require_credits('chat_message_basic', calculate_chat_cost)(f)

def require_advanced_chat_credits(f):
    """Require credits for advanced chat with context (Elite feature)"""
    
    def calculate_advanced_chat_cost(request):
        try:
            data = request.get_json() or {}
            metadata = {}
            
            # Check for document context
            if data.get('use_documents', False):
                metadata['document_context'] = True
                
            # Check for conversation length
            conversation_id = data.get('conversation_id')
            if conversation_id:
                metadata['context_length'] = 1000  # Placeholder
                
            return metadata
        except:
            return {}
    
    # Combine Elite requirement with credit deduction
    def combined_decorator(f):
        return require_credits('chat_message_advanced', calculate_advanced_chat_cost)(
            elite_feature_required(f)
        )
    
    return combined_decorator(f)

def require_document_credits(f):
    """Require credits for document upload and processing"""
    
    def calculate_document_cost(request):
        try:
            metadata = {}
            
            # Check file size from request
            if hasattr(request, 'files') and request.files:
                for file in request.files.values():
                    if file and hasattr(file, 'content_length'):
                        size_mb = (file.content_length or 0) / (1024 * 1024)
                        metadata['file_size_mb'] = size_mb
                    break
            
            return metadata
        except:
            return {}
    
    return require_credits('document_upload', calculate_document_cost)(f)

def require_health_credits(f):
    """Require credits for health analysis features (Elite feature)"""
    
    def calculate_health_cost(request):
        try:
            data = request.get_json() or {}
            metadata = {}
            
            # Check for comprehensive analysis
            if data.get('comprehensive', False):
                metadata['comprehensive'] = True
                
            # Check for multiple pets
            if data.get('pet_count', 1) > 1:
                metadata['multiple_pets'] = True
                
            return metadata
        except:
            return {}
    
    # Health features require Elite subscription
    def combined_decorator(f):
        return require_credits('health_assessment', calculate_health_cost)(
            elite_feature_required(f)
        )
    
    return combined_decorator(f)

def require_care_archive_credits(f):
    """Require credits for care archive operations (Elite feature)"""
    def combined_decorator(f):
        return require_credits('care_archive_search')(
            elite_feature_required(f)
        )
    
    return combined_decorator(f)

def require_voice_credits(f):
    """Require credits for voice processing (Elite feature)"""
    def combined_decorator(f):
        return require_credits('voice_message')(
            elite_feature_required(f)
        )
    
    return combined_decorator(f)

# Utility functions

def get_user_credit_status():
    """Get current user's credit status (for use in routes)"""
    if hasattr(g, 'user_id') and g.user_id:
        credit_service = CreditSystemService()
        return credit_service.get_user_credit_status(g.user_id)
    return None

def add_credit_response_headers(response, credits_used=None, action=None):
    """Add credit information to response headers"""
    if credits_used is not None:
        response.headers['X-Credits-Used'] = str(credits_used)
        response.headers['X-Cost-USD'] = f"${credits_used/100:.2f}"
    if action:
        response.headers['X-Credit-Action'] = action
    return response 