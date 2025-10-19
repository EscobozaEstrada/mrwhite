"""
Database migration to create health tracking tables for the Health & Savings Tracker module.

This migration creates the following tables:
- health_records: Main health record table
- vaccinations: Vaccination-specific details
- medications: Medication-specific details  
- health_reminders: Health reminder system
- pet_profiles: Enhanced pet profile information
- health_insights: AI-generated health insights

Run this script to set up the database schema for health tracking functionality.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_database_url():
    """Get database URL from environment variables"""
    # Default to SQLite for development if no DATABASE_URL is set
    return os.getenv('DATABASE_URL', 'sqlite:///health_tracker.db')

def create_health_tables(engine):
    """Create all health tracking tables"""
    
    sql_commands = [
        # Create health_records table
        """
        CREATE TABLE IF NOT EXISTS health_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            pet_id INTEGER,
            record_type VARCHAR(50) NOT NULL CHECK (record_type IN (
                'vaccination', 'vet_visit', 'medication', 'allergy', 'surgery', 
                'injury', 'checkup', 'emergency', 'dental', 'grooming'
            )),
            title VARCHAR(200) NOT NULL,
            description TEXT,
            record_date DATE NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            veterinarian_name VARCHAR(100),
            clinic_name VARCHAR(100),
            clinic_address TEXT,
            cost DECIMAL(10,2),
            insurance_covered BOOLEAN DEFAULT FALSE,
            insurance_amount DECIMAL(10,2),
            notes TEXT,
            tags VARCHAR(500),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """,
        
        # Create vaccinations table
        """
        CREATE TABLE IF NOT EXISTS vaccinations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            health_record_id INTEGER NOT NULL,
            vaccine_name VARCHAR(100) NOT NULL,
            vaccine_type VARCHAR(50),
            batch_number VARCHAR(50),
            manufacturer VARCHAR(100),
            administration_date DATE NOT NULL,
            next_due_date DATE,
            completed BOOLEAN DEFAULT TRUE,
            adverse_reactions TEXT,
            FOREIGN KEY (health_record_id) REFERENCES health_records(id) ON DELETE CASCADE
        );
        """,
        
        # Create medications table
        """
        CREATE TABLE IF NOT EXISTS medications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            health_record_id INTEGER NOT NULL,
            medication_name VARCHAR(100) NOT NULL,
            dosage VARCHAR(50),
            frequency VARCHAR(50),
            start_date DATE NOT NULL,
            end_date DATE,
            active BOOLEAN DEFAULT TRUE,
            prescribed_by VARCHAR(100),
            reason TEXT,
            side_effects TEXT,
            FOREIGN KEY (health_record_id) REFERENCES health_records(id) ON DELETE CASCADE
        );
        """,
        
        # Create health_reminders table
        """
        CREATE TABLE IF NOT EXISTS health_reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            pet_id INTEGER,
            reminder_type VARCHAR(50) NOT NULL CHECK (reminder_type IN (
                'vaccination', 'vet_appointment', 'medication', 'grooming', 'checkup', 'custom'
            )),
            title VARCHAR(200) NOT NULL,
            description TEXT,
            due_date DATE NOT NULL,
            reminder_date DATE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR(20) DEFAULT 'pending' CHECK (status IN (
                'pending', 'completed', 'overdue', 'cancelled'
            )),
            completed_at DATETIME,
            send_email BOOLEAN DEFAULT TRUE,
            send_push BOOLEAN DEFAULT TRUE,
            days_before_reminder INTEGER DEFAULT 7,
            health_record_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (health_record_id) REFERENCES health_records(id) ON DELETE SET NULL
        );
        """,
        
        # Create pet_profiles table
        """
        CREATE TABLE IF NOT EXISTS pet_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name VARCHAR(100) NOT NULL,
            breed VARCHAR(100),
            age INTEGER,
            weight DECIMAL(5,2),
            gender VARCHAR(10),
            microchip_id VARCHAR(50),
            spayed_neutered BOOLEAN,
            known_allergies TEXT,
            medical_conditions TEXT,
            emergency_vet_name VARCHAR(100),
            emergency_vet_phone VARCHAR(20),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """,
        
        # Create health_insights table
        """
        CREATE TABLE IF NOT EXISTS health_insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            pet_id INTEGER,
            insight_type VARCHAR(50) NOT NULL,
            title VARCHAR(200) NOT NULL,
            content TEXT NOT NULL,
            confidence_score DECIMAL(3,2),
            generated_by VARCHAR(50),
            based_on_records TEXT,
            expiry_date DATE,
            shown_to_user BOOLEAN DEFAULT FALSE,
            user_feedback VARCHAR(20),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """,
        
        # Create indexes for better performance
        """
        CREATE INDEX IF NOT EXISTS idx_health_records_user_id ON health_records(user_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_health_records_pet_id ON health_records(pet_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_health_records_record_date ON health_records(record_date);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_health_records_record_type ON health_records(record_type);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_vaccinations_health_record_id ON vaccinations(health_record_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_medications_health_record_id ON medications(health_record_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_health_reminders_user_id ON health_reminders(user_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_health_reminders_due_date ON health_reminders(due_date);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_health_reminders_status ON health_reminders(status);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_pet_profiles_user_id ON pet_profiles(user_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_health_insights_user_id ON health_insights(user_id);
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_health_insights_pet_id ON health_insights(pet_id);
        """,
    ]
    
    with engine.connect() as conn:
        for sql in sql_commands:
            try:
                conn.execute(text(sql))
                print(f"✓ Executed: {sql.strip().split()[2]} {sql.strip().split()[5] if len(sql.strip().split()) > 5 else ''}")
            except SQLAlchemyError as e:
                print(f"✗ Error executing SQL: {e}")
                raise
        
        conn.commit()

def create_sample_data(engine):
    """Create sample data for testing (optional)"""
    
    sample_data_sql = [
        # Sample pet profile
        """
        INSERT OR IGNORE INTO pet_profiles (id, user_id, name, breed, age, weight, gender, known_allergies, medical_conditions)
        VALUES (1, 1, 'Buddy', 'Golden Retriever', 5, 65.5, 'Male', 'Chicken, Grass pollen', 'Hip dysplasia (mild)');
        """,
        
        # Sample health record
        """
        INSERT OR IGNORE INTO health_records 
        (id, user_id, pet_id, record_type, title, description, record_date, veterinarian_name, clinic_name, cost, insurance_covered, insurance_amount, notes)
        VALUES (1, 1, 1, 'vaccination', 'Annual DHPP Vaccination', 'Routine annual vaccination for distemper, hepatitis, parvovirus, and parainfluenza', 
                '2024-01-15', 'Dr. Sarah Johnson', 'Happy Paws Veterinary Clinic', 75.00, TRUE, 60.00, 'No adverse reactions observed');
        """,
        
        # Sample vaccination details
        """
        INSERT OR IGNORE INTO vaccinations 
        (id, health_record_id, vaccine_name, vaccine_type, administration_date, next_due_date, manufacturer)
        VALUES (1, 1, 'DHPP', 'core', '2024-01-15', '2025-01-15', 'Merck Animal Health');
        """,
        
        # Sample reminder
        """
        INSERT OR IGNORE INTO health_reminders 
        (id, user_id, pet_id, reminder_type, title, description, due_date, reminder_date, status)
        VALUES (1, 1, 1, 'vaccination', 'DHPP Vaccination Due', 'Annual DHPP vaccination is due for Buddy', 
                '2025-01-15', '2025-01-08', 'pending');
        """,
        
        # Sample health insight
        """
        INSERT OR IGNORE INTO health_insights 
        (id, user_id, pet_id, insight_type, title, content, confidence_score, generated_by, based_on_records)
        VALUES (1, 1, 1, 'care_tip', 'Hip Health for Golden Retrievers', 
                'Based on Buddy''s breed and age, consider adding joint supplements and regular low-impact exercise to support hip health. Golden Retrievers are prone to hip dysplasia, and preventive care can help maintain mobility.',
                0.85, 'gpt-4', '1');
        """
    ]
    
    with engine.connect() as conn:
        for sql in sample_data_sql:
            try:
                conn.execute(text(sql))
                print(f"✓ Sample data inserted")
            except SQLAlchemyError as e:
                print(f"Note: Sample data may already exist or users table not available: {e}")
        
        conn.commit()

def main():
    """Main migration function"""
    print("🏥 Health & Savings Tracker Database Migration")
    print("=" * 50)
    
    # Get database URL
    database_url = get_database_url()
    print(f"Database URL: {database_url}")
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        print("✓ Database connection successful")
        
        # Create health tables
        print("\n📋 Creating health tracking tables...")
        create_health_tables(engine)
        print("✓ Health tracking tables created successfully")
        
        # Ask if user wants sample data
        create_samples = input("\n❓ Create sample data for testing? (y/N): ").lower().strip()
        if create_samples in ['y', 'yes']:
            print("\n📝 Creating sample data...")
            create_sample_data(engine)
            print("✓ Sample data created successfully")
        
        print("\n🎉 Migration completed successfully!")
        print("\nNext steps:")
        print("1. Update your Flask app to use these new models")
        print("2. Test the health tracking API endpoints")
        print("3. Configure the frontend to use the health dashboard")
        
    except SQLAlchemyError as e:
        print(f"❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 