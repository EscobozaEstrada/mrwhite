from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # Add folder_id column to user_images table
    try:
        # Check if column already exists
        result = db.session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='user_images' AND column_name='folder_id'"))
        column_exists = result.fetchone() is not None
        
        if not column_exists:
            # Add the column
            db.session.execute(text("ALTER TABLE user_images ADD COLUMN folder_id INTEGER"))
            # Add foreign key constraint
            db.session.execute(text("ALTER TABLE user_images ADD CONSTRAINT fk_user_images_folder_id FOREIGN KEY (folder_id) REFERENCES folders (id)"))
            # Add index
            db.session.execute(text("CREATE INDEX idx_user_images_folder_id ON user_images (folder_id)"))
            db.session.commit()
            print("Successfully added folder_id column to user_images table")
        else:
            print("folder_id column already exists in user_images table")
    except Exception as e:
        db.session.rollback()
        print(f"Error adding folder_id column: {str(e)}") 