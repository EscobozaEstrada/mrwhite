import os
import uuid
import tempfile
from typing import Dict, Optional, Tuple
from flask import current_app
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from .s3_handler import upload_file_to_s3
import logging

# Set up logging
logger = logging.getLogger(__name__)

def process_audio_file(file: FileStorage, user_id: int, user_description: Optional[str] = None) -> Dict[str, any]:
    """
    Process an audio file and upload it to S3
    
    Args:
        file: The audio file to process
        user_id: The ID of the user who uploaded the file
        user_description: Optional description of the audio file
        
    Returns:
        Dict with file information including S3 URL
    """
    try:
        # Generate a unique filename to prevent collisions
        original_filename = secure_filename(file.filename)
        file_extension = os.path.splitext(original_filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Create S3 key with user folder structure
        s3_key = f"users/{user_id}/audio/{unique_filename}"
        
        # Save file to temporary location
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, unique_filename)
        
        try:
            # Save the file temporarily
            file.save(temp_path)
            
            # Upload to S3
            success, message, s3_url = upload_file_to_s3(temp_path, s3_key, file.content_type)
            
            if not success:
                logger.error(f"Failed to upload audio to S3: {message}")
                raise Exception(f"S3 upload failed: {message}")
                
            logger.info(f"Audio file uploaded successfully to S3: {s3_url}")
            
            # Create result object
            result = {
                'filename': unique_filename,
                'original_filename': original_filename,
                'file_type': file.content_type,
                'type': 'audio',
                'success': True,
                'name': original_filename,
                'url': s3_url,
                's3_key': s3_key
            }
            
            # Add description if provided
            if user_description:
                result['description'] = user_description
                
            return result
            
        finally:
            # Clean up temporary files
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                os.rmdir(temp_dir)
            except Exception as e:
                logger.warning(f"Error cleaning up temp files: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error processing audio file: {str(e)}")
        return {
            'filename': file.filename,
            'file_type': getattr(file, 'content_type', 'unknown'),
            'type': 'audio',
            'success': False,
            'error': str(e),
            'name': file.filename
        } 