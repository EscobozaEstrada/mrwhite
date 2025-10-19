from app import create_app, db
from app.models.folder import Folder
from app.models.image import UserImage

app = create_app()
with app.app_context():
    # Create the tables
    db.create_all()
    print("Tables created successfully!") 