-- Add missing columns to ic_documents table for vet report functionality
-- Migration: 007_add_vet_report_columns.sql

-- Add is_vet_report column to mark documents as vet reports
ALTER TABLE ic_documents 
ADD COLUMN IF NOT EXISTS is_vet_report BOOLEAN DEFAULT FALSE;

-- Add dog_profile_id column to link documents to specific dogs
ALTER TABLE ic_documents 
ADD COLUMN IF NOT EXISTS dog_profile_id INTEGER REFERENCES pet_profiles(id) ON DELETE CASCADE;

-- Create index for efficient vet report queries
CREATE INDEX IF NOT EXISTS idx_ic_documents_is_vet_report ON ic_documents(is_vet_report);
CREATE INDEX IF NOT EXISTS idx_ic_documents_dog_profile_id ON ic_documents(dog_profile_id);

-- Update existing documents to mark vet reports based on filename patterns
UPDATE ic_documents 
SET is_vet_report = TRUE 
WHERE filename ILIKE '%vet%' 
   OR filename ILIKE '%report%' 
   OR filename ILIKE '%medical%'
   OR filename ILIKE '%health%'
   OR file_type IN ('pdf', 'doc', 'docx') 
   AND (filename ILIKE '%max%' OR filename ILIKE '%bella%');

-- Add comment to document the new columns
COMMENT ON COLUMN ic_documents.is_vet_report IS 'Marks documents as veterinary reports for health mode';
COMMENT ON COLUMN ic_documents.dog_profile_id IS 'Links documents to specific dog profiles';
