-- Up migration: Add cluster_id column to osm_courts_temp staging table
-- This column is used by populate_cluster_metadata.py to assign cluster IDs

-- Add cluster_id column if it doesn't exist
ALTER TABLE osm_courts_temp ADD COLUMN IF NOT EXISTS cluster_id UUID;
