"""
Book comment access model
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func

from .base import Base


class BookCommentAccess(Base):
    """Track which book_notes are accessible in wayofdog mode"""
    __tablename__ = "ic_book_comments_access"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE", use_alter=True, name="fk_ic_book_access_user_id"), nullable=False)
    book_note_id = Column(Integer, ForeignKey("book_notes.id", ondelete="CASCADE"), nullable=False)

    # Access metadata
    last_accessed = Column(DateTime(timezone=True))
    access_count = Column(Integer, default=0)

    # Pinecone reference
    pinecone_namespace = Column(String(200))
    pinecone_id = Column(String(200))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'book_note_id', name='unique_book_comment_access'),
    )

    def __repr__(self):
        return f"<BookCommentAccess(id={self.id}, user_id={self.user_id}, book_note_id={self.book_note_id})>"


