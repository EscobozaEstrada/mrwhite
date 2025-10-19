import os
from flask import Blueprint, request, jsonify, g
from app import db
from app.models.enhanced_book import EnhancedBook, EnhancedBookChapter
from app.services.enhanced_book_service import EnhancedBookService
from app.middleware.auth import require_auth
from app.middleware.credit_middleware import require_credits
from app.models.message import Message
from app.models.conversation import Conversation

enhanced_book_bp = Blueprint('enhanced_book', __name__)
enhanced_book_service = EnhancedBookService()

@enhanced_book_bp.route('/enhanced-books', methods=['POST'])
@require_auth
def create_enhanced_book():
    """Create a new enhanced book"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['title', 'tone_type', 'text_style']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400
        
        # Create the book
        book = enhanced_book_service.create_enhanced_book(
            user_id=g.user_id,
            title=data['title'],
            tone_type=data['tone_type'],
            text_style=data['text_style'],
            categories=data.get('categories', []),  # Optional field, defaults to empty
            cover_image=data.get('cover_image'),  # Optional field
            book_type=data.get('book_type', 'general')  # Optional, defaults to general
        )
        
        return jsonify({'success': True, 'book': book}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@enhanced_book_bp.route('/enhanced-books/<int:book_id>/categorize', methods=['POST'])
@require_auth
def categorize_messages(book_id):
    """Categorize messages for a book"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'categories' not in data or not isinstance(data['categories'], list):
            return jsonify({'success': False, 'message': 'Categories must be provided as a list'}), 400
        
        # Categorize messages
        categorized_messages = enhanced_book_service.categorize_messages(
            user_id=g.user_id,
            book_id=book_id,
            categories=data['categories']
        )
        
        return jsonify({'success': True, 'categorized_messages': categorized_messages}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@enhanced_book_bp.route('/enhanced-books/<int:book_id>/generate', methods=['POST'])
@require_auth
@require_credits('book_generation')
def generate_book_chapters(book_id):
    """Generate book chapters from categorized messages"""
    try:
        # Generate chapters
        book = enhanced_book_service.generate_book_chapters(
            user_id=g.user_id,
            book_id=book_id
        )
        
        return jsonify({'success': True, 'book': book}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@enhanced_book_bp.route('/enhanced-books/<int:book_id>/pdf', methods=['POST'])
@require_auth
def generate_pdf(book_id):
    """Generate PDF for a book"""
    try:
        # Generate PDF
        pdf_url = enhanced_book_service.generate_pdf(
            user_id=g.user_id,
            book_id=book_id
        )
        
        return jsonify({'success': True, 'pdf_url': pdf_url}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@enhanced_book_bp.route('/enhanced-books/<int:book_id>/epub', methods=['POST'])
@require_auth
def generate_epub(book_id):
    """Generate EPUB for a book"""
    try:
        # Generate EPUB
        epub_url = enhanced_book_service.generate_epub(
            user_id=g.user_id,
            book_id=book_id
        )
        
        return jsonify({'success': True, 'epub_url': epub_url}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@enhanced_book_bp.route('/enhanced-books', methods=['GET'])
@require_auth
def get_user_books():
    """Get all enhanced books for the current user"""
    try:
        # Get books
        books = EnhancedBook.query.filter_by(user_id=g.user_id).order_by(EnhancedBook.created_at.desc()).all()
        
        return jsonify({'success': True, 'books': [book.to_dict() for book in books]}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@enhanced_book_bp.route('/enhanced-books/<int:book_id>', methods=['GET'])
@require_auth
def get_book(book_id):
    """Get a specific enhanced book"""
    try:
        # Get book
        book = EnhancedBook.query.get(book_id)
        if not book or book.user_id != g.user_id:
            return jsonify({'success': False, 'message': 'Book not found or access denied'}), 404
        
        return jsonify({'success': True, 'book': book.to_dict()}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@enhanced_book_bp.route('/enhanced-books/<int:book_id>/chapters/<int:chapter_id>', methods=['PUT'])
@require_auth
def update_chapter(book_id, chapter_id):
    """Update a chapter's title and content"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'title' not in data or 'content' not in data:
            return jsonify({'success': False, 'message': 'Title and content are required'}), 400
        
        # Update chapter
        chapter = enhanced_book_service.update_chapter(
            user_id=g.user_id,
            book_id=book_id,
            chapter_id=chapter_id,
            title=data['title'],
            content=data['content']
        )
        
        return jsonify({'success': True, 'chapter': chapter}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@enhanced_book_bp.route('/enhanced-books/<int:book_id>/chapters/<int:chapter_id>', methods=['DELETE'])
@require_auth
def delete_chapter(book_id, chapter_id):
    """Delete a chapter"""
    try:
        # Delete chapter
        result = enhanced_book_service.delete_chapter(
            user_id=g.user_id,
            book_id=book_id,
            chapter_id=chapter_id
        )
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@enhanced_book_bp.route('/enhanced-books/<int:book_id>/ai-chat-edit', methods=['POST'])
@require_auth
def ai_chat_edit(book_id):
    """AI-assisted chapter editing"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'message' not in data or 'bookContext' not in data:
            return jsonify({'success': False, 'message': 'Message and book context are required'}), 400
            
        # Extract data
        user_message = data['message']
        book_context = data['bookContext']
        chat_history = data.get('chatHistory', [])
        
        # Call enhanced book service for AI editing
        result = enhanced_book_service.process_ai_chat_edit(
            user_id=g.user_id,
            book_id=book_id,
            message=user_message,
            book_context=book_context,
            chat_history=chat_history
        )
        
        return jsonify({
            'success': True,
            'message': result['message'],
            'editedContent': result.get('editedContent'),
            'intent': result.get('intent', 'edit')  # Default to 'edit' for backward compatibility
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@enhanced_book_bp.route('/enhanced-books/<int:book_id>/latest-chats', methods=['GET'])
@require_auth
def get_latest_chats(book_id):
    """Fetch and format recent chat messages for a book"""
    try:
        # Get the book to access its tone and style
        book = EnhancedBook.query.get(book_id)
        if not book or book.user_id != g.user_id:
            return jsonify({'success': False, 'message': 'Book not found or access denied'}), 404
        
        # Get parameters from query
        category = request.args.get('category')
        chapter_id = request.args.get('chapterId')
        
        if chapter_id:
            try:
                chapter_id = int(chapter_id)
            except ValueError:
                return jsonify({'success': False, 'message': 'Invalid chapter ID'}), 400
        
        # Get recent chat messages
        result = enhanced_book_service.get_formatted_recent_chats(
            user_id=g.user_id,
            book_id=book_id,
            tone_type=book.tone_type,
            text_style=book.text_style,
            category=category,
            chapter_id=chapter_id
        )
        
        return jsonify({
            'success': True,
            'formattedContent': result['formattedContent'],
            'messageCount': result['messageCount']
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500 

@enhanced_book_bp.route('/enhanced-books/<int:book_id>', methods=['DELETE'])
@require_auth
def delete_book(book_id):
    """Delete an enhanced book"""
    try:
        # Delete book using service
        result = enhanced_book_service.delete_book(
            user_id=g.user_id,
            book_id=book_id
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500 