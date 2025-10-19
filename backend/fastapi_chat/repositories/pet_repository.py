"""
Pet Profile Repository
Database operations for pet profiles with async support
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, date
from pet_models_pkg.pet_models import PetProfile, PetProfileCreate, PetProfileUpdate

logger = logging.getLogger(__name__)

class PetRepository:
    """
    Repository for pet profile database operations
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def create_pet_profile(self, user_id: int, pet_data: Dict[str, Any]) -> Optional[PetProfile]:
        """
        Create a new pet profile
        """
        try:
            # Handle date_of_birth conversion
            if pet_data.get('date_of_birth') and isinstance(pet_data['date_of_birth'], str):
                try:
                    pet_data['date_of_birth'] = datetime.fromisoformat(pet_data['date_of_birth']).date()
                except ValueError:
                    pet_data['date_of_birth'] = None
            
            pet_profile = PetProfile(
                user_id=user_id,
                **pet_data
            )
            
            self.db.add(pet_profile)
            await self.db.commit()
            await self.db.refresh(pet_profile)
            
            logger.info(f"✅ Created pet profile: {pet_profile.name} for user {user_id}")
            return pet_profile
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Error creating pet profile: {e}")
            await self.db.rollback()
            return None
    
    async def get_user_pets(self, user_id: int) -> List[PetProfile]:
        """
        Get all pet profiles for a user
        """
        try:
            result = await self.db.execute(
                select(PetProfile).where(PetProfile.user_id == user_id)
            )
            pets = result.scalars().all()
            logger.info(f"📋 Retrieved {len(pets)} pets for user {user_id}")
            return list(pets)
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Error retrieving pets for user {user_id}: {e}")
            return []
    
    async def get_pet_by_id(self, user_id: int, pet_id: int) -> Optional[PetProfile]:
        """
        Get a specific pet profile by ID (with user verification)
        """
        try:
            result = await self.db.execute(
                select(PetProfile).where(
                    and_(PetProfile.id == pet_id, PetProfile.user_id == user_id)
                )
            )
            pet = result.scalar_one_or_none()
            
            if pet:
                logger.info(f"🐕 Retrieved pet: {pet.name} (ID: {pet_id}) for user {user_id}")
            else:
                logger.warning(f"🚫 Pet not found: ID {pet_id} for user {user_id}")
            
            return pet
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Error retrieving pet {pet_id}: {e}")
            return None
    
    async def get_pet_by_name(self, user_id: int, pet_name: str) -> Optional[PetProfile]:
        """
        Get a pet profile by name (case-insensitive)
        """
        try:
            result = await self.db.execute(
                select(PetProfile).where(
                    and_(
                        PetProfile.user_id == user_id,
                        PetProfile.name.ilike(f"%{pet_name}%")
                    )
                )
            )
            pet = result.scalar_one_or_none()
            
            if pet:
                logger.info(f"🐕 Found pet by name: {pet.name} for user {user_id}")
            else:
                logger.debug(f"🔍 No pet found with name '{pet_name}' for user {user_id}")
            
            return pet
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Error searching for pet by name '{pet_name}': {e}")
            return None
    
    async def update_pet_profile(
        self, 
        user_id: int, 
        pet_id: int, 
        update_data: Dict[str, Any]
    ) -> Optional[PetProfile]:
        """
        Update a pet profile
        """
        try:
            # Handle date_of_birth conversion
            if update_data.get('date_of_birth') and isinstance(update_data['date_of_birth'], str):
                try:
                    update_data['date_of_birth'] = datetime.fromisoformat(update_data['date_of_birth']).date()
                except ValueError:
                    update_data['date_of_birth'] = None
            
            # Add updated timestamp
            update_data['updated_at'] = datetime.utcnow()
            
            # Remove None values to avoid overwriting existing data
            clean_data = {k: v for k, v in update_data.items() if v is not None}
            
            await self.db.execute(
                update(PetProfile).where(
                    and_(PetProfile.id == pet_id, PetProfile.user_id == user_id)
                ).values(**clean_data)
            )
            
            await self.db.commit()
            
            # Return updated pet
            updated_pet = await self.get_pet_by_id(user_id, pet_id)
            
            if updated_pet:
                logger.info(f"✅ Updated pet profile: {updated_pet.name} (ID: {pet_id})")
                logger.debug(f"🔧 Updated fields: {list(clean_data.keys())}")
            
            return updated_pet
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Error updating pet {pet_id}: {e}")
            await self.db.rollback()
            return None
    
    async def update_pet_field(
        self, 
        user_id: int, 
        pet_name: str, 
        field_name: str, 
        field_value: Any
    ) -> bool:
        """
        Update a specific field for a pet (by name)
        """
        try:
            # Get the pet first
            pet = await self.get_pet_by_name(user_id, pet_name)
            if not pet:
                logger.warning(f"🚫 Cannot update field '{field_name}': Pet '{pet_name}' not found for user {user_id}")
                return False
            
            # Prepare update data
            update_data = {
                field_name: field_value,
                'updated_at': datetime.utcnow()
            }
            
            await self.db.execute(
                update(PetProfile).where(
                    and_(PetProfile.id == pet.id, PetProfile.user_id == user_id)
                ).values(**update_data)
            )
            
            await self.db.commit()
            
            logger.info(f"✅ Updated {field_name} for {pet.name}: {field_value}")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Error updating field '{field_name}' for pet '{pet_name}': {e}")
            await self.db.rollback()
            return False
    
    async def delete_pet_profile(self, user_id: int, pet_id: int) -> bool:
        """
        Delete a pet profile
        """
        try:
            result = await self.db.execute(
                delete(PetProfile).where(
                    and_(PetProfile.id == pet_id, PetProfile.user_id == user_id)
                )
            )
            
            if result.rowcount > 0:
                await self.db.commit()
                logger.info(f"🗑️ Deleted pet profile: ID {pet_id} for user {user_id}")
                return True
            else:
                logger.warning(f"🚫 Pet not found for deletion: ID {pet_id} for user {user_id}")
                return False
                
        except SQLAlchemyError as e:
            logger.error(f"❌ Error deleting pet {pet_id}: {e}")
            await self.db.rollback()
            return False
    
    async def get_missing_fields_summary(self, user_id: int) -> Dict[str, List[str]]:
        """
        Get summary of missing fields for all user's pets
        """
        try:
            pets = await self.get_user_pets(user_id)
            summary = {}
            
            for pet in pets:
                missing_fields = pet.get_missing_fields()
                if missing_fields:
                    summary[pet.name] = missing_fields
            
            logger.info(f"📊 Missing fields summary for user {user_id}: {len(summary)} pets with missing data")
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error getting missing fields summary: {e}")
            return {}
    
    async def search_pets_by_criteria(
        self, 
        user_id: int, 
        criteria: Dict[str, Any]
    ) -> List[PetProfile]:
        """
        Search pets by multiple criteria
        """
        try:
            query = select(PetProfile).where(PetProfile.user_id == user_id)
            
            # Add search criteria
            if criteria.get('breed'):
                query = query.where(PetProfile.breed.ilike(f"%{criteria['breed']}%"))
            
            if criteria.get('age_min'):
                query = query.where(PetProfile.age >= criteria['age_min'])
            
            if criteria.get('age_max'):
                query = query.where(PetProfile.age <= criteria['age_max'])
            
            if criteria.get('gender'):
                query = query.where(PetProfile.gender == criteria['gender'])
            
            result = await self.db.execute(query)
            pets = result.scalars().all()
            
            logger.info(f"🔍 Search found {len(pets)} pets matching criteria for user {user_id}")
            return list(pets)
            
        except SQLAlchemyError as e:
            logger.error(f"❌ Error searching pets: {e}")
            return []
