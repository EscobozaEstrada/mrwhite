#!/usr/bin/env python3
"""
AWS SSM Parameter Store Secret Upload Script for Frontend (Dynamic Version)

This script reads ALL variables starting with NEXT_PUBLIC_ from the frontend's .env file
and uploads them to AWS SSM, making them available to the Amplify build process.

Usage:
    cd frontend/scripts
    python upload_secrets_to_ssm.py --environment prod --env-file ../.env
"""

import os
import sys
import argparse
import boto3
from dotenv import dotenv_values
from botocore.exceptions import ClientError, NoCredentialsError
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SSMSecretUploader:
    def __init__(self, environment='dev', organization='monetizespirit', project='mrwhite'):
        self.environment = environment
        self.parameter_prefix = f"/{organization}/{project}/{environment}/"
        try:
            self.ssm_client = boto3.client('ssm')
            logger.info(f"✅ AWS SSM client initialized for environment: {environment}")
        except NoCredentialsError:
            logger.error("❌ AWS credentials not found. Please configure them.")
            sys.exit(1)

    def is_sensitive(self, env_key: str) -> bool:
        """
        Determines if an environment variable key suggests a sensitive value.
        Treats keys with 'KEY', 'TOKEN', or 'SECRET' as sensitive, with exceptions.
        """
        key_lower = env_key.lower()
        sensitive_keywords = ['api_key', 'token', 'secret']
        
        # Explicitly public keys are not sensitive
        if 'public_key' in key_lower or 'publishable_key' in key_lower:
            return False
            
        return any(keyword in key_lower for keyword in sensitive_keywords)

    def upload_parameter(self, parameter_name, parameter_value, parameter_type='String'):
        """Uploads a single parameter to SSM, overwriting if it exists."""
        full_parameter_name = f"{self.parameter_prefix}{parameter_name}"
        try:
            self.ssm_client.put_parameter(
                Name=full_parameter_name,
                Value=parameter_value,
                Type=parameter_type,
                Overwrite=True,
                Description=f"Auto-uploaded from frontend .env for {self.environment}"
            )
            logger.info(f"✅ Uploaded parameter: {full_parameter_name} (Type: {parameter_type})")
            return True
        except ClientError as e:
            logger.error(f"❌ Failed to upload parameter {full_parameter_name}: {str(e)}")
            return False

    def upload_secrets(self, env_file_path):
        """
        Loads a .env file and uploads all NEXT_PUBLIC_ variables to SSM.
        """
        if not os.path.exists(env_file_path):
            logger.error(f"❌ .env file not found at: {env_file_path}")
            sys.exit(1)
        
        env_vars = dotenv_values(env_file_path)
        if not env_vars:
            logger.error(f"❌ No variables found in {env_file_path}. Is the file empty or formatted incorrectly?")
            sys.exit(1)

        successful_uploads = 0
        total_to_upload = 0
        
        logger.info(f"🚀 Starting dynamic upload of frontend environment variables from {env_file_path}...")
        
        for env_key, value in env_vars.items():
            # Only process variables meant for the frontend build
            if env_key.startswith('NEXT_PUBLIC_'):
                total_to_upload += 1
                if not value or not value.strip():
                    logger.warning(f"⚠️  Variable {env_key} is empty, skipping.")
                    continue

                # Convert NEXT_PUBLIC_STRIPE_PUBLIC_KEY to stripe_public_key
                param_name = env_key.replace('NEXT_PUBLIC_', '').lower()
                
                # Determine if it's a secret
                param_type = 'SecureString' if self.is_sensitive(env_key) else 'String'
                
                if self.upload_parameter(param_name, value, param_type):
                    successful_uploads += 1
        
        logger.info(f"🎉 Upload complete. {successful_uploads}/{total_to_upload} variables uploaded to SSM.")

def main():
    parser = argparse.ArgumentParser(description='Upload frontend secrets to AWS SSM.')
    parser.add_argument('--environment', '-e', default='prod', choices=['dev', 'staging', 'prod'])
    parser.add_argument('--env-file', default='../.env', help='Path to frontend .env file')
    args = parser.parse_args()

    uploader = SSMSecretUploader(environment=args.environment)
    
    # Ensure the path to the .env file is correct relative to the script's location
    script_dir = os.path.dirname(__file__)
    env_file_abs_path = os.path.join(script_dir, args.env_file)
    
    uploader.upload_secrets(env_file_abs_path)

if __name__ == '__main__':
    main()
