-- Migration: Add individual court names for clustered courts
-- This enables proper naming for individual courts within clusters
-- Date: 2025-01-24

-- Add individual_court_name column
ALTER TABLE courts ADD COLUMN IF NOT EXISTS individual_court_name VARCHAR(255);

-- Create index for individual court name lookups
CREATE INDEX IF NOT EXISTS idx_courts_individual_court_name ON courts (individual_court_name);

-- Function to populate individual court names for existing clusters
CREATE OR REPLACE FUNCTION populate_individual_court_names()
RETURNS INTEGER AS $$
DECLARE
    cluster_record RECORD;
    court_record RECORD;
    court_counter INTEGER;
    total_updated INTEGER := 0;
BEGIN
    -- Get all clusters with more than 1 court
    FOR cluster_record IN 
        SELECT cluster_id, COUNT(*) as court_count
        FROM courts 
        WHERE cluster_id IS NOT NULL
        GROUP BY cluster_id
        HAVING COUNT(*) > 1
        ORDER BY cluster_id
    LOOP
        court_counter := 1;
        
        -- Get all courts in this cluster, ordered by id for consistent naming
        FOR court_record IN
            SELECT id, osm_id
            FROM courts 
            WHERE cluster_id = cluster_record.cluster_id
            ORDER BY id
        LOOP
            -- Update with individual court name
            UPDATE courts 
            SET individual_court_name = 'Court ' || court_counter::TEXT
            WHERE id = court_record.id;
            
            total_updated := total_updated + 1;
            court_counter := court_counter + 1;
        END LOOP;
    END LOOP;
    
    RETURN total_updated;
END;
$$ LANGUAGE plpgsql;

-- Function to clean court counts from photon_name values
CREATE OR REPLACE FUNCTION clean_photon_names()
RETURNS INTEGER AS $$
DECLARE
    court_record RECORD;
    clean_name TEXT;
    total_updated INTEGER := 0;
BEGIN
    -- Find photon_name values that contain court counts
    FOR court_record IN
        SELECT id, photon_name
        FROM courts 
        WHERE photon_name LIKE '%(% Courts)' OR photon_name LIKE '%(% Court)'
        ORDER BY id
    LOOP
        -- Remove court count from name using regex
        clean_name := regexp_replace(court_record.photon_name, '\s*\(\d+\s+Courts?\)', '', 'g');
        
        IF clean_name != court_record.photon_name THEN
            UPDATE courts 
            SET photon_name = clean_name
            WHERE id = court_record.id;
            
            total_updated := total_updated + 1;
        END IF;
    END LOOP;
    
    RETURN total_updated;
END;
$$ LANGUAGE plpgsql;

-- Execute the functions to populate data
DO $$
DECLARE
    cleaned_count INTEGER;
    populated_count INTEGER;
BEGIN
    -- Clean existing photon names
    SELECT clean_photon_names() INTO cleaned_count;
    RAISE NOTICE 'Cleaned % photon_name values', cleaned_count;
    
    -- Populate individual court names
    SELECT populate_individual_court_names() INTO populated_count;
    RAISE NOTICE 'Populated % individual court names', populated_count;
END $$;

-- Drop the temporary functions
DROP FUNCTION IF EXISTS populate_individual_court_names();
DROP FUNCTION IF EXISTS clean_photon_names();

-- Add constraint to ensure individual court names are properly formatted
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'chk_individual_court_name_format'
    ) THEN
        ALTER TABLE courts ADD CONSTRAINT chk_individual_court_name_format 
        CHECK (individual_court_name IS NULL OR individual_court_name ~ '^Court \d+$');
    END IF;
END $$;

-- Add comments for documentation
COMMENT ON COLUMN courts.individual_court_name IS 'Individual court name within a cluster (e.g., "Court 1", "Court 2")';
COMMENT ON INDEX idx_courts_individual_court_name IS 'Index for efficient lookups by individual court name';

-- Update table comment to reflect new functionality
COMMENT ON TABLE courts IS 'Sports courts and recreational facilities with individual naming for clustered courts';
