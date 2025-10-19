from flask import Blueprint, request, jsonify, g, current_app
from app.middleware.auth import require_auth
from werkzeug.utils import secure_filename
import os
import uuid
from app.utils.s3_handler import upload_file_to_s3

upload_bp = Blueprint('upload', __name__, url_prefix='/api/upload')

@upload_bp.route('/image', methods=['POST'])
@require_auth
def upload_image():
    """
    Upload an image file to S3
    
    Returns:
    - success: bool
    - message: str
    - url: str (S3 URL of the uploaded image)
    """
    try:
        # Get user ID from g object (set by require_auth middleware)
        user_id = g.user_id
        
        # Check if image file is present
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No image file provided'
            }), 400
        
        file = request.files['file']
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
            file_extension = os.path.splitext(secure_filename(file.filename))[1]
        else:
            file_extension = '.jpg'  # Default extension
        unique_filename = f"upload_{uuid.uuid4()}{file_extension}"
        
        # Define S3 key for the image
        s3_key = f"uploads/{user_id}/images/{unique_filename}"
        
        # Save file temporarily
        temp_folder = os.path.join(current_app.config['TEMP_FOLDER'])
        os.makedirs(temp_folder, exist_ok=True)
        temp_path = os.path.join(temp_folder, unique_filename)
        file.save(temp_path)
        
        # Upload to S3
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
        
        return jsonify({
            'success': True,
            'message': 'Image uploaded successfully',
            'url': s3_url
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error uploading image: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Internal server error: {str(e)}'
        }), 500