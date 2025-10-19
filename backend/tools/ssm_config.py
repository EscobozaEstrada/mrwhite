"""
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
                region = os.getenv('AWS_REGION', 'us-east-1')
                self._ssm_client = boto3.client('ssm', region_name=region)
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
        
        # Helper to set both config attribute and environment variable
        # This allows code to use either app.config or os.getenv() transparently
        def _set_config(key, param_name, default=None, param_type='String'):
            value = self.ssm.get_parameter(param_name, default, param_type)
            setattr(self, key, value)
            # Always set in os.environ for libraries that read from environment
            if value is not None:
                os.environ[key] = str(value)
            return value
        
        # Database Configuration
        self.SQLALCHEMY_DATABASE_URI = _set_config('DATABASE_URL', 'database_url', 
            os.getenv('DATABASE_URL', 'sqlite:///app.db'))
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
        self.SECRET_KEY = _set_config('SECRET_KEY', 'app_secret_key', 'dev-secret-key')
        self.JWT_SECRET_KEY = _set_config('JWT_SECRET_KEY', 'jwt_secret_key', self.SECRET_KEY)
        
        # JWT Configuration
        self.JWT_ACCESS_TOKEN_EXPIRES_DAYS = _set_config('JWT_EXPIRY_DAYS', 'jwt_expiry_days', 1, 'int')
        from datetime import timedelta
        self.JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=self.JWT_ACCESS_TOKEN_EXPIRES_DAYS)
        self.JWT_ALGORITHM = _set_config('JWT_ALGORITHM', 'jwt_algorithm', 'HS256')
        
        # Cookie Configuration
        self.JWT_TOKEN_LOCATION = ['headers', 'cookies']
        self.JWT_COOKIE_SECURE = _set_config('COOKIE_SECURE', 'cookie_secure', False, 'bool')
        self.JWT_COOKIE_CSRF_PROTECT = False
        self.JWT_COOKIE_SAMESITE = _set_config('COOKIE_SAMESITE', 'cookie_samesite', 'Lax')
        self.JWT_ACCESS_COOKIE_NAME = 'access_token'
        self.JWT_ACCESS_COOKIE_PATH = '/'
        self.JWT_COOKIE_DOMAIN = None
        
        # Additional Cookie Configuration
        self.COOKIE_HTTPONLY = _set_config('COOKIE_HTTPONLY', 'cookie_httponly', True, 'bool')
        self.COOKIE_SECURE = _set_config('COOKIE_SECURE', 'cookie_secure', False, 'bool')
        self.COOKIE_MAX_AGE = _set_config('COOKIE_MAX_AGE', 'cookie_max_age', 604800, 'int')
        self.COOKIE_SAMESITE = _set_config('COOKIE_SAMESITE', 'cookie_samesite', 'Lax')
        
        # AWS Configuration - also set in environment for boto3
        self.AWS_ACCESS_KEY_ID = _set_config('AWS_ACCESS_KEY_ID', 'aws_access_key_id')
        self.AWS_SECRET_ACCESS_KEY = _set_config('AWS_SECRET_ACCESS_KEY', 'aws_secret_access_key')
        self.S3_BUCKET_NAME = _set_config('S3_BUCKET_NAME', 's3_bucket_name')
        
        # SES Configuration
        self.SES_SMTP_HOST = _set_config('SES_SMTP_HOST', 'ses_smtp_host')
        self.SES_SMTP_PORT = _set_config('SES_SMTP_PORT', 'ses_smtp_port')
        self.SES_SMTP_USERNAME = _set_config('SES_SMTP_USERNAME', 'ses_smtp_username')
        self.SES_SMTP_PASSWORD = _set_config('SES_SMTP_PASSWORD', 'ses_smtp_password')
        self.SES_EMAIL_FROM = _set_config('SES_EMAIL_FROM', 'ses_email_from')
        
        # API Keys - also set in environment for libraries that need them
        self.OPENAI_API_KEY = _set_config('OPENAI_API_KEY', 'openai_api_key')
        self.PINECONE_API_KEY = _set_config('PINECONE_API_KEY', 'pinecone_api_key')
        self.TEXTBELT_API_KEY = _set_config('TEXTBELT_API_KEY', 'textbelt_api_key')
        
        # Payment Processing - also set in environment for stripe library
        self.STRIPE_SECRET_KEY = _set_config('STRIPE_SECRET_KEY', 'stripe_secret_key')
        self.STRIPE_PUBLISHABLE_KEY = _set_config('STRIPE_PUBLISHABLE_KEY', 'stripe_publishable_key')
        
        # Firebase Configuration
        self.FIREBASE_PROJECT_ID = _set_config('FIREBASE_PROJECT_ID', 'firebase_project_id')
        self.FIREBASE_API_KEY = _set_config('FIREBASE_API_KEY', 'firebase_api_key')
        self.FIREBASE_AUTH_DOMAIN = _set_config('FIREBASE_AUTH_DOMAIN', 'firebase_auth_domain')
        self.FIREBASE_STORAGE_BUCKET = _set_config('FIREBASE_STORAGE_BUCKET', 'firebase_storage_bucket')
        self.FIREBASE_MESSAGING_SENDER_ID = _set_config('FIREBASE_MESSAGING_SENDER_ID', 'firebase_messaging_sender_id')
        self.FIREBASE_APP_ID = _set_config('FIREBASE_APP_ID', 'firebase_app_id')
        self.FIREBASE_MEASUREMENT_ID = _set_config('FIREBASE_MEASUREMENT_ID', 'firebase_measurement_id')
        
        # Firebase Service Account JSON (from SSM)
        self.FIREBASE_SERVICE_ACCOUNT_JSON = _set_config('FIREBASE_SERVICE_ACCOUNT_JSON', 'firebase_service_account_json')
        
        # VAPID Keys for Push Notifications
        self.VAPID_PRIVATE_KEY = _set_config('VAPID_PRIVATE_KEY', 'vapid_private_key')
        self.VAPID_PUBLIC_KEY = _set_config('VAPID_PUBLIC_KEY', 'vapid_public_key')
        self.VAPID_EMAIL = _set_config('VAPID_EMAIL', 'vapid_email')
        
        # Application URLs
        self.FRONTEND_URL = _set_config('FRONTEND_URL', 'frontend_url', 'http://localhost:3000')
        
        # OpenAI Configuration
        self.OPENAI_EMBEDDING_MODEL = _set_config('OPENAI_EMBEDDING_MODEL', 'openai_embedding_model', 'text-embedding-3-large')
        self.OPENAI_CHAT_MODEL = _set_config('OPENAI_CHAT_MODEL', 'openai_chat_model', 'gpt-4')
        self.OPENAI_TEMPERATURE = _set_config('OPENAI_TEMPERATURE', 'openai_temperature', 0.7, 'float')
        self.OPENAI_MAX_TOKENS = _set_config('OPENAI_MAX_TOKENS', 'openai_max_tokens', 1000, 'int')
        self.OPENAI_FILE_UPLOAD_TEMPERATURE = _set_config('OPENAI_FILE_UPLOAD_TEMPERATURE', 'openai_file_upload_temperature', 0.9, 'float')
        
        # Pinecone Configuration - also set in environment
        self.PINECONE_ENVIRONMENT = _set_config('PINECONE_ENVIRONMENT', 'pinecone_environment')
        self.PINECONE_INDEX_NAME = _set_config('PINECONE_INDEX_NAME', 'pinecone_index_name')
        
        # Flask Server Configuration
        self.FLASK_HOST = _set_config('FLASK_HOST', 'flask_host', '0.0.0.0')
        self.FLASK_PORT = _set_config('FLASK_PORT', 'flask_port', 5001, 'int')
        self.FLASK_DEBUG = _set_config('FLASK_DEBUG', 'flask_debug', False, 'bool')
        
        # CORS Configuration
        self.CORS_MAX_AGE = _set_config('CORS_MAX_AGE', 'cors_max_age', 3600, 'int')

def get_config(environment: str = None) -> Config:
    """
    Get configuration object for the specified environment
    
    Args:
        environment: Environment name (dev, staging, prod)
        
    Returns:
        Config object with SSM parameter store integration
    """
    return Config(environment=environment)