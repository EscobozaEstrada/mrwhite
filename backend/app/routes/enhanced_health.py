"""Enhanced Health Routes for comprehensive health assessment and management"""

from flask import Blueprint, request, jsonify
from app.middleware.auth import require_auth
from app.middleware.subscription import premium_required
from app.middleware.validation import validate_json_content
import asyncio
import logging
from datetime import datetime, timedelta

from app.services.enhanced_health_intelligence_service import EnhancedHealthIntelligenceService
from app.services.care_archive_service import CareArchiveService
from app.models.care_record import CareRecord

enhanced_health_bp = Blueprint('enhanced_health', __name__, url_prefix='/api/enhanced-health')
health_service = EnhancedHealthIntelligenceService()
care_service = CareArchiveService()

def success_response(data=None, message="Success"):
    return {'success': True, 'message': message, 'data': data}

def error_response(message="Error", error=None):
    response = {'success': False, 'message': message}
    if error: response['error'] = str(error)
    return response

@enhanced_health_bp.route('/assessment/<pet_name>', methods=['GET'])
@require_auth
def get_health_assessment(pet_name):
    """Get comprehensive health assessment for a specific pet"""
    try:
        user_id = request.current_user['id']
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            assessment = loop.run_until_complete(
                health_service.comprehensive_health_assessment(user_id, pet_name)
            )
        finally:
            loop.close()
        
        return jsonify(success_response(
            data=assessment.dict(),
            message=f"Health assessment completed for {pet_name}"
        ))
    except Exception as e:
        logging.error(f"Health assessment error: {str(e)}")
        return jsonify(error_response("Assessment failed", str(e))), 500

@enhanced_health_bp.route('/emergency-triage', methods=['POST'])
@require_auth
@validate_json_content
def emergency_triage():
    """Emergency health triage with pet context"""
    try:
        user_id = request.current_user['id']
        data = request.get_json()
        
        if 'query' not in data:
            return jsonify(error_response("Emergency query required")), 400
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                health_service.emergency_health_triage(
                    user_id, data['query'], data.get('pet_name')
                )
            )
        finally:
            loop.close()
        
        return jsonify(success_response(data=result, message="Emergency triage completed"))
    except Exception as e:
        logging.error(f"Emergency triage error: {str(e)}")
        return jsonify(error_response("Triage failed", str(e))), 500

@enhanced_health_bp.route('/pets', methods=['GET'])
@require_auth
def get_user_pets():
    """Get user's pets with basic health information"""
    try:
        user_id = request.current_user['id']
        pets = CareRecord.query.filter_by(user_id=user_id, is_active=True)\
                              .with_entities(CareRecord.pet_name)\
                              .distinct().all()
        
        pets_data = []
        for pet in pets:
            if pet.pet_name:
                latest = CareRecord.query.filter_by(
                    user_id=user_id, pet_name=pet.pet_name, is_active=True
                ).order_by(CareRecord.date_occurred.desc()).first()
                
                if latest:
                    pets_data.append({
                        'pet_name': latest.pet_name,
                        'breed': latest.pet_breed,
                        'age_months': latest.pet_age,
                        'weight_kg': latest.pet_weight,
                        'last_visit': latest.date_occurred.isoformat(),
                        'record_count': CareRecord.query.filter_by(
                            user_id=user_id, pet_name=pet.pet_name, is_active=True
                        ).count()
                    })
        
        return jsonify(success_response(
            data={'pets': pets_data},
            message=f"Found {len(pets_data)} pet(s)"
        ))
    except Exception as e:
        logging.error(f"Get pets error: {str(e)}")
        return jsonify(error_response("Failed to get pets", str(e))), 500

@enhanced_health_bp.route('/health-score/<pet_name>', methods=['GET'])
@require_auth
def get_health_score(pet_name):
    """Get health risk score for a pet"""
    try:
        user_id = request.current_user['id']
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            assessment = loop.run_until_complete(
                health_service.comprehensive_health_assessment(user_id, pet_name)
            )
        finally:
            loop.close()
        
        score_data = {
            'pet_name': assessment.pet_name,
            'overall_risk': assessment.overall_risk.value,
            'risk_score': assessment.risk_score,
            'interpretation': _get_score_interpretation(assessment.risk_score),
            'key_concerns': assessment.key_concerns[:3],
            'urgent_alerts': len([a for a in assessment.alerts if a.priority >= 4])
        }
        
        return jsonify(success_response(data=score_data, message="Health score calculated"))
    except Exception as e:
        logging.error(f"Health score error: {str(e)}")
        return jsonify(error_response("Score calculation failed", str(e))), 500

@enhanced_health_bp.route('/care-record', methods=['POST'])
@require_auth
@premium_required
@validate_json_content
def create_enhanced_care_record():
    """Create care record with enhanced health tracking"""
    try:
        user_id = request.current_user['id']
        data = request.get_json()
        
        # Validate required fields
        required = ['title', 'category', 'date_occurred']
        for field in required:
            if field not in data:
                return jsonify(error_response(f'Missing field: {field}')), 400
        
        # Parse dates
        try:
            date_occurred = datetime.fromisoformat(data['date_occurred'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify(error_response('Invalid date format')), 400
        
        reminder_date = None
        if data.get('reminder_date'):
            try:
                reminder_date = datetime.fromisoformat(data['reminder_date'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify(error_response('Invalid reminder date')), 400
        
        # Create care record
        success, message, care_record = care_service.create_care_record(
            user_id=user_id,
            title=data['title'],
            category=data['category'],
            date_occurred=date_occurred,
            description=data.get('description'),
            metadata=data.get('metadata', {}),
            reminder_date=reminder_date
        )
        
        if success and care_record:
            # Update enhanced fields
            care_record.pet_name = data.get('pet_name')
            care_record.pet_breed = data.get('pet_breed')
            care_record.pet_age = data.get('pet_age')
            care_record.pet_weight = data.get('pet_weight')
            care_record.severity_level = data.get('severity_level')
            care_record.symptoms = data.get('symptoms')
            care_record.medications = data.get('medications')
            care_record.follow_up_required = data.get('follow_up_required', False)
            care_record.health_tags = data.get('health_tags')
            
            from app import db
            db.session.commit()
            
            return jsonify(success_response(
                data=care_record.to_dict(),
                message="Enhanced care record created"
            )), 201
        else:
            return jsonify(error_response(message)), 400
            
    except Exception as e:
        logging.error(f"Create care record error: {str(e)}")
        return jsonify(error_response("Record creation failed", str(e))), 500

def _get_score_interpretation(risk_score: float) -> str:
    """Get human-readable risk score interpretation"""
    if risk_score >= 70:
        return "High risk - requires immediate attention"
    elif risk_score >= 50:
        return "Moderate risk - schedule vet checkup soon"
    elif risk_score >= 25:
        return "Low-moderate risk - routine monitoring recommended"
    else:
        return "Low risk - maintain current care routine" 