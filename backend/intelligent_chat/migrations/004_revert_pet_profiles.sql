-- ============================================================================
-- REVERT PET_PROFILES TABLE TO ORIGINAL STRUCTURE
-- Remove columns added by intelligent_chat (002_enhance_pet_profiles.sql)
-- Version: 1.0.0
-- ============================================================================

-- Drop columns added by intelligent_chat
ALTER TABLE pet_profiles DROP COLUMN IF EXISTS image_url;
ALTER TABLE pet_profiles DROP COLUMN IF EXISTS image_description;
ALTER TABLE pet_profiles DROP COLUMN IF EXISTS collar_size;
ALTER TABLE pet_profiles DROP COLUMN IF EXISTS shoulder_height;
ALTER TABLE pet_profiles DROP COLUMN IF EXISTS girth;
ALTER TABLE pet_profiles DROP COLUMN IF EXISTS body_length;
ALTER TABLE pet_profiles DROP COLUMN IF EXISTS personality_traits;
ALTER TABLE pet_profiles DROP COLUMN IF EXISTS behavior_goals;
ALTER TABLE pet_profiles DROP COLUMN IF EXISTS purchase_date;
ALTER TABLE pet_profiles DROP COLUMN IF EXISTS adoption_date;
ALTER TABLE pet_profiles DROP COLUMN IF EXISTS historical_events;
ALTER TABLE pet_profiles DROP COLUMN IF EXISTS photo_gallery;
ALTER TABLE pet_profiles DROP COLUMN IF EXISTS registrations;

-- Drop indexes created by intelligent_chat
DROP INDEX IF EXISTS idx_pet_profiles_image_url;
DROP INDEX IF EXISTS idx_pet_profiles_purchase_date;
DROP INDEX IF EXISTS idx_pet_profiles_historical_events;
DROP INDEX IF EXISTS idx_pet_profiles_photo_gallery;

-- pet_profiles table is now back to its original structure
-- Only columns: id, user_id, name, breed, age, weight, gender, date_of_birth, 
--               microchip_id, spayed_neutered, known_allergies, medical_conditions,
--               emergency_vet_name, emergency_vet_phone, created_at, updated_at,
--               comprehensive_profile, color
