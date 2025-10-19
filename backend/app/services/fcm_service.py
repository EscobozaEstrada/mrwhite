"""
Firebase Cloud Messaging (FCM) Service
Handles push notification sending using Firebase Admin SDK
"""

import os
import logging
import json
from typing import Dict, List, Optional, Any
from firebase_admin import messaging, credentials, initialize_app, exceptions
import firebase_admin

logger = logging.getLogger(__name__)

class FCMService:
    """Service for sending push notifications via Firebase Cloud Messaging"""
    
    def __init__(self):
        self.initialized = False
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            # Check if Firebase is already initialized
            if len(firebase_admin._apps) > 0:
                self.initialized = True
                logger.info("Firebase Admin SDK already initialized")
                return
            
            # Initialize with service account file or JSON string
            firebase_service_account_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH')
            firebase_service_account_key = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY')
            
            if firebase_service_account_path and os.path.exists(firebase_service_account_path):
                # Use service account file from path
                try:
                    cred = credentials.Certificate(firebase_service_account_path)
                    initialize_app(cred)
                    logger.info(f"Firebase initialized with service account file: {firebase_service_account_path}")
                except Exception as e:
                    logger.error(f"Failed to initialize Firebase with service account file: {e}")
                    return
            elif firebase_service_account_key:
                # Use service account key from environment (JSON string)
                try:
                    service_account_info = json.loads(firebase_service_account_key)
                    cred = credentials.Certificate(service_account_info)
                    initialize_app(cred)
                    logger.info("Firebase initialized with service account key from environment")
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid Firebase service account JSON: {e}")
                    return
            else:
                # Use default credentials (for Google Cloud environment)
                try:
                    initialize_app()
                    logger.info("Firebase initialized with default credentials")
                except Exception as e:
                    logger.error(f"Failed to initialize Firebase with default credentials: {e}")
                    return
            
            self.initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
            self.initialized = False
    
    def _ensure_https_url(self, url: str) -> str:
        """Ensure URL is HTTPS for Firebase compatibility"""
        if not url:
            return "https://mrwhiteaibuddy.com/reminders"  # Default HTTPS URL
        
        # For 34.228.255.83, use a default HTTPS URL instead
        if os.getenv('FRONTEND_URL') in url or "127.0.0.1" in url:
            return "https://mrwhiteaibuddy.com/reminders"
        
        # Ensure HTTPS
        if url.startswith("http://"):
            return url.replace("http://", "https://", 1)
        elif not url.startswith("https://"):
            return f"https://{url}"
        
        return url
    
    def send_notification(
        self, 
        token: str, 
        title: str, 
        body: str, 
        data: Optional[Dict[str, str]] = None,
        click_action: Optional[str] = None
    ) -> bool:
        """
        Send a push notification to a single device
        
        Args:
            token: FCM device token
            title: Notification title
            body: Notification body
            data: Optional data payload
            click_action: Optional URL to open when notification is clicked
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.initialized:
            logger.error("FCM Service not initialized")
            return False
        
        try:
            # Build notification
            notification = messaging.Notification(
                title=title,
                body=body
            )
            
            # Build data payload
            if data is None:
                data = {}
            
            # Add click action to data if provided
            if click_action:
                data['click_action'] = click_action
            
            # Ensure HTTPS URL for click action
            https_click_action = self._ensure_https_url(click_action or '/reminders')
            
            # Create message
            message = messaging.Message(
                notification=notification,
                data=data,
                token=token,
                webpush=messaging.WebpushConfig(
                    notification=messaging.WebpushNotification(
                        title=title,
                        body=body,
                        icon='/logo.png',
                        badge='/logo.png',
                        require_interaction=True
                    ),
                    fcm_options=messaging.WebpushFCMOptions(
                        link=https_click_action
                    )
                )
            )
            
            # Send message
            response = messaging.send(message)
            logger.info(f"Successfully sent FCM message: {response}")
            return True
            
        except messaging.UnregisteredError:
            logger.warning(f"FCM token is unregistered: {token}")
            return False
        except messaging.SenderIdMismatchError:
            logger.error(f"FCM sender ID mismatch for token: {token}")
            return False
        except exceptions.InvalidArgumentError as e:
            logger.error(f"Invalid FCM argument: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send FCM notification: {e}")
            return False
    
    def send_multicast_notification(
        self, 
        tokens: List[str], 
        title: str, 
        body: str, 
        data: Optional[Dict[str, str]] = None,
        click_action: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a push notification to multiple devices
        
        Args:
            tokens: List of FCM device tokens
            title: Notification title
            body: Notification body
            data: Optional data payload
            click_action: Optional URL to open when notification is clicked
            
        Returns:
            dict: Results with success_count, failure_count, and failed_tokens
        """
        if not self.initialized:
            logger.error("FCM Service not initialized")
            return {
                'success_count': 0,
                'failure_count': len(tokens),
                'failed_tokens': tokens
            }
        
        if not tokens:
            return {
                'success_count': 0,
                'failure_count': 0,
                'failed_tokens': []
            }
        
        try:
            # Build notification
            notification = messaging.Notification(
                title=title,
                body=body
            )
            
            # Build data payload
            if data is None:
                data = {}
            
            # Add click action to data if provided
            if click_action:
                data['click_action'] = click_action
            
            # Ensure HTTPS URL for click action
            https_click_action = self._ensure_https_url(click_action or '/reminders')
            
            # Create multicast message
            multicast_message = messaging.MulticastMessage(
                notification=notification,
                data=data,
                tokens=tokens,
                webpush=messaging.WebpushConfig(
                    notification=messaging.WebpushNotification(
                        title=title,
                        body=body,
                        icon='/logo.png',
                        badge='/logo.png',
                        require_interaction=True
                    ),
                    fcm_options=messaging.WebpushFCMOptions(
                        link=https_click_action
                    )
                )
            )
            
            # Send multicast message
            response = messaging.send_multicast(multicast_message)
            
            # Process responses
            failed_tokens = []
            for idx, resp in enumerate(response.responses):
                if not resp.success:
                    failed_tokens.append(tokens[idx])
                    logger.warning(f"Failed to send to token {tokens[idx]}: {resp.exception}")
            
            logger.info(f"FCM multicast sent - Success: {response.success_count}, Failed: {response.failure_count}")
            
            return {
                'success_count': response.success_count,
                'failure_count': response.failure_count,
                'failed_tokens': failed_tokens
            }
            
        except Exception as e:
            logger.error(f"Failed to send FCM multicast notification: {e}")
            return {
                'success_count': 0,
                'failure_count': len(tokens),
                'failed_tokens': tokens
            }
    
    def send_to_user_devices(
        self, 
        user_device_tokens: Dict[str, Dict], 
        title: str, 
        body: str, 
        data: Optional[Dict[str, str]] = None,
        click_action: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send notification to all active devices of a user
        
        Args:
            user_device_tokens: User's device tokens from database
            title: Notification title
            body: Notification body
            data: Optional data payload
            click_action: Optional URL to open when notification is clicked
            
        Returns:
            dict: Results with success_count, failure_count, and platform_results
        """
        if not user_device_tokens:
            return {
                'success_count': 0,
                'failure_count': 0,
                'platform_results': {}
            }
        
        total_success = 0
        total_failure = 0
        platform_results = {}
        
        # Extract active FCM tokens
        active_tokens = []
        for platform, token_data in user_device_tokens.items():
            if (isinstance(token_data, dict) and 
                token_data.get('active', True) and 
                token_data.get('type') == 'fcm' and 
                token_data.get('token')):
                
                active_tokens.append(token_data['token'])
                platform_results[platform] = {'attempted': True}
        
        if not active_tokens:
            logger.info("No active FCM tokens found for user")
            return {
                'success_count': 0,
                'failure_count': 0,
                'platform_results': platform_results
            }
        
        # Send to all active tokens
        if len(active_tokens) == 1:
            success = self.send_notification(
                token=active_tokens[0],
                title=title,
                body=body,
                data=data,
                click_action=click_action
            )
            total_success = 1 if success else 0
            total_failure = 0 if success else 1
        else:
            result = self.send_multicast_notification(
                tokens=active_tokens,
                title=title,
                body=body,
                data=data,
                click_action=click_action
            )
            total_success = result['success_count']
            total_failure = result['failure_count']
        
        return {
            'success_count': total_success,
            'failure_count': total_failure,
            'platform_results': platform_results
        }
    
    def is_available(self) -> bool:
        """Check if FCM service is available"""
        return self.initialized


# Global FCM service instance
_fcm_service = None

def get_fcm_service() -> FCMService:
    """Get global FCM service instance"""
    global _fcm_service
    if _fcm_service is None:
        _fcm_service = FCMService()
    return _fcm_service 