-- Migration: Remove import_timestamp column and use updated_at instead
-- This simplifies the schema by using standard created_at/updated_at columns

-- Remove import_timestamp column
ALTER TABLE courts DROP COLUMN IF EXISTS import_timestamp;

-- Remove the index on import_timestamp
DROP INDEX IF EXISTS idx_courts_import_timestamp;

-- Add comment to clarify updated_at usage
COMMENT ON COLUMN courts.updated_at IS 'Last updated timestamp - automatically updated on any record change including data enrichment';


