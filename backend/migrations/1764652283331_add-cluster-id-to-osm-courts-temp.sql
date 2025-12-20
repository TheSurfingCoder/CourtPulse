-- Up migration: Add cluster_id column to osm_courts_temp staging table
-- This column is used by populate_cluster_metadata.py to assign cluster IDs
-- Note: osm_courts_temp is a temporary staging table that may not exist in all environments

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'osm_courts_temp') THEN
        ALTER TABLE osm_courts_temp ADD COLUMN IF NOT EXISTS cluster_id UUID;
    END IF;
END $$;
