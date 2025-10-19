from app import db
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import JSON

class BookTag(db.Model):
    """Predefined book categories/tags for organizing content"""
    __tablename__ = 'book_tags'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=True)
    color = db.Column(db.String(7), default='#3B82F6')  # Hex color for UI
    icon = db.Column(db.String(50), nullable=True)  # Icon name for UI
    category_order = db.Column(db.Integer, default=0)  # Display order
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    def __repr__(self):
        return f"<BookTag {self.name}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'color': self.color,
            'icon': self.icon,
            'category_order': self.category_order,
            'is_active': self.is_active
        }

class CustomBook(db.Model):
    """User-created custom books from their content"""
    __tablename__ = 'custom_books'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Book metadata
    title = db.Column(db.String(255), nullable=False)
    subtitle = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, nullable=True)
    cover_image_url = db.Column(db.String(512), nullable=True)  # S3 URL
    
    # Content configuration
    selected_tags = db.Column(JSON, nullable=True)  # List of tag IDs included
    date_range_start = db.Column(db.DateTime, nullable=True)  # Content from this date
    date_range_end = db.Column(db.DateTime, nullable=True)    # Content to this date
    content_types = db.Column(JSON, nullable=True)  # ['chat', 'photos', 'documents']
    
    # Generation settings
    book_style = db.Column(db.String(50), default='narrative')  # narrative, timeline, reference
    include_photos = db.Column(db.Boolean, default=True)
    include_documents = db.Column(db.Boolean, default=True)
    include_chat_history = db.Column(db.Boolean, default=True)
    auto_organize_by_date = db.Column(db.Boolean, default=True)
    
    # Book status and generation
    generation_status = db.Column(db.String(50), default='draft', index=True)  # draft, generating, completed, failed
    generation_progress = db.Column(db.Integer, default=0)  # Percentage
    generation_started_at = db.Column(db.DateTime, nullable=True)
    generation_completed_at = db.Column(db.DateTime, nullable=True)
    generation_error = db.Column(db.Text, nullable=True)
    
    # Output formats
    pdf_url = db.Column(db.String(512), nullable=True)  # Generated PDF on S3
    epub_url = db.Column(db.String(512), nullable=True)  # Generated EPUB on S3
    html_content = db.Column(db.Text, nullable=True)  # HTML version
    
    # Analytics and metrics
    total_content_items = db.Column(db.Integer, default=0)  # Total items included
    total_photos = db.Column(db.Integer, default=0)
    total_documents = db.Column(db.Integer, default=0)
    total_chat_messages = db.Column(db.Integer, default=0)
    word_count = db.Column(db.Integer, default=0)
    
    # Metadata
    processing_metadata = db.Column(JSON, nullable=True)  # LangGraph processing info
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), index=True)
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # Relationships
    chapters = db.relationship('BookChapter', backref='book', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<CustomBook {self.id} - {self.title}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'subtitle': self.subtitle,
            'description': self.description,
            'cover_image_url': self.cover_image_url,
            'selected_tags': self.selected_tags,
            'date_range_start': self.date_range_start.isoformat() if self.date_range_start else None,
            'date_range_end': self.date_range_end.isoformat() if self.date_range_end else None,
            'content_types': self.content_types,
            'book_style': self.book_style,
            'include_photos': self.include_photos,
            'include_documents': self.include_documents,
            'include_chat_history': self.include_chat_history,
            'auto_organize_by_date': self.auto_organize_by_date,
            'generation_status': self.generation_status,
            'generation_progress': self.generation_progress,
            'generation_started_at': self.generation_started_at.isoformat() if self.generation_started_at else None,
            'generation_completed_at': self.generation_completed_at.isoformat() if self.generation_completed_at else None,
            'generation_error': self.generation_error,
            'pdf_url': self.pdf_url,
            'epub_url': self.epub_url,
            'total_content_items': self.total_content_items,
            'total_photos': self.total_photos,
            'total_documents': self.total_documents,
            'total_chat_messages': self.total_chat_messages,
            'word_count': self.word_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'chapters': [chapter.to_dict() for chapter in self.chapters]
        }

class BookChapter(db.Model):
    """Chapters within a custom book"""
    __tablename__ = 'book_chapters'
    
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('custom_books.id'), nullable=False, index=True)
    
    # Chapter metadata
    chapter_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    subtitle = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, nullable=True)
    
    # Content organization
    primary_tag_id = db.Column(db.Integer, db.ForeignKey('book_tags.id'), nullable=True)
    date_range_start = db.Column(db.DateTime, nullable=True)
    date_range_end = db.Column(db.DateTime, nullable=True)
    
    # Chapter content
    content_html = db.Column(db.Text, nullable=True)  # Generated HTML content
    content_markdown = db.Column(db.Text, nullable=True)  # Markdown version
    content_summary = db.Column(db.Text, nullable=True)  # AI-generated summary
    
    # Analytics
    word_count = db.Column(db.Integer, default=0)
    content_item_count = db.Column(db.Integer, default=0)
    
    # Metadata
    chapter_metadata = db.Column(JSON, nullable=True)  # Additional processing info
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # Relationships
    content_items = db.relationship('BookContentItem', backref='chapter', lazy=True, cascade='all, delete-orphan')
    primary_tag = db.relationship('BookTag', backref='chapters')
    
    def __repr__(self):
        return f"<BookChapter {self.id} - Chapter {self.chapter_number}: {self.title}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'chapter_number': self.chapter_number,
            'title': self.title,
            'subtitle': self.subtitle,
            'description': self.description,
            'primary_tag_id': self.primary_tag_id,
            'date_range_start': self.date_range_start.isoformat() if self.date_range_start else None,
            'date_range_end': self.date_range_end.isoformat() if self.date_range_end else None,
            'content_summary': self.content_summary,
            'word_count': self.word_count,
            'content_item_count': self.content_item_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'content_items': [item.to_dict() for item in self.content_items],
            'primary_tag': self.primary_tag.to_dict() if self.primary_tag else None
        }

class BookContentItem(db.Model):
    """Individual content items within book chapters"""
    __tablename__ = 'book_content_items'
    
    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('book_chapters.id'), nullable=False, index=True)
    
    # Content source identification
    content_type = db.Column(db.String(50), nullable=False, index=True)  # 'chat', 'photo', 'document'
    source_id = db.Column(db.Integer, nullable=False, index=True)  # ID in original table
    source_table = db.Column(db.String(50), nullable=False)  # 'messages', 'user_images', 'documents'
    
    # Content details
    title = db.Column(db.String(255), nullable=True)
    content_text = db.Column(db.Text, nullable=True)  # Extracted/processed text
    content_url = db.Column(db.String(512), nullable=True)  # S3 URL for media
    thumbnail_url = db.Column(db.String(512), nullable=True)  # Thumbnail for photos
    
    # Context and metadata
    original_date = db.Column(db.DateTime, nullable=False, index=True)  # When content was created
    tags = db.Column(JSON, nullable=True)  # Associated tags
    ai_analysis = db.Column(db.Text, nullable=True)  # AI-generated description/analysis
    
    # Organization within chapter
    item_order = db.Column(db.Integer, default=0)  # Order within chapter
    include_in_export = db.Column(db.Boolean, default=True)
    
    # Processing metadata
    processing_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    def __repr__(self):
        return f"<BookContentItem {self.id} - {self.content_type}:{self.source_id}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'content_type': self.content_type,
            'source_id': self.source_id,
            'source_table': self.source_table,
            'title': self.title,
            'content_text': self.content_text,
            'content_url': self.content_url,
            'thumbnail_url': self.thumbnail_url,
            'original_date': self.original_date.isoformat(),
            'tags': self.tags,
            'ai_analysis': self.ai_analysis,
            'item_order': self.item_order,
            'include_in_export': self.include_in_export,
            'processing_notes': self.processing_notes,
            'created_at': self.created_at.isoformat()
        } 