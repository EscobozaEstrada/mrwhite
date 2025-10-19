#!/usr/bin/env python3
"""
Book Content Routes - API endpoints for book content processing and management
"""

from flask import Blueprint, request, jsonify, current_app, g
from datetime import datetime, timezone
import os
import logging

from app.services.book_content_service import BookContentService
from app.models.custom_book import CustomBook, BookChapter
from app import db

# Create blueprint
book_content_bp = Blueprint('book_content', __name__)

# Initialize service
book_content_service = BookContentService()

logger = logging.getLogger(__name__)


@book_content_bp.route('/process-docx', methods=['POST'])
def process_docx_file():
    """Process a DOCX file and create structured book content"""
    try:
        data = request.get_json()
        
        file_path = data.get('file_path')
        book_title = data.get('book_title', 'The Way of the Dog Anahata')
        
        if not file_path:
            return jsonify({
                'success': False,
                'message': 'File path is required'
            }), 400
        
        current_app.logger.info(f"📖 Processing DOCX file: {file_path}")
        
        # Process the DOCX file
        result = book_content_service.process_docx_file(
            file_path=file_path,
            book_title=book_title,
            user_id=None  # No user authentication required
        )
        
        if not result['success']:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
        
        # Save the processed book to database
        save_result = book_content_service.save_processed_book(
            book_data=result['book_data'],
            user_id=None # No user authentication required
        )
        
        if save_result['success']:
            return jsonify({
                'success': True,
                'book_id': save_result['book_id'],
                'book_data': result['book_data'],
                'message': 'DOCX file processed and book created successfully'
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': save_result['message']
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"❌ Error processing DOCX file: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error processing DOCX file: {str(e)}'
        }), 500


@book_content_bp.route('/test', methods=['GET'])
def test_endpoint():
    """Simple test endpoint"""
    return jsonify({
        'success': True,
        'message': 'Book content routes are working!'
    }), 200


@book_content_bp.route('/book-content/<int:book_id>', methods=['GET'])
def get_book_content(book_id: int):
    """Get structured book content by ID"""
    try:
        current_app.logger.info(f"📚 Getting book content for book {book_id}")
        
        # Get book from database
        book = CustomBook.query.filter_by(id=book_id).first()
        
        if not book:
            return jsonify({
                'success': False,
                'message': 'Book not found'
            }), 404
        
        # Get chapters from the database
        chapters = BookChapter.query.filter_by(book_id=book.id).order_by(BookChapter.chapter_number).all()
        
        # Format chapters for response
        chapters_data = []
        for chapter in chapters:
            chapters_data.append({
                'id': chapter.id,
                'chapter_number': chapter.chapter_number,
                'title': chapter.title,
                'content': chapter.content_html,
                'html_content': chapter.content_html,
                'word_count': chapter.word_count
            })
        
        return jsonify({
            'success': True,
            'book': {
                'id': book.id,
                'title': book.title,
                'description': book.description,
                'content_type': 'docx_processed',
                'total_pages': book.total_content_items,
                'total_chapters': len(chapters_data),
                'chapters': chapters_data,
                'metadata': book.processing_metadata or {},
                'processing_info': {
                    'generation_status': book.generation_status,
                    'word_count': book.word_count
                },
                'created_at': book.created_at.isoformat() if book.created_at else None,
                'updated_at': book.updated_at.isoformat() if book.updated_at else None
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"❌ Error getting book content: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error retrieving book content: {str(e)}'
        }), 500


@book_content_bp.route('/book-chapter/<int:book_id>/<int:chapter_id>', methods=['GET'])
def get_book_chapter(book_id: int, chapter_id: int):
    """Get specific chapter content"""
    try:
        current_app.logger.info(f"📄 Getting chapter {chapter_id} for book {book_id}")
        
        # Get book from database
        book = CustomBook.query.filter_by(
            id=book_id,
            user_id=g.user_id
        ).first()
        
        if not book:
            return jsonify({
                'success': False,
                'message': 'Book not found'
            }), 404
        
        # Get specific chapter from database
        chapter = BookChapter.query.filter_by(
            book_id=book.id,
            id=chapter_id
        ).first()
        
        if not chapter:
            return jsonify({
                'success': False,
                'message': 'Chapter not found'
            }), 404
        
        # Get total chapter count
        total_chapters = BookChapter.query.filter_by(book_id=book.id).count()
        
        return jsonify({
            'success': True,
            'chapter': {
                'id': chapter.id,
                'chapter_number': chapter.chapter_number,
                'title': chapter.title,
                'content': chapter.content_html,
                'word_count': chapter.word_count
            },
            'book_info': {
                'id': book.id,
                'title': book.title,
                'total_chapters': total_chapters
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"❌ Error getting chapter: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error retrieving chapter: {str(e)}'
        }), 500


@book_content_bp.route('/books', methods=['GET'])
def list_books():
    """Get list of all available custom books"""
    try:
        current_app.logger.info(f"📚 Fetching books list")
        
        # Get all custom books
        books = CustomBook.query.all()
        
        books_data = []
        for book in books:
            chapter_count = BookChapter.query.filter_by(book_id=book.id).count()
            books_data.append({
                'id': book.id,
                'title': book.title,
                'description': getattr(book, 'description', None),
                'total_chapters': chapter_count,
                'created_at': book.created_at.isoformat() if book.created_at else None,
                'updated_at': book.updated_at.isoformat() if book.updated_at else None
            })
        
        current_app.logger.info(f"📖 Found {len(books_data)} books")
        
        return jsonify({
            'success': True,
            'books': books_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"❌ Error fetching books list: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error fetching books: {str(e)}'
        }), 500


# Initialize the default book if it doesn't exist
@book_content_bp.route('/initialize-default-book', methods=['POST'])
def initialize_default_book():
    """Initialize the default 'Way of the Dog Anahata' book from DOCX"""
    try:
        current_app.logger.info(f"🎯 Initializing default book")
        
        # Check if the book already exists
        existing_book = CustomBook.query.filter_by(
            user_id=g.user_id,
            title='The Way of the Dog Anahata'
        ).first()
        
        if existing_book:
            return jsonify({
                'success': True,
                'book_id': existing_book.id,
                'message': 'Default book already exists'
            }), 200
        
        # Process the DOCX file (using the path provided by user)
        docx_path = '/Users/aayushsaini/Downloads/Mr-White-Project/backend/The Way of the Dog Anahata 2025-5-13.docx'
        
        if not os.path.exists(docx_path):
            return jsonify({
                'success': False,
                'message': f'DOCX file not found at: {docx_path}'
            }), 404
        
        # Process the DOCX file
        result = book_content_service.process_docx_file(
            file_path=docx_path,
            book_title='The Way of the Dog Anahata',
            user_id=None # No user authentication required
        )
        
        if not result['success']:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
        
        # Save the processed book to database
        save_result = book_content_service.save_processed_book(
            book_data=result['book_data'],
            user_id=None # No user authentication required
        )
        
        if save_result['success']:
            return jsonify({
                'success': True,
                'book_id': save_result['book_id'],
                'message': 'Default book initialized successfully'
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': save_result['message']
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"❌ Error initializing default book: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error initializing default book: {str(e)}'
        }), 500


# Error handlers
@book_content_bp.errorhandler(404)
def book_content_not_found(error):
    return jsonify({
        'success': False,
        'message': 'Book content endpoint not found'
    }), 404


@book_content_bp.errorhandler(500)
def book_content_server_error(error):
    return jsonify({
        'success': False,
        'message': 'Internal server error in book content service'
    }), 500 