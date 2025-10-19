from flask import Blueprint, request, jsonify
from app.middleware.auth import require_auth
import asyncio
import logging

from app.services.health_intelligence_service import HealthIntelligenceService

health_intelligence_bp = Blueprint('health_intelligence', __name__, url_prefix='/api/health-intelligence')

def success_response(data=None, message="Success"):
    """Create a success response"""
    response = {'success': True, 'message': message}
    if data is not None:
        response['data'] = data
    return response

def error_response(message="Error", error=None):
    """Create an error response"""
    response = {'success': False, 'message': message}
    if error:
        response['error'] = str(error)
    return response

health_service = HealthIntelligenceService()

@health_intelligence_bp.route('/dashboard', methods=['GET'])
@require_auth
def get_health_dashboard():
    """Get comprehensive health dashboard data"""
    try:
        current_user_id = request.current_user['id']
        dashboard_data = health_service.get_health_dashboard_data(current_user_id)
        return jsonify(success_response(data=dashboard_data, message="Health dashboard data retrieved successfully"))
    except Exception as e:
        return jsonify(error_response(message="Failed to retrieve health dashboard data", error=str(e))), 500



@health_intelligence_bp.route('/analyze', methods=['POST'])
@require_auth
def analyze_health_data():
    """Analyze user's complete health data for insights"""
    try:
        current_user_id = request.current_user['id']
        data = request.get_json()
        
        analysis_type = data.get('type', 'general')  # general, trends, recommendations
        
        # Use health service to get dashboard data which includes analysis
        dashboard_data = health_service.get_health_dashboard_data(current_user_id)
        
        return jsonify(success_response(data={
            'analysis_type': analysis_type,
            'health_summary': dashboard_data.get('summary', ''),
            'stats': dashboard_data.get('stats', {}),
            'insights': dashboard_data.get('insights', []),
            'recommendations': []  # Could be enhanced with specific recommendations
        }, message="Health data analysis completed"))
        
    except Exception as e:
        return jsonify(error_response(message="Failed to analyze health data", error=str(e))), 500 