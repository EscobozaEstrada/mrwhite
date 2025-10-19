"""Add book_type and selected_categories to enhanced_books

Revision ID: add_book_type_enhanced_books
Revises: 
Create Date: 2025-10-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_book_type_enhanced_books'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add book_type column to enhanced_books
    op.add_column('enhanced_books', 
        sa.Column('book_type', sa.String(length=50), nullable=True)
    )
    
    # Add selected_categories column to enhanced_books
    op.add_column('enhanced_books',
        sa.Column('selected_categories', postgresql.JSON(astext_type=sa.Text()), nullable=True)
    )
    
    # Set default value for existing rows
    op.execute("UPDATE enhanced_books SET book_type = 'general' WHERE book_type IS NULL")
    op.execute("UPDATE enhanced_books SET selected_categories = '[]' WHERE selected_categories IS NULL")
    
    # Make book_type NOT NULL after setting defaults
    op.alter_column('enhanced_books', 'book_type', nullable=False)


def downgrade():
    # Remove the columns
    op.drop_column('enhanced_books', 'selected_categories')
    op.drop_column('enhanced_books', 'book_type')



