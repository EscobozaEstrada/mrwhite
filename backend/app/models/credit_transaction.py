from app import db
from datetime import datetime
import json

class CreditTransaction(db.Model):
    """Track all credit transactions for audit and duplicate prevention"""
    __tablename__ = 'credit_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)  # Credits amount (can be negative for deductions)
    transaction_type = db.Column(db.String(50), nullable=False)  # 'purchase', 'subscription_bonus', 'daily_free', 'deduction', etc.
    
    # Payment tracking for duplicate prevention
    payment_intent_id = db.Column(db.String(255), unique=True, nullable=True)  # Stripe payment intent ID
    checkout_session_id = db.Column(db.String(255), unique=True, nullable=True)  # Stripe checkout session ID
    
    # Metadata and audit
    transaction_metadata = db.Column(db.Text, nullable=True)  # JSON metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='credit_transactions')
    
    def __init__(self, user_id, amount, transaction_type, payment_intent_id=None, checkout_session_id=None, metadata=None):
        self.user_id = user_id
        self.amount = amount
        self.transaction_type = transaction_type
        self.payment_intent_id = payment_intent_id
        self.checkout_session_id = checkout_session_id
        self.transaction_metadata = json.dumps(metadata) if metadata else None
    
    def get_metadata(self):
        """Get metadata as dictionary"""
        return json.loads(self.transaction_metadata) if self.transaction_metadata else {}
    
    def set_metadata(self, metadata_dict):
        """Set metadata from dictionary"""
        self.transaction_metadata = json.dumps(metadata_dict) if metadata_dict else None
    
    @staticmethod
    def is_payment_processed(payment_intent_id=None, checkout_session_id=None):
        """Check if a payment has already been processed to prevent duplicates"""
        if payment_intent_id:
            return CreditTransaction.query.filter_by(payment_intent_id=payment_intent_id).first() is not None
        if checkout_session_id:
            return CreditTransaction.query.filter_by(checkout_session_id=checkout_session_id).first() is not None
        return False
    
    def __repr__(self):
        return f'<CreditTransaction {self.id}: User {self.user_id}, {self.amount} credits, {self.transaction_type}>'
