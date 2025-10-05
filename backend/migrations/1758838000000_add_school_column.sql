-- Add school boolean column to courts table
-- This column will be true when the court's name was derived from a school search

ALTER TABLE courts 
ADD COLUMN school BOOLEAN DEFAULT FALSE;

-- Create an index for efficient filtering
CREATE INDEX idx_courts_school ON courts(school);

-- Update existing records where photon_name contains school keywords
UPDATE courts 
SET school = TRUE 
WHERE photon_name ILIKE '%school%' 
   OR photon_name ILIKE '%academy%' 
   OR photon_name ILIKE '%college%' 
   OR photon_name ILIKE '%university%' 
   OR photon_name ILIKE '%institute%';
