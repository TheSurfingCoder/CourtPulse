-- Up migration: Remove unused columns from courts table
-- Removes columns that are no longer used in the application

-- Remove google_place_id (not used, no Google Places integration)
ALTER TABLE courts DROP COLUMN IF EXISTS google_place_id;

-- Remove photon_name (replaced by facility_name)
ALTER TABLE courts DROP COLUMN IF EXISTS photon_name;
