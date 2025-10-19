from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from app.middleware.auth import require_auth
from app.services.auth_service import AuthService
from app.services.enhanced_document_processing_service import EnhancedDocumentProcessingService
from app.services.enhanced_document_chat_agents import EnhancedDocumentChatAgents
from app.models.care_record import Document
from app import db
import uuid
import os
import tempfile
import asyncio
import requests

# Create blueprint
enhanced_document_bp = Blueprint('enhanced_document', __name__)

# Initialize enhanced services lazily
document_processing_service = None
document_chat_agents = None

def get_document_processing_service():
    """Get document processing service with lazy initialization"""
    global document_processing_service
    if document_processing_service is None:
        document_processing_service = EnhancedDocumentProcessingService()
    return document_processing_service

def get_document_chat_agents():
    """Get document chat agents with lazy initialization"""
    global document_chat_agents
    if document_chat_agents is None:
        document_chat_agents = EnhancedDocumentChatAgents()
    return document_chat_agents

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'doc', 'docx', 'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@enhanced_document_bp.route('/upload', methods=['POST'])
def upload_document():
    """Enhanced document upload with comprehensive AI processing"""
    try:
        # Get user from token
        token = request.cookies.get('token')
        success, message, user_data = AuthService.get_user_from_token(token)
        
        if not success:
            return jsonify({'success': False, 'message': message}), 401
        
        user_id = user_data['id']
        
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'success': False, 
                'message': f'File type not supported. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # Secure the filename
        filename = secure_filename(file.filename)
        if not filename:
            filename = f"document_{uuid.uuid4().hex[:8]}.pdf"
        
        current_app.logger.info(f"📤 Processing enhanced document upload: {filename} for user {user_id}")
        
        # Process the document through enhanced service
        result = get_document_processing_service().upload_and_process_document(
            user_id=user_id,
            file_obj=file,
            original_filename=filename
        )
        
        if result['success']:
            current_app.logger.info(f"✅ Enhanced document processed successfully: {result['document_id']}")
            
            # Get processing details
            processing_result = result['processing_result']
            
            return jsonify({
                'success': True,
                'message': f"Document '{filename}' processed successfully with enhanced AI analysis",
                'document': result['document'],
                'processing_summary': {
                    'document_type': processing_result.get('document_classification', 'unknown'),
                    'summary': processing_result.get('document_summary', ''),
                    'key_insights': processing_result.get('key_insights', []),
                    'pet_information': processing_result.get('pet_information', {}),
                    'health_information': processing_result.get('health_information', {}),
                    'care_instructions': processing_result.get('care_instructions', []),
                    'quality_score': processing_result.get('quality_score', 0.0),
                    'vector_stored': processing_result.get('vector_stored', False),
                    'chunks_created': processing_result.get('chunks_created', 0),
                    'workflow_trace': processing_result.get('workflow_trace', [])
                },
                's3_url': result['s3_url']
            }), 200
        else:
            current_app.logger.error(f"❌ Enhanced document processing failed: {result['error_message']}")
            return jsonify({
                'success': False,
                'message': f'Document processing failed: {result["error_message"]}'
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"❌ Enhanced document upload failed: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Document upload error: {str(e)}'
        }), 500



@enhanced_document_bp.route('/search', methods=['POST'])
def search_documents():
    """Enhanced document search with AI-powered results"""
    try:
        # Get user from token
        token = request.cookies.get('token')
        success, message, user_data = AuthService.get_user_from_token(token)
        
        if not success:
            return jsonify({'success': False, 'message': message}), 401
        
        user_id = user_data['id']
        
        # Get search parameters
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'success': False, 'message': 'Search query is required'}), 400
        
        query = data['query']
        search_type = data.get('search_type', 'semantic')  # semantic, name, hybrid
        limit = data.get('limit', 10)
        
        current_app.logger.info(f"🔍 Enhanced document search for user {user_id}: {query}")
        
        # Process search through enhanced agents
        result = get_document_chat_agents().process_document_chat(
            user_id=user_id,
            query=f"search: {query}",
            conversation_context={
                'search_type': search_type,
                'search_limit': limit,
                'search_only': True
            }
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'query': query,
                'search_type': search_type,
                'documents_found': result['documents_found'],
                'total_results': len(result['documents_found']),
                'intent': result['intent'],
                'confidence_score': result['confidence_score'],
                'related_documents': result['related_documents'],
                'suggestions': result['follow_up_suggestions']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result.get('error_message', 'Search failed'),
                'documents_found': []
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"❌ Enhanced document search error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Document search error: {str(e)}',
            'documents_found': []
        }), 500

@enhanced_document_bp.route('/retrieve/<path:document_name>', methods=['GET'])
def retrieve_document_by_name(document_name):
    """Retrieve specific document by name using enhanced agents"""
    try:
        # Get user from token
        token = request.cookies.get('token')
        success, message, user_data = AuthService.get_user_from_token(token)
        
        if not success:
            return jsonify({'success': False, 'message': message}), 401
        
        user_id = user_data['id']
        
        current_app.logger.info(f"📄 Retrieving document by name for user {user_id}: {document_name}")
        
        # Process retrieval through enhanced agents
        result = get_document_chat_agents().process_document_chat(
            user_id=user_id,
            query=f"show me {document_name}",
            conversation_context={
                'retrieval_mode': True,
                'document_name': document_name
            }
        )
        
        if result['success'] and result['selected_document']:
            document = result['selected_document']
            
            return jsonify({
                'success': True,
                'document': document,
                'response': result['response'],
                'confidence_score': result['confidence_score'],
                'related_documents': result['related_documents'],
                'suggestions': result['follow_up_suggestions']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': f'Document "{document_name}" not found',
                'response': result.get('response', 'Document not found in your records.'),
                'suggestions': result.get('follow_up_suggestions', [])
            }), 404
            
    except Exception as e:
        current_app.logger.error(f"❌ Document retrieval error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Document retrieval error: {str(e)}'
        }), 500

@enhanced_document_bp.route('/list', methods=['GET'])
def list_documents():
    """List user documents with enhanced metadata"""
    try:
        # Get user from token
        token = request.cookies.get('token')
        success, message, user_data = AuthService.get_user_from_token(token)
        
        if not success:
            return jsonify({'success': False, 'message': message}), 401
        
        user_id = user_data['id']
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        sort_by = request.args.get('sort_by', 'created_at')
        order = request.args.get('order', 'desc')
        
        current_app.logger.info(f"📋 Listing documents for user {user_id}")
        
        # Query documents with pagination
        query = Document.query.filter_by(user_id=user_id)
        
        # Apply sorting
        if sort_by == 'created_at':
            if order == 'desc':
                query = query.order_by(Document.created_at.desc())
            else:
                query = query.order_by(Document.created_at.asc())
        elif sort_by == 'filename':
            if order == 'desc':
                query = query.order_by(Document.original_filename.desc())
            else:
                query = query.order_by(Document.original_filename.asc())
        elif sort_by == 'file_type':
            if order == 'desc':
                query = query.order_by(Document.file_type.desc())
            else:
                query = query.order_by(Document.file_type.asc())
        
        # Paginate results
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # Format documents with enhanced metadata
        documents = []
        for doc in pagination.items:
            doc_dict = {
                'id': doc.id,
                'filename': doc.filename,
                'original_filename': doc.original_filename,
                'file_type': doc.file_type,
                'file_size': doc.file_size,
                's3_url': doc.s3_url,
                'content_summary': doc.content_summary,
                'is_processed': doc.is_processed,
                'processing_status': doc.processing_status,
                'created_at': doc.created_at.isoformat() if doc.created_at else None,
                'updated_at': doc.updated_at.isoformat() if doc.updated_at else None,
                'metadata': doc.meta_data or {}
            }
            
            # Add enhanced metadata if available
            if doc.meta_data and 'processing_results' in doc.meta_data:
                processing_results = doc.meta_data['processing_results']
                doc_dict['enhanced_metadata'] = {
                    'document_type': processing_results.get('document_details', {}).get('type', 'unknown'),
                    'quality_score': processing_results.get('document_details', {}).get('quality_score', 0.0),
                    'pet_data': processing_results.get('pet_data', {}),
                    'insights_count': processing_results.get('content_analysis', {}).get('insights_count', 0),
                    'chunks_created': processing_results.get('content_analysis', {}).get('chunks_created', 0)
                }
            
            documents.append(doc_dict)
        
        # Calculate statistics
        total_documents = pagination.total
        processed_documents = sum(1 for doc in documents if doc['is_processed'])
        
        return jsonify({
            'success': True,
            'documents': documents,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_documents,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            },
            'statistics': {
                'total_documents': total_documents,
                'processed_documents': processed_documents,
                'processing_rate': (processed_documents / total_documents * 100) if total_documents > 0 else 0,
                'file_types': {}
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"❌ Document listing error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Document listing error: {str(e)}',
            'documents': []
        }), 500

@enhanced_document_bp.route('/reprocess/<int:document_id>', methods=['POST'])
def reprocess_document(document_id):
    """Reprocess document with enhanced AI analysis"""
    try:
        # Get user from token
        token = request.cookies.get('token')
        success, message, user_data = AuthService.get_user_from_token(token)
        
        if not success:
            return jsonify({'success': False, 'message': message}), 401
        
        user_id = user_data['id']
        
        # Get document
        document = Document.query.filter_by(id=document_id, user_id=user_id).first()
        if not document:
            return jsonify({'success': False, 'message': 'Document not found'}), 404
        
        current_app.logger.info(f"🔄 Reprocessing document {document_id} for user {user_id}")
        
        # Download file from S3
        response = requests.get(document.s3_url)
        if response.status_code != 200:
            return jsonify({'success': False, 'message': 'Failed to download document from S3'}), 500
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{document.file_type}') as temp_file:
            temp_file.write(response.content)
            temp_file_path = temp_file.name
        
        try:
            # Reprocess the document with enhanced service
            processing_result = asyncio.run(get_document_processing_service().process_document(
                user_id=user_id,
                file_path=temp_file_path,
                original_filename=document.original_filename,
                document_id=document_id
            ))
            
            if processing_result['success']:
                current_app.logger.info(f"✅ Document {document_id} reprocessed successfully")
                
                return jsonify({
                    'success': True,
                    'message': 'Document reprocessed successfully with enhanced AI analysis',
                    'document': document.to_dict(),
                    'processing_result': {
                        'document_type': processing_result.get('document_classification', 'unknown'),
                        'summary': processing_result.get('document_summary', ''),
                        'key_insights': processing_result.get('key_insights', []),
                        'pet_information': processing_result.get('pet_information', {}),
                        'health_information': processing_result.get('health_information', {}),
                        'care_instructions': processing_result.get('care_instructions', []),
                        'quality_score': processing_result.get('quality_score', 0.0),
                        'workflow_trace': processing_result.get('workflow_trace', [])
                    }
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': processing_result.get('error_message', 'Reprocessing failed')
                }), 500
                
        finally:
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            
    except Exception as e:
        current_app.logger.error(f"❌ Document reprocessing error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Document reprocessing error: {str(e)}'
        }), 500

@enhanced_document_bp.route('/delete/<int:document_id>', methods=['DELETE'])
def delete_document(document_id):
    """Delete document and its associated vectors"""
    try:
        # Get user from token
        token = request.cookies.get('token')
        success, message, user_data = AuthService.get_user_from_token(token)
        
        if not success:
            return jsonify({'success': False, 'message': message}), 401
        
        user_id = user_data['id']
        
        # Get document
        document = Document.query.filter_by(id=document_id, user_id=user_id).first()
        if not document:
            return jsonify({'success': False, 'message': 'Document not found'}), 404
        
        current_app.logger.info(f"🗑️ Deleting document {document_id} for user {user_id}")
        
        # Delete from database
        db.session.delete(document)
        db.session.commit()
        
        # Note: Vector deletion would be handled by the vector store cleanup
        # This could be enhanced with explicit vector deletion
        
        return jsonify({
            'success': True,
            'message': f'Document "{document.original_filename}" deleted successfully'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"❌ Document deletion error: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Document deletion error: {str(e)}'
        }), 500

@enhanced_document_bp.route('/stats', methods=['GET'])
def get_document_stats():
    """Get comprehensive document statistics"""
    try:
        # Get user from token
        token = request.cookies.get('token')
        success, message, user_data = AuthService.get_user_from_token(token)
        
        if not success:
            return jsonify({'success': False, 'message': message}), 401
        
        user_id = user_data['id']
        
        current_app.logger.info(f"📊 Getting document statistics for user {user_id}")
        
        # Get all user documents
        documents = Document.query.filter_by(user_id=user_id).all()
        
        # Calculate statistics
        total_documents = len(documents)
        processed_documents = sum(1 for doc in documents if doc.is_processed)
        
        # File type distribution
        file_types = {}
        for doc in documents:
            file_types[doc.file_type] = file_types.get(doc.file_type, 0) + 1
        
        # Processing status distribution
        processing_status = {}
        for doc in documents:
            status = doc.processing_status or 'unknown'
            processing_status[status] = processing_status.get(status, 0) + 1
        
        # Quality score distribution (from enhanced processing)
        quality_scores = []
        for doc in documents:
            if doc.meta_data and 'processing_results' in doc.meta_data:
                quality_score = doc.meta_data['processing_results'].get('quality_score', 0.0)
                quality_scores.append(quality_score)
        
        avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        return jsonify({
            'success': True,
            'statistics': {
                'total_documents': total_documents,
                'processed_documents': processed_documents,
                'unprocessed_documents': total_documents - processed_documents,
                'processing_rate': (processed_documents / total_documents * 100) if total_documents > 0 else 0,
                'file_types': file_types,
                'processing_status': processing_status,
                'quality_metrics': {
                    'average_quality_score': avg_quality_score,
                    'total_scored_documents': len(quality_scores),
                    'quality_distribution': {
                        'excellent': sum(1 for score in quality_scores if score >= 0.9),
                        'good': sum(1 for score in quality_scores if 0.7 <= score < 0.9),
                        'fair': sum(1 for score in quality_scores if 0.5 <= score < 0.7),
                        'poor': sum(1 for score in quality_scores if score < 0.5)
                    }
                }
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"❌ Document statistics error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Document statistics error: {str(e)}',
            'statistics': {}
        }), 500

@enhanced_document_bp.route('/suggestions', methods=['POST'])
def get_document_suggestions():
    """Get AI-powered document suggestions"""
    try:
        # Get user from token
        token = request.cookies.get('token')
        success, message, user_data = AuthService.get_user_from_token(token)
        
        if not success:
            return jsonify({'success': False, 'message': message}), 401
        
        user_id = user_data['id']
        
        # Get parameters
        data = request.get_json()
        context = data.get('context', '')
        suggestion_type = data.get('type', 'general')  # general, health, care, search
        
        current_app.logger.info(f"💡 Getting document suggestions for user {user_id}")
        
        # Process suggestions through enhanced agents
        result = get_document_chat_agents().process_document_chat(
            user_id=user_id,
            query=f"suggest documents for: {context}",
            conversation_context={
                'suggestion_mode': True,
                'suggestion_type': suggestion_type,
                'context': context
            }
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'suggestions': result['follow_up_suggestions'],
                'related_documents': result['related_documents'],
                'context': context,
                'suggestion_type': suggestion_type
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result.get('error_message', 'Failed to generate suggestions'),
                'suggestions': []
            }), 500 
            
    except Exception as e:
        current_app.logger.error(f"❌ Document suggestions error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Document suggestions error: {str(e)}',
            'suggestions': []
        }), 500