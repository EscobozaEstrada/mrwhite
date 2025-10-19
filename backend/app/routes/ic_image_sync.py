"""
IC Image Sync API Routes
Handles synchronization of intelligent_chat images to gallery
"""

from flask import Blueprint, request, jsonify, current_app
from app.services.ic_image_sync_service import ICImageSyncService
from app.middleware.auth import require_auth

ic_sync_bp = Blueprint('ic_sync', __name__, url_prefix='/api/ic-sync')


@ic_sync_bp.route('/sync-images', methods=['POST'])
@require_auth
def sync_user_images():
    """
    Sync IC images to user_images table for gallery display
    
    Body:
    - limit: int (optional, default: 100) - max images to sync in one batch
    
    Returns:
    - success: bool
    - message: str
    - synced_count: int
    - skipped_count: int
    """
    try:
        user_id = request.current_user['id']
        data = request.get_json() or {}
        limit = data.get('limit', 100)
        
        # Validate limit
        if not isinstance(limit, int) or limit <= 0 or limit > 500:
            return jsonify({
                'success': False,
                'message': 'Invalid limit. Must be between 1 and 500'
            }), 400
        
        sync_service = ICImageSyncService()
        result = sync_service.sync_ic_images_to_gallery(user_id, limit)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        current_app.logger.error(f"IC image sync API error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@ic_sync_bp.route('/status', methods=['GET'])
@require_auth
def get_sync_status():
    """
    Get sync status for current user
    
    Returns:
    - success: bool
    - ic_images_total: int
    - synced_to_gallery: int
    - unsynced: int
    - sync_percentage: float
    """
    try:
        user_id = request.current_user['id']
        
        sync_service = ICImageSyncService()
        result = sync_service.get_sync_status(user_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        current_app.logger.error(f"IC sync status API error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@ic_sync_bp.route('/admin/sync-all', methods=['POST'])
@require_auth
def admin_sync_all_images():
    """
    Admin endpoint to sync IC images for all users
    
    Body:
    - batch_size: int (optional, default: 50) - batch size per user
    
    Returns:
    - success: bool
    - message: str
    - total_synced: int
    - total_skipped: int
    - processed_users: int
    """
    try:
        # Check if user is admin (you might want to implement proper admin check)
        user_id = request.current_user['id']
        
        # For now, we'll allow any authenticated user to run this
        # In production, you should add proper admin role checking
        
        data = request.get_json() or {}
        batch_size = data.get('batch_size', 50)
        
        # Validate batch size
        if not isinstance(batch_size, int) or batch_size <= 0 or batch_size > 200:
            return jsonify({
                'success': False,
                'message': 'Invalid batch_size. Must be between 1 and 200'
            }), 400
        
        sync_service = ICImageSyncService()
        result = sync_service.sync_all_users_ic_images(batch_size)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        current_app.logger.error(f"Admin IC sync API error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500
