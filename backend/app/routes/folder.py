"""
Folder API Routes for Gallery Folder Management

This module provides API endpoints for:
- Creating, updating, and deleting folders
- Adding and removing images from folders
- Listing folders and their contents
"""

from flask import Blueprint, request, jsonify, current_app
from app.middleware.auth import require_auth
from app.middleware.validation import validate_json_content
from app.models.folder import ImageFolder
from app.models.folder_image import FolderImage
from app.models.image import UserImage
from app import db
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from functools import wraps

folder_bp = Blueprint('folder', __name__, url_prefix='/api/folder')

# Custom JSON validation for folder routes
def validate_folder_json(required_fields):
    """Custom decorator to validate JSON request content with required fields"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Skip validation for OPTIONS requests
            if request.method == 'OPTIONS':
                return f(*args, **kwargs)
            
            # Check if request has JSON content
            if not request.is_json:
                return jsonify({'success': False, 'message': 'Request must contain JSON data'}), 400
            
            try:
                data = request.get_json()
                if data is None:
                    return jsonify({'success': False, 'message': 'Invalid JSON data'}), 400
                
                # Validate required fields
                for field in required_fields:
                    if field not in data or data[field] is None or data[field] == "":
                        return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
            except Exception as e:
                return jsonify({'success': False, 'message': f'Failed to parse JSON: {str(e)}'}), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@folder_bp.route('/list', methods=['GET'])
@require_auth
def list_folders():
    """
    List all folders for the current user
    
    Returns:
    - success: bool
    - folders: list of folder objects
    """
    try:
        user_id = request.current_user['id']
        
        # Get all folders for the user
        folders = ImageFolder.get_user_folders(user_id)
        folder_list = []
        
        for folder in folders:
            folder_data = folder.to_dict()
            # Add image count to each folder
            image_count = FolderImage.get_folder_image_count(folder.id)
            folder_data['image_count'] = image_count
            folder_list.append(folder_data)
        
        return jsonify({
            'success': True,
            'folders': folder_list
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error listing folders: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500

@folder_bp.route('/create', methods=['POST'])
@require_auth
@validate_folder_json(['name'])
def create_folder():
    """
    Create a new folder
    
    JSON Body:
    - name: str (required)
    - description: str (optional)
    
    Returns:
    - success: bool
    - folder: folder object
    """
    try:
        user_id = request.current_user['id']
        data = request.get_json()
        
        name = data.get('name')
        description = data.get('description', '')
        
        # Create new folder
        folder = ImageFolder(
            user_id=user_id,
            name=name,
            description=description
        )
        
        # Get highest display_order and increment
        highest_order = db.session.query(db.func.max(ImageFolder.display_order))\
            .filter(ImageFolder.user_id == user_id).scalar() or 0
        folder.display_order = highest_order + 1
        
        db.session.add(folder)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'folder': folder.to_dict(),
            'message': 'Folder created successfully'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating folder: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to create folder'
        }), 500

@folder_bp.route('/<int:folder_id>', methods=['GET'])
@require_auth
def get_folder(folder_id):
    """
    Get folder details and images
    
    Returns:
    - success: bool
    - folder: folder details
    - images: list of images in the folder
    """
    try:
        user_id = request.current_user['id']
        
        # Get folder
        folder = ImageFolder.query.filter_by(id=folder_id, user_id=user_id, is_deleted=False).first()
        if not folder:
            return jsonify({
                'success': False,
                'message': 'Folder not found'
            }), 404
        
        # Get images in folder
        folder_images = FolderImage.get_folder_images(folder_id)
        images = []
        
        for folder_image in folder_images:
            image = UserImage.query.filter_by(id=folder_image.image_id, is_deleted=False).first()
            if image:
                image_data = image.to_gallery_dict()
                # Override display_order with folder-specific order
                image_data['display_order'] = folder_image.display_order
                images.append(image_data)
        
        return jsonify({
            'success': True,
            'folder': folder.to_dict(),
            'images': images
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting folder: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500

@folder_bp.route('/<int:folder_id>', methods=['PUT'])
@require_auth
def update_folder(folder_id):
    """
    Update folder details
    
    JSON Body:
    - name: str (optional)
    - description: str (optional)
    
    Returns:
    - success: bool
    - folder: updated folder object
    """
    try:
        user_id = request.current_user['id']
        data = request.get_json()
        
        # Get folder
        folder = ImageFolder.query.filter_by(id=folder_id, user_id=user_id, is_deleted=False).first()
        if not folder:
            return jsonify({
                'success': False,
                'message': 'Folder not found'
            }), 404
        
        # Update fields if provided
        if 'name' in data:
            folder.name = data['name']
        if 'description' in data:
            folder.description = data['description']
        
        folder.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'folder': folder.to_dict(),
            'message': 'Folder updated successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating folder: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to update folder'
        }), 500

@folder_bp.route('/<int:folder_id>', methods=['DELETE'])
@require_auth
def delete_folder(folder_id):
    """
    Delete a folder (soft delete)
    
    Returns:
    - success: bool
    - message: str
    """
    try:
        user_id = request.current_user['id']
        
        # Get folder
        folder = ImageFolder.query.filter_by(id=folder_id, user_id=user_id, is_deleted=False).first()
        if not folder:
            return jsonify({
                'success': False,
                'message': 'Folder not found'
            }), 404
        
        # Soft delete
        folder.is_deleted = True
        folder.deleted_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Folder deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting folder: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to delete folder'
        }), 500

@folder_bp.route('/<int:folder_id>/add-image', methods=['POST'])
@require_auth
@validate_folder_json(['image_id'])
def add_image_to_folder(folder_id):
    """
    Add an image to a folder
    
    JSON Body:
    - image_id: int (required)
    
    Returns:
    - success: bool
    - message: str
    """
    try:
        user_id = request.current_user['id']
        data = request.get_json()
        image_id = data.get('image_id')
        
        # Verify folder exists and belongs to user
        folder = ImageFolder.query.filter_by(id=folder_id, user_id=user_id, is_deleted=False).first()
        if not folder:
            return jsonify({
                'success': False,
                'message': 'Folder not found'
            }), 404
        
        # Verify image exists and belongs to user
        image = UserImage.query.filter_by(id=image_id, user_id=user_id, is_deleted=False).first()
        if not image:
            return jsonify({
                'success': False,
                'message': 'Image not found'
            }), 404
        
        # Check if image is already in folder
        existing = FolderImage.query.filter_by(folder_id=folder_id, image_id=image_id).first()
        if existing:
            return jsonify({
                'success': False,
                'message': 'Image is already in this folder'
            }), 400
        
        # Get highest display_order in folder and increment
        highest_order = db.session.query(db.func.max(FolderImage.display_order))\
            .filter(FolderImage.folder_id == folder_id).scalar() or 0
        
        # Add image to folder
        folder_image = FolderImage(
            folder_id=folder_id,
            image_id=image_id,
            display_order=highest_order + 1
        )
        
        db.session.add(folder_image)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Image added to folder successfully'
        }), 201
        
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Image is already in this folder'
        }), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding image to folder: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to add image to folder'
        }), 500

@folder_bp.route('/<int:folder_id>/remove-image/<int:image_id>', methods=['DELETE'])
@require_auth
def remove_image_from_folder(folder_id, image_id):
    """
    Remove an image from a folder
    
    Returns:
    - success: bool
    - message: str
    """
    try:
        user_id = request.current_user['id']
        
        # Verify folder exists and belongs to user
        folder = ImageFolder.query.filter_by(id=folder_id, user_id=user_id, is_deleted=False).first()
        if not folder:
            return jsonify({
                'success': False,
                'message': 'Folder not found'
            }), 404
        
        # Find the folder-image association
        folder_image = FolderImage.query.filter_by(folder_id=folder_id, image_id=image_id).first()
        if not folder_image:
            return jsonify({
                'success': False,
                'message': 'Image not found in folder'
            }), 404
        
        # Remove image from folder
        db.session.delete(folder_image)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Image removed from folder successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error removing image from folder: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to remove image from folder'
        }), 500

@folder_bp.route('/<int:folder_id>/reorder', methods=['POST'])
@require_auth
def reorder_folder_images(folder_id):
    """
    Update the order of images in a folder
    
    JSON Body:
    - imageIds: list of image IDs in the desired order
    
    Returns:
    - success: bool
    - message: str
    """
    try:
        user_id = request.current_user['id']
        data = request.get_json()
        
        if not data or 'imageIds' not in data:
            return jsonify({
                'success': False,
                'message': 'Image IDs are required'
            }), 400
        
        image_ids = data['imageIds']
        
        if not isinstance(image_ids, list) or not all(isinstance(id, int) for id in image_ids):
            return jsonify({
                'success': False,
                'message': 'Invalid image IDs format'
            }), 400
        
        # Verify folder exists and belongs to user
        folder = ImageFolder.query.filter_by(id=folder_id, user_id=user_id, is_deleted=False).first()
        if not folder:
            return jsonify({
                'success': False,
                'message': 'Folder not found'
            }), 404
        
        # Update image order
        for idx, image_id in enumerate(image_ids):
            folder_image = FolderImage.query.filter_by(folder_id=folder_id, image_id=image_id).first()
            if folder_image:
                folder_image.display_order = idx
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Images reordered successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error reordering folder images: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to reorder images'
        }), 500 