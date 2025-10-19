from flask import Blueprint, request, jsonify, current_app, g
from app.middleware.auth import require_auth
from app.services.user_book_service import UserBookService
from app.services.auth_service import AuthService
from datetime import datetime, timezone
import json
from typing import Dict, Any

# g object is used to store authenticated user data during request lifecycle

# Create blueprint
user_book_bp = Blueprint('user_book', __name__)


@user_book_bp.route('/copy', methods=['GET'])
@require_auth
def get_authenticated_book_copy():
    """Get authenticated user's book copy"""
    try:
        book_title = request.args.get('title', 'The Way of the Dog Anahata')
        book_type = request.args.get('type', 'public')
        
        current_app.logger.info(f"📖 Getting book copy for user {g.user_id}")
        
        result = UserBookService.get_or_create_user_book_copy(
            user_id=g.user_id,
            book_title=book_title,
            book_type=book_type
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'book_copy': result['book_copy'],
                'message': result['message']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Error getting book copy: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting book copy: {str(e)}'
        }), 500

@user_book_bp.route('/test-copy', methods=['GET'])
def get_test_book_copy():
    """Get test book copy without authentication (DEPRECATED - use authenticated endpoint)"""
    try:
        book_title = request.args.get('title', 'The Way of the Dog Anahata')
        book_type = request.args.get('type', 'public')
        
        current_app.logger.warning(f"⚠️ Using deprecated test endpoint for book copy")
        
        # Use a test user ID for demo
        test_user_id = 1
        
        result = UserBookService.get_or_create_user_book_copy(
            user_id=test_user_id,
            book_title=book_title,
            book_type=book_type
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'book_copy': result['book_copy'],
                'message': result['message']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Error getting test book copy: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting book copy: {str(e)}'
        }), 500


@user_book_bp.route('/progress/<int:book_copy_id>', methods=['GET'])
@require_auth
def get_user_progress(book_copy_id: int):
    """Get reading progress for authenticated user"""
    try:
        current_app.logger.info(f"📊 Getting progress for book copy {book_copy_id}, user {g.user_id}")
        
        result = UserBookService.get_reading_progress(g.user_id, book_copy_id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'progress': result['progress']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Error getting progress: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting progress: {str(e)}'
        }), 500

@user_book_bp.route('/progress/<int:book_copy_id>', methods=['PUT'])  
@require_auth
def update_user_progress(book_copy_id: int):
    """Update reading progress for authenticated user"""
    try:
        data = request.get_json()
        current_app.logger.info(f"📈 Updating progress for book copy {book_copy_id}, user {g.user_id}")
        
        result = UserBookService.update_reading_progress(
            user_id=g.user_id,  # Use authenticated user ID
            book_copy_id=book_copy_id,
            progress_data=data
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'progress': result['progress']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Error updating progress: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error updating progress: {str(e)}'
        }), 500

@user_book_bp.route('/test-progress/<int:book_copy_id>', methods=['GET'])
def get_test_progress(book_copy_id: int):
    """Get reading progress for test user (DEPRECATED - use authenticated endpoint)"""
    try:
        current_app.logger.warning(f"⚠️ Using deprecated test endpoint for progress: {book_copy_id}")
        
        result = UserBookService.get_reading_progress(1, book_copy_id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'progress': result['progress']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Error getting test progress: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting progress: {str(e)}'
        }), 500


@user_book_bp.route('/test-progress/<int:book_copy_id>', methods=['PUT'])
def update_test_progress(book_copy_id: int):
    """Update reading progress for test user (DEPRECATED - use authenticated endpoint)"""
    try:
        data = request.get_json()
        current_app.logger.warning(f"⚠️ Using deprecated test endpoint for progress update: {book_copy_id}")
        
        result = UserBookService.update_reading_progress(
            user_id=1,  # Test user ID
            book_copy_id=book_copy_id,
            progress_data=data
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'progress': result['progress']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Error updating test progress: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error updating progress: {str(e)}'
        }), 500


@user_book_bp.route('/notes/<int:book_copy_id>', methods=['GET'])
@require_auth
def get_user_notes(book_copy_id: int):
    """Get notes for authenticated user"""
    try:
        current_app.logger.info(f"📝 Getting notes for book copy {book_copy_id}, user {g.user_id}")
        
        result = UserBookService.get_notes(g.user_id, book_copy_id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'notes': result['notes']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Error getting notes: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting notes: {str(e)}'
        }), 500

@user_book_bp.route('/test-notes/<int:book_copy_id>', methods=['GET'])
def get_test_notes(book_copy_id: int):
    """Get notes for test user (DEPRECATED - use authenticated endpoint)"""
    try:
        current_app.logger.warning(f"⚠️ Using deprecated test endpoint for book copy {book_copy_id}")
        
        result = UserBookService.get_notes(1, book_copy_id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'notes': result['notes']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Error getting test notes: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting notes: {str(e)}'
        }), 500


@user_book_bp.route('/notes', methods=['POST'])
@require_auth
def create_user_note():
    """Create note for authenticated user"""
    try:
        data = request.get_json()
        current_app.logger.info(f"📝 Creating note for user {g.user_id}")
        current_app.logger.info(f"📝 Raw data received: {data}")
        
        # Extract book_copy_id and pass the rest as note_data
        book_copy_id = data.pop('book_copy_id', None)
        current_app.logger.info(f"📝 book_copy_id: {book_copy_id}")
        current_app.logger.info(f"📝 note_data after pop: {data}")
        
        if not book_copy_id:
            return jsonify({
                'success': False,
                'message': 'book_copy_id is required'
            }), 400
        
        current_app.logger.info(f"📝 Calling UserBookService.create_note with user_id={g.user_id}, book_copy_id={book_copy_id}, note_data={data}")
        
        result = UserBookService.create_note(
            user_id=g.user_id,  # Use authenticated user ID
            book_copy_id=book_copy_id,
            note_data=data
        )
        
        current_app.logger.info(f"📝 Service result: {result}")
        
        if result['success']:
            return jsonify({
                'success': True,
                'note': result['note']
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Error creating note: {str(e)}")
        import traceback
        current_app.logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'Error creating note: {str(e)}'
        }), 500

@user_book_bp.route('/test-notes', methods=['POST'])
def create_test_note():
    """Create note for test user (DEPRECATED - use authenticated endpoint)"""
    try:
        data = request.get_json()
        current_app.logger.warning(f"⚠️ Using deprecated test endpoint for note creation")
        current_app.logger.info(f"📝 Raw data received: {data}")
        
        # Extract book_copy_id and pass the rest as note_data
        book_copy_id = data.pop('book_copy_id', None)
        current_app.logger.info(f"📝 book_copy_id: {book_copy_id}")
        current_app.logger.info(f"📝 note_data after pop: {data}")
        
        if not book_copy_id:
            return jsonify({
                'success': False,
                'message': 'book_copy_id is required'
            }), 400
        
        current_app.logger.info(f"📝 Calling UserBookService.create_note with user_id=1, book_copy_id={book_copy_id}, note_data={data}")
        
        result = UserBookService.create_note(
            user_id=1,  # Test user ID
            book_copy_id=book_copy_id,
            note_data=data
        )
        
        current_app.logger.info(f"📝 Service result: {result}")
        
        if result['success']:
            return jsonify({
                'success': True,
                'note': result['note']
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Error creating test note: {str(e)}")
        import traceback
        current_app.logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'Error creating note: {str(e)}'
        }), 500


@user_book_bp.route('/test-highlights/<int:book_copy_id>', methods=['GET'])
def get_test_highlights(book_copy_id: int):
    """Get highlights for test user"""
    try:
        current_app.logger.info(f"🖍️ Getting test highlights for book copy {book_copy_id}")
        
        result = UserBookService.get_highlights(1, book_copy_id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'highlights': result['highlights']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Error getting test highlights: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting highlights: {str(e)}'
        }), 500


@user_book_bp.route('/test-highlights', methods=['POST'])
def create_test_highlight():
    """Create highlight for test user"""
    try:
        data = request.get_json()
        current_app.logger.info(f"🖍️ Creating test highlight")
        
        # Extract book_copy_id and pass the rest as highlight_data
        book_copy_id = data.pop('book_copy_id', None)
        if not book_copy_id:
            return jsonify({
                'success': False,
                'message': 'book_copy_id is required'
            }), 400
        
        result = UserBookService.create_highlight(
            user_id=1,  # Test user ID
            book_copy_id=book_copy_id,
            highlight_data=data
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'highlight': result['highlight']
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Error creating test highlight: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error creating highlight: {str(e)}'
        }), 500


@user_book_bp.route('/my-copy', methods=['GET'])
def get_my_book_copy():
    """Get or create user's personal copy of a book (DEPRECATED - use /copy endpoint)"""
    try:
        book_title = request.args.get('title')
        book_type = request.args.get('type', 'public')
        book_reference_id = request.args.get('reference_id', type=int)
        
        # Use test user ID for demo mode
        test_user_id = 1
        current_app.logger.info(f"📖 Getting book copy for test user {test_user_id}")
        
        result = UserBookService.get_or_create_user_book_copy(
            user_id=test_user_id,
            book_title=book_title,
            book_type=book_type,
            book_reference_id=book_reference_id
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'book_copy': result['book_copy'],
                'message': result['message']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Error getting user book copy: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error getting book copy: {str(e)}'
        }), 500


@user_book_bp.route('/my-books', methods=['GET'])
@require_auth
def get_user_books():
    """Get all books for the authenticated user"""
    try:
        current_app.logger.info(f"📚 Getting all books for user {g.user_id}")
        
        result = UserBookService.get_user_books(g.user_id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'books': result['books'],
                'total_books': result['total_books']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Error getting user books: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error retrieving books: {str(e)}'
        }), 500


@user_book_bp.route('/progress/<int:book_copy_id>', methods=['PUT'])
@require_auth
def update_reading_progress(book_copy_id: int):
    """Update reading progress for a book"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Progress data is required'
            }), 400
        
        current_app.logger.info(f"📊 Updating progress for book {book_copy_id}, user {g.user_id}")
        
        result = UserBookService.update_reading_progress(
            user_id=g.user_id,
            book_copy_id=book_copy_id,
            progress_data=data
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'progress': result['progress'],
                'message': result['message']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Error updating progress: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error updating progress: {str(e)}'
        }), 500


@user_book_bp.route('/notes', methods=['POST'])
@require_auth
def create_note():
    """Create a new note for a book"""
    try:
        data = request.get_json()
        
        if not data or 'book_copy_id' not in data or 'note_text' not in data:
            return jsonify({
                'success': False,
                'message': 'Book copy ID and note text are required'
            }), 400
        
        book_copy_id = data['book_copy_id']
        
        current_app.logger.info(f"📝 Creating note for book {book_copy_id}, user {g.user_id}")
        
        result = UserBookService.create_note(
            user_id=g.user_id,
            book_copy_id=book_copy_id,
            note_data=data
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'note': result['note'],
                'message': result['message']
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Error creating note: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error creating note: {str(e)}'
        }), 500


@user_book_bp.route('/highlights', methods=['POST'])
@require_auth
def create_highlight():
    """Create a new highlight for a book"""
    try:
        data = request.get_json()
        
        if not data or 'book_copy_id' not in data or 'highlighted_text' not in data:
            return jsonify({
                'success': False,
                'message': 'Book copy ID and highlighted text are required'
            }), 400
        
        book_copy_id = data['book_copy_id']
        
        current_app.logger.info(f"🎨 Creating highlight for book {book_copy_id}, user {g.user_id}")
        
        result = UserBookService.create_highlight(
            user_id=g.user_id,
            book_copy_id=book_copy_id,
            highlight_data=data
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'highlight': result['highlight'],
                'message': result['message']
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Error creating highlight: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error creating highlight: {str(e)}'
        }), 500


@user_book_bp.route('/annotations/<int:book_copy_id>', methods=['GET'])
@require_auth
def get_book_annotations(book_copy_id: int):
    """Get all notes and highlights for a book"""
    try:
        current_app.logger.info(f"📋 Getting annotations for book {book_copy_id}, user {g.user_id}")
        
        result = UserBookService.get_book_annotations(
            user_id=g.user_id,
            book_copy_id=book_copy_id
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'notes': result['notes'],
                'highlights': result['highlights'],
                'total_notes': result['total_notes'],
                'total_highlights': result['total_highlights']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Error getting annotations: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error retrieving annotations: {str(e)}'
        }), 500


@user_book_bp.route('/notes/<int:note_id>', methods=['PUT'])
@require_auth
def update_note(note_id: int):
    """Update an existing note"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Note data is required'
            }), 400
        
        current_app.logger.info(f"📝 Updating note {note_id} for user {g.user_id}")
        
        result = UserBookService.update_note(
            user_id=g.user_id,
            note_id=note_id,
            note_data=data
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'note': result['note'],
                'message': result['message']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Error updating note: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error updating note: {str(e)}'
        }), 500


@user_book_bp.route('/notes/<int:note_id>', methods=['DELETE'])
@require_auth
def delete_note(note_id: int):
    """Delete a note"""
    try:
        current_app.logger.info(f"🗑️ Deleting note {note_id} for user {g.user_id}")
        
        result = UserBookService.delete_note(
            user_id=g.user_id,
            note_id=note_id
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': result['message']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Error deleting note: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error deleting note: {str(e)}'
        }), 500


@user_book_bp.route('/highlights/<int:highlight_id>', methods=['DELETE'])
@require_auth
def delete_highlight(highlight_id: int):
    """Delete a highlight"""
    try:
        current_app.logger.info(f"🗑️ Deleting highlight {highlight_id} for user {g.user_id}")
        
        result = UserBookService.delete_highlight(
            user_id=g.user_id,
            highlight_id=highlight_id
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': result['message']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Error deleting highlight: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error deleting highlight: {str(e)}'
        }), 500


@user_book_bp.route('/sessions/start', methods=['POST'])
@require_auth
def start_reading_session():
    """Start a new reading session"""
    try:
        data = request.get_json()
        
        if not data or 'book_copy_id' not in data:
            return jsonify({
                'success': False,
                'message': 'Book copy ID is required'
            }), 400
        
        book_copy_id = data['book_copy_id']
        
        current_app.logger.info(f"▶️ Starting reading session for book {book_copy_id}, user {g.user_id}")
        
        result = UserBookService.start_reading_session(
            user_id=g.user_id,
            book_copy_id=book_copy_id
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'session': result['session'],
                'message': result['message']
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Error starting reading session: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error starting session: {str(e)}'
        }), 500


@user_book_bp.route('/sessions/<int:session_id>/end', methods=['PUT'])
@require_auth
def end_reading_session(session_id: int):
    """End a reading session with analytics"""
    try:
        data = request.get_json() or {}
        
        current_app.logger.info(f"⏹️ Ending reading session {session_id} for user {g.user_id}")
        
        result = UserBookService.end_reading_session(
            user_id=g.user_id,
            session_id=session_id,
            session_data=data
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'session': result['session'],
                'message': result['message']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Error ending reading session: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error ending session: {str(e)}'
        }), 500


@user_book_bp.route('/analytics', methods=['GET'])
@require_auth
def get_reading_analytics():
    """Get reading analytics for user"""
    try:
        book_copy_id = request.args.get('book_copy_id', type=int)
        
        current_app.logger.info(f"📊 Getting reading analytics for user {g.user_id}")
        
        result = UserBookService.get_reading_analytics(
            user_id=g.user_id,
            book_copy_id=book_copy_id
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'analytics': result['analytics']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Error getting analytics: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error retrieving analytics: {str(e)}'
        }), 500


@user_book_bp.route('/search/notes', methods=['GET'])
@require_auth
def search_notes():
    """Search through user's notes"""
    try:
        query = request.args.get('q', '').strip()
        book_copy_id = request.args.get('book_copy_id', type=int)
        
        if not query:
            return jsonify({
                'success': False,
                'message': 'Search query is required'
            }), 400
        
        current_app.logger.info(f"🔍 Searching notes for user {g.user_id}: {query}")
        
        # This would be implemented in UserBookService.search_notes()
        # For now, returning a placeholder response
        return jsonify({
            'success': True,
            'notes': [],
            'total_results': 0,
            'message': 'Note search functionality coming soon'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"❌ Error searching notes: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error searching notes: {str(e)}'
        }), 500


@user_book_bp.route('/export/annotations/<int:book_copy_id>', methods=['GET'])
@require_auth
def export_annotations(book_copy_id: int):
    """Export all annotations for a book"""
    try:
        format_type = request.args.get('format', 'json').lower()
        
        current_app.logger.info(f"📤 Exporting annotations for book {book_copy_id}, user {g.user_id}")
        
        result = UserBookService.get_book_annotations(
            user_id=g.user_id,
            book_copy_id=book_copy_id
        )
        
        if result['success']:
            if format_type == 'json':
                return jsonify({
                    'success': True,
                    'export_data': {
                        'book_copy_id': book_copy_id,
                        'export_date': datetime.now(timezone.utc).isoformat(),
                        'notes': result['notes'],
                        'highlights': result['highlights']
                    },
                    'format': 'json'
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': f'Unsupported export format: {format_type}'
                }), 400
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Error exporting annotations: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error exporting annotations: {str(e)}'
        }), 500


@user_book_bp.route('/search', methods=['POST'])
@require_auth
def search_user_knowledge_base():
    """Search user's knowledge base using semantic search"""
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({
                'success': False,
                'message': 'Search query is required'
            }), 400
        
        query = data['query']
        book_copy_id = data.get('book_copy_id')
        top_k = data.get('top_k', 10)
        
        current_app.logger.info(f"🔍 Searching knowledge base for user {g.user_id}: '{query}'")
        
        # Use the Pinecone service to search
        from app.services.pinecone_integration_service import PineconeBookNotesService
        pinecone_service = PineconeBookNotesService()
        
        result = pinecone_service.search_user_knowledge_base(
            user_id=g.user_id,
            query=query,
            top_k=top_k
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'results': result['results'],
                'query': query,
                'message': result['message']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Error searching knowledge base: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Search error: {str(e)}'
        }), 500


@user_book_bp.route('/related/<item_id>', methods=['GET'])
@require_auth
def get_related_content(item_id: str):
    """Get related content for a specific note or highlight"""
    try:
        current_app.logger.info(f"🔗 Finding related content for item {item_id}, user {g.user_id}")
        
        # Use the Pinecone service to find related content
        from app.services.pinecone_integration_service import PineconeBookNotesService
        pinecone_service = PineconeBookNotesService()
        
        result = pinecone_service.get_related_notes(
            user_id=g.user_id,
            current_note_id=int(item_id.split('_')[-1]) if '_' in item_id else int(item_id),
            top_k=5
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'related_items': result['related_items'],
                'message': result['message']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Error finding related content: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error finding related content: {str(e)}'
        }), 500


@user_book_bp.route('/insights/<int:book_copy_id>', methods=['GET'])
@require_auth
def get_reading_insights(book_copy_id: int):
    """Generate AI insights from user's notes and highlights for a book"""
    try:
        current_app.logger.info(f"🧠 Generating insights for book {book_copy_id}, user {g.user_id}")
        
        # Use the Pinecone service to generate insights
        from app.services.pinecone_integration_service import PineconeBookNotesService
        pinecone_service = PineconeBookNotesService()
        
        result = pinecone_service.generate_insights_from_notes(
            user_id=g.user_id,
            book_copy_id=book_copy_id
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'insights': result['insights'],
                'message': result['message']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"❌ Error generating insights: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error generating insights: {str(e)}'
        }), 500


@user_book_bp.route('/backfill-knowledge-base', methods=['POST'])
@require_auth
def backfill_knowledge_base():
    """Backfill existing notes to the knowledge base for semantic search"""
    try:
        from app.models.db import db
        from app.models.user_book import UserBookNote, UserBookCopy
        from app.services.pinecone_integration_service import PineconeBookNotesService
        
        user_id = g.user_id
        book_copy_id = request.args.get('book_copy_id', type=int)
        
        current_app.logger.info(f"🔄 Starting knowledge base backfill for user {user_id}")
        
        # Query to get notes
        query = UserBookNote.query.filter_by(user_id=user_id)
        
        # If book_copy_id is provided, filter by it
        if book_copy_id:
            query = query.filter_by(book_copy_id=book_copy_id)
            
        # Get all notes
        notes = query.all()
        
        if not notes:
            return jsonify({
                'success': True,
                'message': 'No notes found to backfill',
                'stats': {
                    'total': 0,
                    'success': 0,
                    'failed': 0
                }
            }), 200
        
        pinecone_service = PineconeBookNotesService()
        success_count = 0
        error_count = 0
        
        for note in notes:
            # Get the book copy to get the book title
            book_copy = UserBookCopy.query.get(note.book_copy_id)
            book_title = book_copy.book_title if book_copy else 'Unknown'
            
            # Convert to dict
            note_data = {
                'id': note.id,
                'note_text': note.note_text,
                'note_type': note.note_type,
                'color': note.color,
                'page_number': note.page_number,
                'book_copy_id': note.book_copy_id,
                'book_title': book_title,
                'selected_text': note.selected_text if hasattr(note, 'selected_text') else '',
                'pdf_coordinates': note.pdf_coordinates if hasattr(note, 'pdf_coordinates') else {}
            }
            
            # Add to knowledge base
            result = pinecone_service.add_note_to_knowledge_base(note.user_id, note_data)
            
            if result.get('success', False):
                success_count += 1
            else:
                error_count += 1
        
        return jsonify({
            'success': True,
            'message': f'Backfilled {success_count} notes to knowledge base',
            'stats': {
                'total': len(notes),
                'success': success_count,
                'failed': error_count
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"❌ Error backfilling knowledge base: {str(e)}")
        import traceback
        current_app.logger.error(f"❌ Full traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'Error backfilling knowledge base: {str(e)}'
        }), 500


# Error handlers for the user book blueprint
@user_book_bp.errorhandler(404)
def user_book_not_found(error):
    return jsonify({
        'success': False,
        'message': 'User book endpoint not found',
        'available_endpoints': [
            '/my-copy', '/my-books', '/progress/<book_copy_id>', 
            '/notes', '/highlights', '/annotations/<book_copy_id>',
            '/sessions/start', '/sessions/<session_id>/end', '/analytics'
        ]
    }), 404


@user_book_bp.errorhandler(500)
def user_book_internal_error(error):
    return jsonify({
        'success': False,
        'message': 'Internal server error in user book system'
    }), 500 