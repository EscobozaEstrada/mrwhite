-- ============================================================================
-- CREATE IC_DOG_PROFILES TABLE
-- Simplified dog profiles table for intelligent_chat system
-- User-controlled, no AI auto-updates
-- Version: 1.0.0
-- ============================================================================

CREATE TABLE IF NOT EXISTS ic_dog_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Basic Information (User-fillable)
    name VARCHAR(100) NOT NULL,
    breed VARCHAR(100),
    age INTEGER CHECK (age >= 0 AND age <= 30),
    date_of_birth DATE,
    weight NUMERIC(5, 2) CHECK (weight > 0 AND weight <= 300),
    gender VARCHAR(10),
    color VARCHAR(100),
    
    -- Image Fields
    image_url VARCHAR(500),           -- S3 URL of dog photo
    image_description TEXT,           -- Claude Vision analysis (personalized to this dog)
    
    -- Free-form Additional Details (JSONB for flexibility)
    comprehensive_profile JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_ic_dog_profiles_user_id ON ic_dog_profiles(user_id);
CREATE INDEX idx_ic_dog_profiles_name ON ic_dog_profiles(name);
CREATE INDEX idx_ic_dog_profiles_created_at ON ic_dog_profiles(created_at DESC);

-- GIN index for JSONB column
CREATE INDEX idx_ic_dog_profiles_comprehensive_profile ON ic_dog_profiles USING gin(comprehensive_profile);

-- Comments
COMMENT ON TABLE ic_dog_profiles IS 'Simplified dog profiles for intelligent_chat - user-controlled only';
COMMENT ON COLUMN ic_dog_profiles.image_url IS 'S3 URL of dog photo uploaded by user';
COMMENT ON COLUMN ic_dog_profiles.image_description IS 'Claude Vision analysis - personalized description of what is visible in the photo';
COMMENT ON COLUMN ic_dog_profiles.comprehensive_profile IS 'JSONB field for additional user-provided details';