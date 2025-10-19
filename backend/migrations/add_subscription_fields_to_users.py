from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app import create_app, db

def add_subscription_fields_to_users():
    """
    Add subscription related fields to the users table
    """
    app = create_app()
    with app.app_context():
        # Check if columns already exist to avoid errors
        conn = db.engine.connect()
        inspector = db.inspect(db.engine)
        columns = inspector.get_columns('users')
        column_names = [col['name'] for col in columns]
        
        # Add new columns if they don't exist
        if 'is_premium' not in column_names:
            conn.execute(db.text('ALTER TABLE users ADD COLUMN is_premium BOOLEAN DEFAULT FALSE'))
            print("Added is_premium column")
            
        if 'stripe_customer_id' not in column_names:
            conn.execute(db.text('ALTER TABLE users ADD COLUMN stripe_customer_id VARCHAR(100) UNIQUE'))
            conn.execute(db.text('CREATE INDEX ix_users_stripe_customer_id ON users (stripe_customer_id)'))
            print("Added stripe_customer_id column")
            
        if 'stripe_subscription_id' not in column_names:
            conn.execute(db.text('ALTER TABLE users ADD COLUMN stripe_subscription_id VARCHAR(100) UNIQUE'))
            print("Added stripe_subscription_id column")
            
        if 'subscription_status' not in column_names:
            conn.execute(db.text('ALTER TABLE users ADD COLUMN subscription_status VARCHAR(50)'))
            print("Added subscription_status column")
            
        if 'subscription_start_date' not in column_names:
            conn.execute(db.text('ALTER TABLE users ADD COLUMN subscription_start_date TIMESTAMP'))
            print("Added subscription_start_date column")
            
        if 'subscription_end_date' not in column_names:
            conn.execute(db.text('ALTER TABLE users ADD COLUMN subscription_end_date TIMESTAMP'))
            print("Added subscription_end_date column")
            
        if 'last_payment_date' not in column_names:
            conn.execute(db.text('ALTER TABLE users ADD COLUMN last_payment_date TIMESTAMP'))
            print("Added last_payment_date column")
            
        if 'payment_failed' not in column_names:
            conn.execute(db.text('ALTER TABLE users ADD COLUMN payment_failed BOOLEAN DEFAULT FALSE'))
            print("Added payment_failed column")
            
        conn.close()
        
        # Commit the transaction
        db.session.commit()
        print("Migration completed successfully")

if __name__ == '__main__':
    add_subscription_fields_to_users() 