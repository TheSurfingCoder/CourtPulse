-- Up migration: Clean up courts schema for better data structure
-- This migration simplifies the location columns and removes redundant fields

-- Drop redundant columns
ALTER TABLE courts DROP COLUMN IF EXISTS name;
ALTER TABLE courts DROP COLUMN IF EXISTS type;
ALTER TABLE courts DROP COLUMN IF EXISTS import_batch_id;
ALTER TABLE courts DROP COLUMN IF EXISTS location;
ALTER TABLE courts DROP COLUMN IF EXISTS location_point;
ALTER TABLE courts DROP COLUMN IF EXISTS centroid_point;
ALTER TABLE courts DROP COLUMN IF EXISTS centroid_generated;

-- Add simplified centroid column
ALTER TABLE courts ADD COLUMN IF NOT EXISTS centroid GEOGRAPHY(POINT, 4326);

-- Create index for new centroid column
CREATE INDEX IF NOT EXISTS idx_courts_centroid ON courts USING GIST (centroid);

-- Add comments for documentation
COMMENT ON COLUMN courts.geom IS 'Original polygon geometry from OSM GeoJSON';
COMMENT ON COLUMN courts.centroid IS 'Calculated center point from polygon geometry';

-- Down migration: Restore previous schema (for rollback if needed)
-- Note: This will not restore data that was dropped
/*
ALTER TABLE courts DROP COLUMN IF EXISTS centroid;
DROP INDEX IF EXISTS idx_courts_centroid;

ALTER TABLE courts 
ADD COLUMN IF NOT EXISTS name VARCHAR(255) NOT NULL DEFAULT 'Unknown Court',
ADD COLUMN IF NOT EXISTS type VARCHAR(50) NOT NULL DEFAULT 'basketball',
ADD COLUMN IF NOT EXISTS import_batch_id VARCHAR(100),
ADD COLUMN IF NOT EXISTS location GEOMETRY(POINT, 4326) NOT NULL,
ADD COLUMN IF NOT EXISTS location_point GEOGRAPHY(POINT, 4326),
ADD COLUMN IF NOT EXISTS centroid_point GEOGRAPHY(POINT, 4326),
ADD COLUMN IF NOT EXISTS centroid_generated GEOGRAPHY(POINT, 4326);

CREATE INDEX IF NOT EXISTS idx_courts_location ON courts USING GIST (location);
CREATE INDEX IF NOT EXISTS idx_courts_location_point ON courts USING GIST (location_point);
CREATE INDEX IF NOT EXISTS idx_courts_centroid_generated ON courts USING GIST (centroid_generated);
*/
