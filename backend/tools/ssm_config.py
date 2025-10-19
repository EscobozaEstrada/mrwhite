    `"""
SSM-aware Flask Configuration

This module provides Flask configuration that can read from AWS SSM Parameter Store
with automatic fallback to environment variables.
"""

import os
import json
import logging
from typing import Optional, Any, Dict
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

logger = logging.getLogger(__name__)

class SSMConfigManager:
    """Manages configuration from AWS SSM Parameter Store"""
    
    def __init__(self, environment: str = 'dev', organization: str = 'monetizespirit', project: str = 'mrwhite'):
        self.environment = environment
        self.organization = organization 
        self.project = project
        self.parameter_prefix = f"/{organization}/{project}/{environment}/"
        self._ssm_client = None
        self._cache = {}
        
    @property
    def ssm_client(self):
        """Lazy initialization of SSM client"""
        if self._ssm_client is None:
            try:
                self._ssm_client = boto3.client('ssm')
            except NoCredentialsError:
                logger.warning("⚠️  AWS credentials not found, SSM parameters will not be available")
                self._ssm_client = False  # Mark as unavailable
            except Exception as e:
                logger.warning(f"⚠️  Failed to initialize SSM client: {e}")
                self._ssm_client = False
        return self._ssm_client if self._ssm_client is not False else None
    
    def get_parameter(self, param_name: str, default: Any = None, param_type: str = 'String') -> Any:
        """
        Get a parameter from SSM with fallback to environment variables
        
        Args:
            param_name: SSM parameter name (without prefix)
            default: Default value if parameter not found
            param_type: Expected parameter type for conversion
            
        Returns:
            Parameter value or default
        """
        # Check cache first
        cache_key = f"{self.parameter_prefix}{param_name}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Try SSM first
        if self.ssm_client:
            try:
                full_param_name = f"{self.parameter_prefix}{param_name}"
                response = self.ssm_client.get_parameter(
                    Name=full_param_name,
                    WithDecryption=True
                )
                value = response['Parameter']['Value']
                
                # Type conversion
                if param_type == 'int':
                    value = int(value)
                elif param_type == 'float':
                    value = float(value)
                elif param_type == 'bool':
                    value = value.lower() in ('true', '1', 'yes', 'on')
                elif param_type == 'json':
                    value = json.loads(value)
                
                # Cache the value
                self._cache[cache_key] = value
                return value
                
            except ClientError as e:
                if e.response['Error']['Code'] != 'ParameterNotFound':
                    logger.warning(f"⚠️  Error accessing SSM parameter {param_name}: {e}")
            except Exception as e:
                logger.warning(f"⚠️  Unexpected error accessing SSM parameter {param_name}: {e}")
        
        # Fallback to environment variable
        env_var_name = param_name.upper()
        env_value = os.getenv(env_var_name, default)
        
        if env_value is not None and param_type in ['int', 'float', 'bool', 'json']:
            try:
                if param_type == 'int':
                    env_value = int(env_value)
                elif param_type == 'float':
                    env_value = float(env_value)
                elif param_type == 'bool':
                    env_value = str(env_value).lower() in ('true', '1', 'yes', 'on')
                elif param_type == 'json':
                    env_value = json.loads(env_value)
            except (ValueError, json.JSONDecodeError) as e:
                logger.warning(f"⚠️  Error converting environment variable {env_var_name}: {e}")
                env_value = default
        
        return env_value

class Config:
    """Flask configuration using SSM Parameter Store with environment variable fallback"""
    
    def __init__(self, environment: str = None):
        if environment is None:
            environment = os.getenv('ENVIRONMENT', 'dev')
        
        self.ssm = SSMConfigManager(environment=environment)
        
        # Database Configuration
        self.SQLALCHEMY_DATABASE_URI = self.ssm.get_parameter(
            'database_url', 
            os.getenv('DATABASE_URL', 'sqlite:///app.db')
        )
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False
        
        # Database connection pool settings
        self.SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'pool_timeout': 20,
            'max_overflow': 10,
            'pool_size': 5,
        }
        
        # Application Security
        self.SECRET_KEY = self.ssm.get_parameter('app_secret_key', 'dev-secret-key')
        self.JWT_SECRET_KEY = self.ssm.get_parameter('jwt_secret_key', self.SECRET_KEY)
        
        # JWT Configuration
        self.JWT_ACCESS_TOKEN_EXPIRES_DAYS = self.ssm.get_parameter('jwt_expiry_days', 1, 'int')
        from datetime import timedelta
        self.JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=self.JWT_ACCESS_TOKEN_EXPIRES_DAYS)
        self.JWT_ALGORITHM = self.ssm.get_parameter('jwt_algorithm', 'HS256')
        
        # Cookie Configuration
        self.JWT_TOKEN_LOCATION = ['headers', 'cookies']
        self.JWT_COOKIE_SECURE = self.ssm.get_parameter('cookie_secure', False, 'bool')
        self.JWT_COOKIE_CSRF_PROTECT = False
        self.JWT_COOKIE_SAMESITE = self.ssm.get_parameter('cookie_samesite', 'Lax')
        self.JWT_ACCESS_COOKIE_NAME = 'access_token'
        self.JWT_ACCESS_COOKIE_PATH = '/'
        self.JWT_COOKIE_DOMAIN = None
        
        # Additional Cookie Configuration
        self.COOKIE_HTTPONLY = self.ssm.get_parameter('cookie_httponly', True, 'bool')
        self.COOKIE_SECURE = self.ssm.get_parameter('cookie_secure', False, 'bool')
        self.COOKIE_MAX_AGE = self.ssm.get_parameter('cookie_max_age', 604800, 'int')
        self.COOKIE_SAMESITE = self.ssm.get_parameter('cookie_samesite', 'Lax')
        
        # AWS Configuration
        self.AWS_ACCESS_KEY_ID = self.ssm.get_parameter('aws_access_key_id')
        self.AWS_SECRET_ACCESS_KEY = self.ssm.get_parameter('aws_secret_access_key')
        self.S3_BUCKET_NAME = self.ssm.get_parameter('s3_bucket_name')
        
        # SES Configuration
        self.SES_SMTP_HOST = self.ssm.get_parameter('ses_smtp_host')
        self.SES_SMTP_PORT = self.ssm.get_parameter('ses_smtp_port')
        self.SES_SMTP_USERNAME = self.ssm.get_parameter('ses_smtp_username')
        self.SES_SMTP_PASSWORD = self.ssm.get_parameter('ses_smtp_password')
        self.SES_EMAIL_FROM = self.ssm.get_parameter('ses_email_from')
        
        # API Keys
        self.OPENAI_API_KEY = self.ssm.get_parameter('openai_api_key')
        self.PINECONE_API_KEY = self.ssm.get_parameter('pinecone_api_key')
        self.TEXTBELT_API_KEY = self.ssm.get_parameter('textbelt_api_key')
        
        # Payment Processing
        self.STRIPE_SECRET_KEY = self.ssm.get_parameter('stripe_secret_key')
        self.STRIPE_PUBLISHABLE_KEY = self.ssm.get_parameter('stripe_publishable_key')
        
        # Firebase Configuration
        self.FIREBASE_PROJECT_ID = self.ssm.get_parameter('firebase_project_id')
        self.FIREBASE_API_KEY = self.ssm.get_parameter('firebase_api_key')
        self.FIREBASE_AUTH_DOMAIN = self.ssm.get_parameter('firebase_auth_domain')
        self.FIREBASE_STORAGE_BUCKET = self.ssm.get_parameter('firebase_storage_bucket')
        self.FIREBASE_MESSAGING_SENDER_ID = self.ssm.get_parameter('firebase_messaging_sender_id')
        self.FIREBASE_APP_ID = self.ssm.get_parameter('firebase_app_id')
        self.FIREBASE_MEASUREMENT_ID = self.ssm.get_parameter('firebase_measurement_id')
        
        # Firebase Service Account JSON (from SSM)
        self.FIREBASE_SERVICE_ACCOUNT_JSON = self.ssm.get_parameter('firebase_service_account_json')
        
        # VAPID Keys for Push Notifications
        self.VAPID_PRIVATE_KEY = self.ssm.get_parameter('vapid_private_key')
        self.VAPID_PUBLIC_KEY = self.ssm.get_parameter('vapid_public_key')
        self.VAPID_EMAIL = self.ssm.get_parameter('vapid_email')
        
        # Application URLs
        self.FRONTEND_URL = self.ssm.get_parameter('frontend_url', 'http://localhost:3000')
        
        # OpenAI Configuration
        self.OPENAI_EMBEDDING_MODEL = self.ssm.get_parameter('openai_embedding_model', 'text-embedding-3-large')
        self.OPENAI_CHAT_MODEL = self.ssm.get_parameter('openai_chat_model', 'gpt-4')
        self.OPENAI_TEMPERATURE = self.ssm.get_parameter('openai_temperature', 0.7, 'float')
        self.OPENAI_MAX_TOKENS = self.ssm.get_parameter('openai_max_tokens', 1000, 'int')
        self.OPENAI_FILE_UPLOAD_TEMPERATURE = self.ssm.get_parameter('openai_file_upload_temperature', 0.9, 'float')
        
        # Pinecone Configuration
        self.PINECONE_ENVIRONMENT = self.ssm.get_parameter('pinecone_environment')
        self.PINECONE_INDEX_NAME = self.ssm.get_parameter('pinecone_index_name')
        
        # Flask Server Configuration
        self.FLASK_HOST = self.ssm.get_parameter('flask_host', '0.0.0.0')
        self.FLASK_PORT = self.ssm.get_parameter('flask_port', 5001, 'int')
        self.FLASK_DEBUG = self.ssm.get_parameter('flask_debug', False, 'bool')
        
        # CORS Configuration
        self.CORS_MAX_AGE = self.ssm.get_parameter('cors_max_age', 3600, 'int')

def get_config(environment: str = None) -> Config:
    """
    Get configuration object for the specified environment
    
    Args:
        environment: Environment name (dev, staging, prod)
        
    Returns:
        Config object with SSM parameter store integration
    """
    return Config(environment=environment)