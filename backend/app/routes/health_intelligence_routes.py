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

@health_intelligence_bp.route('/chat', methods=['POST'])
@require_auth
def health_chat():
    """Process health-related chat queries using LangGraph AI agent"""
    try:
        current_user_id = request.current_user['id']
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify(error_response(message="Query is required")), 400
        
        query = data['query']
        thread_id = data.get('thread_id')
        
        # Process health query asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                health_service.process_health_query(
                    user_id=current_user_id,
                    query=query,
                    thread_id=thread_id
                )
            )
        finally:
            loop.close()
        
        return jsonify(success_response(data=result, message="Health query processed successfully"))
        
    except Exception as e:
        return jsonify(error_response(message="Failed to process health query", error=str(e))), 500

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