from app import db
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import JSON

class CareRecord(db.Model):
    __tablename__ = 'care_records'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Pet identification (CRITICAL for multi-pet households)
    pet_name = db.Column(db.String(100), nullable=True, index=True)
    pet_breed = db.Column(db.String(100), nullable=True)
    pet_age = db.Column(db.Integer, nullable=True)  # Age in months
    pet_weight = db.Column(db.Float, nullable=True)  # Weight in kg/lbs
    
    # Core record fields
    title = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)  # vaccination, vet_visit, medication, milestone, etc.
    date_occurred = db.Column(db.DateTime, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    
    # Health-specific fields
    severity_level = db.Column(db.Integer, nullable=True)  # 1-5 scale for symptoms/issues
    symptoms = db.Column(JSON, nullable=True)  # List of symptoms
    medications = db.Column(JSON, nullable=True)  # Current medications
    follow_up_required = db.Column(db.Boolean, default=False)
    follow_up_date = db.Column(db.DateTime, nullable=True)
    
    # Enhanced metadata
    meta_data = db.Column(JSON, nullable=True)  # Store additional structured data
    health_tags = db.Column(JSON, nullable=True)  # Searchable health tags
    
    # Reminders and scheduling
    reminder_date = db.Column(db.DateTime, nullable=True, index=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    # Audit fields
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), index=True)
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # Relationships
    documents = db.relationship('Document', backref='care_record', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<CareRecord {self.id} - {self.title} ({self.pet_name})>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'category': self.category,
            'pet_name': self.pet_name,
            'pet_breed': self.pet_breed,
            'pet_age': self.pet_age,
            'pet_weight': self.pet_weight,
            'date_occurred': self.date_occurred.isoformat(),
            'description': self.description,
            'severity_level': self.severity_level,
            'symptoms': self.symptoms,
            'medications': self.medications,
            'follow_up_required': self.follow_up_required,
            'follow_up_date': self.follow_up_date.isoformat() if self.follow_up_date else None,
            'metadata': self.meta_data,
            'health_tags': self.health_tags,
            'reminder_date': self.reminder_date.isoformat() if self.reminder_date else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'documents': [doc.to_dict() for doc in self.documents]
        }

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    care_record_id = db.Column(db.Integer, db.ForeignKey('care_records.id'), nullable=True, index=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)  # pdf, image, text, etc.
    file_size = db.Column(db.Integer, nullable=False)
    s3_url = db.Column(db.String(512), nullable=False)
    s3_key = db.Column(db.String(255), nullable=False)
    content_summary = db.Column(db.Text, nullable=True)  # AI-generated summary
    extracted_text = db.Column(db.Text, nullable=True)  # Extracted text content
    meta_data = db.Column(JSON, nullable=True)  # Store additional structured data
    is_processed = db.Column(db.Boolean, default=False, index=True)
    processing_status = db.Column(db.String(50), default='pending', index=True)  # pending, processing, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), index=True)
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    def __repr__(self):
        return f"<Document {self.id} - {self.filename}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_type': self.file_type,
            'file_size': self.file_size,
            's3_url': self.s3_url,
            'content_summary': self.content_summary,
            'metadata': self.meta_data,
            'is_processed': self.is_processed,
            'processing_status': self.processing_status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class KnowledgeBase(db.Model):
    __tablename__ = 'knowledge_bases'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    vector_count = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.now(timezone.utc), index=True)
    pinecone_namespace = db.Column(db.String(100), nullable=False, unique=True)
    meta_data = db.Column(JSON, nullable=True)  # Store statistics and metadata
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), index=True)
    
    def __repr__(self):
        return f"<KnowledgeBase {self.id} - User {self.user_id}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'vector_count': self.vector_count,
            'last_updated': self.last_updated.isoformat(),
            'metadata': self.meta_data,
            'created_at': self.created_at.isoformat()
        } 