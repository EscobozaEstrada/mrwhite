"""
Firebase Service Account Helper

This module provides a helper function to get Firebase service account credentials
from either SSM Parameter Store or a local JSON file, with automatic fallback.
"""

import os
import json
import tempfile
import logging
from typing import Optional, Dict, Any
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

logger = logging.getLogger(__name__)

def get_firebase_service_account(environment: str = None) -> Optional[str]:
    """
    Get Firebase service account credentials, trying SSM first, then local file
    
    Args:
        environment: Environment name (dev, staging, prod) 
        
    Returns:
        Path to Firebase service account JSON file (either temporary or local)
        Returns None if no credentials found
    """
    if environment is None:
        environment = os.getenv('ENVIRONMENT', 'dev')
    
    organization = os.getenv('ORGANIZATION', 'monetizespirit')
    project = os.getenv('PROJECT_NAME', 'mrwhite')
    
    # Try to get from SSM Parameter Store first
    try:
        ssm_client = boto3.client('ssm')
        parameter_name = f"/{organization}/{project}/{environment}/firebase_service_account_json"
        
        response = ssm_client.get_parameter(
            Name=parameter_name,
            WithDecryption=True
        )
        
        # Parse the JSON from SSM
        firebase_config = json.loads(response['Parameter']['Value'])
        
        # Create a temporary file with the JSON content
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(firebase_config, temp_file, indent=2)
        temp_file.close()
        
        logger.info(f"✅ Firebase service account loaded from SSM Parameter Store")
        return temp_file.name
        
    except NoCredentialsError:
        logger.info("⚠️  AWS credentials not found, falling back to local file")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ParameterNotFound':
            logger.info("⚠️  Firebase service account not found in SSM, falling back to local file")
        else:
            logger.warning(f"⚠️  Error accessing SSM parameter: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in SSM parameter: {e}")
    except Exception as e:
        logger.warning(f"⚠️  Unexpected error accessing SSM: {e}")
    
    # Fallback to local file
    local_paths = [
        os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH'),
        '/home/danae/development/mrwhite/Mr-White-Project/backend/firebase-service-account.json',
        'firebase-service-account.json',
        os.path.join(os.path.dirname(__file__), '..', 'firebase-service-account.json')
    ]
    
    for path in local_paths:
        if path and os.path.exists(path):
            logger.info(f"✅ Firebase service account loaded from local file: {path}")
            return path
    
    logger.error("❌ Firebase service account not found in SSM or local file system")
    return None

def get_firebase_config_dict(environment: str = None) -> Optional[Dict[str, Any]]:
    """
    Get Firebase service account configuration as a dictionary
    
    Args:
        environment: Environment name (dev, staging, prod)
        
    Returns:
        Firebase service account configuration dictionary or None
    """
    service_account_path = get_firebase_service_account(environment)
    
    if service_account_path:
        try:
            with open(service_account_path, 'r') as f:
                config = json.load(f)
            
            # Clean up temporary file if it was created from SSM
            if service_account_path.startswith(tempfile.gettempdir()):
                os.unlink(service_account_path)
            
            return config
        except Exception as e:
            logger.error(f"❌ Error reading Firebase service account file: {e}")
            
            # Clean up temporary file if it was created from SSM
            if service_account_path.startswith(tempfile.gettempdir()):
                try:
                    os.unlink(service_account_path)
                except:
                    pass
    
    return None

# Convenience function for backward compatibility
def get_firebase_credentials(environment: str = None) -> Optional[str]:
    """Alias for get_firebase_service_account for backward compatibility"""
    return get_firebase_service_account(environment)