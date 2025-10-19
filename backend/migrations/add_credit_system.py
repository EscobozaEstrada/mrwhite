"""
Migration: Add Credit System to User Model

This migration adds all necessary fields for the credit-based cost management system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text
from datetime import datetime

def upgrade():
    """Add credit system fields to users table"""
    
    app = create_app()
    with app.app_context():
        print("Starting credit system migration...")
        
        # Add new columns to users table
        migration_queries = [
            # Credit System fields
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS credits_balance INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS total_credits_purchased INTEGER DEFAULT 0", 
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS credits_used_today INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS credits_used_this_month INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_credit_reset_date DATE DEFAULT CURRENT_DATE",
            
            # Usage Analytics
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS lifetime_usage_stats JSON DEFAULT '{}'",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_tier VARCHAR(50) DEFAULT 'free'",
            
            # Free Credits & Bonuses
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS daily_free_credits_claimed BOOLEAN DEFAULT FALSE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS signup_bonus_claimed BOOLEAN DEFAULT FALSE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_credits INTEGER DEFAULT 0",
        ]
        
        for query in migration_queries:
            try:
                db.session.execute(text(query))
                print(f"✅ Executed: {query[:50]}...")
            except Exception as e:
                print(f"❌ Failed: {query[:50]}... - {str(e)}")
        
        # Commit the schema changes
        db.session.commit()
        print("✅ Schema migration completed")
        
        # Initialize existing users with credits and subscription tiers using raw SQL
        print("Initializing existing users...")
        
        try:
            # Get all users using raw SQL to avoid model mismatch
            users_result = db.session.execute(text("SELECT id, is_premium, subscription_status FROM users"))
            users = users_result.fetchall()
            
            for user_row in users:
                user_id, is_premium, subscription_status = user_row
                
                # Set subscription tier and credits based on current premium status
                if is_premium and subscription_status == 'active':
                    subscription_tier = 'premium'
                    credits_balance = 1000  # Give premium users 1000 credits ($10 value)
                else:
                    subscription_tier = 'free'
                    credits_balance = 100   # Give free users 100 credits ($1 value) as welcome bonus
                
                # Update user with credit system fields using raw SQL
                update_query = text("""
                    UPDATE users SET 
                        subscription_tier = :tier,
                        credits_balance = :balance,
                        total_credits_purchased = 0,
                        credits_used_today = 0,
                        credits_used_this_month = 0,
                        last_credit_reset_date = CURRENT_DATE,
                        daily_free_credits_claimed = FALSE,
                        signup_bonus_claimed = TRUE,
                        referral_credits = 0,
                        lifetime_usage_stats = '{}'::json
                    WHERE id = :user_id
                """)
                
                db.session.execute(update_query, {
                    'tier': subscription_tier,
                    'balance': credits_balance,
                    'user_id': user_id
                })
            
            db.session.commit()
            print(f"✅ Initialized {len(users)} existing users with credits")
            
        except Exception as e:
            print(f"❌ Failed to initialize users: {str(e)}")
            db.session.rollback()
        
        # Create indexes for performance
        index_queries = [
            "CREATE INDEX IF NOT EXISTS idx_users_subscription_tier ON users(subscription_tier)",
            "CREATE INDEX IF NOT EXISTS idx_users_credits_balance ON users(credits_balance)",
            "CREATE INDEX IF NOT EXISTS idx_users_last_credit_reset ON users(last_credit_reset_date)",
        ]
        
        for query in index_queries:
            try:
                db.session.execute(text(query))
                print(f"✅ Created index: {query.split('idx_')[1].split(' ')[0]}")
            except Exception as e:
                print(f"❌ Index creation failed: {str(e)}")
        
        db.session.commit()
        print("✅ Credit system migration completed successfully!")

def downgrade():
    """Remove credit system fields (use with caution)"""
    
    app = create_app()
    with app.app_context():
        print("Starting credit system rollback...")
        
        # Remove indexes first
        rollback_indexes = [
            "DROP INDEX IF EXISTS idx_users_subscription_tier",
            "DROP INDEX IF EXISTS idx_users_credits_balance", 
            "DROP INDEX IF EXISTS idx_users_last_credit_reset",
        ]
        
        for query in rollback_indexes:
            try:
                db.session.execute(text(query))
                print(f"✅ Dropped index")
            except Exception as e:
                print(f"❌ Index drop failed: {str(e)}")
        
        # Remove columns
        rollback_queries = [
            "ALTER TABLE users DROP COLUMN IF EXISTS credits_balance",
            "ALTER TABLE users DROP COLUMN IF EXISTS total_credits_purchased",
            "ALTER TABLE users DROP COLUMN IF EXISTS credits_used_today",
            "ALTER TABLE users DROP COLUMN IF EXISTS credits_used_this_month", 
            "ALTER TABLE users DROP COLUMN IF EXISTS last_credit_reset_date",
            "ALTER TABLE users DROP COLUMN IF EXISTS lifetime_usage_stats",
            "ALTER TABLE users DROP COLUMN IF EXISTS subscription_tier",
            "ALTER TABLE users DROP COLUMN IF EXISTS daily_free_credits_claimed",
            "ALTER TABLE users DROP COLUMN IF EXISTS signup_bonus_claimed",
            "ALTER TABLE users DROP COLUMN IF EXISTS referral_credits",
        ]
        
        for query in rollback_queries:
            try:
                db.session.execute(text(query))
                print(f"✅ Dropped column")
            except Exception as e:
                print(f"❌ Column drop failed: {str(e)}")
        
        db.session.commit()
        print("✅ Credit system rollback completed")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        print("⚠️  WARNING: This will remove all credit system data!")
        confirm = input("Type 'yes' to confirm rollback: ")
        if confirm.lower() == 'yes':
            downgrade()
        else:
            print("Rollback cancelled")
    else:
        upgrade() 