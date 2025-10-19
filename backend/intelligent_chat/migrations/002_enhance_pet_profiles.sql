-- ============================================================================
-- ENHANCE PET_PROFILES TABLE
-- Add comprehensive fields for intelligent chat dog profiles
-- Version: 1.0.0
-- ============================================================================

-- Add image fields
ALTER TABLE pet_profiles ADD COLUMN IF NOT EXISTS image_url VARCHAR(500);
ALTER TABLE pet_profiles ADD COLUMN IF NOT EXISTS image_description TEXT;

-- Add dimension fields
ALTER TABLE pet_profiles ADD COLUMN IF NOT EXISTS collar_size VARCHAR(20);
ALTER TABLE pet_profiles ADD COLUMN IF NOT EXISTS shoulder_height NUMERIC(5, 2);  -- in inches
ALTER TABLE pet_profiles ADD COLUMN IF NOT EXISTS girth NUMERIC(5, 2);  -- in inches
ALTER TABLE pet_profiles ADD COLUMN IF NOT EXISTS body_length NUMERIC(5, 2);  -- in inches

-- Add personality and behavior fields
ALTER TABLE pet_profiles ADD COLUMN IF NOT EXISTS personality_traits TEXT;
ALTER TABLE pet_profiles ADD COLUMN IF NOT EXISTS behavior_goals TEXT;

-- Add historical events field (JSONB for flexibility)
ALTER TABLE pet_profiles ADD COLUMN IF NOT EXISTS historical_events JSONB DEFAULT '{}';

-- Add purchase/adoption date
ALTER TABLE pet_profiles ADD COLUMN IF NOT EXISTS purchase_date DATE;
ALTER TABLE pet_profiles ADD COLUMN IF NOT EXISTS adoption_date DATE;

-- Add photo gallery (array of S3 URLs)
ALTER TABLE pet_profiles ADD COLUMN IF NOT EXISTS photo_gallery JSONB DEFAULT '[]';

-- Add registrations and certifications (JSONB for flexibility)
ALTER TABLE pet_profiles ADD COLUMN IF NOT EXISTS registrations JSONB DEFAULT '[]';

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_pet_profiles_image_url ON pet_profiles(image_url) WHERE image_url IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_pet_profiles_purchase_date ON pet_profiles(purchase_date);
CREATE INDEX IF NOT EXISTS idx_pet_profiles_historical_events ON pet_profiles USING gin(historical_events);
CREATE INDEX IF NOT EXISTS idx_pet_profiles_photo_gallery ON pet_profiles USING gin(photo_gallery);

-- Add comments for documentation
COMMENT ON COLUMN pet_profiles.image_url IS 'S3 URL of the main dog photo';
COMMENT ON COLUMN pet_profiles.image_description IS 'Claude Vision analysis of the dog photo for chatbot context';
COMMENT ON COLUMN pet_profiles.collar_size IS 'Dog collar size (XS, S, M, L, XL, etc.)';
COMMENT ON COLUMN pet_profiles.shoulder_height IS 'Height at shoulder in inches';
COMMENT ON COLUMN pet_profiles.girth IS 'Chest girth in inches';
COMMENT ON COLUMN pet_profiles.body_length IS 'Body length from neck to tail base in inches';
COMMENT ON COLUMN pet_profiles.personality_traits IS 'Personality traits the user adores about their dog';
COMMENT ON COLUMN pet_profiles.behavior_goals IS 'Behaviors the user wants to change or improve';
COMMENT ON COLUMN pet_profiles.historical_events IS 'JSON object with memorable dates: {"first_walk": "2024-01-15", "first_bath": "2024-01-20"}';
COMMENT ON COLUMN pet_profiles.purchase_date IS 'Date the dog was purchased';
COMMENT ON COLUMN pet_profiles.adoption_date IS 'Date the dog was adopted';
COMMENT ON COLUMN pet_profiles.photo_gallery IS 'Array of photo objects: [{"url": "s3://...", "type": "vacation", "date": "2024-01-15", "description": "Beach trip"}]';
COMMENT ON COLUMN pet_profiles.registrations IS 'Array of registration/certification objects: [{"type": "AKC", "number": "123", "date": "2024-01-01", "document_url": "s3://..."}]';

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
