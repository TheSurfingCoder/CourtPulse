-- Migration: Clean up courts table schema for Photon integration
-- Remove redundant columns and add new ones for Photon data
-- Date: 2025-01-16

-- Remove redundant columns
ALTER TABLE courts DROP COLUMN IF EXISTS address;
ALTER TABLE courts DROP COLUMN IF EXISTS surface;
ALTER TABLE courts DROP COLUMN IF EXISTS google_place_id;

-- Add new columns for Photon integration
ALTER TABLE courts ADD COLUMN IF NOT EXISTS photon_name VARCHAR(255);
ALTER TABLE courts ADD COLUMN IF NOT EXISTS photon_distance_km DECIMAL(10,6);
ALTER TABLE courts ADD COLUMN IF NOT EXISTS photon_source VARCHAR(50) DEFAULT 'search_api';
ALTER TABLE courts ADD COLUMN IF NOT EXISTS import_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Update indexes (drop old, create new)
DROP INDEX IF EXISTS idx_courts_google_place_id;
CREATE INDEX IF NOT EXISTS idx_courts_photon_name ON courts (photon_name);
CREATE INDEX IF NOT EXISTS idx_courts_photon_source ON courts (photon_source);
CREATE INDEX IF NOT EXISTS idx_courts_import_timestamp ON courts (import_timestamp);

-- Add database-level validation constraints
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'chk_photon_distance_positive'
    ) THEN
        ALTER TABLE courts ADD CONSTRAINT chk_photon_distance_positive 
        CHECK (photon_distance_km IS NULL OR photon_distance_km >= 0);
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'chk_photon_source_valid'
    ) THEN
        ALTER TABLE courts ADD CONSTRAINT chk_photon_source_valid 
        CHECK (photon_source IN ('search_api', 'reverse_geocoding', 'fallback'));
    END IF;
END $$;

-- Add comments for documentation
COMMENT ON COLUMN courts.photon_name IS 'Name extracted from Photon API (search or reverse geocoding)';
COMMENT ON COLUMN courts.photon_distance_km IS 'Distance to the found location in kilometers';
COMMENT ON COLUMN courts.photon_source IS 'Source of the name (search_api, reverse_geocoding, fallback)';
COMMENT ON COLUMN courts.import_timestamp IS 'When this record was last imported/updated';

-- Update table comment
COMMENT ON TABLE courts IS 'Sports courts and recreational facilities with Photon geocoding integration';


