-- Up migration: Remove enriched_name column from courts table
-- This column was never populated and is not needed

-- Drop the enriched_name column
ALTER TABLE courts DROP COLUMN IF EXISTS enriched_name;
