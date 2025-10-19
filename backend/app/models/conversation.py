from app import db
from datetime import datetime, timezone

class Conversation(db.Model):
    __tablename__ = 'conversations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=True)
    thread_id = db.Column(db.String(100), nullable=True, index=True)  # LangGraph thread ID
    is_bookmarked = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), index=True)
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc), index=True)
    
    # Relationships
    # user relationship is defined via backref in User model
    messages = db.relationship('Message', backref='conversation', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Conversation {self.id}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'thread_id': self.thread_id,
            'is_bookmarked': self.is_bookmarked,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'message_count': len(self.messages)
        } 