from flask import Blueprint, request, jsonify, current_app, g
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date
from typing import Dict, Any
import logging

from app.services.health_service import HealthService
from app.models.health_models import HealthRecordType, ReminderType, HealthReminder, ReminderStatus
from app.utils.jwt import decode_token
from app import db

logger = logging.getLogger(__name__)

# Create blueprint
health_bp = Blueprint('health', __name__, url_prefix='/api/health')

def get_health_service():
    """Get health service instance with database session"""
    return HealthService(db.session)

def validate_required_fields(data, required_fields):
    """Simple validation for required fields"""
    for field in required_fields:
        if field not in data or data[field] is None or str(data[field]).strip() == '':
            return f'Field {field} is required'
    return None

def cookie_auth_required(f):
    """Decorator for cookie-based authentication"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.cookies.get('token')
        if not token:
            return jsonify({'error': 'Authentication required'}), 401
        
        try:
            user_data = decode_token(token)
            g.user_id = user_data.get('id')
            g.user_email = user_data.get('email')
        except:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

# ==================== HEALTH RECORD ENDPOINTS ====================

@health_bp.route('/records', methods=['POST'])
@jwt_required()
def create_health_record():
    """
    Create a new health record
    
    Expected JSON:
    {
        "record_type": "vaccination|vet_visit|medication|allergy|surgery|injury|checkup|emergency|dental|grooming",
        "title": "string",
        "description": "string (optional)",
        "record_date": "YYYY-MM-DD",
        "pet_id": int (optional),
        "veterinarian_name": "string (optional)",
        "clinic_name": "string (optional)",
        "clinic_address": "string (optional)",
        "cost": float (optional),
        "insurance_covered": boolean (optional),
        "insurance_amount": float (optional),
        "notes": "string (optional)",
        "tags": "string (optional)",
        "vaccination_details": {...} (optional, for vaccination records),
        "medication_details": {...} (optional, for medication records)
    }
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['record_type', 'title', 'record_date']
        validation_error = validate_required_fields(data, required_fields)
        if validation_error:
            return jsonify({'error': validation_error}), 400
        
        # Validate record type
        try:
            HealthRecordType(data['record_type'])
        except ValueError:
            return jsonify({'error': 'Invalid record type'}), 400
        
        # Validate date format
        try:
            data['record_date'] = datetime.strptime(data['record_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Create health record
        health_service = get_health_service()
        record = health_service.create_health_record(user_id, data)
        
        return jsonify({
            'message': 'Health record created successfully',
            'record': {
                'id': record.id,
                'record_type': record.record_type.value,
                'title': record.title,
                'record_date': record.record_date.isoformat(),
                'created_at': record.created_at.isoformat()
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating health record: {str(e)}")
        return jsonify({'error': 'Failed to create health record'}), 500

@health_bp.route('/records', methods=['GET'])
@jwt_required()
def get_health_records():
    """
    Get health records with filtering options
    
    Query parameters:
    - pet_id: int (optional)
    - record_type: string (optional)
    - start_date: YYYY-MM-DD (optional)
    - end_date: YYYY-MM-DD (optional)
    - limit: int (optional, default 100)
    - search: string (optional)
    """
    try:
        user_id = get_jwt_identity()
        
        # Get query parameters
        pet_id = request.args.get('pet_id', type=int)
        record_type = request.args.get('record_type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = request.args.get('limit', default=100, type=int)
        search_query = request.args.get('search')
        
        # Validate dates if provided
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid start_date format. Use YYYY-MM-DD'}), 400
        
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid end_date format. Use YYYY-MM-DD'}), 400
        
        health_service = get_health_service()
        
        # Use search if provided, otherwise get filtered records
        if search_query:
            records = health_service.search_health_records(user_id, search_query, pet_id)
        else:
            records = health_service.get_health_records(
                user_id=user_id,
                pet_id=pet_id,
                record_type=record_type,
                start_date=start_date,
                end_date=end_date,
                limit=limit
            )
        
        # Format response
        records_data = []
        for record in records:
            record_data = {
                'id': record.id,
                'pet_id': record.pet_id,
                'record_type': record.record_type.value,
                'title': record.title,
                'description': record.description,
                'record_date': record.record_date.isoformat(),
                'veterinarian_name': record.veterinarian_name,
                'clinic_name': record.clinic_name,
                'cost': float(record.cost) if record.cost else None,
                'insurance_covered': record.insurance_covered,
                'insurance_amount': float(record.insurance_amount) if record.insurance_amount else None,
                'notes': record.notes,
                'tags': record.tags,
                'created_at': record.created_at.isoformat(),
                'updated_at': record.updated_at.isoformat()
            }
            
            # Add vaccination details if available
            if record.vaccinations:
                record_data['vaccination_details'] = [{
                    'vaccine_name': v.vaccine_name,
                    'vaccine_type': v.vaccine_type,
                    'administration_date': v.administration_date.isoformat(),
                    'next_due_date': v.next_due_date.isoformat() if v.next_due_date else None,
                    'adverse_reactions': v.adverse_reactions
                } for v in record.vaccinations]
            
            # Add medication details if available
            if record.medications:
                record_data['medication_details'] = [{
                    'medication_name': m.medication_name,
                    'dosage': m.dosage,
                    'frequency': m.frequency,
                    'start_date': m.start_date.isoformat(),
                    'end_date': m.end_date.isoformat() if m.end_date else None,
                    'active': m.active,
                    'prescribed_by': m.prescribed_by,
                    'reason': m.reason
                } for m in record.medications]
            
            records_data.append(record_data)
        
        return jsonify({
            'records': records_data,
            'total': len(records_data)
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving health records: {str(e)}")
        return jsonify({'error': 'Failed to retrieve health records'}), 500

@health_bp.route('/records/<int:record_id>', methods=['GET'])
@jwt_required()
def get_health_record(record_id):
    """Get a specific health record by ID"""
    try:
        user_id = get_jwt_identity()
        health_service = get_health_service()
        
        record = health_service.get_health_record_by_id(user_id, record_id)
        if not record:
            return jsonify({'error': 'Health record not found'}), 404
        
        # Format response (similar to get_health_records)
        record_data = {
            'id': record.id,
            'pet_id': record.pet_id,
            'record_type': record.record_type.value,
            'title': record.title,
            'description': record.description,
            'record_date': record.record_date.isoformat(),
            'veterinarian_name': record.veterinarian_name,
            'clinic_name': record.clinic_name,
            'clinic_address': record.clinic_address,
            'cost': float(record.cost) if record.cost else None,
            'insurance_covered': record.insurance_covered,
            'insurance_amount': float(record.insurance_amount) if record.insurance_amount else None,
            'notes': record.notes,
            'tags': record.tags,
            'created_at': record.created_at.isoformat(),
            'updated_at': record.updated_at.isoformat()
        }
        
        return jsonify({'record': record_data}), 200
        
    except Exception as e:
        logger.error(f"Error retrieving health record {record_id}: {str(e)}")
        return jsonify({'error': 'Failed to retrieve health record'}), 500

@health_bp.route('/records/<int:record_id>', methods=['PUT'])
@jwt_required()
def update_health_record(record_id):
    """Update a health record"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        health_service = get_health_service()
        record = health_service.update_health_record(user_id, record_id, data)
        
        if not record:
            return jsonify({'error': 'Health record not found'}), 404
        
        return jsonify({
            'message': 'Health record updated successfully',
            'record': {
                'id': record.id,
                'title': record.title,
                'updated_at': record.updated_at.isoformat()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating health record {record_id}: {str(e)}")
        return jsonify({'error': 'Failed to update health record'}), 500

@health_bp.route('/records/<int:record_id>', methods=['DELETE'])
@jwt_required()
def delete_health_record(record_id):
    """Delete a health record"""
    try:
        user_id = get_jwt_identity()
        health_service = get_health_service()
        
        success = health_service.delete_health_record(user_id, record_id)
        if not success:
            return jsonify({'error': 'Health record not found'}), 404
        
        return jsonify({'message': 'Health record deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error deleting health record {record_id}: {str(e)}")
        return jsonify({'error': 'Failed to delete health record'}), 500

# ==================== REMINDER ENDPOINTS ====================

@health_bp.route('/reminders', methods=['GET'])
@cookie_auth_required
def get_reminders_cookie():
    """Get reminders with cookie authentication"""
    try:
        user_id = g.user_id
        pet_id = request.args.get('pet_id', type=int)
        
        health_service = get_health_service()
        reminders = health_service.get_all_reminders(user_id, pet_id)
        
        reminders_data = [{
            'id': r.id,
            'pet_id': r.pet_id,
            'reminder_type': r.reminder_type.value,
            'title': r.title,
            'description': r.description,
            'due_date': r.due_date.isoformat(),
            'due_time': r.due_time.strftime('%H:%M') if r.due_time else None,
            'reminder_date': r.reminder_date.isoformat() if r.reminder_date else None,
            'reminder_time': r.reminder_time.strftime('%H:%M') if r.reminder_time else None,
            'status': r.status.value,
            'days_before_reminder': r.days_before_reminder if hasattr(r, 'days_before_reminder') else None,
            'send_email': r.send_email,
            'send_push': r.send_push,
            'created_at': r.created_at.isoformat()
        } for r in reminders]
        
        return jsonify({
            'reminders': reminders_data,
            'total': len(reminders_data)
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving reminders: {str(e)}")
        return jsonify({'error': 'Failed to retrieve reminders'}), 500

@health_bp.route('/reminders', methods=['POST'])
@cookie_auth_required
def create_reminder_cookie():
    """Create a new health reminder with cookie authentication"""
    try:
        user_id = g.user_id
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['reminder_type', 'title', 'due_date']
        validation_error = validate_required_fields(data, required_fields)
        if validation_error:
            return jsonify({'error': validation_error}), 400
        
        # Validate reminder type
        try:
            ReminderType(data['reminder_type'])
        except ValueError:
            return jsonify({'error': 'Invalid reminder type'}), 400
        
        # Validate dates
        try:
            data['due_date'] = datetime.strptime(data['due_date'], '%Y-%m-%d').date()
            if 'reminder_date' in data and data['reminder_date']:
                data['reminder_date'] = datetime.strptime(data['reminder_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        health_service = get_health_service()
        reminder = health_service.create_reminder(user_id, data)
        
        return jsonify({
            'message': 'Reminder created successfully',
            'reminder': {
                'id': reminder.id,
                'reminder_type': reminder.reminder_type.value,
                'title': reminder.title,
                'due_date': reminder.due_date.isoformat(),
                'reminder_date': reminder.reminder_date.isoformat() if reminder.reminder_date else None,
                'created_at': reminder.created_at.isoformat()
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating reminder: {str(e)}")
        return jsonify({'error': 'Failed to create reminder'}), 500

@health_bp.route('/reminders/<int:reminder_id>/complete', methods=['POST'])
@cookie_auth_required
def complete_reminder_cookie(reminder_id):
    """Mark a reminder as completed with cookie authentication"""
    try:
        user_id = g.user_id
        health_service = get_health_service()
        
        success = health_service.complete_reminder(user_id, reminder_id)
        if not success:
            return jsonify({'error': 'Reminder not found'}), 404
        
        return jsonify({'message': 'Reminder completed successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error completing reminder {reminder_id}: {str(e)}")
        return jsonify({'error': 'Failed to complete reminder'}), 500

@health_bp.route('/reminders/<int:reminder_id>', methods=['DELETE'])
@cookie_auth_required
def delete_reminder_cookie(reminder_id):
    """Delete a reminder with cookie authentication"""
    try:
        user_id = g.user_id
        health_service = get_health_service()
        
        logger.info(f"🗑️  Attempting to delete reminder {reminder_id} for user {user_id}")
        
        success = health_service.delete_reminder(user_id, reminder_id)
        if not success:
            logger.warning(f"❌ Reminder {reminder_id} not found for user {user_id}")
            return jsonify({'error': 'Reminder not found'}), 404
        
        logger.info(f"✅ Successfully deleted reminder {reminder_id} for user {user_id}")
        return jsonify({'message': 'Reminder deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"❌ DETAILED ERROR deleting reminder {reminder_id}: {str(e)}")
        logger.error(f"❌ Error type: {type(e).__name__}")
        logger.error(f"❌ Error args: {e.args}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Failed to delete reminder', 'details': str(e)}), 500

@health_bp.route('/reminders/overdue', methods=['GET'])
@jwt_required()
def get_overdue_reminders():
    """Get overdue reminders for the user"""
    try:
        user_id = get_jwt_identity()
        health_service = get_health_service()
        
        reminders = health_service.get_overdue_reminders(user_id)
        
        reminders_data = [{
            'id': r.id,
            'pet_id': r.pet_id,
            'reminder_type': r.reminder_type.value,
            'title': r.title,
            'due_date': r.due_date.isoformat(),
            'days_overdue': (date.today() - r.due_date).days
        } for r in reminders]
        
        return jsonify({
            'overdue_reminders': reminders_data,
            'total': len(reminders_data)
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving overdue reminders: {str(e)}")
        return jsonify({'error': 'Failed to retrieve overdue reminders'}), 500

# ==================== AI INSIGHTS ENDPOINTS ====================

@health_bp.route('/insights/generate', methods=['POST'])
@jwt_required()
def generate_insights():
    """Generate AI health insights"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        pet_id = data.get('pet_id')
        
        health_service = get_health_service()
        insights = health_service.generate_health_insights(user_id, pet_id)
        
        insights_data = [{
            'id': i.id,
            'insight_type': i.insight_type,
            'title': i.title,
            'content': i.content,
            'confidence_score': float(i.confidence_score) if i.confidence_score else None,
            'created_at': i.created_at.isoformat()
        } for i in insights]
        
        return jsonify({
            'message': 'Health insights generated successfully',
            'insights': insights_data,
            'total': len(insights_data)
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating insights: {str(e)}")
        return jsonify({'error': 'Failed to generate insights'}), 500

@health_bp.route('/insights', methods=['GET'])
@jwt_required()
def get_insights():
    """Get existing health insights"""
    try:
        user_id = get_jwt_identity()
        pet_id = request.args.get('pet_id', type=int)
        
        health_service = get_health_service()
        insights = health_service.get_health_insights(user_id, pet_id)
        
        insights_data = [{
            'id': i.id,
            'pet_id': i.pet_id,
            'insight_type': i.insight_type,
            'title': i.title,
            'content': i.content,
            'confidence_score': float(i.confidence_score) if i.confidence_score else None,
            'shown_to_user': i.shown_to_user,
            'user_feedback': i.user_feedback,
            'created_at': i.created_at.isoformat()
        } for i in insights]
        
        return jsonify({
            'insights': insights_data,
            'total': len(insights_data)
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving insights: {str(e)}")
        return jsonify({'error': 'Failed to retrieve insights'}), 500

# ==================== ANALYTICS ENDPOINTS ====================

@health_bp.route('/summary', methods=['GET'])
@cookie_auth_required
def get_health_summary_cookie():
    """Get comprehensive health summary for dashboard with cookie authentication"""
    try:
        user_id = g.user_id
        pet_id = request.args.get('pet_id', type=int)
        
        health_service = get_health_service()
        
        # Get reminders for summary calculation
        reminders = health_service.get_all_reminders(user_id, pet_id)
        
        summary = {
            'total_reminders': len(reminders),
            'overdue_reminders': len([r for r in reminders if r.due_date < date.today() and r.status.value == 'pending']),
            'upcoming_reminders': len([r for r in reminders if r.status.value == 'pending']),
            'completed_reminders': len([r for r in reminders if r.status.value == 'completed']),
            'reminder_types': {}
        }
        
        # Count by type
        for reminder in reminders:
            reminder_type = reminder.reminder_type.value
            summary['reminder_types'][reminder_type] = summary['reminder_types'].get(reminder_type, 0) + 1
        
        return jsonify({'summary': summary}), 200
        
    except Exception as e:
        logger.error(f"Error retrieving health summary: {str(e)}")
        return jsonify({'error': 'Failed to retrieve health summary'}), 500

# ==================== HEALTH CHAT ENDPOINTS ====================



# ==================== ERROR HANDLERS ====================

@health_bp.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400

@health_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@health_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500 

# ==================== JWT-BASED ENDPOINTS (for API usage) ====================

@health_bp.route('/api/reminders', methods=['POST'])
@jwt_required()
def create_reminder_jwt():
    """Create a new health reminder with JWT authentication (API)"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['reminder_type', 'title', 'due_date']
        validation_error = validate_required_fields(data, required_fields)
        if validation_error:
            return jsonify({'error': validation_error}), 400
        
        # Validate reminder type
        try:
            ReminderType(data['reminder_type'])
        except ValueError:
            return jsonify({'error': 'Invalid reminder type'}), 400
        
        # Validate dates
        try:
            data['due_date'] = datetime.strptime(data['due_date'], '%Y-%m-%d').date()
            if 'reminder_date' in data and data['reminder_date']:
                data['reminder_date'] = datetime.strptime(data['reminder_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        health_service = get_health_service()
        reminder = health_service.create_reminder(user_id, data)
        
        return jsonify({
            'message': 'Reminder created successfully',
            'reminder': {
                'id': reminder.id,
                'reminder_type': reminder.reminder_type.value,
                'title': reminder.title,
                'due_date': reminder.due_date.isoformat(),
                'reminder_date': reminder.reminder_date.isoformat() if reminder.reminder_date else None,
                'created_at': reminder.created_at.isoformat()
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating reminder: {str(e)}")
        return jsonify({'error': 'Failed to create reminder'}), 500

@health_bp.route('/api/reminders', methods=['GET'])
@jwt_required()
def get_reminders_jwt():
    """Get reminders with JWT authentication (API)"""
    try:
        user_id = get_jwt_identity()
        pet_id = request.args.get('pet_id', type=int)
        
        health_service = get_health_service()
        reminders = health_service.get_all_reminders(user_id, pet_id)
        
        reminders_data = [{
            'id': r.id,
            'pet_id': r.pet_id,
            'reminder_type': r.reminder_type.value,
            'title': r.title,
            'description': r.description,
            'due_date': r.due_date.isoformat(),
            'due_time': r.due_time.strftime('%H:%M') if r.due_time else None,
            'reminder_date': r.reminder_date.isoformat() if r.reminder_date else None,
            'reminder_time': r.reminder_time.strftime('%H:%M') if r.reminder_time else None,
            'status': r.status.value,
            'days_before_reminder': r.days_before_reminder if hasattr(r, 'days_before_reminder') else None,
            'send_email': r.send_email,
            'send_push': r.send_push,
            'created_at': r.created_at.isoformat()
        } for r in reminders]
        
        return jsonify({
            'reminders': reminders_data,
            'total': len(reminders_data)
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving reminders: {str(e)}")
        return jsonify({'error': 'Failed to retrieve reminders'}), 500

@health_bp.route('/test', methods=['GET'])
def test_health_blueprint():
    """Simple test route to verify health blueprint is working"""
    return jsonify({'message': 'Health blueprint is working!', 'status': 'ok'}), 200

@health_bp.route('/reminders/<int:reminder_id>', methods=['PUT'])
@cookie_auth_required
def update_reminder_cookie(reminder_id):
    """Update a reminder with cookie authentication - forwards to enhanced system"""
    try:
        user_id = g.user_id
        data = request.get_json() or {}
        
        # Import here to avoid circular imports
        from app.services.health_service import HealthService
        
        health_service = HealthService()
        
        # Forward to enhanced reminder system
        from app.models.health_models import HealthReminder, ReminderStatus
        
        reminder = HealthReminder.query.filter_by(id=reminder_id, user_id=user_id).first()
        if not reminder:
            return jsonify({'error': 'Reminder not found'}), 404
        
        # Update fields
        if 'title' in data:
            reminder.title = data['title']
        
        if 'description' in data:
            reminder.description = data['description']
        
        if 'status' in data:
            # If status is being updated to completed, use the completion method
            if data['status'] == 'completed':
                reminder.mark_completed(
                    completed_by='user',
                    completion_method='web_portal'
                )
            else:
                reminder.status = ReminderStatus(data['status'])
        
        if 'reminder_type' in data:
            from app.models.health_models import ReminderType
            reminder.reminder_type = ReminderType(data['reminder_type'])
        
        reminder.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Reminder updated successfully',
            'reminder': {
                'id': reminder.id,
                'title': reminder.title,
                'status': reminder.status.value,
                'updated_at': reminder.updated_at.isoformat()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating reminder {reminder_id}: {str(e)}")
        return jsonify({'error': 'Failed to update reminder'}), 500
