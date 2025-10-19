#!/usr/bin/env python3
"""
AWS SSM Parameter Store Secret Upload Script

This script reads secrets from ../.env file and uploads them to AWS SSM Parameter Store
for secure access by App Runner without storing secrets in Terraform state.

Usage:
    python upload_secrets_to_ssm.py --environment dev
    python upload_secrets_to_ssm.py --environment prod

Requirements:
    pip install boto3 python-dotenv
"""

import os
import sys
import argparse
import boto3
from pathlib import Path
from dotenv import load_dotenv
from botocore.exceptions import ClientError, NoCredentialsError
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SSMSecretUploader:
    def __init__(self, environment='dev', organization='monetizespirit', project='mrwhite'):
        """
        Initialize SSM Secret Uploader
        
        Args:
            environment: Environment name (dev, staging, prod)
            organization: Organization name for parameter path
            project: Project name for parameter path
        """
        self.environment = environment
        self.organization = organization
        self.project = project
        self.parameter_prefix = f"/{organization}/{project}/{environment}/"
        
        # Initialize AWS SSM client
        try:
            self.ssm_client = boto3.client('ssm')
            logger.info(f"✅ AWS SSM client initialized for environment: {environment}")
        except NoCredentialsError:
            logger.error("❌ AWS credentials not found. Please configure AWS credentials.")
            sys.exit(1)
        except Exception as e:
            logger.error(f"❌ Failed to initialize AWS SSM client: {str(e)}")
            sys.exit(1)

    def load_env_file(self, env_file_path):
        """
        Load environment variables from .env file with multiline support
        
        Args:
            env_file_path: Path to the .env file
            
        Returns:
            dict: Dictionary of environment variables
        """
        if not os.path.exists(env_file_path):
            logger.error(f"❌ .env file not found at: {env_file_path}")
            sys.exit(1)
            
        # Load .env file
        load_dotenv(env_file_path)
        
        # Read all variables from .env file manually for better control
        env_vars = {}
        try:
            with open(env_file_path, 'r') as file:
                lines = file.readlines()
                
            i = 0
            while i < len(lines):
                line = lines[i].rstrip('\n\r')
                line_num = i + 1
                
                # Skip empty lines and comments
                if not line.strip() or line.strip().startswith('#'):
                    i += 1
                    continue
                    
                # Parse key=value pairs
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Handle multiline values (quoted strings that span multiple lines)
                    if value.startswith('"') and not value.endswith('"'):
                        # This is the start of a multiline quoted string
                        multiline_value = value[1:]  # Remove opening quote
                        i += 1
                        
                        # Continue reading lines until we find the closing quote
                        while i < len(lines):
                            next_line = lines[i].rstrip('\n\r')
                            if next_line.endswith('"'):
                                # Found closing quote
                                multiline_value += '\n' + next_line[:-1]  # Remove closing quote
                                break
                            else:
                                multiline_value += '\n' + next_line
                            i += 1
                        
                        if i >= len(lines):
                            logger.warning(f"⚠️  Line {line_num}: Unterminated multiline string for key '{key}'")
                        
                        env_vars[key] = multiline_value
                        
                    else:
                        # Single line value
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                            
                        env_vars[key] = value
                        
                else:
                    logger.warning(f"⚠️  Line {line_num}: Invalid format - {line}")
                
                i += 1
                        
        except Exception as e:
            logger.error(f"❌ Failed to read .env file: {str(e)}")
            sys.exit(1)
            
        logger.info(f"✅ Loaded {len(env_vars)} environment variables from {env_file_path}")
        return env_vars

    def get_secrets_mapping(self):
        """
        Define which environment variables should be stored as secure parameters
        
        Returns:
            dict: Mapping of env vars to SSM parameter names and types
        """
        return {
            # Database credentials (handled by AWS RDS managed passwords)
            # 'DATABASE_URL': {'param_name': 'database_url', 'type': 'SecureString'},
            
            # API Keys
            'OPENAI_API_KEY': {'param_name': 'openai_api_key', 'type': 'SecureString'},
            'PINECONE_API_KEY': {'param_name': 'pinecone_api_key', 'type': 'SecureString'},
            
            # Application Security
            'SECRET_KEY': {'param_name': 'app_secret_key', 'type': 'SecureString'},
            'JWT_SECRET_KEY': {'param_name': 'jwt_secret_key', 'type': 'SecureString'},
            
            # AWS Configuration (for local development only)
            'AWS_ACCESS_KEY_ID': {'param_name': 'aws_access_key_id', 'type': 'SecureString'},
            'AWS_SECRET_ACCESS_KEY': {'param_name': 'aws_secret_access_key', 'type': 'SecureString'},
            
            # Payment Processing
            'STRIPE_SECRET_KEY': {'param_name': 'stripe_secret_key', 'type': 'SecureString'},
            'STRIPE_PUBLISHABLE_KEY': {'param_name': 'stripe_publishable_key', 'type': 'String'},
            
            # Firebase Configuration
            'FIREBASE_PROJECT_ID': {'param_name': 'firebase_project_id', 'type': 'String'},
            'FIREBASE_API_KEY': {'param_name': 'firebase_api_key', 'type': 'SecureString'},
            'FIREBASE_AUTH_DOMAIN': {'param_name': 'firebase_auth_domain', 'type': 'String'},
            'FIREBASE_STORAGE_BUCKET': {'param_name': 'firebase_storage_bucket', 'type': 'String'},
            'FIREBASE_MESSAGING_SENDER_ID': {'param_name': 'firebase_messaging_sender_id', 'type': 'String'},
            'FIREBASE_APP_ID': {'param_name': 'firebase_app_id', 'type': 'String'},
            'FIREBASE_MEASUREMENT_ID': {'param_name': 'firebase_measurement_id', 'type': 'String'},
            
            # Email Configuration
            'SES_SMTP_HOST': {'param_name': 'ses_smtp_host', 'type': 'String'},
            'SES_SMTP_PORT': {'param_name': 'ses_smtp_port', 'type': 'String'},
            'SES_SMTP_USERNAME': {'param_name': 'ses_smtp_username', 'type': 'String'},
            'SES_SMTP_PASSWORD': {'param_name': 'ses_smtp_password', 'type': 'SecureString'},
            'SES_EMAIL_FROM': {'param_name': 'ses_email_from', 'type': 'String'},
            
            # External API Keys
            'TEXTBELT_API_KEY': {'param_name': 'textbelt_api_key', 'type': 'SecureString'},
            
            # Application Configuration (non-sensitive)
            'FRONTEND_URL': {'param_name': 'frontend_url', 'type': 'String'},
            'PINECONE_ENVIRONMENT': {'param_name': 'pinecone_environment', 'type': 'String'},
            'PINECONE_INDEX_NAME': {'param_name': 'pinecone_index_name', 'type': 'String'},
            
            # OpenAI Configuration
            'OPENAI_EMBEDDING_MODEL': {'param_name': 'openai_embedding_model', 'type': 'String'},
            'OPENAI_CHAT_MODEL': {'param_name': 'openai_chat_model', 'type': 'String'},
            'OPENAI_TEMPERATURE': {'param_name': 'openai_temperature', 'type': 'String'},
            'OPENAI_MAX_TOKENS': {'param_name': 'openai_max_tokens', 'type': 'String'},
            'OPENAI_FILE_UPLOAD_TEMPERATURE': {'param_name': 'openai_file_upload_temperature', 'type': 'String'},
            
            # JWT Configuration
            'JWT_EXPIRY_DAYS': {'param_name': 'jwt_expiry_days', 'type': 'String'},
            'JWT_ALGORITHM': {'param_name': 'jwt_algorithm', 'type': 'String'},
            
            # Cookie Configuration
            'COOKIE_SECURE': {'param_name': 'cookie_secure', 'type': 'String'},
            'COOKIE_HTTPONLY': {'param_name': 'cookie_httponly', 'type': 'String'},
            'COOKIE_SAMESITE': {'param_name': 'cookie_samesite', 'type': 'String'},
            'COOKIE_MAX_AGE': {'param_name': 'cookie_max_age', 'type': 'String'},
            
            # AWS S3 Configuration
            'S3_BUCKET_NAME': {'param_name': 's3_bucket_name', 'type': 'String'},
            
            # Flask Configuration
            'FLASK_HOST': {'param_name': 'flask_host', 'type': 'String'},
            'FLASK_PORT': {'param_name': 'flask_port', 'type': 'String'},
            'FLASK_DEBUG': {'param_name': 'flask_debug', 'type': 'String'},
            'FLASK_ENV': {'param_name': 'flask_env', 'type': 'String'},
            
            # CORS Configuration
            'CORS_MAX_AGE': {'param_name': 'cors_max_age', 'type': 'String'},
            
            # VAPID Keys for Push Notifications
            'VAPID_PRIVATE_KEY': {'param_name': 'vapid_private_key', 'type': 'SecureString'},
            'VAPID_PUBLIC_KEY': {'param_name': 'vapid_public_key', 'type': 'String'},
            'VAPID_EMAIL': {'param_name': 'vapid_email', 'type': 'String'},
        }

    def get_json_files_mapping(self):
        """
        Define which JSON files should be uploaded to SSM Parameter Store
        
        Returns:
            dict: Mapping of file paths to SSM parameter names and types
        """
        return {
            'firebase-service-account.json': {
                'param_name': 'firebase_service_account_json', 
                'type': 'SecureString',
                'description': 'Firebase service account credentials JSON file'
            },
        }

    def upload_parameter(self, parameter_name, parameter_value, parameter_type='SecureString'):
        """
        Upload a single parameter to SSM Parameter Store
        
        Args:
            parameter_name: Name of the parameter
            parameter_value: Value of the parameter
            parameter_type: Type of parameter (String, SecureString, StringList)
        """
        full_parameter_name = f"{self.parameter_prefix}{parameter_name}"
        
        try:
            # Check if parameter already exists
            try:
                existing_param = self.ssm_client.get_parameter(
                    Name=full_parameter_name,
                    WithDecryption=True
                )
                
                # If parameter exists and values are the same, skip
                if existing_param['Parameter']['Value'] == parameter_value:
                    logger.info(f"⏭️  Parameter {full_parameter_name} already exists with same value, skipping")
                    return True
                    
                # Update existing parameter
                self.ssm_client.put_parameter(
                    Name=full_parameter_name,
                    Value=parameter_value,
                    Type=parameter_type,
                    Overwrite=True,
                    Description=f"Auto-uploaded from .env for {self.environment} environment"
                )
                logger.info(f"🔄 Updated parameter: {full_parameter_name}")
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'ParameterNotFound':
                    # Create new parameter
                    self.ssm_client.put_parameter(
                        Name=full_parameter_name,
                        Value=parameter_value,
                        Type=parameter_type,
                        Description=f"Auto-uploaded from .env for {self.environment} environment"
                    )
                    logger.info(f"✅ Created parameter: {full_parameter_name}")
                else:
                    raise e
                    
            return True
            
        except ClientError as e:
            logger.error(f"❌ Failed to upload parameter {full_parameter_name}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error uploading parameter {full_parameter_name}: {str(e)}")
            return False

    def upload_secrets(self, env_vars):
        """
        Upload all secrets from environment variables to SSM Parameter Store
        
        Args:
            env_vars: Dictionary of environment variables
        """
        secrets_mapping = self.get_secrets_mapping()
        
        successful_uploads = 0
        failed_uploads = 0
        skipped_uploads = 0
        
        logger.info(f"🚀 Starting upload of secrets to SSM Parameter Store...")
        logger.info(f"📍 Parameter prefix: {self.parameter_prefix}")
        
        for env_key, config in secrets_mapping.items():
            if env_key in env_vars:
                value = env_vars[env_key]
                
                # Skip empty values
                if not value or value.strip() == '':
                    logger.warning(f"⚠️  Skipping empty value for {env_key}")
                    skipped_uploads += 1
                    continue
                
                param_name = config['param_name']
                param_type = config['type']
                
                if self.upload_parameter(param_name, value, param_type):
                    successful_uploads += 1
                else:
                    failed_uploads += 1
            else:
                logger.warning(f"⚠️  Environment variable {env_key} not found in .env file")
                skipped_uploads += 1
        
        # Summary
        logger.info(f"\n📊 Upload Summary:")
        logger.info(f"✅ Successful uploads: {successful_uploads}")
        logger.info(f"❌ Failed uploads: {failed_uploads}")
        logger.info(f"⏭️  Skipped uploads: {skipped_uploads}")
        
        if failed_uploads > 0:
            logger.error(f"❌ {failed_uploads} uploads failed. Please check the errors above.")
            return False
        else:
            logger.info(f"🎉 All uploads completed successfully!")
            return True

    def upload_json_files(self, base_directory='.'):
        """
        Upload JSON files (like Firebase service account) to SSM Parameter Store
        
        Args:
            base_directory: Base directory to look for JSON files
            
        Returns:
            tuple: (successful_uploads, failed_uploads, skipped_uploads)
        """
        import json
        
        json_files_mapping = self.get_json_files_mapping()
        
        successful_uploads = 0
        failed_uploads = 0
        skipped_uploads = 0
        
        logger.info(f"🗂️  Starting upload of JSON files to SSM Parameter Store...")
        
        for file_name, config in json_files_mapping.items():
            file_path = os.path.join(base_directory, file_name)
            
            if os.path.exists(file_path):
                try:
                    # Read and validate JSON file
                    with open(file_path, 'r') as f:
                        json_content = json.load(f)
                    
                    # Convert back to string for storage
                    json_string = json.dumps(json_content, separators=(',', ':'))
                    
                    # Upload to SSM
                    success = self.upload_parameter(
                        config['param_name'], 
                        json_string, 
                        config['type']
                    )
                    
                    if success:
                        successful_uploads += 1
                        logger.info(f"✅ Uploaded JSON file: {file_name} -> {config['param_name']}")
                    else:
                        failed_uploads += 1
                        
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Invalid JSON in file {file_name}: {str(e)}")
                    failed_uploads += 1
                except Exception as e:
                    logger.error(f"❌ Failed to upload JSON file {file_name}: {str(e)}")
                    failed_uploads += 1
            else:
                logger.warning(f"⚠️  JSON file not found: {file_path}")
                skipped_uploads += 1
        
        return successful_uploads, failed_uploads, skipped_uploads

    def list_uploaded_parameters(self):
        """
        List all parameters that were uploaded to verify they exist
        """
        try:
            logger.info(f"\n📋 Listing parameters with prefix: {self.parameter_prefix}")
            
            paginator = self.ssm_client.get_paginator('get_parameters_by_path')
            page_iterator = paginator.paginate(
                Path=self.parameter_prefix,
                Recursive=True,
                WithDecryption=False  # Don't decrypt for listing
            )
            
            parameters = []
            for page in page_iterator:
                parameters.extend(page['Parameters'])
            
            if parameters:
                logger.info(f"📦 Found {len(parameters)} parameters:")
                for param in sorted(parameters, key=lambda x: x['Name']):
                    param_type = param['Type']
                    param_name = param['Name'].replace(self.parameter_prefix, '')
                    logger.info(f"  • {param_name} ({param_type})")
            else:
                logger.warning(f"⚠️  No parameters found with prefix: {self.parameter_prefix}")
                
        except Exception as e:
            logger.error(f"❌ Failed to list parameters: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Upload secrets from .env file to AWS SSM Parameter Store')
    parser.add_argument(
        '--environment', '-e',
        default='dev',
        choices=['dev', 'staging', 'prod'],
        help='Environment name (default: dev)'
    )
    parser.add_argument(
        '--organization', '-o',
        default='monetizespirit',
        help='Organization name for parameter path (default: monetizespirit)'
    )
    parser.add_argument(
        '--project', '-p',
        default='mrwhite',
        help='Project name for parameter path (default: mrwhite)'
    )
    parser.add_argument(
        '--env-file',
        default='../.env',
        help='Path to .env file (default: ../.env)'
    )
    parser.add_argument(
        '--list-only',
        action='store_true',
        help='Only list existing parameters, do not upload'
    )
    
    args = parser.parse_args()
    
    # Initialize uploader
    uploader = SSMSecretUploader(
        environment=args.environment,
        organization=args.organization,
        project=args.project
    )
    
    if args.list_only:
        uploader.list_uploaded_parameters()
        return
    
    # Load environment variables
    # Handle path resolution - if it's a relative path, make it relative to the script location
    if not os.path.isabs(args.env_file):
        env_file_path = os.path.join(os.path.dirname(__file__), args.env_file)
    else:
        env_file_path = args.env_file
        
    # If the file doesn't exist and we're using the default path, try looking in the current directory
    if not os.path.exists(env_file_path) and args.env_file == '../.env':
        # Try looking for .env in the current working directory
        current_dir_env = os.path.join(os.getcwd(), '.env')
        if os.path.exists(current_dir_env):
            env_file_path = current_dir_env
            logger.info(f"📁 Using .env file from current directory: {env_file_path}")
    
    env_vars = uploader.load_env_file(env_file_path)
    
    # Upload secrets from .env file
    success_env = uploader.upload_secrets(env_vars)
    
    # Upload JSON files (like Firebase service account)
    json_base_dir = os.path.dirname(env_file_path)  # Same directory as .env file
    json_success, json_failed, json_skipped = uploader.upload_json_files(json_base_dir)
    
    # Overall success if both .env and JSON uploads succeeded
    overall_success = success_env and (json_failed == 0)
    
    # List uploaded parameters for verification
    uploader.list_uploaded_parameters()
    
    if overall_success:
        logger.info(f"\n🎉 All secrets and JSON files successfully uploaded to SSM Parameter Store!")
        logger.info(f"💡 Update your App Runner configuration to use these parameters.")
        if json_success > 0:
            logger.info(f"🔐 Firebase service account JSON is now securely stored in SSM.")
            logger.info(f"💡 You can now remove firebase-service-account.json from git and use SSM instead.")
        sys.exit(0)
    else:
        logger.error(f"\n❌ Some uploads failed. Please check the errors above.")
        sys.exit(1)

if __name__ == '__main__':
    main()