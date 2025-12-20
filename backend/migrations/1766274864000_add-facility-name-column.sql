-- Up Migration: Add facility_name column to courts table
-- This column stores the name of the facility (park, school, etc.) containing the court
ALTER TABLE courts ADD COLUMN IF NOT EXISTS facility_name TEXT;

-- Down Migration (not typically needed)
-- ALTER TABLE courts DROP COLUMN IF EXISTS facility_name;

