from app import db
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import JSON


class UserBookCopy(db.Model):
    """User's personal copy of a book with individual settings and progress"""
    __tablename__ = 'user_book_copies'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Book reference
    book_title = db.Column(db.String(255), nullable=False)
    book_type = db.Column(db.String(50), nullable=False)  # 'public' or 'generated'
    book_reference_id = db.Column(db.Integer, nullable=True)  # CustomBook ID for generated books
    original_pdf_url = db.Column(db.String(512), nullable=False)  # Source PDF URL
    
    # User-specific settings
    font_size = db.Column(db.String(20), default='medium')  # small, medium, large
    theme = db.Column(db.String(20), default='light')  # light, dark, sepia
    reading_speed = db.Column(db.Integer, default=250)  # words per minute
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), 
                          onupdate=lambda: datetime.now(timezone.utc))
    last_accessed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    progress = db.relationship('ReadingProgress', backref='book_copy', lazy=True, cascade='all, delete-orphan')
    notes = db.relationship('BookNote', backref='book_copy', lazy=True, cascade='all, delete-orphan')
    highlights = db.relationship('BookHighlight', backref='book_copy', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'book_title': self.book_title,
            'book_type': self.book_type,
            'book_reference_id': self.book_reference_id,
            'original_pdf_url': self.original_pdf_url,
            'font_size': self.font_size,
            'theme': self.theme,
            'reading_speed': self.reading_speed,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_accessed_at': self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            'total_notes': len(self.notes),
            'total_highlights': len(self.highlights)
        }


class ReadingProgress(db.Model):
    """Tracks user's reading progress through a book"""
    __tablename__ = 'reading_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    user_book_copy_id = db.Column(db.Integer, db.ForeignKey('user_book_copies.id'), nullable=False, index=True)
    
    # Progress tracking
    current_page = db.Column(db.Integer, default=1)
    total_pages = db.Column(db.Integer, nullable=True)
    progress_percentage = db.Column(db.Float, default=0.0)  # 0-100
    
    # Reading session data
    reading_time_minutes = db.Column(db.Integer, default=0)  # Total reading time
    session_count = db.Column(db.Integer, default=0)  # Number of reading sessions
    
    # PDF-specific tracking
    pdf_scroll_position = db.Column(db.Float, default=0.0)  # 0-1 for PDF scroll
    pdf_zoom_level = db.Column(db.Float, default=1.0)
    pdf_page_mode = db.Column(db.String(20), default='fit-width')  # fit-width, fit-page, actual-size
    
    # Chapter/section tracking
    current_chapter = db.Column(db.String(100), nullable=True)
    chapters_completed = db.Column(JSON, default=list)  # List of completed chapter IDs
    
    # Timestamps
    last_read_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    reading_started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    estimated_completion_date = db.Column(db.DateTime, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_book_copy_id': self.user_book_copy_id,
            'current_page': self.current_page,
            'total_pages': self.total_pages,
            'progress_percentage': self.progress_percentage,
            'reading_time_minutes': self.reading_time_minutes,
            'session_count': self.session_count,
            'pdf_scroll_position': self.pdf_scroll_position,
            'pdf_zoom_level': self.pdf_zoom_level,
            'pdf_page_mode': self.pdf_page_mode,
            'current_chapter': self.current_chapter,
            'chapters_completed': self.chapters_completed,
            'last_read_at': self.last_read_at.isoformat() if self.last_read_at else None,
            'reading_started_at': self.reading_started_at.isoformat() if self.reading_started_at else None,
            'estimated_completion_date': self.estimated_completion_date.isoformat() if self.estimated_completion_date else None
        }


class BookNote(db.Model):
    """User notes attached to specific locations in the book"""
    __tablename__ = 'book_notes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_book_copy_id = db.Column(db.Integer, db.ForeignKey('user_book_copies.id'), nullable=False, index=True)
    
    # Note content
    note_text = db.Column(db.Text, nullable=False)
    note_type = db.Column(db.String(50), default='note')  # note, bookmark, reminder
    color = db.Column(db.String(20), default='yellow')  # yellow, blue, green, red, purple
    
    # Location in book
    page_number = db.Column(db.Integer, nullable=True)
    chapter_name = db.Column(db.String(200), nullable=True)
    pdf_coordinates = db.Column(JSON, nullable=True)  # {x, y, page} for PDF position
    
    # Text selection context
    selected_text = db.Column(db.Text, nullable=True)  # The text the note refers to
    context_before = db.Column(db.String(500), nullable=True)  # Text before selection
    context_after = db.Column(db.String(500), nullable=True)  # Text after selection
    
    # Organization
    tags = db.Column(JSON, default=list)  # User-defined tags
    is_private = db.Column(db.Boolean, default=True)
    is_archived = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), 
                          onupdate=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_book_copy_id': self.user_book_copy_id,
            'note_text': self.note_text,
            'note_type': self.note_type,
            'color': self.color,
            'page_number': self.page_number,
            'chapter_name': self.chapter_name,
            'pdf_coordinates': self.pdf_coordinates,
            'selected_text': self.selected_text,
            'context_before': self.context_before,
            'context_after': self.context_after,
            'tags': self.tags,
            'is_private': self.is_private,
            'is_archived': self.is_archived,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class BookHighlight(db.Model):
    """User highlights in the book text"""
    __tablename__ = 'book_highlights'
    
    id = db.Column(db.Integer, primary_key=True)
    user_book_copy_id = db.Column(db.Integer, db.ForeignKey('user_book_copies.id'), nullable=False, index=True)
    
    # Highlight properties
    highlighted_text = db.Column(db.Text, nullable=False)
    color = db.Column(db.String(20), default='yellow')  # yellow, blue, green, red, purple
    highlight_type = db.Column(db.String(50), default='highlight')  # highlight, underline, strikethrough
    
    # Location in book
    page_number = db.Column(db.Integer, nullable=True)
    chapter_name = db.Column(db.String(200), nullable=True)
    pdf_coordinates = db.Column(JSON, nullable=False)  # {startX, startY, endX, endY, page}
    
    # Context for finding highlight again
    context_before = db.Column(db.String(500), nullable=True)
    context_after = db.Column(db.String(500), nullable=True)
    text_length = db.Column(db.Integer, nullable=False)
    
    # Organization
    tags = db.Column(JSON, default=list)
    is_archived = db.Column(db.Boolean, default=False)
    
    # Associated note (optional)
    note_id = db.Column(db.Integer, db.ForeignKey('book_notes.id'), nullable=True)
    note = db.relationship('BookNote', backref='associated_highlights', foreign_keys=[note_id])
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), 
                          onupdate=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_book_copy_id': self.user_book_copy_id,
            'highlighted_text': self.highlighted_text,
            'color': self.color,
            'highlight_type': self.highlight_type,
            'page_number': self.page_number,
            'chapter_name': self.chapter_name,
            'pdf_coordinates': self.pdf_coordinates,
            'context_before': self.context_before,
            'context_after': self.context_after,
            'text_length': self.text_length,
            'tags': self.tags,
            'is_archived': self.is_archived,
            'note_id': self.note_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ReadingSession(db.Model):
    """Individual reading sessions for analytics"""
    __tablename__ = 'reading_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_book_copy_id = db.Column(db.Integer, db.ForeignKey('user_book_copies.id'), nullable=False, index=True)
    
    # Session data
    start_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    end_time = db.Column(db.DateTime, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    
    # Progress during session
    start_page = db.Column(db.Integer, nullable=True)
    end_page = db.Column(db.Integer, nullable=True)
    pages_read = db.Column(db.Integer, default=0)
    
    # Engagement metrics
    notes_created = db.Column(db.Integer, default=0)
    highlights_created = db.Column(db.Integer, default=0)
    pdf_interactions = db.Column(db.Integer, default=0)  # zoom, scroll, etc.
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_book_copy_id': self.user_book_copy_id,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_minutes': self.duration_minutes,
            'start_page': self.start_page,
            'end_page': self.end_page,
            'pages_read': self.pages_read,
            'notes_created': self.notes_created,
            'highlights_created': self.highlights_created,
            'pdf_interactions': self.pdf_interactions
        } 