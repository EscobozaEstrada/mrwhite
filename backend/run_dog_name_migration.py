"""
Script to run the dog_name migration
"""

from migrations.add_dog_name_to_users import run_migration

if __name__ == "__main__":
    print("Running migration to add dog_name column to users table...")
    run_migration()
    print("Migration script completed.") 