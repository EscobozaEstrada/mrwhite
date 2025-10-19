from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
from app.middleware.auth import require_auth
from app.middleware.subscription import premium_required
from app.middleware.usage_limits import check_document_usage, check_care_record_usage
from app.services.care_archive_service import CareArchiveService

from app.middleware.validation import validate_json_content
from app.middleware.credit_middleware import require_health_credits
from app.models.conversation import Conversation
from app.models.message import Message
# Document model will be imported dynamically when needed
from app import db
import os
import json

care_archive_bp = Blueprint('care_archive', __name__)

# Services are initialized locally to avoid application context issues

@care_archive_bp.route('/upload-document', methods=['POST'])
@require_auth
@premium_required
@check_document_usage
def upload_document():
    """Upload and process a document for the care archive"""
    try:
        care_service = CareArchiveService()  # Create service locally
        user_id = request.current_user['id']
        
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        # Validate file type
        allowed_extensions = {'pdf', 'txt', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'gif'}
        file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        
        if file_extension not in allowed_extensions:
            return jsonify({
                'success': False, 
                'message': f'File type not supported. Allowed: {", ".join(allowed_extensions)}'
            }), 400
        
        # Get care record ID if provided
        care_record_id = request.form.get('care_record_id')
        if care_record_id:
            try:
                care_record_id = int(care_record_id)
            except ValueError:
                return jsonify({'success': False, 'message': 'Invalid care record ID'}), 400
        
        # Upload and process document
        success, message, document = care_service.upload_and_process_document(
            file, user_id, care_record_id
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'document': document.to_dict() if document else None
            }), 200
        else:
            return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        current_app.logger.error(f"Error uploading document: {str(e)}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@care_archive_bp.route('/create-care-record', methods=['POST'])
@require_auth
@premium_required
@check_care_record_usage
@validate_json_content
def create_care_record():
    """Create a new care record"""
    try:
        care_service = CareArchiveService()  # Create service locally
        user_id = request.current_user['id']
        data = request.json
        
        # Validate required fields
        required_fields = ['title', 'category', 'date_occurred']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
        
        # Parse date
        try:
            date_occurred = datetime.fromisoformat(data['date_occurred'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid date format'}), 400
        
        # Parse reminder date if provided
        reminder_date = None
        if data.get('reminder_date'):
            try:
                reminder_date = datetime.fromisoformat(data['reminder_date'].replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'success': False, 'message': 'Invalid reminder date format'}), 400
        
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
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'care_record': care_record.to_dict() if care_record else None
            }), 201
        else:
            return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        current_app.logger.error(f"Error creating care record: {str(e)}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@care_archive_bp.route('/care-timeline', methods=['GET'])
@require_auth
def get_care_timeline():
    """Get user's care timeline"""
    try:
        care_service = CareArchiveService()  # Create service locally
        user_id = request.current_user['id']
        limit = int(request.args.get('limit', 50))
        
        timeline = care_service.get_user_care_timeline(user_id, limit)
        
        return jsonify({
            'success': True,
            'timeline': timeline,
            'count': len(timeline)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting care timeline: {str(e)}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@care_archive_bp.route('/care-records/<category>', methods=['GET'])
@require_auth
def get_care_records_by_category(category):
    """Get care records by category"""
    try:
        care_service = CareArchiveService()  # Create service locally
        user_id = request.current_user['id']
        
        records = care_service.get_care_records_by_category(user_id, category)
        
        return jsonify({
            'success': True,
            'records': [record.to_dict() for record in records],
            'count': len(records)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting care records by category: {str(e)}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@care_archive_bp.route('/search', methods=['POST'])
@require_auth
@validate_json_content
def search_archive():
    """Search user's care archive"""
    try:
        care_service = CareArchiveService()  # Create service locally
        user_id = request.current_user['id']
        data = request.json
        
        if 'query' not in data:
            return jsonify({'success': False, 'message': 'Query is required'}), 400
        
        limit = int(data.get('limit', 10))
        results = care_service.search_user_archive(user_id, data['query'], limit)
        
        return jsonify({
            'success': True,
            'results': results,
            'total_found': results.get('total_found', 0)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error searching archive: {str(e)}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@care_archive_bp.route('/reminders', methods=['GET'])
@require_auth
def get_upcoming_reminders():
    """Get upcoming care reminders"""
    try:
        care_service = CareArchiveService()  # Create service locally
        user_id = request.current_user['id']
        days_ahead = int(request.args.get('days_ahead', 30))
        
        reminders = care_service.get_upcoming_reminders(user_id, days_ahead)
        
        return jsonify({
            'success': True,
            'reminders': [reminder.to_dict() for reminder in reminders],
            'count': len(reminders)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting reminders: {str(e)}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@care_archive_bp.route('/knowledge-base-stats', methods=['GET'])
@require_auth
def get_knowledge_base_stats():
    """Get user's knowledge base statistics"""
    try:
        care_service = CareArchiveService()  # Create service locally
        user_id = request.current_user['id']
        
        stats = care_service.get_knowledge_base_stats(user_id)
        
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting knowledge base stats: {str(e)}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@care_archive_bp.route('/delete-document/<int:document_id>', methods=['DELETE'])
@require_auth
def delete_document(document_id):
    """Delete a document"""
    try:
        care_service = CareArchiveService()  # Create service locally
        user_id = request.current_user['id']
        
        success, message = care_service.delete_document(user_id, document_id)
        
        if success:
            return jsonify({'success': True, 'message': message}), 200
        else:
            return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        current_app.logger.error(f"Error deleting document: {str(e)}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


@care_archive_bp.route('/conversation/<int:conversation_id>/context', methods=['GET'])
@require_auth
@premium_required
def get_conversation_context(conversation_id):
    """Get conversation with enhanced context"""
    try:
        from app.services.care_archive_service import CareArchiveService
        care_service = CareArchiveService()
        user_id = request.current_user['id']
        
        # Get conversation data using care archive service
        conversation_data = care_service.get_conversation_summary(user_id, conversation_id)
        
        if conversation_data:
            return jsonify({
                'success': True,
                'conversation_data': conversation_data
            }), 200
        else:
            return jsonify({'success': False, 'message': 'Conversation not found'}), 404
            
    except Exception as e:
        current_app.logger.error(f"Error getting conversation context: {str(e)}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@care_archive_bp.route('/care-summary', methods=['GET'])
@require_auth
@premium_required
def get_care_summary():
    """Get comprehensive care summary for user"""
    try:
        from app.services.care_archive_service import CareArchiveService
        care_service = CareArchiveService()
        user_id = request.current_user['id']
        
        # Get user's care summary using care archive service
        summary = care_service.get_user_summary(user_id)
        
        return jsonify({
            'success': True,
            'summary': summary
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting care summary: {str(e)}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@care_archive_bp.route('/conversation/<int:conversation_id>/suggestions', methods=['GET'])
@require_auth
@premium_required
def get_follow_up_suggestions(conversation_id):
    """Get follow-up question suggestions"""
    try:
        from app.services.care_archive_service import CareArchiveService
        care_service = CareArchiveService()
        user_id = request.current_user['id']
        
        # Generate simple follow-up suggestions
        suggestions = [
            "Tell me more about the symptoms",
            "What treatments have been tried?",
            "How is the recovery progressing?",
            "Any changes in behavior?"
        ]
        
        return jsonify({
            'success': True,
            'suggestions': suggestions
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting follow-up suggestions: {str(e)}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@care_archive_bp.route('/analyze-intent', methods=['POST'])
@require_auth
@validate_json_content
def analyze_intent():
    """Analyze user query intent"""
    try:
        from app.utils.intent_detector import IntentDetector
        data = request.json
        user_id = request.current_user['id']
        
        if 'message' not in data:
            return jsonify({'success': False, 'message': 'Message is required'}), 400
        
        # Use intent detector utility
        intent_detector = IntentDetector()
        intent_analysis = intent_detector.detect_intent(data['message'])
        
        return jsonify({
            'success': True,
            'intent_analysis': intent_analysis
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error analyzing intent: {str(e)}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

# Care record categories endpoint
@care_archive_bp.route('/categories', methods=['GET'])
@require_auth
def get_care_categories():
    """Get available care record categories"""
    categories = [
        {'value': 'vaccination', 'label': 'Vaccination', 'icon': '💉'},
        {'value': 'vet_visit', 'label': 'Vet Visit', 'icon': '🏥'},
        {'value': 'medication', 'label': 'Medication', 'icon': '💊'},
        {'value': 'milestone', 'label': 'Milestone', 'icon': '🎯'},
        {'value': 'grooming', 'label': 'Grooming', 'icon': '✂️'},
        {'value': 'training', 'label': 'Training', 'icon': '🎓'},
        {'value': 'diet', 'label': 'Diet & Nutrition', 'icon': '🍽️'},
        {'value': 'exercise', 'label': 'Exercise', 'icon': '🏃'},
        {'value': 'behavior', 'label': 'Behavior', 'icon': '🐕'},
        {'value': 'other', 'label': 'Other', 'icon': '📝'}
    ]
    
    return jsonify({
        'success': True,
        'categories': categories
    }), 200

@care_archive_bp.route('/backfill-knowledge-base', methods=['POST'])
@require_auth  
def backfill_knowledge_base():
    """Backfill existing care records to knowledge base for better semantic search"""
    try:
        care_service = CareArchiveService()
        user_id = request.current_user['id']
        
        current_app.logger.info(f"Starting knowledge base backfill for user {user_id}")
        
        # Perform backfill
        success, message, stats = care_service.backfill_care_records_to_knowledge_base(user_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'stats': stats
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message,
                'stats': stats
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Error in backfill endpoint: {str(e)}")
        return jsonify({
            'success': False, 
            'message': 'Internal server error during backfill',
            'stats': {"total_processed": 0, "successful": 0, "failed": 0, "skipped": 0}
        }), 500 

@care_archive_bp.route('/enhanced-chat', methods=['POST'])
@require_auth
@premium_required
@require_health_credits
@validate_json_content
def enhanced_chat():
    """Enhanced chat with health context - redirects to working enhanced chat service"""
    try:
        from app.services.enhanced_chat_service import EnhancedChatService
        enhanced_chat_service = EnhancedChatService()
        
        user_id = request.current_user['id']
        data = request.json
        
        current_app.logger.info("="*60)
        current_app.logger.info("CARE ARCHIVE ENHANCED CHAT ENDPOINT CALLED")
        current_app.logger.info(f"User ID: {user_id}")
        current_app.logger.info(f"Request data: {data}")
        current_app.logger.info("="*60)
        
        if 'message' not in data:
            return jsonify({'success': False, 'message': 'Message is required'}), 400
        
        conversation_id = data.get('conversation_id')
        thread_id = data.get('thread_id')
        
        current_app.logger.info(f"Extracted - conversation_id: {conversation_id}, thread_id: {thread_id}")
        
        # Generate contextual response using enhanced chat service
        success, response, context_info = enhanced_chat_service.generate_contextual_response(
            user_id=user_id,
            message=data['message'], 
            conversation_id=conversation_id,
            thread_id=thread_id
        )
        
        current_app.logger.info(f"Service returned - success: {success}")
        current_app.logger.info(f"Context info: {context_info}")
        
        if success:
            return jsonify({
                'success': True,
                'response': response,
                'context_info': context_info
            }), 200
        else:
            return jsonify({'success': False, 'message': response}), 400
            
    except Exception as e:
        current_app.logger.error(f"Error in enhanced chat: {str(e)}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500 