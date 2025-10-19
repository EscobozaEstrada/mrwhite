from flask import Blueprint, request, jsonify, g
from flask_cors import cross_origin
from app.middleware.auth import require_auth
from app.services.usage_tracking_service import UsageTrackingService
import logging

usage_bp = Blueprint('usage', __name__)

@usage_bp.route('/status', methods=['GET'])
@cross_origin(supports_credentials=True)
@require_auth
def get_usage_status():
    """Get user's current usage statistics"""
    try:
        usage_service = UsageTrackingService()
        usage_stats = usage_service.get_user_usage(g.user_id)
        
        return jsonify({
            'success': True,
            'data': usage_stats
        }), 200
        
    except Exception as e:
        logging.error(f"Error getting usage status: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@usage_bp.route('/limits', methods=['GET'])
@cross_origin(supports_credentials=True)
@require_auth
def get_usage_limits():
    """Get usage limits for free tier"""
    try:
        return jsonify({
            'success': True,
            'limits': UsageTrackingService.FREE_LIMITS
        }), 200
        
    except Exception as e:
        logging.error(f"Error getting usage limits: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500 