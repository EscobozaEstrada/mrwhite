from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timedelta, timezone
import secrets
from flask import current_app
from app import db, bcrypt
from app.models.user import User
from app.utils.jwt import generate_token, decode_token
from app.utils.mail import send_email


class AuthService:
    """Service class for handling authentication operations"""
    
    @staticmethod
    def create_user(username: str, email: str, password: str, confirm_password: str, timezone: str = 'UTC') -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Create a new user account with timezone support
        
        Args:
            timezone: User's timezone (e.g., 'America/New_York', 'Asia/Kolkata', 'Europe/London')
        
        Returns:
            Tuple of (success: bool, message: str, user_data: Optional[Dict])
        """
        try:
            # Validation
            if User.query.filter_by(username=username).first():
                return False, 'Username already exists', None
            
            if User.query.filter_by(email=email).first():
                return False, 'Email already exists', None
                
            if password != confirm_password:
                return False, 'Passwords do not match', None
            
            if len(password) < 8:
                return False, 'Password must be at least 8 characters long', None
            
            # 🌍 TIMEZONE VALIDATION: Validate timezone format
            try:
                import pytz
                pytz.timezone(timezone)  # This will raise an exception if timezone is invalid
            except:
                timezone = 'UTC'  # Fallback to UTC if invalid timezone
            
            # Create user with timezone
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            new_user = User(username=username, email=email, password_hash=hashed_password, timezone=timezone)
            
            db.session.add(new_user)
            db.session.commit()
            
            return True, 'User created successfully', new_user.to_dict()
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating user: {str(e)}")
            return False, 'Internal server error', None
    
    @staticmethod
    def authenticate_user(username: str, password: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Authenticate user credentials
        
        Returns:
            Tuple of (success: bool, message: str, user_data: Optional[Dict])
        """
        try:
            user = User.query.filter_by(username=username).first()
            
            if not user:
                return False, 'Invalid credentials', None
            
            if not bcrypt.check_password_hash(user.password_hash, password):
                return False, 'Invalid credentials', None
            
            return True, 'Authentication successful', user.to_dict()
            
        except Exception as e:
            current_app.logger.error(f"Error authenticating user: {str(e)}")
            return False, 'Internal server error', None
    
    @staticmethod
    def get_user_from_token(token: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Get user data from JWT token
        
        Returns:
            Tuple of (success: bool, message: str, user_data: Optional[Dict])
        """
        try:
            if not token:
                return False, 'No token provided', None
            
            user_data = decode_token(token)
            if not user_data:
                return False, 'Invalid or expired token', None
            
            user_id = user_data.get('id')
            if not user_id:
                return False, 'Invalid token format', None
            
            user = User.query.get(user_id)
            if not user:
                return False, 'User not found', None
            
            return True, 'Token valid', user.to_dict()
            
        except Exception as e:
            current_app.logger.error(f"Error validating token: {str(e)}")
            return False, 'Invalid or expired token', None
    
    @staticmethod
    def request_password_reset(email: str) -> Tuple[bool, str]:
        """
        Request password reset for user
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            user = User.query.filter_by(email=email).first()
            
            # Always return success for security reasons
            if not user:
                return True, 'If your email is registered, you will receive reset instructions'
            
            # Generate secure token
            token = secrets.token_hex(32)
            # Increase token expiration time from 1 hour to 24 hours to avoid timezone issues
            token_expires = datetime.now(timezone.utc) + timedelta(hours=24)
            
            # Ensure we're storing a timezone-aware datetime
            if token_expires.tzinfo is None:
                token_expires = token_expires.replace(tzinfo=timezone.utc)
            
            # Log token creation for debugging
            current_app.logger.info(f"Creating reset token - Expires at: {token_expires}")
            
            # Save token to user
            user.reset_token = token
            user.reset_token_expires = token_expires
            db.session.commit()
            
            # Send reset email
            reset_url = f"{current_app.config['FRONTEND_URL']}/reset-password/{token}"
            success = AuthService._send_password_reset_email(email, reset_url)
            
            if success:
                return True, 'Reset link sent to your registered email.'
            else:
                return False, 'Error sending email. Please try again later.'
                
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error requesting password reset: {str(e)}")
            return False, 'Internal server error'
    
    @staticmethod
    def verify_reset_token(token: str) -> Tuple[bool, str]:
        """
        Verify password reset token
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if not token:
                return False, 'Token is required'
            
            user = User.query.filter_by(reset_token=token).first()
            
            if not user:
                return False, 'Invalid or expired token'
                
            if not user.reset_token_expires:
                return False, 'Token has no expiration date'
                
            # Log current time and token expiration time for debugging
            current_time = datetime.now(timezone.utc)
            
            # Ensure token_expires has timezone info
            token_expires = user.reset_token_expires
            if token_expires.tzinfo is None:
                # If token_expires is naive (no timezone), assume it's in UTC
                token_expires = token_expires.replace(tzinfo=timezone.utc)
                
            current_app.logger.info(f"Token verification - Current time: {current_time}, Token expires: {token_expires}")
            
            if token_expires < current_time:
                current_app.logger.warning(f"Token expired - Expired at: {token_expires}, Current time: {current_time}")
                return False, 'Token has expired'
            
            return True, 'Token is valid'
            
        except Exception as e:
            current_app.logger.error(f"Error verifying reset token: {str(e)}")
            return False, 'Internal server error'
    
    @staticmethod
    def reset_password(token: str, password: str, confirm_password: str) -> Tuple[bool, str]:
        """
        Reset user password using token
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if not all([token, password, confirm_password]):
                return False, 'All fields are required'
            
            if password != confirm_password:
                return False, 'Passwords do not match'
            
            if len(password) < 8:
                return False, 'Password must be at least 8 characters long'
            
            user = User.query.filter_by(reset_token=token).first()
            
            if not user:
                return False, 'Invalid token'
                
            if not user.reset_token_expires:
                return False, 'Token has no expiration date'
                
            # Log current time and token expiration time for debugging
            current_time = datetime.now(timezone.utc)
            
            # Ensure token_expires has timezone info
            token_expires = user.reset_token_expires
            if token_expires.tzinfo is None:
                # If token_expires is naive (no timezone), assume it's in UTC
                token_expires = token_expires.replace(tzinfo=timezone.utc)
                
            current_app.logger.info(f"Password reset - Current time: {current_time}, Token expires: {token_expires}")
            
            if token_expires < current_time:
                current_app.logger.warning(f"Token expired during reset - Expired at: {token_expires}, Current time: {current_time}")
                return False, 'Token has expired'
            
            # Check if new password is the same as current password
            if bcrypt.check_password_hash(user.password_hash, password):
                return False, 'You cannot use your current password. Please enter a new password.'
            
            # Update password and clear token
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            user.password_hash = hashed_password
            user.reset_token = None
            user.reset_token_expires = None
            db.session.commit()
            
            return True, 'Password has been successfully reset'
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error resetting password: {str(e)}")
            return False, 'Internal server error'
    
    @staticmethod
    def _send_password_reset_email(email: str, reset_url: str) -> bool:
        """Send password reset email"""
        subject = "Mr. White - Password Reset"
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #000; color: #fff; border-radius: 5px;">
                    <h2 style="color: #fff; text-align: center;">Mr. White Password Reset</h2>
                    <p>Hello,</p>
                    <p>You requested a password reset for your Mr. White account.</p>
                    <p>Please click the link below to reset your password:</p>
                    <p style="text-align: center;">
                        <a href="{reset_url}" style="display: inline-block; background-color: #fff; color: #000; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">Reset Your Password</a>
                    </p>
                    <p>This link will expire in 24 hours.</p>
                    <p>If you did not request this, please ignore this email.</p>
                    <hr style="border: 1px solid #333; margin: 20px 0;">
                    <p style="text-align: center; font-size: 12px; color: #999;">Mr. White - AI Assistant for Dog Care & Beyond</p>
                </div>
            </body>
        </html>
        """
        
        return send_email(email, subject, html_content) 