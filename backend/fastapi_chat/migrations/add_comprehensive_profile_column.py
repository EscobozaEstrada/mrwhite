"""
Database Migration Script: Add comprehensive_profile JSONB column to pet_profiles table
This migration adds the comprehensive JSON storage for complete pet details
"""

import asyncio
import logging
import sys
import os

# Add the project directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import json

# Import the database session from models to use the same connection as the main app
from models import AsyncSessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComprehensiveProfileMigration:
    """Migration class to add and populate comprehensive_profile JSONB column"""
    
    def __init__(self):
        # Use the same database session factory as the main application
        self.async_session_factory = AsyncSessionLocal
    
    def create_json_from_columns(self, pet_data: dict) -> dict:
        """Create unstructured JSON profile from existing column data"""
        json_profile = {}
        
        # Only add fields that have actual data (not None or empty)
        if pet_data.get("breed"):
            json_profile["breed"] = pet_data["breed"]
        
        if pet_data.get("age"):
            json_profile["age"] = pet_data["age"]
            
        if pet_data.get("weight"):
            json_profile["weight"] = float(pet_data["weight"])
            
        if pet_data.get("gender"):
            json_profile["gender"] = pet_data["gender"]
            
        if pet_data.get("date_of_birth"):
            json_profile["date_of_birth"] = pet_data["date_of_birth"].isoformat()
            
        if pet_data.get("microchip_id"):
            json_profile["microchip_id"] = pet_data["microchip_id"]
            
        if pet_data.get("spayed_neutered") is not None:
            json_profile["spayed_neutered"] = pet_data["spayed_neutered"]
            
        if pet_data.get("known_allergies"):
            json_profile["known_allergies"] = pet_data["known_allergies"]
            
        if pet_data.get("medical_conditions"):
            json_profile["medical_conditions"] = pet_data["medical_conditions"]
            
        if pet_data.get("emergency_vet_name"):
            json_profile["vet_name"] = pet_data["emergency_vet_name"]
            
        if pet_data.get("emergency_vet_phone"):
            json_profile["vet_phone"] = pet_data["emergency_vet_phone"]
        
        return json_profile
    
    async def check_column_exists(self, session: AsyncSession) -> bool:
        """Check if comprehensive_profile column already exists"""
        try:
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'pet_profiles' 
                AND column_name = 'comprehensive_profile';
            """))
            return result.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking column existence: {e}")
            return False
    
    async def add_column(self, session: AsyncSession):
        """Add comprehensive_profile JSONB column to pet_profiles table"""
        try:
            await session.execute(text("""
                ALTER TABLE pet_profiles 
                ADD COLUMN comprehensive_profile JSONB DEFAULT '{}';
            """))
            await session.commit()
            logger.info("✅ Added comprehensive_profile JSONB column to pet_profiles table")
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Error adding column: {e}")
            raise
    
    async def populate_existing_pets(self, session: AsyncSession):
        """Populate comprehensive_profile for existing pets"""
        try:
            # Get all existing pets
            result = await session.execute(text("""
                SELECT id, user_id, name, breed, age, weight, gender, date_of_birth,
                       microchip_id, spayed_neutered, known_allergies, medical_conditions,
                       emergency_vet_name, emergency_vet_phone
                FROM pet_profiles 
                WHERE comprehensive_profile IS NULL OR comprehensive_profile = '{}'
            """))
            
            pets = result.fetchall()
            logger.info(f"🔄 Found {len(pets)} pets to populate with comprehensive profiles")
            
            for pet in pets:
                # Convert row to dict
                pet_data = {
                    "name": pet.name,
                    "breed": pet.breed,
                    "age": pet.age,
                    "weight": pet.weight,
                    "gender": pet.gender,
                    "date_of_birth": pet.date_of_birth,
                    "microchip_id": pet.microchip_id,
                    "spayed_neutered": pet.spayed_neutered,
                    "known_allergies": pet.known_allergies,
                    "medical_conditions": pet.medical_conditions,
                    "emergency_vet_name": pet.emergency_vet_name,
                    "emergency_vet_phone": pet.emergency_vet_phone
                }
                
                # Create JSON from existing column data (only non-empty values)
                json_profile = self.create_json_from_columns(pet_data)
                
                # Update pet with JSON profile (empty if no data in columns)
                await session.execute(text("""
                    UPDATE pet_profiles 
                    SET comprehensive_profile = :profile 
                    WHERE id = :pet_id
                """), {
                    "profile": json.dumps(json_profile),
                    "pet_id": pet.id
                })
                
                if json_profile:
                    logger.info(f"✅ Migrated {len(json_profile)} fields from columns to JSON for pet: {pet.name} (ID: {pet.id})")
                else:
                    logger.info(f"✅ Set empty JSON profile for pet: {pet.name} (ID: {pet.id}) - no column data to migrate")
            
            await session.commit()
            logger.info(f"✅ Successfully populated {len(pets)} pet comprehensive profiles")
            
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Error populating existing pets: {e}")
            raise
    
    async def run_migration(self):
        """Run the complete migration process"""
        logger.info("🚀 Starting comprehensive profile migration...")
        
        async with self.async_session_factory() as session:
            try:
                # Check if column already exists
                column_exists = await self.check_column_exists(session)
                
                if not column_exists:
                    # Add the column
                    await self.add_column(session)
                else:
                    logger.info("ℹ️ comprehensive_profile column already exists")
                
                # Populate existing pets
                await self.populate_existing_pets(session)
                
                logger.info("✅ Migration completed successfully!")
                
            except Exception as e:
                logger.error(f"❌ Migration failed: {e}")
                raise
            finally:
                await session.close()
    
    async def cleanup(self):
        """Clean up database connections - using shared connection, no cleanup needed"""
        pass

async def main():
    """Run the migration"""
    migration = ComprehensiveProfileMigration()
    try:
        await migration.run_migration()
    finally:
        await migration.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
