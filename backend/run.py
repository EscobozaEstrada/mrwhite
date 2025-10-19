from app import create_app, db
from app.models.user import User
from app.models.contact import Contact
from app.models.care_record import CareRecord, Document, KnowledgeBase

app = create_app()

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(
        debug=app.config.get('FLASK_DEBUG', False), 
        host=app.config.get('FLASK_HOST', '0.0.0.0'), 
        port=int(app.config.get('FLASK_PORT', 5001))
    )