from app import db
from datetime import datetime, timezone
import json

class Attachment(db.Model):
    __tablename__ = 'attachments'
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=False, index=True)
    type = db.Column(db.String(50), nullable=False)  # 'file', 'image', or 'audio'
    url = db.Column(db.String(512), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    def __repr__(self):
        return f"<Attachment {self.id} - {self.name}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'url': self.url,
            'name': self.name
        }

class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(10), nullable=False, index=True)  # 'user' or 'ai'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    liked = db.Column(db.Boolean, default=False, index=True)
    disliked = db.Column(db.Boolean, default=False, index=True)
    is_bookmarked = db.Column(db.Boolean, default=False, index=True)
    bookmark_date = db.Column(db.DateTime, nullable=True, index=True)
    
    # Relationships
    attachments = db.relationship('Attachment', backref='message', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Message {self.id} - {self.type}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'type': self.type,
            'created_at': self.created_at.isoformat() + 'Z',
            'liked': self.liked,
            'disliked': self.disliked,
            'is_bookmarked': self.is_bookmarked,
            'bookmark_date': self.bookmark_date.isoformat() + 'Z' if self.bookmark_date else None,
            'attachments': [attachment.to_dict() for attachment in self.attachments]
        } 