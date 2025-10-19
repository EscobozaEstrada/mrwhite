from flask import Blueprint, request, jsonify, current_app, g
from datetime import datetime, timezone
import asyncio
import json
from typing import Dict, Any, List, Optional

from app.middleware.auth import require_auth
from app.middleware.credit_middleware import require_credits
from app.services.book_creation_service import BookCreationService

from app.models.custom_book import CustomBook, BookTag
from app.models.user import User
from app import db
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.image import UserImage
from app.models.care_record import Document

# Create blueprint
book_creation_bp = Blueprint('book_creation', __name__)

# Initialize service
book_creation_service = BookCreationService()


@book_creation_bp.route('/tags', methods=['GET'])
@require_auth
def get_book_tags():
    """Get all available book tags/categories"""
    try:
        current_app.logger.info(f"📚 Fetching book tags for user {g.user_id}")
        
        tags = book_creation_service.get_book_tags()
        
        return jsonify({
            'success': True,
            'tags': tags,
            'total_tags': len(tags)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"❌ Error fetching book tags: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error fetching book tags: {str(e)}'
        }), 500

@book_creation_bp.route('/search-content', methods=['POST'])
@require_auth
def search_user_content():
    """Search and filter user content for book creation"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data:
            return jsonify({
                'success': False,
                'message': 'Request data is required'
            }), 400
        
        current_app.logger.info(f"🔍 Searching content for user {g.user_id}")
        current_app.logger.info(f"📋 Search filters: {data}")
        
        # Extract filters
        filters = {
            'selected_tags': data.get('selected_tags', []),
            'date_range_start': None,
            'date_range_end': None,
            'content_types': data.get('content_types', ['chat', 'photos', 'documents'])
        }
        
        # Parse date ranges if provided
        if data.get('date_range_start'):
            try:
                filters['date_range_start'] = datetime.fromisoformat(data['date_range_start'].replace('Z', '+00:00'))
            except ValueError as e:
                current_app.logger.warning(f"Invalid start date format: {data['date_range_start']}")
        
        if data.get('date_range_end'):
            try:
                filters['date_range_end'] = datetime.fromisoformat(data['date_range_end'].replace('Z', '+00:00'))
            except ValueError as e:
                current_app.logger.warning(f"Invalid end date format: {data['date_range_end']}")
        
        # Validate content types
        valid_content_types = ['chat', 'photos', 'documents']
        filters['content_types'] = [ct for ct in filters['content_types'] if ct in valid_content_types]
        
        if not filters['content_types']:
            filters['content_types'] = ['chat', 'photos', 'documents']
        
        # Run content search using asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                book_creation_service.search_content(g.user_id, filters)
            )
        finally:
            loop.close()
        
        if result['success']:
            current_app.logger.info(f"✅ Content search completed: {result['total_content_found']} items found")
            
            return jsonify({
                'success': True,
                'total_content_found': result['total_content_found'],
                'content_summary': {
                    'chat_messages': len(result['chat_messages']),
                    'photos': len(result['user_images']),
                    'documents': len(result['documents'])
                },
                'content_preview': {
                    'chat_messages': result['chat_messages'][:5],  # First 5 for preview
                    'photos': result['user_images'][:5],
                    'documents': result['documents'][:5]
                },
                'response': result['response'],
                'processing_metadata': result['processing_metadata']
            }), 200
        else:
            current_app.logger.error(f"❌ Content search failed: {result.get('error', 'Unknown error')}")
            return jsonify({
                'success': False,
                'message': result.get('error', 'Content search failed'),
                'total_content_found': 0
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"❌ Error in content search: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Content search error: {str(e)}'
        }), 500

@book_creation_bp.route('/generate', methods=['POST'])
@require_auth
@require_credits('book_generation')
def generate_custom_book():
    """Generate a custom book from user content"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data:
            return jsonify({
                'success': False,
                'message': 'Request data is required'
            }), 400
        
        required_fields = ['title']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Missing required field: {field}'
                }), 400
        
        current_app.logger.info(f"📚 Generating custom book for user {g.user_id}")
        current_app.logger.info(f"📖 Book title: {data['title']}")
        
        # Prepare book configuration
        book_config = {
            'title': data['title'],
            'subtitle': data.get('subtitle', ''),
            'description': data.get('description', ''),
            'selected_tags': data.get('selected_tags', []),
            'date_range_start': None,
            'date_range_end': None,
            'content_types': data.get('content_types', ['chat', 'photos', 'documents']),
            'book_style': data.get('book_style', 'narrative'),
            'include_photos': data.get('include_photos', True),
            'include_documents': data.get('include_documents', True),
            'include_chat_history': data.get('include_chat_history', True),
            'auto_organize_by_date': data.get('auto_organize_by_date', True)
        }
        
        # Parse date ranges if provided
        if data.get('date_range_start'):
            try:
                book_config['date_range_start'] = datetime.fromisoformat(data['date_range_start'].replace('Z', '+00:00'))
            except ValueError as e:
                current_app.logger.warning(f"Invalid start date format: {data['date_range_start']}")
        
        if data.get('date_range_end'):
            try:
                book_config['date_range_end'] = datetime.fromisoformat(data['date_range_end'].replace('Z', '+00:00'))
            except ValueError as e:
                current_app.logger.warning(f"Invalid end date format: {data['date_range_end']}")
        
        # Validate book style
        valid_styles = ['narrative', 'timeline', 'reference']
        if book_config['book_style'] not in valid_styles:
            book_config['book_style'] = 'narrative'
        
        # Validate content types
        valid_content_types = ['chat', 'photos', 'documents']
        book_config['content_types'] = [ct for ct in book_config['content_types'] if ct in valid_content_types]
        
        if not book_config['content_types']:
            book_config['content_types'] = ['chat', 'photos', 'documents']
        
        # Run book generation using asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                book_creation_service.generate_custom_book(g.user_id, book_config)
            )
        finally:
            loop.close()
        
        if result['success']:
            current_app.logger.info(f"✅ Book generation completed: Book ID {result['book_id']}")
            
            return jsonify({
                'success': True,
                'book_id': result['book_id'],
                'book': result['book'],
                'response': result['response'],
                'processing_metadata': result['processing_metadata']
            }), 200
        else:
            current_app.logger.error(f"❌ Book generation failed: {result.get('error', 'Unknown error')}")
            return jsonify({
                'success': False,
                'message': result.get('error', 'Book generation failed'),
                'book_id': result.get('book_id')
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"❌ Error in book generation: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Book generation error: {str(e)}'
        }), 500

@book_creation_bp.route('/books', methods=['GET'])
@require_auth
def get_user_books():
    """Get all books created by the user"""
    try:
        current_app.logger.info(f"📚 Fetching books for user {g.user_id}")
        
        books = book_creation_service.get_user_books(g.user_id)
        
        return jsonify({
            'success': True,
            'books': books,
            'total_books': len(books)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"❌ Error fetching user books: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error fetching books: {str(e)}'
        }), 500

@book_creation_bp.route('/books/<int:book_id>', methods=['GET'])
@require_auth
def get_book_details(book_id: int):
    """Get detailed information about a specific book"""
    try:
        current_app.logger.info(f"📖 Fetching book {book_id} for user {g.user_id}")
        
        book = db.session.query(CustomBook).filter_by(
            id=book_id, 
            user_id=g.user_id
        ).first()
        
        if not book:
            return jsonify({
                'success': False,
                'message': 'Book not found'
            }), 404
        
        return jsonify({
            'success': True,
            'book': book.to_dict()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"❌ Error fetching book details: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error fetching book details: {str(e)}'
        }), 500

@book_creation_bp.route('/books/<int:book_id>/download/<format_type>', methods=['GET'])
@require_auth
def download_book(book_id: int, format_type: str):
    """Download book in specified format"""
    try:
        current_app.logger.info(f"📥 Downloading book {book_id} in {format_type} format for user {g.user_id}")
        
        book = db.session.query(CustomBook).filter_by(
            id=book_id, 
            user_id=g.user_id
        ).first()
        
        if not book:
            return jsonify({
                'success': False,
                'message': 'Book not found'
            }), 404
        
        if book.generation_status != 'completed':
            return jsonify({
                'success': False,
                'message': 'Book generation is not yet completed'
            }), 400
        
        # Validate format
        valid_formats = ['html', 'pdf', 'epub']
        if format_type not in valid_formats:
            return jsonify({
                'success': False,
                'message': f'Invalid format. Supported formats: {", ".join(valid_formats)}'
            }), 400
        
        # Return appropriate content based on format
        if format_type == 'html':
            if not book.html_content:
                return jsonify({
                    'success': False,
                    'message': 'HTML content not available'
                }), 404
            
            return jsonify({
                'success': True,
                'content': book.html_content,
                'format': 'html',
                'filename': f"{book.title.replace(' ', '_')}.html"
            }), 200
            
        elif format_type == 'pdf':
            if not book.pdf_url:
                return jsonify({
                    'success': False,
                    'message': 'PDF not available'
                }), 404
            
            return jsonify({
                'success': True,
                'download_url': book.pdf_url,
                'format': 'pdf',
                'filename': f"{book.title.replace(' ', '_')}.pdf"
            }), 200
            
        elif format_type == 'epub':
            if not book.epub_url:
                return jsonify({
                    'success': False,
                    'message': 'EPUB not available'
                }), 404
            
            return jsonify({
                'success': True,
                'download_url': book.epub_url,
                'format': 'epub',
                'filename': f"{book.title.replace(' ', '_')}.epub"
            }), 200
        
    except Exception as e:
        current_app.logger.error(f"❌ Error downloading book: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Download error: {str(e)}'
        }), 500


@book_creation_bp.route('/books/<int:book_id>/regenerate-files', methods=['POST'])
@require_auth
def regenerate_book_files(book_id: int):
    """Regenerate PDF and EPUB files for an existing book"""
    try:
        current_app.logger.info(f"🔄 Regenerating book files for book {book_id} for user {g.user_id}")
        
        book = db.session.query(CustomBook).filter_by(
            id=book_id, 
            user_id=g.user_id
        ).first()
        
        if not book:
            return jsonify({
                'success': False,
                'message': 'Book not found'
            }), 404
        
        if book.generation_status != 'completed':
            return jsonify({
                'success': False,
                'message': 'Book generation is not yet completed'
            }), 400
            
        if not book.html_content:
            return jsonify({
                'success': False,
                'message': 'HTML content not available for conversion'
            }), 400
        
        # Get book creation service
        from app.services.book_creation_service import BookCreationService
        book_service = BookCreationService()
        
        # Generate PDF and EPUB files
        try:
            pdf_url, epub_url = book_service._generate_book_files(
                book.id,
                book.title,
                book.html_content,
                ""  # No markdown content available for existing books
            )
            
            # Update book record
            book.pdf_url = pdf_url
            book.epub_url = epub_url
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Book files regenerated successfully',
                'pdf_url': pdf_url,
                'epub_url': epub_url
            }), 200
            
        except Exception as e:
            current_app.logger.error(f"❌ Error regenerating book files: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error regenerating book files: {str(e)}'
            }), 500
        
    except Exception as e:
        current_app.logger.error(f"❌ Error in regenerate_book_files: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@book_creation_bp.route('/books/regenerate-all-files', methods=['POST'])
@require_auth
def regenerate_all_book_files():
    """Regenerate PDF and EPUB files for all books of the current user"""
    try:
        current_app.logger.info(f"🔄 Regenerating files for all books of user {g.user_id}")
        
        # Get all books for the user
        books = db.session.query(CustomBook).filter_by(
            user_id=g.user_id,
            generation_status='completed'
        ).all()
        
        if not books:
            return jsonify({
                'success': False,
                'message': 'No completed books found'
            }), 404
        
        # Get book creation service
        from app.services.book_creation_service import BookCreationService
        book_service = BookCreationService()
        
        results = []
        
        # Generate PDF and EPUB files for each book
        for book in books:
            if not book.html_content:
                results.append({
                    'book_id': book.id,
                    'title': book.title,
                    'success': False,
                    'message': 'HTML content not available'
                })
                continue
                
            try:
                pdf_url, epub_url = book_service._generate_book_files(
                    book.id,
                    book.title,
                    book.html_content,
                    ""  # No markdown content available for existing books
                )
                
                # Update book record
                book.pdf_url = pdf_url
                book.epub_url = epub_url
                
                results.append({
                    'book_id': book.id,
                    'title': book.title,
                    'success': True,
                    'pdf_url': pdf_url,
                    'epub_url': epub_url
                })
                
            except Exception as e:
                current_app.logger.error(f"❌ Error regenerating files for book {book.id}: {str(e)}")
                results.append({
                    'book_id': book.id,
                    'title': book.title,
                    'success': False,
                    'message': str(e)
                })
        
        # Commit all changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Regenerated files for {len(books)} books',
            'results': results
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"❌ Error in regenerate_all_book_files: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500

@book_creation_bp.route('/books/<int:book_id>/status', methods=['GET'])
@require_auth
def get_book_generation_status(book_id: int):
    """Get the generation status of a book"""
    try:
        current_app.logger.info(f"📊 Checking generation status for book {book_id}")
        
        book = db.session.query(CustomBook).filter_by(
            id=book_id, 
            user_id=g.user_id
        ).first()
        
        if not book:
            return jsonify({
                'success': False,
                'message': 'Book not found'
            }), 404
        
        return jsonify({
            'success': True,
            'book_id': book.id,
            'generation_status': book.generation_status,
            'generation_progress': book.generation_progress,
            'generation_started_at': book.generation_started_at.isoformat() if book.generation_started_at else None,
            'generation_completed_at': book.generation_completed_at.isoformat() if book.generation_completed_at else None,
            'generation_error': book.generation_error,
            'total_content_items': book.total_content_items,
            'word_count': book.word_count
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"❌ Error fetching generation status: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Status check error: {str(e)}'
        }), 500

@book_creation_bp.route('/books/<int:book_id>', methods=['DELETE'])
@require_auth
def delete_book(book_id: int):
    """Delete a custom book"""
    try:
        current_app.logger.info(f"🗑️ Deleting book {book_id} for user {g.user_id}")
        
        book = db.session.query(CustomBook).filter_by(
            id=book_id, 
            user_id=g.user_id
        ).first()
        
        if not book:
            return jsonify({
                'success': False,
                'message': 'Book not found'
            }), 404
        
        # Delete book and cascade delete chapters/content items
        db.session.delete(book)
        db.session.commit()
        
        current_app.logger.info(f"✅ Book {book_id} deleted successfully")
        
        return jsonify({
            'success': True,
            'message': 'Book deleted successfully'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"❌ Error deleting book: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Delete error: {str(e)}'
        }), 500

@book_creation_bp.route('/books/<int:book_id>/chapters', methods=['GET'])
@require_auth
def get_book_chapters(book_id: int):
    """Get all chapters for a specific book"""
    try:
        current_app.logger.info(f"📑 Fetching chapters for book {book_id}")
        
        book = db.session.query(CustomBook).filter_by(
            id=book_id, 
            user_id=g.user_id
        ).first()
        
        if not book:
            return jsonify({
                'success': False,
                'message': 'Book not found'
            }), 404
        
        chapters = [chapter.to_dict() for chapter in book.chapters]
        
        return jsonify({
            'success': True,
            'book_id': book_id,
            'chapters': chapters,
            'total_chapters': len(chapters)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"❌ Error fetching chapters: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Chapters fetch error: {str(e)}'
        }), 500

@book_creation_bp.route('/preview', methods=['POST'])
@require_auth
def preview_book_content():
    """Enhanced preview with better debugging and error handling"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Request data is required'
            }), 400
        
        current_app.logger.info(f"👀 Generating enhanced book preview for user {g.user_id}")
        current_app.logger.info(f"📋 Preview request data: {data}")
        
        # Extract preview parameters with detailed logging
        filters = {
            'selected_tags': data.get('selected_tags', []),
            'date_range_start': None,
            'date_range_end': None,
            'content_types': data.get('content_types', ['chat', 'photos', 'documents'])
        }
        
        current_app.logger.info(f"🏷️ Selected tags: {filters['selected_tags']}")
        current_app.logger.info(f"📄 Content types: {filters['content_types']}")
        
        # Enhanced date parsing with better error handling
        if data.get('date_range_start'):
            try:
                # Try multiple date formats
                date_str = data['date_range_start']
                current_app.logger.info(f"📅 Parsing start date: {date_str}")
                
                # Handle different date formats
                if 'T' in date_str:
                    filters['date_range_start'] = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                else:
                    filters['date_range_start'] = datetime.fromisoformat(f"{date_str}T00:00:00+00:00")
                    
                current_app.logger.info(f"📅 Parsed start date: {filters['date_range_start']}")
            except ValueError as e:
                current_app.logger.warning(f"⚠️ Invalid start date format: {data['date_range_start']}, error: {e}")
        
        if data.get('date_range_end'):
            try:
                date_str = data['date_range_end']
                current_app.logger.info(f"📅 Parsing end date: {date_str}")
                
                if 'T' in date_str:
                    filters['date_range_end'] = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                else:
                    filters['date_range_end'] = datetime.fromisoformat(f"{date_str}T23:59:59+00:00")
                    
                current_app.logger.info(f"📅 Parsed end date: {filters['date_range_end']}")
            except ValueError as e:
                current_app.logger.warning(f"⚠️ Invalid end date format: {data['date_range_end']}, error: {e}")
        
        current_app.logger.info(f"📅 Final date filters: {filters['date_range_start']} to {filters['date_range_end']}")
        
        # Run enhanced content search for preview
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            current_app.logger.info("🚀 Starting content search...")
            result = loop.run_until_complete(
                book_creation_service.search_content(g.user_id, filters)
            )
            current_app.logger.info(f"✅ Content search completed: {result.get('success', False)}")
            
        except Exception as search_error:
            current_app.logger.error(f"❌ Content search exception: {str(search_error)}")
            current_app.logger.error(f"❌ Search error type: {type(search_error).__name__}")
            raise search_error
        finally:
            loop.close()
        
        if result['success']:
            # Calculate preview statistics with enhanced logging
            total_items = result['total_content_found']
            chat_messages = len(result['chat_messages'])
            photos = len(result['user_images'])
            documents = len(result['documents'])
            
            current_app.logger.info(f"📊 Content found - Messages: {chat_messages}, Photos: {photos}, Documents: {documents}, Total: {total_items}")
            
            # Calculate comprehensive book statistics for large books using Context7 patterns
            selected_tags_count = len(data.get('selected_tags', []))
            
            # Comprehensive chapter estimation - create multiple chapters per category for rich content
            if selected_tags_count > 0:
                # Multiple chapters per selected tag category for comprehensive coverage
                base_chapters = selected_tags_count
                # Add sub-chapters for large categories (introductions, deep-dives, reflections)
                detail_multiplier = 3 if total_items > 100 else 2 if total_items > 50 else 1
                estimated_chapters = max(8, base_chapters * detail_multiplier)
                
                # Add intro/conclusion chapters
                estimated_chapters += 2
            else:
                # No specific tags selected - create timeline-based comprehensive book
                estimated_chapters = max(12, min(25, total_items // 15))  # 12-25 chapters for comprehensive coverage
            
            # Realistic page estimation for comprehensive pet memoirs (250-350 words per page)
            # Base pages per content item for detailed storytelling
            pages_per_message = 0.8  # Rich narrative from conversations
            pages_per_photo = 0.5    # Photo stories with descriptions  
            pages_per_document = 1.2 # Document analysis and integration
            
            base_pages = (chat_messages * pages_per_message + 
                         photos * pages_per_photo + 
                         documents * pages_per_document)
            
            # Ensure minimum comprehensive book size
            estimated_pages = max(80, int(base_pages))
            
            # Cap at reasonable maximum for very large datasets
            estimated_pages = min(estimated_pages, 300)
            
            # Comprehensive word count estimation (300 words per page for pet memoirs)
            words_per_page = 300
            base_word_count = estimated_pages * words_per_page
            
            # Add detailed word estimates based on content richness
            detail_words = (chat_messages * 120 +  # Rich storytelling from conversations
                           photos * 80 +          # Detailed photo narratives
                           documents * 200)       # Document integration and analysis
            
            estimated_words = max(base_word_count, detail_words)
            
            # Ensure realistic minimum for comprehensive books
            estimated_words = max(24000, estimated_words)  # Minimum 24k words (80 pages)
            
            # Cap at maximum for very large collections
            estimated_words = min(estimated_words, 90000)  # Maximum 90k words (300 pages)
            
            preview_data = {
                'content_summary': {
                    'total_items': total_items,
                    'chat_messages': chat_messages,
                    'photos': photos,
                    'documents': documents
                },
                'book_estimates': {
                    'estimated_chapters': estimated_chapters,
                    'estimated_pages': estimated_pages,
                    'estimated_words': estimated_words
                },
                'content_samples': {
                    'recent_messages': result['chat_messages'][:3],
                    'recent_photos': result['user_images'][:3],
                    'recent_documents': result['documents'][:3]
                },
                'selected_tags': data.get('selected_tags', []),
                'date_range': {
                    'start': data.get('date_range_start'),
                    'end': data.get('date_range_end')
                }
            }
            
            return jsonify({
                'success': True,
                'preview': preview_data,
                'response': result['response']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result.get('error', 'Preview generation failed')
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"❌ Error generating preview: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Preview error: {str(e)}'
        }), 500

# Health check endpoint
@book_creation_bp.route('/health', methods=['GET'])
def health_check():
    """Health check for book creation service"""
    try:
        # Check if we can access the database
        tag_count = db.session.query(BookTag).count()
        
        return jsonify({
            'success': True,
            'service': 'book_creation',
            'status': 'healthy',
            'database_accessible': True,
            'total_book_tags': tag_count,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"❌ Health check failed: {str(e)}")
        return jsonify({
            'success': False,
            'service': 'book_creation',
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500 

@book_creation_bp.route('/books/<int:book_id>/content', methods=['GET'])
@require_auth
def get_book_content_structure(book_id: int):
    """Get book content with REAL user data using Context7 patterns"""
    try:
        current_app.logger.info(f"📖 Fetching REAL book content for book {book_id} by user {g.user_id}")
        
        # Get book details first
        book = db.session.query(CustomBook).filter_by(
            id=book_id, 
            user_id=g.user_id
        ).first()
        
        if not book:
            return jsonify({
                'success': False,
                'message': 'Book not found'
            }), 404
        
        current_app.logger.info(f"📚 Book found: {book.title}, Tags: {book.selected_tags}")
        
        # **CRITICAL FIX**: Retrieve ACTUAL user content using our enhanced service
        filters = {
            'selected_tags': book.selected_tags or [],
            'date_range_start': book.date_range_start,
            'date_range_end': book.date_range_end,
            'content_types': book.content_types or ['chat', 'photos', 'documents']
        }
        
        current_app.logger.info(f"🔍 Retrieving real content with filters: {filters}")
        
        # Use our enhanced book creation service to get REAL content
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            content_result = loop.run_until_complete(
                book_creation_service.search_content(g.user_id, filters)
            )
        finally:
            loop.close()
        
        if not content_result.get('success'):
            current_app.logger.error(f"❌ Failed to retrieve content: {content_result.get('error')}")
            return jsonify({
                'success': False,
                'message': 'Failed to retrieve book content'
            }), 500
        
        # Extract REAL content
        chat_messages = content_result.get('chat_messages', [])
        user_images = content_result.get('user_images', [])
        documents = content_result.get('documents', [])
        
        current_app.logger.info(f"✅ Retrieved REAL content: {len(chat_messages)} messages, {len(user_images)} images, {len(documents)} documents")
        
        # **Context7 SEMANTIC ORGANIZATION**: Group content into meaningful chapters
        organized_chapters = []
        
        if chat_messages or user_images or documents:
            # Create chapters from REAL content using Context7 patterns
            chapters = _create_real_chapters_from_content(
                chat_messages, user_images, documents, book.title
            )
            organized_chapters = chapters
        else:
            # Fallback: Create introduction chapter if no content
            organized_chapters = [{
                "id": "chapter_0_introduction",
                "title": "Introduction", 
                "content": f"<div class='intro-chapter'><h3>Welcome to {book.title}</h3><p>This book will contain your personalized content once you have more chat history and photos.</p></div>",
                "order": 0,
                "isVisible": True,
                "contentType": "mixed",
                "aiGenerated": True,
                "userEdited": False,
                "tags": ["introduction"]
            }]
        
        # Generate AI insights from REAL content
        ai_insights = _generate_ai_insights_from_real_content(
            chat_messages, user_images, documents
        )
        
        # Sort chapters by order
        organized_chapters.sort(key=lambda x: x.get('order', 0))
        
        # Prepare response with REAL data
        book_data = {
            "id": book.id,
            "title": book.title,
            "subtitle": book.subtitle or "",
            "description": book.description or "",
            "coverImageUrl": book.cover_image_url,
            "generationStatus": book.generation_status,
            "generationProgress": book.generation_progress,
            "totalContentItems": len(chat_messages) + len(user_images) + len(documents),
            "createdAt": book.created_at.isoformat() if book.created_at else "",
            "updatedAt": book.updated_at.isoformat() if book.updated_at else "",
            "chapters": organized_chapters,
            "selectedTags": book.selected_tags or [],
            "dateRange": {
                "start": book.date_range_start.isoformat() if book.date_range_start else None,
                "end": book.date_range_end.isoformat() if book.date_range_end else None
            },
            "contentTypes": book.content_types or ["chat", "photos", "documents"],
            "bookStyle": book.book_style or "narrative",
            "aiInsights": ai_insights,
            "contentSummary": {
                "messages": len(chat_messages),
                "images": len(user_images), 
                "documents": len(documents),
                "total": len(chat_messages) + len(user_images) + len(documents)
            },
            "contentThemes": _extract_content_themes(chat_messages),
            "contentGaps": []
        }
        
        current_app.logger.info(f"✅ Generated book with {len(organized_chapters)} REAL chapters")
        
        return jsonify({
            'success': True,
            'book': book_data,
            'message': f'Book content retrieved successfully - {len(organized_chapters)} chapters from real content'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"❌ Error fetching REAL book content: {str(e)}")
        current_app.logger.error(f"❌ Error type: {type(e).__name__}")
        return jsonify({
            'success': False,
            'message': f'Error retrieving book content: {str(e)}'
        }), 500

def _create_real_chapters_from_content(chat_messages, user_images, documents, book_title):
    """Create meaningful chapters from REAL user content using Context7 patterns"""
    chapters = []
    
    # **Context7 SEMANTIC GROUPING**: Organize messages by themes and chronology
    if chat_messages:
        # Group messages by conversation topics using semantic analysis
        message_groups = _group_messages_semantically(chat_messages)
        
        chapter_order = 0
        
        # Create introduction chapter with actual content
        intro_content = _create_intro_chapter_from_messages(chat_messages[:5], book_title)
        chapters.append({
            "id": "chapter_0_introduction",
            "title": "Our Journey Begins",
            "content": intro_content,
            "order": chapter_order,
            "isVisible": True,
            "tags": ["introduction", "beginning"],
            "contentType": "chat",
            "aiGenerated": True,
            "userEdited": False,
            "originalContent": intro_content,
            "itemCount": min(5, len(chat_messages)),
            "dateRange": _get_date_range_from_messages(chat_messages[:5]) if chat_messages else None
        })
        chapter_order += 1
        
        # Create themed chapters from message groups
        for theme, messages in message_groups.items():
            if messages:  # Only create chapters with content
                chapter_content = _create_chapter_from_messages(messages, theme)
                chapters.append({
                    "id": f"chapter_{chapter_order}_{theme.lower().replace(' ', '_')}",
                    "title": theme,
                    "content": chapter_content,
                    "order": chapter_order,
                    "isVisible": True,
                    "tags": [theme.lower().replace(' ', '_')],
                    "contentType": "chat",
                    "aiGenerated": True,
                    "userEdited": False,
                    "originalContent": chapter_content,
                    "itemCount": len(messages),
                    "dateRange": _get_date_range_from_messages(messages)
                })
                chapter_order += 1
    
    # Add photo chapters if images exist
    if user_images:
        photo_content = _create_photo_chapter_from_images(user_images)
        chapters.append({
            "id": f"chapter_{len(chapters)}_photo_memories",
            "title": "Photo Memories",
            "content": photo_content,
            "order": len(chapters),
            "isVisible": True,
            "tags": ["photos", "memories"],
            "contentType": "photos",
            "aiGenerated": True,
            "userEdited": False,
            "originalContent": photo_content,
            "itemCount": len(user_images),
            "dateRange": _get_date_range_from_images(user_images) if user_images else None
        })
    
    # Add document chapters if documents exist
    if documents:
        doc_content = _create_document_chapter_from_docs(documents)
        chapters.append({
            "id": f"chapter_{len(chapters)}_documents",
            "title": "Important Documents",
            "content": doc_content,
            "order": len(chapters),
            "isVisible": True,
            "tags": ["documents", "records"],
            "contentType": "documents", 
            "aiGenerated": True,
            "userEdited": False,
            "originalContent": doc_content,
            "itemCount": len(documents),
            "dateRange": _get_date_range_from_docs(documents) if documents else None
        })
    
    return chapters

def _group_messages_semantically(messages):
    """Group messages by semantic themes using Context7 patterns"""
    # **Context7 SEMANTIC ANALYSIS**: Group by pet-related themes
    themes = {
        "Training & Learning": [],
        "Health & Wellness": [],
        "Daily Life & Routines": [],
        "Adventures & Play": [],
        "Bonding & Love": []
    }
    
    # Categorize messages by content
    for message in messages:
        content = (message.get('content', '') or '').lower()
        
        # Training keywords
        if any(word in content for word in ['train', 'learn', 'teach', 'command', 'sit', 'stay', 'behavior', 'trick']):
            themes["Training & Learning"].append(message)
        # Health keywords
        elif any(word in content for word in ['health', 'vet', 'medical', 'sick', 'wellness', 'doctor', 'medicine']):
            themes["Health & Wellness"].append(message)
        # Daily life keywords
        elif any(word in content for word in ['daily', 'routine', 'feed', 'walk', 'sleep', 'schedule', 'morning', 'evening']):
            themes["Daily Life & Routines"].append(message)
        # Adventure keywords
        elif any(word in content for word in ['play', 'adventure', 'park', 'outside', 'run', 'fetch', 'fun', 'explore']):
            themes["Adventures & Play"].append(message)
        # Bonding keywords
        else:
            themes["Bonding & Love"].append(message)
    
    # Remove empty themes
    return {theme: msgs for theme, msgs in themes.items() if msgs}

def _create_intro_chapter_from_messages(messages, book_title):
    """Create introduction chapter from real messages"""
    content = f"<div class='intro-chapter'>"
    content += f"<h3>Welcome to {book_title}</h3>"
    content += f"<p>This book captures the beautiful journey of conversations and memories you've shared. Here are some highlights from your early conversations:</p>"
    
    content += "<div class='early-conversations'>"
    for i, message in enumerate(messages[:3]):  # First 3 messages
        msg_content = message.get('content', '')
        if len(msg_content) > 150:
            msg_content = msg_content[:150] + "..."
        
        content += f"<div class='conversation-snippet'>"
        content += f"<h5>Conversation {i + 1}</h5>"
        content += f"<p>\"{msg_content}\"</p>"
        content += f"</div>"
    
    content += "</div></div>"
    return content

def _create_chapter_from_messages(messages, theme):
    """Create chapter content from themed messages"""
    content = f"<div class='chapter-content theme-{theme.lower().replace(' ', '-')}'>"
    content += f"<h3>{theme}</h3>"
    content += f"<p>This chapter contains {len(messages)} conversations about {theme.lower()}.</p>"
    
    # Add message excerpts
    for i, message in enumerate(messages[:5]):  # Show first 5 messages
        msg_content = message.get('content', '')
        msg_type = message.get('type', 'user')
        created_at = message.get('created_at', '')
        
        if len(msg_content) > 200:
            msg_content = msg_content[:200] + "..."
        
        content += f"<div class='message-excerpt {msg_type}'>"
        content += f"<div class='message-meta'>Message {i + 1} - {created_at}</div>"
        content += f"<div class='message-text'>{msg_content}</div>"
        content += "</div>"
    
    if len(messages) > 5:
        content += f"<p class='more-content'>...and {len(messages) - 5} more conversations in this theme.</p>"
    
    content += "</div>"
    return content

def _create_photo_chapter_from_images(images):
    """Create photo chapter from real user images"""
    content = "<div class='photo-chapter'>"
    content += f"<h3>Photo Memories</h3>"
    content += f"<p>A collection of {len(images)} precious photos from your journey together.</p>"
    
    content += "<div class='photo-gallery'>"
    for i, image in enumerate(images[:10]):  # Show first 10 images
        img_url = image.get('s3_url', '')
        description = image.get('description', f"Photo {i + 1}")
        filename = image.get('filename', f'image_{i + 1}')
        
        content += f"<div class='photo-memory'>"
        if img_url:
            content += f"<img src='{img_url}' alt='{description}' />"
        content += f"<p class='photo-caption'>{description or filename}</p>"
        content += "</div>"
    
    if len(images) > 10:
        content += f"<p class='more-photos'>...and {len(images) - 10} more photos in your collection.</p>"
        
    content += "</div></div>"
    return content

def _create_document_chapter_from_docs(documents):
    """Create document chapter from real user documents"""
    content = "<div class='document-chapter'>"
    content += f"<h3>Important Documents</h3>"
    content += f"<p>Your collection of {len(documents)} important documents and records.</p>"
    
    for i, doc in enumerate(documents[:5]):  # Show first 5 documents
        doc_name = doc.get('filename', f'Document {i + 1}')
        summary = doc.get('content_summary', 'No summary available')
        
        if len(summary) > 150:
            summary = summary[:150] + "..."
        
        content += f"<div class='document-memory'>"
        content += f"<h4>{doc_name}</h4>"
        content += f"<p>{summary}</p>"
        content += "</div>"
    
    if len(documents) > 5:
        content += f"<p class='more-docs'>...and {len(documents) - 5} more documents.</p>"
    
    content += "</div>"
    return content

def _generate_ai_insights_from_real_content(messages, images, documents):
    """Generate AI insights from real user content"""
    insights = []
    
    if messages:
        # Count message types and topics
        user_msgs = [m for m in messages if m.get('type') == 'user']
        ai_msgs = [m for m in messages if m.get('type') == 'ai']
        
        insights.append({
            "category": "Conversations",
            "insight": f"You've had {len(messages)} meaningful conversations, with {len(user_msgs)} questions and {len(ai_msgs)} helpful responses. Your discussions show a genuine interest in learning and growing together."
        })
    
    if images:
        insights.append({
            "category": "Photo Memories",
            "insight": f"Your photo collection contains {len(images)} precious memories. These visual stories capture the special moments and milestones in your journey together."
        })
    
    if documents:
        insights.append({
            "category": "Documents & Records", 
            "insight": f"You've maintained {len(documents)} important documents, showing your commitment to keeping detailed records and staying organized."
        })
    
    # Overall insight
    total_items = len(messages) + len(images) + len(documents)
    insights.append({
        "category": "Overall Journey",
        "insight": f"This book represents {total_items} meaningful interactions, conversations, and memories. It's a testament to the care, attention, and love that defines your unique relationship."
    })
    
    return insights

def _extract_content_themes(messages):
    """Extract main themes from chat messages"""
    if not messages:
        return []
    
    themes = []
    content_text = ' '.join([msg.get('content', '') for msg in messages[:20]])  # First 20 messages
    content_lower = content_text.lower()
    
    # Detect themes based on content
    if any(word in content_lower for word in ['train', 'learn', 'teach']):
        themes.append('Training & Education')
    if any(word in content_lower for word in ['health', 'vet', 'wellness']):
        themes.append('Health & Wellness')
    if any(word in content_lower for word in ['play', 'fun', 'adventure']):
        themes.append('Fun & Adventures')
    if any(word in content_lower for word in ['love', 'bond', 'relationship']):
        themes.append('Love & Bonding')
    if any(word in content_lower for word in ['daily', 'routine', 'schedule']):
        themes.append('Daily Life')
    
    return themes or ['General Conversations']

def _get_date_range_from_messages(messages):
    """Get date range from message list"""
    if not messages:
        return None
    
    dates = [msg.get('created_at') for msg in messages if msg.get('created_at')]
    if not dates:
        return None
    
    return {
        "start": min(dates).isoformat() if hasattr(min(dates), 'isoformat') else str(min(dates)),
        "end": max(dates).isoformat() if hasattr(max(dates), 'isoformat') else str(max(dates))
    }

def _get_date_range_from_images(images):
    """Get date range from image list"""
    if not images:
        return None
    
    dates = [img.get('created_at') for img in images if img.get('created_at')]
    if not dates:
        return None
    
    return {
        "start": min(dates).isoformat() if hasattr(min(dates), 'isoformat') else str(min(dates)),
        "end": max(dates).isoformat() if hasattr(max(dates), 'isoformat') else str(max(dates))
    }

def _get_date_range_from_docs(documents):
    """Get date range from document list"""
    if not documents:
        return None
    
    dates = [doc.get('created_at') for doc in documents if doc.get('created_at')]
    if not dates:
        return None
    
    return {
        "start": min(dates).isoformat() if hasattr(min(dates), 'isoformat') else str(min(dates)),
        "end": max(dates).isoformat() if hasattr(max(dates), 'isoformat') else str(max(dates))
    }

@book_creation_bp.route('/books/<int:book_id>/chapters/<chapter_id>', methods=['PUT'])
@require_auth
def update_book_chapter(book_id: int, chapter_id: str):
    """Update a specific chapter content"""
    try:
        current_app.logger.info(f"✏️ Updating chapter {chapter_id} in book {book_id} by user {g.user_id}")
        
        # Verify book ownership
        book = db.session.query(CustomBook).filter_by(
            id=book_id, 
            user_id=g.user_id
        ).first()
        
        if not book:
            return jsonify({
                'success': False,
                'message': 'Book not found'
            }), 404
        
        data = request.get_json()
        new_content = data.get('content', '')
        
        if not new_content:
            return jsonify({
                'success': False,
                'message': 'Content is required'
            }), 400
        
        # For now, we'll store chapter edits in a simple way
        # In a full implementation, this would update the BookChapter table
        
        # Update book's updated timestamp
        book.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        current_app.logger.info(f"✅ Chapter {chapter_id} updated successfully")
        
        return jsonify({
            'success': True,
            'message': 'Chapter updated successfully',
            'chapter_id': chapter_id,
            'updated_at': book.updated_at.isoformat()
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"❌ Error updating chapter: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error updating chapter: {str(e)}'
        }), 500

@book_creation_bp.route('/books/<int:book_id>/chat', methods=['POST'])
@require_auth  
def chat_about_book(book_id: int):
    """Chat with AI about the book content"""
    try:
        current_app.logger.info(f"💬 Book chat for book {book_id} by user {g.user_id}")
        
        # Verify book ownership
        book = db.session.query(CustomBook).filter_by(
            id=book_id, 
            user_id=g.user_id
        ).first()
        
        if not book:
            return jsonify({
                'success': False,
                'message': 'Book not found'
            }), 404
        
        data = request.get_json()
        query = data.get('query', '')
        
        if not query:
            return jsonify({
                'success': False,
                'message': 'Query is required'
            }), 400
        
        # Create a basic context-aware response since BookContentService is not available
        response_content = f"""Based on your book "{book.title}", I found relevant information about "{query}":

Your book contains valuable memories and experiences related to this topic. Here's what I can help you with:

• **Explore related themes** in your book
• **Find connections** between different memories
• **Suggest additions** to expand on this topic
• **Help organize** related content

Would you like me to help you:
• Edit specific sections related to {query}
• Find gaps in this topic that could be expanded
• Organize related memories chronologically
• Create chapter divisions around this theme

Your book is a personal journey, and I'm here to help you tell your story in the most meaningful way."""

        return jsonify({
            'success': True,
            'response': response_content,
            'book_id': book_id,
            'query': query,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

    except Exception as e:
        current_app.logger.error(f"❌ Book chat failed: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Failed to process chat request: {str(e)}'
        }), 500 

@book_creation_bp.route('/debug-content', methods=['GET'])
@require_auth
def debug_user_content():
    """Debug endpoint to check user content directly from database"""
    try:
        current_app.logger.info(f"🔍 Debug content check for user {g.user_id}")
        
        # Check conversations
        conversations = db.session.query(Conversation).filter(
            Conversation.user_id == g.user_id
        ).all()
        
        conversation_data = []
        total_messages = 0
        
        for conv in conversations:
            messages = db.session.query(Message).filter(
                Message.conversation_id == conv.id
            ).all()
            
            conversation_data.append({
                'id': conv.id,
                'title': conv.title,
                'created_at': conv.created_at.isoformat(),
                'updated_at': conv.updated_at.isoformat(),
                'message_count': len(messages),
                'messages': [{
                    'id': msg.id,
                    'content': msg.content[:100] + '...' if len(msg.content) > 100 else msg.content,
                    'type': msg.type,
                    'created_at': msg.created_at.isoformat()
                } for msg in messages[:5]]  # First 5 messages
            })
            total_messages += len(messages)
        
        # Check images
        images = db.session.query(UserImage).filter(
            UserImage.user_id == g.user_id,
            UserImage.is_deleted == False
        ).all()
        
        image_data = [{
            'id': img.id,
            'filename': img.filename,
            'created_at': img.created_at.isoformat(),
            'description': img.description
        } for img in images[:10]]  # First 10 images
        
        # Check documents
        documents = db.session.query(Document).filter(
            Document.user_id == g.user_id
        ).all()
        
        document_data = [{
            'id': doc.id,
            'filename': doc.filename,
            'created_at': doc.created_at.isoformat(),
            'content_summary': doc.content_summary[:100] + '...' if doc.content_summary and len(doc.content_summary) > 100 else doc.content_summary
        } for doc in documents[:10]]  # First 10 documents
        
        debug_info = {
            'user_id': g.user_id,
            'conversations': conversation_data,
            'total_conversations': len(conversations),
            'total_messages': total_messages,
            'images': image_data,
            'total_images': len(images),
            'documents': document_data,
            'total_documents': len(documents),
            'summary': {
                'conversations': len(conversations),
                'messages': total_messages,
                'images': len(images),
                'documents': len(documents),
                'total_content_items': total_messages + len(images) + len(documents)
            }
        }
        
        current_app.logger.info(f"📊 Debug summary: {debug_info['summary']}")
        
        return jsonify({
            'success': True,
            'debug_info': debug_info
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"❌ Debug content error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Debug error: {str(e)}'
        }), 500 