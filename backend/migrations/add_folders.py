"""
Migration script to add folder functionality to gallery

This script:
1. Creates the folders table
2. Adds folder_id column to user_images table
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone

# revision identifiers
revision = 'add_folders_table'
down_revision = None
depends_on = None


def upgrade():
    """Upgrade database schema for folder functionality"""
    
    # Create folders table
    op.create_table(
        'folders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('cover_image_id', sa.Integer(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.now(timezone.utc)),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.now(timezone.utc)),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['cover_image_id'], ['user_images.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add indexes to folders table
    op.create_index('idx_folders_user_id', 'folders', ['user_id'], unique=False)
    op.create_index('idx_folders_is_deleted', 'folders', ['is_deleted'], unique=False)
    op.create_index('idx_folders_created_at', 'folders', ['created_at'], unique=False)
    
    # Add folder_id column to user_images table
    op.add_column('user_images', sa.Column('folder_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_user_images_folder_id', 'user_images', 'folders', ['folder_id'], ['id'])
    op.create_index('idx_user_images_folder_id', 'user_images', ['folder_id'], unique=False)


def downgrade():
    """Downgrade database schema (remove folder functionality)"""
    
    # Remove folder_id from user_images
    op.drop_constraint('fk_user_images_folder_id', 'user_images', type_='foreignkey')
    op.drop_index('idx_user_images_folder_id', 'user_images')
    op.drop_column('user_images', 'folder_id')
    
    # Drop folders table
    op.drop_index('idx_folders_created_at', 'folders')
    op.drop_index('idx_folders_is_deleted', 'folders')
    op.drop_index('idx_folders_user_id', 'folders')
    op.drop_table('folders') 