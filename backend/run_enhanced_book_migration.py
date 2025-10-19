"""
Script to run the enhanced book system migration
"""
from migrations.add_enhanced_book_system import run_migration

if __name__ == "__main__":
    print("Running enhanced book system migration...")
    success = run_migration()
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed. Check the logs for details.") 