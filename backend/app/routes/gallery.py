"""
Gallery API Routes for Image Management

This module provides comprehensive API endpoints for:
- Image upload with OpenAI Vision analysis
- Gallery image listing and pagination
- Image viewing and metadata retrieval
- Image deletion and management
- Search functionality
"""

from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from app.middleware.auth import require_auth
from app.middleware.validation import validate_json_content
from app.services.image_service import image_service
from app.models.image import UserImage
import os

gallery_bp = Blueprint('gallery', __name__, url_prefix='/api/gallery')

@gallery_bp.route('/upload', methods=['POST'])
@require_auth
def upload_image():
    """
    Upload and process an image with OpenAI Vision analysis
    
    Form Data:
    - image: Image file to upload
    - conversation_id: Optional conversation ID for chat context
    - message_id: Optional message ID for chat context
    
    Returns:
    - success: bool
    - message: str
    - image: dict (image data with analysis)
    """
    try:
        user_id = request.current_user['id']
        
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
        
        # Get optional context parameters
        conversation_id = request.form.get('conversation_id')
        message_id = request.form.get('message_id')
        
        # Convert to integers if provided
        if conversation_id:
            try:
                conversation_id = int(conversation_id)
            except ValueError:
                conversation_id = None
                
        if message_id:
            try:
                message_id = int(message_id)
            except ValueError:
                message_id = None
        
        # Process image upload
        success, message, image_data = image_service.process_image_upload(
            file=file,
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'image': image_data
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Error uploading image: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500

@gallery_bp.route('/images', methods=['GET'])
@require_auth
def get_user_images():
    """
    Get user's uploaded images for gallery
    
    Query Parameters:
    - limit: int (default: 50, max: 100)
    - offset: int (default: 0)
    - search: str (optional search term)
    
    Returns:
    - success: bool
    - images: list of image objects
    - total: int (total count)
    - has_more: bool
    """
    try:
        user_id = request.current_user['id']
        
        # Get query parameters
        limit = min(int(request.args.get('limit', 50)), 100)
        offset = int(request.args.get('offset', 0))
        search_term = request.args.get('search', '').strip()
        
        # Get images based on search
        if search_term:
            images = UserImage.search_user_images(user_id, search_term, limit)
            # For search, we don't implement pagination yet, so total = len(images)
            total = len(images)
            has_more = False
            image_list = [img.to_gallery_dict() for img in images]
        else:
            # Get regular paginated images
            images = image_service.get_user_images(user_id, limit + 1, offset)  # Get one extra to check if more exist
            has_more = len(images) > limit
            if has_more:
                images = images[:limit]  # Remove the extra image
            
            image_list = images
            
            # Get total count for pagination
            total = UserImage.get_user_image_count(user_id)
        
        return jsonify({
            'success': True,
            'images': image_list,
            'total': total,
            'has_more': has_more,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting user images: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500

@gallery_bp.route('/images/<int:image_id>', methods=['GET'])
@require_auth
def get_image_details(image_id):
    """
    Get detailed information about a specific image
    
    Returns:
    - success: bool
    - image: dict (detailed image data)
    """
    try:
        user_id = request.current_user['id']
        
        image_data = image_service.get_image_by_id(user_id, image_id)
        
        if not image_data:
            return jsonify({
                'success': False,
                'message': 'Image not found'
            }), 404
        
        return jsonify({
            'success': True,
            'image': image_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting image details: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500

@gallery_bp.route('/images/<int:image_id>', methods=['DELETE'])
@require_auth
def delete_image(image_id):
    """
    Delete a user's image
    
    Returns:
    - success: bool
    - message: str
    """
    try:
        user_id = request.current_user['id']
        
        success, message = image_service.delete_image(user_id, image_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Error deleting image: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500

@gallery_bp.route('/stats', methods=['GET'])
@require_auth
def get_gallery_stats():
    """
    Get user's gallery statistics
    
    Returns:
    - success: bool
    - stats: dict (total_images, total_size, recent_uploads)
    """
    try:
        user_id = request.current_user['id']
        
        # Get total image count
        total_images = UserImage.get_user_image_count(user_id)
        
        # Get recent images (last 7 days)
        from datetime import datetime, timedelta
        from app import db
        
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_count = UserImage.query.filter(
            UserImage.user_id == user_id,
            UserImage.is_deleted == False,
            UserImage.created_at >= week_ago
        ).count()
        
        # Calculate total storage used (approximate)
        images = UserImage.query.filter_by(
            user_id=user_id,
            is_deleted=False
        ).all()
        
        total_size = 0
        for img in images:
            if img.metadata and 'file_size' in img.metadata:
                total_size += img.metadata['file_size']
        
        # Convert to MB
        total_size_mb = round(total_size / (1024 * 1024), 2)
        
        stats = {
            'total_images': total_images,
            'total_size_mb': total_size_mb,
            'recent_uploads': recent_count,
            'storage_limit_mb': 1000,  # Example limit - can be configurable
            'storage_used_percent': min(round((total_size_mb / 1000) * 100, 1), 100)
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting gallery stats: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500

@gallery_bp.route('/search', methods=['GET'])
@require_auth
def search_images():
    """
    Search user's images by description or filename
    
    Query Parameters:
    - q: str (search query)
    - limit: int (default: 20, max: 50)
    
    Returns:
    - success: bool
    - images: list of matching images
    - query: str (search query used)
    """
    try:
        user_id = request.current_user['id']
        
        search_query = request.args.get('q', '').strip()
        limit = min(int(request.args.get('limit', 20)), 50)
        
        if not search_query:
            return jsonify({
                'success': False,
                'message': 'Search query is required'
            }), 400
        
        # Search images
        images = UserImage.search_user_images(user_id, search_query, limit)
        image_list = [img.to_gallery_dict() for img in images]
        
        return jsonify({
            'success': True,
            'images': image_list,
            'query': search_query,
            'count': len(image_list)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error searching images: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500

# Utility endpoint for testing image analysis
@gallery_bp.route('/analyze-url', methods=['POST'])
@require_auth
def analyze_image_url():
    """
    Analyze an image from URL using OpenAI Vision (for testing)
    
    JSON Body:
    - image_url: str (URL of image to analyze)
    
    Returns:
    - success: bool
    - analysis: str (description from OpenAI)
    """
    try:
        user_id = request.current_user['id']
        data = request.get_json()
        
        if not data or 'image_url' not in data:
            return jsonify({
                'success': False,
                'message': 'image_url is required'
            }), 400
        
        image_url = data['image_url']
        
        # For testing purposes - analyze image from URL
        from openai import OpenAI
        import os
        
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": "Analyze this image and provide a detailed description including main subjects, setting, colors, and any notable features."
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url}
                        }
                    ]
                }
            ],
            max_tokens=300
        )
        
        analysis = response.choices[0].message.content
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'image_url': image_url
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error analyzing image URL: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Analysis failed: {str(e)}'
        }), 500 