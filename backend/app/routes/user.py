from flask import Blueprint, request, jsonify, g, current_app
from app.models.user import User
from app import db
from app.middleware.auth import require_auth
from app.services.image_service import image_service
from werkzeug.utils import secure_filename
import os
import uuid
from app.utils.s3_handler import delete_file_from_s3

user_bp = Blueprint('user', __name__, url_prefix='/api/user')

# ... existing code ...

@user_bp.route('/upload-dog-image', methods=['POST'])
@require_auth
def upload_dog_image():
    """
    Upload a dog image for the user's profile
    
    Returns:
    - success: bool
    - message: str
    - image_url: str
    """
    try:
        # Get user ID from g object (set by require_auth middleware)
        user_id = g.user_id
        
        # Check if image file is present
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No image file provided'
            }), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': 'No file selected'
            }), 400
        
        # Validate file is an image
        if not file.content_type or not file.content_type.startswith('image/'):
            return jsonify({
                'success': False,
                'message': 'File must be an image'
            }), 400
        
        # Generate unique filename
        if file.filename:
            file_extension = os.path.splitext(file.filename)[1]
        else:
            file_extension = '.jpg'  # Default extension
        unique_filename = f"dog_profile_{uuid.uuid4()}{file_extension}"
        
        # Use image service to upload to S3
        s3_key = f"users/{user_id}/profile/dog_image/{unique_filename}"
        
        # Save file temporarily
        temp_path = f"/tmp/{unique_filename}"
        file.save(temp_path)
        
        # Upload to S3
        from app.utils.s3_handler import upload_file_to_s3
        success, message, s3_url = upload_file_to_s3(temp_path, s3_key, file.content_type)
        
        # Clean up temp file
        try:
            os.remove(temp_path)
        except:
            pass
        
        if not success:
            return jsonify({
                'success': False,
                'message': f'Failed to upload image: {message}'
            }), 500
        
        # Update user record with dog image URL
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        # Update the user's dog_image field
        user.dog_image = s3_url
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Dog image uploaded successfully',
            'image_url': s3_url
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error uploading dog image: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Internal server error: {str(e)}'
        }), 500

@user_bp.route('/remove-dog-image', methods=['DELETE'])
@require_auth
def remove_dog_image():
    """
    Remove the dog image from the user's profile
    
    Returns:
    - success: bool
    - message: str
    """
    try:
        user_id = g.user_id
        
        # Get user record
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        # Check if user has a dog image
        if not user.dog_image:
            return jsonify({
                'success': False,
                'message': 'No dog image to remove'
            }), 400
        
        # Extract S3 key from URL
        s3_url = user.dog_image
        
        # Try to delete from S3 if it's an S3 URL
        if 's3' in s3_url.lower() or 'amazonaws' in s3_url.lower():
            try:
                # Extract the S3 key from the URL
                # Assuming URL format: https://bucket-name.s3.region.amazonaws.com/key
                # or https://s3.region.amazonaws.com/bucket-name/key
                parts = s3_url.split('/')
                s3_key = '/'.join(parts[3:]) if 's3.' in parts[2] else '/'.join(parts[4:])
                
                # Delete from S3
                delete_success = delete_file_from_s3(s3_key)
                if not delete_success:
                    current_app.logger.warning(f"Failed to delete image from S3: {s3_key}")
            except Exception as e:
                current_app.logger.warning(f"Error deleting from S3: {str(e)}")
                # Continue even if S3 deletion fails
        
        # Update user record
        user.dog_image = None
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Dog image removed successfully'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error removing dog image: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Internal server error: {str(e)}'
        }), 500 