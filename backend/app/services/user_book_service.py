from flask import current_app
from app import db
from app.models.user_book import UserBookCopy, ReadingProgress, BookNote, BookHighlight, ReadingSession
from app.models.user import User
from datetime import datetime, timezone, timedelta
import json
from typing import Dict, Any, List, Optional
from sqlalchemy import and_, or_, func, desc
from app.services.pinecone_integration_service import PineconeBookNotesService
import os


class UserBookService:
    """Service for managing user book copies, progress, notes, and highlights"""
    
    # Default public book information
    PUBLIC_BOOK_INFO = {
        'title': 'The Way of the Dog Anahata',
        'type': 'public',
        'pdf_url': os.getenv('FRONTEND_URL') + '/books/the-way-of-the-dog-anahata.pdf',
        'total_pages': 110,  # Will be detected automatically from local PDF
        'description': 'A comprehensive guide to understanding and training dogs through ancient wisdom and modern techniques.'
    }
    
    def __init__(self):
        self.pinecone_service = PineconeBookNotesService()
    
    @staticmethod
    def get_or_create_user_book_copy(user_id: int, book_title: str = None, book_type: str = 'public', 
                                   book_reference_id: int = None) -> Dict[str, Any]:
        """Get or create a user's personal copy of a book"""
        try:
            # Use default public book if no title specified
            if not book_title:
                book_title = UserBookService.PUBLIC_BOOK_INFO['title']
                book_type = 'public'
            
            # Check if user already has this book
            existing_copy = db.session.query(UserBookCopy).filter_by(
                user_id=user_id,
                book_title=book_title,
                book_type=book_type
            ).first()
            
            if existing_copy:
                # Update last accessed time and PDF URL if it has changed
                existing_copy.last_accessed_at = datetime.now(timezone.utc)
                
                # Update PDF URL if it has changed (for local vs S3 switching)
                new_pdf_url = UserBookService.PUBLIC_BOOK_INFO['pdf_url'] if book_type == 'public' else existing_copy.original_pdf_url
                if existing_copy.original_pdf_url != new_pdf_url:
                    existing_copy.original_pdf_url = new_pdf_url
                    current_app.logger.info(f"📄 Updated PDF URL for book copy {existing_copy.id} to: {new_pdf_url}")
                
                db.session.commit()
                
                current_app.logger.info(f"📖 Retrieved existing book copy {existing_copy.id} for user {user_id}")
                return {
                    'success': True,
                    'book_copy': existing_copy.to_dict(),
                    'message': 'Book copy retrieved successfully'
                }
            
            # Create new book copy
            if book_type == 'public':
                pdf_url = UserBookService.PUBLIC_BOOK_INFO['pdf_url']
            else:
                # For generated books, we'll need to get the PDF URL from CustomBook
                from app.models.custom_book import CustomBook
                custom_book = db.session.query(CustomBook).filter_by(
                    id=book_reference_id,
                    user_id=user_id
                ).first()
                
                if not custom_book:
                    return {
                        'success': False,
                        'message': 'Generated book not found'
                    }
                
                pdf_url = custom_book.pdf_url or ''
            
            # Create user book copy
            new_copy = UserBookCopy(
                user_id=user_id,
                book_title=book_title,
                book_type=book_type,
                book_reference_id=book_reference_id,
                original_pdf_url=pdf_url,
                last_accessed_at=datetime.now(timezone.utc)
            )
            
            db.session.add(new_copy)
            db.session.flush()  # Get the ID
            
            # Create initial reading progress
            initial_progress = ReadingProgress(
                user_book_copy_id=new_copy.id,
                total_pages=UserBookService.PUBLIC_BOOK_INFO['total_pages'] if book_type == 'public' else None
            )
            
            db.session.add(initial_progress)
            db.session.commit()
            
            current_app.logger.info(f"📖 Created new book copy {new_copy.id} for user {user_id}")
            
            return {
                'success': True,
                'book_copy': new_copy.to_dict(),
                'message': 'Book copy created successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"❌ Error getting/creating book copy: {str(e)}")
            return {
                'success': False,
                'message': f'Error managing book copy: {str(e)}'
            }
    
    @staticmethod
    def get_user_books(user_id: int) -> Dict[str, Any]:
        """Get all books for a user"""
        try:
            books = db.session.query(UserBookCopy).filter_by(user_id=user_id).all()
            
            books_data = []
            for book in books:
                book_dict = book.to_dict()
                
                # Get latest progress
                progress = db.session.query(ReadingProgress).filter_by(
                    user_book_copy_id=book.id
                ).first()
                
                if progress:
                    book_dict['progress'] = progress.to_dict()
                
                books_data.append(book_dict)
            
            return {
                'success': True,
                'books': books_data,
                'total_books': len(books_data)
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Error getting user books: {str(e)}")
            return {
                'success': False,
                'message': f'Error retrieving books: {str(e)}'
            }
    
    @staticmethod
    def update_reading_progress(user_id: int, book_copy_id: int, progress_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user's reading progress"""
        try:
            # Verify book ownership
            book_copy = db.session.query(UserBookCopy).filter_by(
                id=book_copy_id,
                user_id=user_id
            ).first()
            
            if not book_copy:
                return {
                    'success': False,
                    'message': 'Book copy not found'
                }
            
            # Get or create progress record
            progress = db.session.query(ReadingProgress).filter_by(
                user_book_copy_id=book_copy_id
            ).first()
            
            if not progress:
                progress = ReadingProgress(user_book_copy_id=book_copy_id)
                db.session.add(progress)
            
            # Update progress fields
            if 'current_page' in progress_data:
                progress.current_page = progress_data['current_page']
            
            if 'total_pages' in progress_data:
                progress.total_pages = progress_data['total_pages']
            
            if 'pdf_scroll_position' in progress_data:
                progress.pdf_scroll_position = progress_data['pdf_scroll_position']
            
            if 'pdf_zoom_level' in progress_data:
                progress.pdf_zoom_level = progress_data['pdf_zoom_level']
            
            if 'pdf_page_mode' in progress_data:
                progress.pdf_page_mode = progress_data['pdf_page_mode']
            
            if 'current_chapter' in progress_data:
                progress.current_chapter = progress_data['current_chapter']
            
            if 'reading_time_minutes' in progress_data:
                progress.reading_time_minutes += progress_data['reading_time_minutes']
            
            # Calculate progress percentage
            if progress.current_page and progress.total_pages:
                progress.progress_percentage = min(100.0, (progress.current_page / progress.total_pages) * 100)
            
            progress.last_read_at = datetime.now(timezone.utc)
            
            # Update book copy last accessed
            book_copy.last_accessed_at = datetime.now(timezone.utc)
            
            db.session.commit()
            
            current_app.logger.info(f"📊 Updated reading progress for book {book_copy_id}, user {user_id}")
            
            return {
                'success': True,
                'progress': progress.to_dict(),
                'message': 'Reading progress updated successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"❌ Error updating reading progress: {str(e)}")
            return {
                'success': False,
                'message': f'Error updating progress: {str(e)}'
            }
    
    @staticmethod
    def create_note(user_id: int, book_copy_id: int, note_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new note for a book and add it to user's knowledge base"""
        try:
            # Verify book ownership
            book_copy = db.session.query(UserBookCopy).filter_by(
                id=book_copy_id,
                user_id=user_id
            ).first()
            
            if not book_copy:
                return {
                    'success': False,
                    'message': 'Book copy not found'
                }
            
            # Create note
            note = BookNote(
                user_book_copy_id=book_copy_id,
                note_text=note_data.get('note_text', ''),
                note_type=note_data.get('note_type', 'note'),
                color=note_data.get('color', 'yellow'),
                page_number=note_data.get('page_number'),
                chapter_name=note_data.get('chapter_name'),
                pdf_coordinates=note_data.get('pdf_coordinates'),
                selected_text=note_data.get('selected_text'),
                context_before=note_data.get('context_before'),
                context_after=note_data.get('context_after'),
                tags=note_data.get('tags', []),
                is_private=note_data.get('is_private', True)
            )
            
            db.session.add(note)
            db.session.commit()
            
            current_app.logger.info(f"📝 Created note {note.id} for book {book_copy_id}, user {user_id}")
            
            # Add note to user's knowledge base using Pinecone
            try:
                pinecone_service = PineconeBookNotesService()
                
                # Prepare data for knowledge base
                kb_note_data = {
                    'id': note.id,
                    'note_text': note.note_text,
                    'note_type': note.note_type,
                    'color': note.color,
                    'page_number': note.page_number,
                    'book_title': book_copy.book_title,
                    'book_copy_id': book_copy_id,
                    'selected_text': note.selected_text or '',
                    'context_before': note.context_before or '',
                    'context_after': note.context_after or '',
                    'chapter_name': note.chapter_name,
                    'tags': note.tags or []
                }
                
                kb_result = pinecone_service.add_note_to_knowledge_base(user_id, kb_note_data)
                
                if kb_result.get('success'):
                    current_app.logger.info(f"✅ Note {note.id} successfully added to user {user_id}'s knowledge base")
                else:
                    current_app.logger.warning(f"⚠️ Note {note.id} saved locally but failed to add to knowledge base: {kb_result.get('message')}")
                    
            except Exception as kb_error:
                # Log the error but don't fail the note creation
                current_app.logger.error(f"❌ Error adding note to knowledge base: {str(kb_error)}")
            
            return {
                'success': True,
                'note': note.to_dict(),
                'message': 'Note created successfully and added to knowledge base'
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"❌ Error creating note: {str(e)}")
            return {
                'success': False,
                'message': f'Error creating note: {str(e)}'
            }
    
    @staticmethod
    def create_highlight(user_id: int, book_copy_id: int, highlight_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new highlight for a book and add it to user's knowledge base"""
        try:
            # Verify book ownership
            book_copy = db.session.query(UserBookCopy).filter_by(
                id=book_copy_id,
                user_id=user_id
            ).first()
            
            if not book_copy:
                return {
                    'success': False,
                    'message': 'Book copy not found'
                }
            
            # Create highlight
            highlight = BookHighlight(
                user_book_copy_id=book_copy_id,
                highlighted_text=highlight_data.get('highlighted_text', ''),
                color=highlight_data.get('color', 'yellow'),
                highlight_type=highlight_data.get('highlight_type', 'highlight'),
                page_number=highlight_data.get('page_number'),
                chapter_name=highlight_data.get('chapter_name'),
                pdf_coordinates=highlight_data.get('pdf_coordinates', {}),
                context_before=highlight_data.get('context_before'),
                context_after=highlight_data.get('context_after'),
                text_length=len(highlight_data.get('highlighted_text', '')),
                tags=highlight_data.get('tags', [])
            )
            
            db.session.add(highlight)
            db.session.commit()
            
            current_app.logger.info(f"🎨 Created highlight {highlight.id} for book {book_copy_id}, user {user_id}")
            
            # Add highlight to user's knowledge base using Pinecone
            try:
                pinecone_service = PineconeBookNotesService()
                
                # Prepare data for knowledge base
                kb_highlight_data = {
                    'id': highlight.id,
                    'highlighted_text': highlight.highlighted_text,
                    'highlight_type': highlight.highlight_type,
                    'color': highlight.color,
                    'page_number': highlight.page_number,
                    'book_title': book_copy.book_title,
                    'book_copy_id': book_copy_id,
                    'context_before': highlight.context_before or '',
                    'context_after': highlight.context_after or '',
                    'chapter_name': highlight.chapter_name,
                    'tags': highlight.tags or []
                }
                
                kb_result = pinecone_service.add_highlight_to_knowledge_base(user_id, kb_highlight_data)
                
                if kb_result.get('success'):
                    current_app.logger.info(f"✅ Highlight {highlight.id} successfully added to user {user_id}'s knowledge base")
                else:
                    current_app.logger.warning(f"⚠️ Highlight {highlight.id} saved locally but failed to add to knowledge base: {kb_result.get('message')}")
                    
            except Exception as kb_error:
                # Log the error but don't fail the highlight creation
                current_app.logger.error(f"❌ Error adding highlight to knowledge base: {str(kb_error)}")
            
            return {
                'success': True,
                'highlight': highlight.to_dict(),
                'message': 'Highlight created successfully and added to knowledge base'
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"❌ Error creating highlight: {str(e)}")
            return {
                'success': False,
                'message': f'Error creating highlight: {str(e)}'
            }
    
    @staticmethod
    def get_book_annotations(user_id: int, book_copy_id: int) -> Dict[str, Any]:
        """Get all notes and highlights for a book"""
        try:
            # Verify book ownership
            book_copy = db.session.query(UserBookCopy).filter_by(
                id=book_copy_id,
                user_id=user_id
            ).first()
            
            if not book_copy:
                return {
                    'success': False,
                    'message': 'Book copy not found'
                }
            
            # Get notes
            notes = db.session.query(BookNote).filter_by(
                user_book_copy_id=book_copy_id,
                is_archived=False
            ).order_by(BookNote.created_at.desc()).all()
            
            # Get highlights
            highlights = db.session.query(BookHighlight).filter_by(
                user_book_copy_id=book_copy_id,
                is_archived=False
            ).order_by(BookHighlight.created_at.desc()).all()
            
            return {
                'success': True,
                'notes': [note.to_dict() for note in notes],
                'highlights': [highlight.to_dict() for highlight in highlights],
                'total_notes': len(notes),
                'total_highlights': len(highlights)
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Error getting book annotations: {str(e)}")
            return {
                'success': False,
                'message': f'Error retrieving annotations: {str(e)}'
            }
    
    @staticmethod
    def get_notes(user_id: int, book_copy_id: int) -> Dict[str, Any]:
        """Get notes for a specific book"""
        try:
            # Verify book ownership
            book_copy = db.session.query(UserBookCopy).filter_by(
                id=book_copy_id,
                user_id=user_id
            ).first()
            
            if not book_copy:
                return {
                    'success': False,
                    'message': 'Book copy not found'
                }
            
            # Get notes
            notes = db.session.query(BookNote).filter_by(
                user_book_copy_id=book_copy_id,
                is_archived=False
            ).order_by(BookNote.created_at.desc()).all()
            
            return {
                'success': True,
                'notes': [note.to_dict() for note in notes],
                'total_notes': len(notes)
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Error getting notes: {str(e)}")
            return {
                'success': False,
                'message': f'Error retrieving notes: {str(e)}'
            }
    
    @staticmethod
    def get_highlights(user_id: int, book_copy_id: int) -> Dict[str, Any]:
        """Get highlights for a specific book"""
        try:
            # Verify book ownership
            book_copy = db.session.query(UserBookCopy).filter_by(
                id=book_copy_id,
                user_id=user_id
            ).first()
            
            if not book_copy:
                return {
                    'success': False,
                    'message': 'Book copy not found'
                }
            
            # Get highlights
            highlights = db.session.query(BookHighlight).filter_by(
                user_book_copy_id=book_copy_id,
                is_archived=False
            ).order_by(BookHighlight.created_at.desc()).all()
            
            return {
                'success': True,
                'highlights': [highlight.to_dict() for highlight in highlights],
                'total_highlights': len(highlights)
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Error getting highlights: {str(e)}")
            return {
                'success': False,
                'message': f'Error retrieving highlights: {str(e)}'
            }
    
    @staticmethod
    def get_reading_progress(user_id: int, book_copy_id: int) -> Dict[str, Any]:
        """Get reading progress for a specific book"""
        try:
            # Verify book ownership
            book_copy = db.session.query(UserBookCopy).filter_by(
                id=book_copy_id,
                user_id=user_id
            ).first()
            
            if not book_copy:
                return {
                    'success': False,
                    'message': 'Book copy not found'
                }
            
            # Get reading progress
            progress = db.session.query(ReadingProgress).filter_by(
                user_book_copy_id=book_copy_id
            ).first()
            
            if not progress:
                # Create initial progress if none exists
                progress = ReadingProgress(
                    user_book_copy_id=book_copy_id,
                    current_page=1,
                    total_pages=UserBookService.PUBLIC_BOOK_INFO['total_pages']
                )
                db.session.add(progress)
                db.session.commit()
            
            return {
                'success': True,
                'progress': progress.to_dict()
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Error getting reading progress: {str(e)}")
            return {
                'success': False,
                'message': f'Error retrieving progress: {str(e)}'
            }
    
    @staticmethod
    def update_note(user_id: int, note_id: int, note_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing note"""
        try:
            # Get note and verify ownership
            note = db.session.query(BookNote).join(UserBookCopy).filter(
                BookNote.id == note_id,
                UserBookCopy.user_id == user_id
            ).first()
            
            if not note:
                return {
                    'success': False,
                    'message': 'Note not found'
                }
            
            # Update note fields
            if 'note_text' in note_data:
                note.note_text = note_data['note_text']
            
            if 'color' in note_data:
                note.color = note_data['color']
            
            if 'tags' in note_data:
                note.tags = note_data['tags']
            
            if 'is_private' in note_data:
                note.is_private = note_data['is_private']
            
            note.updated_at = datetime.now(timezone.utc)
            
            db.session.commit()
            
            return {
                'success': True,
                'note': note.to_dict(),
                'message': 'Note updated successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"❌ Error updating note: {str(e)}")
            return {
                'success': False,
                'message': f'Error updating note: {str(e)}'
            }
    
    @staticmethod
    def delete_note(user_id: int, note_id: int) -> Dict[str, Any]:
        """Delete a note"""
        try:
            # Get note and verify ownership
            note = db.session.query(BookNote).join(UserBookCopy).filter(
                BookNote.id == note_id,
                UserBookCopy.user_id == user_id
            ).first()
            
            if not note:
                return {
                    'success': False,
                    'message': 'Note not found'
                }
            
            db.session.delete(note)
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Note deleted successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"❌ Error deleting note: {str(e)}")
            return {
                'success': False,
                'message': f'Error deleting note: {str(e)}'
            }
    
    @staticmethod
    def delete_highlight(user_id: int, highlight_id: int) -> Dict[str, Any]:
        """Delete a highlight"""
        try:
            # Get highlight and verify ownership
            highlight = db.session.query(BookHighlight).join(UserBookCopy).filter(
                BookHighlight.id == highlight_id,
                UserBookCopy.user_id == user_id
            ).first()
            
            if not highlight:
                return {
                    'success': False,
                    'message': 'Highlight not found'
                }
            
            db.session.delete(highlight)
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Highlight deleted successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"❌ Error deleting highlight: {str(e)}")
            return {
                'success': False,
                'message': f'Error deleting highlight: {str(e)}'
            }
    
    @staticmethod
    def start_reading_session(user_id: int, book_copy_id: int) -> Dict[str, Any]:
        """Start a new reading session"""
        try:
            # Verify book ownership
            book_copy = db.session.query(UserBookCopy).filter_by(
                id=book_copy_id,
                user_id=user_id
            ).first()
            
            if not book_copy:
                return {
                    'success': False,
                    'message': 'Book copy not found'
                }
            
            # Get current progress
            progress = db.session.query(ReadingProgress).filter_by(
                user_book_copy_id=book_copy_id
            ).first()
            
            # Create reading session
            session = ReadingSession(
                user_book_copy_id=book_copy_id,
                start_page=progress.current_page if progress else 1
            )
            
            db.session.add(session)
            db.session.commit()
            
            return {
                'success': True,
                'session': session.to_dict(),
                'message': 'Reading session started'
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"❌ Error starting reading session: {str(e)}")
            return {
                'success': False,
                'message': f'Error starting session: {str(e)}'
            }
    
    @staticmethod
    def end_reading_session(user_id: int, session_id: int, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """End a reading session with analytics"""
        try:
            # Get session and verify ownership
            session = db.session.query(ReadingSession).join(UserBookCopy).filter(
                ReadingSession.id == session_id,
                UserBookCopy.user_id == user_id
            ).first()
            
            if not session:
                return {
                    'success': False,
                    'message': 'Reading session not found'
                }
            
            # Update session data
            session.end_time = datetime.now(timezone.utc)
            
            if session.start_time:
                duration = session.end_time - session.start_time
                session.duration_minutes = int(duration.total_seconds() / 60)
            
            if 'end_page' in session_data:
                session.end_page = session_data['end_page']
                if session.start_page:
                    session.pages_read = max(0, session.end_page - session.start_page)
            
            if 'notes_created' in session_data:
                session.notes_created = session_data['notes_created']
            
            if 'highlights_created' in session_data:
                session.highlights_created = session_data['highlights_created']
            
            if 'pdf_interactions' in session_data:
                session.pdf_interactions = session_data['pdf_interactions']
            
            db.session.commit()
            
            return {
                'success': True,
                'session': session.to_dict(),
                'message': 'Reading session ended'
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"❌ Error ending reading session: {str(e)}")
            return {
                'success': False,
                'message': f'Error ending session: {str(e)}'
            }
    
    @staticmethod
    def get_reading_analytics(user_id: int, book_copy_id: int = None) -> Dict[str, Any]:
        """Get reading analytics for user"""
        try:
            query = db.session.query(ReadingSession).join(UserBookCopy).filter(
                UserBookCopy.user_id == user_id
            )
            
            if book_copy_id:
                query = query.filter(ReadingSession.user_book_copy_id == book_copy_id)
            
            sessions = query.all()
            
            # Calculate analytics
            total_sessions = len(sessions)
            total_reading_time = sum(s.duration_minutes or 0 for s in sessions)
            total_pages_read = sum(s.pages_read or 0 for s in sessions)
            total_notes = sum(s.notes_created or 0 for s in sessions)
            total_highlights = sum(s.highlights_created or 0 for s in sessions)
            
            # Average session length
            avg_session_length = total_reading_time / total_sessions if total_sessions > 0 else 0
            
            # Reading streaks and patterns
            recent_sessions = [s for s in sessions if s.start_time >= datetime.now(timezone.utc) - timedelta(days=30)]
            
            return {
                'success': True,
                'analytics': {
                    'total_sessions': total_sessions,
                    'total_reading_time_minutes': total_reading_time,
                    'total_pages_read': total_pages_read,
                    'total_notes_created': total_notes,
                    'total_highlights_created': total_highlights,
                    'average_session_length_minutes': round(avg_session_length, 2),
                    'recent_sessions_count': len(recent_sessions),
                    'reading_speed_pages_per_hour': round((total_pages_read / (total_reading_time / 60)), 2) if total_reading_time > 0 else 0
                }
            }
            
        except Exception as e:
            current_app.logger.error(f"❌ Error getting reading analytics: {str(e)}")
            return {
                'success': False,
                'message': f'Error retrieving analytics: {str(e)}'
            } 