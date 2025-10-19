from app import db
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import JSON

class EnhancedBook(db.Model):
    """Model for enhanced books with tone and style customization"""
    __tablename__ = 'enhanced_books'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    cover_image = db.Column(db.String(255))
    book_type = db.Column(db.String(50), nullable=False, default='general')  # relationship, historical, medical, training, family, memorial, general
    selected_categories = db.Column(JSON)  # User-selected categories for the book
    tone_type = db.Column(db.String(50), nullable=False)  # friendly, narrative, playful
    text_style = db.Column(db.String(50), nullable=False)  # poppins, times new roman, etc.
    status = db.Column(db.String(50), default='draft')  # draft, processing, completed
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), 
                          onupdate=lambda: datetime.now(timezone.utc))
    pdf_url = db.Column(db.String(255))
    epub_url = db.Column(db.String(255))
    
    # Relationships
    chapters = db.relationship('EnhancedBookChapter', backref='book', lazy=True, 
                              cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert book to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'cover_image': self.cover_image,
            'book_type': self.book_type,
            'selected_categories': self.selected_categories or [],
            'tone_type': self.tone_type,
            'text_style': self.text_style,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'pdf_url': self.pdf_url,
            'epub_url': self.epub_url,
            'chapters': [chapter.to_dict() for chapter in self.chapters]
        }


class EnhancedBookChapter(db.Model):
    """Model for enhanced book chapters"""
    __tablename__ = 'enhanced_book_chapters'
    
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('enhanced_books.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=False)  # The category this chapter belongs to
    order = db.Column(db.Integer, nullable=False)  # Order of chapters in the book
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc))
    last_chat_fetch_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=True)  # Initialize to creation time
    
    def to_dict(self):
        """Convert chapter to dictionary"""
        return {
            'id': self.id,
            'book_id': self.book_id,
            'title': self.title,
            'content': self.content,
            'category': self.category,
            'order': self.order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_chat_fetch_at': self.last_chat_fetch_at.isoformat() if self.last_chat_fetch_at else None
        }


class MessageCategory(db.Model):
    """Model for categorized messages"""
    __tablename__ = 'message_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=False)
    category = db.Column(db.String(100), nullable=False)  # Category assigned to the message
    book_id = db.Column(db.Integer, db.ForeignKey('enhanced_books.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    message = db.relationship('Message', backref='categories', lazy=True)
    
    def to_dict(self):
        """Convert message category to dictionary"""
        return {
            'id': self.id,
            'message_id': self.message_id,
            'category': self.category,
            'book_id': self.book_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        } 