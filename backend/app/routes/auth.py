from flask import Blueprint, request, jsonify, make_response, current_app
import os
from app.utils.jwt import generate_token
from app.services.auth_service import AuthService
from app.middleware.validation import validate_signup_data, validate_login_data

auth_bp = Blueprint('auth', __name__)

# Handler for OPTIONS requests
@auth_bp.route('/<path:path>', methods=['OPTIONS'])
def handle_auth_options(path):
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", os.getenv('FRONTEND_URL'))
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With, Accept, Origin")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response

@auth_bp.route('/signup', methods=['POST'])
@validate_signup_data
def signup():
    data = request.json
    
    # Use AuthService to create user with timezone
    success, message, user_data = AuthService.create_user(
        username=data.get('username', ''),
        email=data.get('email', ''),
        password=data.get('password', ''),
        confirm_password=data.get('confirm_password', ''),
        timezone=data.get('timezone', 'UTC')  # 🌍 Accept timezone from frontend
    )
    
    if not success:
        return jsonify({'message': message}), 400
    
    # Generate token and create response
    from app.models.user import User
    user = User.query.filter_by(username=data['username']).first()
    token = generate_token(user)
    
    response = make_response(jsonify({
        'message': message,
        'user': user_data
    }))
    
    # Set secure cookie
    response.set_cookie(
        'token', 
        token, 
        httponly=os.getenv('COOKIE_HTTPONLY', 'true').lower() == 'true', 
        secure=os.getenv('COOKIE_SECURE', 'false').lower() == 'true',
        max_age=int(os.getenv('COOKIE_MAX_AGE', '86400')),
        samesite=os.getenv('COOKIE_SAMESITE', 'lax'),
        path='/'
    )
    return response


@auth_bp.route('/login', methods=['POST'])
@validate_login_data
def login():
    try:
        data = request.json
        username = data.get('username', '')
        password = data.get('password', '')
        
        current_app.logger.info(f"Login attempt with username: {username}")
        
        # Use AuthService to authenticate user
        success, message, user_data = AuthService.authenticate_user(username, password)
        
        if not success:
            current_app.logger.warning(f"Login failed for username: {username}")
            return jsonify({'message': message}), 401
        
        # Generate token and create response
        from app.models.user import User
        user = User.query.filter_by(username=username).first()
        token = generate_token(user)
        
        current_app.logger.info(f"Login successful for user ID: {user.id}")
        
        response = make_response(jsonify({
            'message': 'Logged in successfully',
            'user': user_data
        }))
        
        # Set secure cookie
        response.set_cookie(
            'token', 
            token, 
            httponly=os.getenv('COOKIE_HTTPONLY', 'true').lower() == 'true', 
            secure=os.getenv('COOKIE_SECURE', 'false').lower() == 'true',
            max_age=int(os.getenv('COOKIE_MAX_AGE', '86400')),
            samesite=os.getenv('COOKIE_SAMESITE', 'lax'),
            path='/'
        )
        return response
    except Exception as e:
        current_app.logger.error(f"Login error: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500

@auth_bp.route('/me', methods=['GET'])
def me():
    token = request.cookies.get('token')
    
    # Use AuthService to get user from token
    success, message, user_data = AuthService.get_user_from_token(token)
    
    if not success:
        status_code = 401 if 'Unauthorized' in message or 'Invalid' in message or 'expired' in message else 404
        return jsonify({'message': message}), status_code
    
    return jsonify(user_data), 200


@auth_bp.route('/logout', methods=['POST'])
def logout():
    response = make_response(jsonify({'message': 'Logged out'}))
    response.delete_cookie('token', path='/')
    return response

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json
    email = data.get('email', '')
    
    if not email:
        return jsonify({'message': 'Email is required'}), 400
    
    # Use AuthService to handle password reset request
    success, message = AuthService.request_password_reset(email)
    
    status_code = 200 if success else 500
    return jsonify({'message': message}), status_code

@auth_bp.route('/verify-reset-token/<token>', methods=['GET'])
def verify_reset_token(token):
    # Use AuthService to verify reset token
    success, message = AuthService.verify_reset_token(token)
    
    status_code = 200 if success else 400
    return jsonify({'message': message}), status_code

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    token = data.get('token', '')
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')
    
    # Use AuthService to reset password
    success, message = AuthService.reset_password(token, password, confirm_password)
    
    status_code = 200 if success else 400
    return jsonify({'message': message}), status_code

@auth_bp.route('/device-token', methods=['POST'])
def register_device_token():
    """Register or update device token for push notifications"""
    try:
        token = request.cookies.get('token')
        
        # Use AuthService to get user from token
        success, message, user_data = AuthService.get_user_from_token(token)
        
        if not success:
            return jsonify({'message': message}), 401
        
        data = request.json
        fcm_token = data.get('token', '')
        platform = data.get('platform', 'web')
        device_info = data.get('device_info', {})
        
        if not fcm_token:
            return jsonify({'message': 'FCM token is required'}), 400
        
        # Get user and update device tokens
        from app.models.user import User
        from app import db
        from datetime import datetime
        from sqlalchemy.orm.attributes import flag_modified
        
        user = User.query.get(user_data['id'])
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        # Initialize device_tokens if None
        if user.device_tokens is None:
            user.device_tokens = {}
        
        # Store FCM token with metadata
        user.device_tokens[platform] = {
            'token': fcm_token,
            'registered_at': datetime.utcnow().isoformat(),
            'active': True,
            'device_info': device_info,
            'type': 'fcm'  # Mark as FCM token
        }
        user.last_device_token_update = datetime.utcnow()
        
        # CRITICAL FIX: Tell SQLAlchemy that the JSON field has been modified
        flag_modified(user, "device_tokens")
        
        db.session.commit()
        
        current_app.logger.info(f"FCM token registered for user {user.id} on platform {platform}")
        
        return jsonify({
            'message': 'FCM device token registered successfully',
            'platform': platform,
            'token_count': len(user.device_tokens)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Device token registration error: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500

@auth_bp.route('/device-token', methods=['DELETE'])
def remove_device_token():
    """Remove device token for push notifications"""
    try:
        token = request.cookies.get('token')
        
        # Use AuthService to get user from token
        success, message, user_data = AuthService.get_user_from_token(token)
        
        if not success:
            return jsonify({'message': message}), 401
        
        data = request.json
        # Handle both old and new parameter names for backwards compatibility
        device_token = data.get('device_token', data.get('token', ''))
        device_type = data.get('device_type', data.get('platform', 'web'))
        
        if not device_token:
            return jsonify({'message': 'Device token is required'}), 400
        
        # Get user and remove device token
        from app.models.user import User
        from app import db
        from datetime import datetime
        from sqlalchemy.orm.attributes import flag_modified
        
        user = User.query.get(user_data['id'])
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        # Initialize device_tokens if None
        if user.device_tokens is None:
            user.device_tokens = {}
        
        # Remove device token by platform
        if device_type in user.device_tokens:
            del user.device_tokens[device_type]
            user.last_device_token_update = datetime.utcnow()
            
            # CRITICAL FIX: Tell SQLAlchemy that the JSON field has been modified
            flag_modified(user, "device_tokens")
            
            db.session.commit()
            
            current_app.logger.info(f"Device token removed for user {user.id} on platform {device_type}")
            
            return jsonify({
                'message': 'Device token removed successfully',
                'platform': device_type,
                'token_count': len(user.device_tokens)
            }), 200
        else:
            # Try to find and remove by token value (fallback)
            removed_platform = None
            for platform, token_data in user.device_tokens.items():
                if isinstance(token_data, dict) and token_data.get('token') == device_token:
                    removed_platform = platform
                    break
            
            if removed_platform:
                del user.device_tokens[removed_platform]
                user.last_device_token_update = datetime.utcnow()
                
                # CRITICAL FIX: Tell SQLAlchemy that the JSON field has been modified
                flag_modified(user, "device_tokens")
                
                db.session.commit()
                
                current_app.logger.info(f"Device token removed for user {user.id} on platform {removed_platform}")
                
                return jsonify({
                    'message': 'Device token removed successfully',
                    'platform': removed_platform,
                    'token_count': len(user.device_tokens)
                }), 200
            else:
                return jsonify({'message': 'Device token not found'}), 404
            
    except Exception as e:
        current_app.logger.error(f"Device token removal error: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500

@auth_bp.route('/push-settings', methods=['PUT'])
def update_push_settings():
    """Update push notification settings"""
    try:
        token = request.cookies.get('token')
        
        # Use AuthService to get user from token
        success, message, user_data = AuthService.get_user_from_token(token)
        
        if not success:
            return jsonify({'message': message}), 401
        
        data = request.json
        push_enabled = data.get('push_notifications_enabled', True)
        
        # Get user and update push settings
        from app.models.user import User
        from app import db
        
        user = User.query.get(user_data['id'])
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        user.push_notifications_enabled = push_enabled
        db.session.commit()
        
        return jsonify({
            'message': 'Push notification settings updated successfully',
            'push_notifications_enabled': push_enabled
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Push settings update error: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500

@auth_bp.route('/test-fcm', methods=['POST'])
def test_fcm_notification():
    """Test FCM notification sending"""
    try:
        token = request.cookies.get('token')
        
        # Use AuthService to get user from token
        success, message, user_data = AuthService.get_user_from_token(token)
        
        if not success:
            return jsonify({'message': message}), 401
        
        # Get user and check device tokens
        from app.models.user import User
        user = User.query.get(user_data['id'])
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        if not user.device_tokens:
            return jsonify({'message': 'No device tokens registered. Please enable push notifications first.'}), 400
        
        # Test FCM service
        from app.services.fcm_service import get_fcm_service
        fcm_service = get_fcm_service()
        
        if not fcm_service.is_available():
            return jsonify({'message': 'FCM service not available'}), 500
        
        # Send test notification
        result = fcm_service.send_to_user_devices(
            user_device_tokens=user.device_tokens,
            title="🧪 Test Notification",
            body="This is a test notification from Mr. White! Your push notifications are working correctly.",
            data={
                'test': 'true',
                'timestamp': datetime.utcnow().isoformat()
            },
            click_action=f"{current_app.config.get('FRONTEND_URL')}/reminders"
        )
        
        return jsonify({
            'message': 'Test notification sent',
            'result': result,
            'device_count': len(user.device_tokens),
            'fcm_available': fcm_service.is_available()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Test FCM error: {str(e)}")
        return jsonify({'message': f'Test failed: {str(e)}'}), 500

@auth_bp.route('/account', methods=['DELETE'])
def delete_account():
    """Delete user account and all associated data"""
    try:
        token = request.cookies.get('token')
        
        # Use AuthService to get user from token
        success, message, user_data = AuthService.get_user_from_token(token)
        
        if not success:
            return jsonify({'success': False, 'message': message}), 401
        
        # Get user
        from app.models.user import User
        from app import db
        
        user = User.query.get(user_data['id'])
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        # Delete user's data
        try:
            # Delete user's conversations
            from app.models.conversation import Conversation
            from app.models.message import Message
            from app.models.health_models import HealthReminder
            from app.models.health_models import ReminderNotification
            
            # Delete user's reminders and notifications
            reminders = HealthReminder.query.filter_by(user_id=user.id).all()
            for reminder in reminders:
                ReminderNotification.query.filter_by(reminder_id=reminder.id).delete()
            
            HealthReminder.query.filter_by(user_id=user.id).delete()
            
            # Delete additional health-related data
            from app.models.health_models import PetProfile, HealthInsight, HealthRecord
            PetProfile.query.filter_by(user_id=user.id).delete(synchronize_session=False)
            HealthInsight.query.filter_by(user_id=user.id).delete(synchronize_session=False)
            HealthRecord.query.filter_by(user_id=user.id).delete(synchronize_session=False)
            
            # Delete user's conversations and messages (with proper cascade handling)
            from app.models.message import Attachment
            
            # First, get all conversation IDs for the user
            conversations = Conversation.query.filter_by(user_id=user.id).all()
            conversation_ids = [conv.id for conv in conversations]
            
            if conversation_ids:
                # Get all message IDs for these conversations
                messages = Message.query.filter(Message.conversation_id.in_(conversation_ids)).all()
                message_ids = [msg.id for msg in messages]
                
                if message_ids:
                    # Delete attachments first (foreign key constraint)
                    Attachment.query.filter(Attachment.message_id.in_(message_ids)).delete(synchronize_session=False)
                
                # Then delete messages
                Message.query.filter(Message.conversation_id.in_(conversation_ids)).delete(synchronize_session=False)
            
            # Finally delete conversations
            Conversation.query.filter_by(user_id=user.id).delete(synchronize_session=False)
            
            # Delete user's credit transactions
            from app.models.credit_transaction import CreditTransaction
            CreditTransaction.query.filter_by(user_id=user.id).delete(synchronize_session=False)
            
            # Delete user's books and book-related data
            from app.models.enhanced_book import EnhancedBook, EnhancedBookChapter, MessageCategory
            from app.models.user_book import UserBookCopy
            from app.models.custom_book import CustomBook, BookChapter
            from app.models.care_record import CareRecord, Document, KnowledgeBase
            from app.models.image import UserImage
            from app.models.folder import ImageFolder
            
            # First, delete chapters and related data for user's books (foreign key constraints)
            user_custom_books = CustomBook.query.filter_by(user_id=user.id).all()
            user_custom_book_ids = [book.id for book in user_custom_books]
            if user_custom_book_ids:
                BookChapter.query.filter(BookChapter.book_id.in_(user_custom_book_ids)).delete(synchronize_session=False)
            
            user_enhanced_books = EnhancedBook.query.filter_by(user_id=user.id).all()
            user_enhanced_book_ids = [book.id for book in user_enhanced_books]
            if user_enhanced_book_ids:
                EnhancedBookChapter.query.filter(EnhancedBookChapter.book_id.in_(user_enhanced_book_ids)).delete(synchronize_session=False)
                MessageCategory.query.filter(MessageCategory.book_id.in_(user_enhanced_book_ids)).delete(synchronize_session=False)
            
            EnhancedBook.query.filter_by(user_id=user.id).delete(synchronize_session=False)
            UserBookCopy.query.filter_by(user_id=user.id).delete(synchronize_session=False)
            CustomBook.query.filter_by(user_id=user.id).delete(synchronize_session=False)
            CareRecord.query.filter_by(user_id=user.id).delete(synchronize_session=False)
            Document.query.filter_by(user_id=user.id).delete(synchronize_session=False)
            KnowledgeBase.query.filter_by(user_id=user.id).delete(synchronize_session=False)
            # Handle folders that reference user images (cover_image_id constraint)
            # First, clear cover_image_id references, then delete folders and images
            db.session.execute(
                db.text("UPDATE folders SET cover_image_id = NULL WHERE user_id = :user_id"),
                {"user_id": user.id}
            )
            # Delete from both possible folder tables (model discrepancy)
            db.session.execute(
                db.text("DELETE FROM folders WHERE user_id = :user_id"),
                {"user_id": user.id}
            )
            
            UserImage.query.filter_by(user_id=user.id).delete(synchronize_session=False)
            ImageFolder.query.filter_by(user_id=user.id).delete(synchronize_session=False)
            
            # Delete user's subscription data
            if hasattr(user, 'stripe_customer_id') and user.stripe_customer_id:
                # Optionally cancel Stripe subscriptions here
                pass
            
            # DELETE INTELLIGENT CHAT DATA (ic_* tables, Pinecone, S3)
            try:
                import asyncio
                import sys
                import os
                
                # Add intelligent_chat to path
                intelligent_chat_path = os.path.join(os.path.dirname(__file__), '../../intelligent_chat')
                if intelligent_chat_path not in sys.path:
                    sys.path.insert(0, intelligent_chat_path)
                
                from services.account_deletion_service import AccountDeletionService
                from models.base import get_db_async
                
                # Create async session and run deletion
                async def delete_ic_data():
                    async for db_session in get_db_async():
                        deletion_service = AccountDeletionService()
                        stats = await deletion_service.delete_user_data_complete(
                            db=db_session,
                            user_id=user.id
                        )
                        current_app.logger.info(f"✅ Intelligent Chat data deleted: {stats}")
                        return stats
                
                # Run async deletion
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                ic_stats = loop.run_until_complete(delete_ic_data())
                loop.close()
                
                current_app.logger.info(f"✅ Intelligent Chat cleanup completed for user {user.id}: {ic_stats}")
                
            except Exception as ic_error:
                current_app.logger.error(f"⚠️ Intelligent Chat cleanup failed (continuing...): {str(ic_error)}")
                # Don't fail the entire deletion if IC cleanup fails
            
            # Finally, delete the user
            db.session.delete(user)
            db.session.commit()
            
            current_app.logger.info(f"User {user.id} account deleted successfully")
            
            # Return success response
            response = jsonify({'success': True, 'message': 'Account deleted successfully'})
            response.delete_cookie('token')
            return response
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting user data: {str(e)}")
            return jsonify({'success': False, 'message': f'Error deleting user data: {str(e)}'}), 500
        
    except Exception as e:
        current_app.logger.error(f"Account deletion error: {str(e)}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

# 🌍 GLOBAL TIMEZONE: Update user timezone endpoint
@auth_bp.route('/update-timezone', methods=['POST'])
def update_timezone():
    """Update user's timezone setting"""
    try:
        data = request.json
        timezone = data.get('timezone', 'UTC')
        
        # Validate timezone
        try:
            import pytz
            pytz.timezone(timezone)
        except:
            return jsonify({'message': 'Invalid timezone format'}), 400
        
        # Get user from cookie
        token = request.cookies.get('token')
        if not token:
            return jsonify({'message': 'Not authenticated'}), 401
        
        from app.utils.jwt import decode_token
        token_payload = decode_token(token)
        if not token_payload:
            return jsonify({'message': 'Invalid token'}), 401
        
        user_id = token_payload.get('id')
        if not user_id:
            return jsonify({'message': 'Invalid token payload'}), 401
        
        from app.models.user import User
        user = User.query.get(user_id)
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        # Update timezone
        user.timezone = timezone
        from app import db
        db.session.commit()
        
        return jsonify({
            'message': 'Timezone updated successfully',
            'timezone': timezone
        })
        
    except Exception as e:
        current_app.logger.error(f"Error updating timezone: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500


