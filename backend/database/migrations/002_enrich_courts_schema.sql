-- Up migration: Enrich courts table schema for data enrichment pipeline
-- This migration adds columns for OSM data, Google Places integration, and enhanced metadata

-- First, let's add the new columns
ALTER TABLE courts 
ADD COLUMN IF NOT EXISTS osm_id VARCHAR(255) UNIQUE NOT NULL,
ADD COLUMN IF NOT EXISTS google_place_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS geom GEOMETRY(POLYGON, 4326),
ADD COLUMN IF NOT EXISTS sport VARCHAR(50) NOT NULL,
ADD COLUMN IF NOT EXISTS hoops INTEGER,
ADD COLUMN IF NOT EXISTS fallback_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS enriched_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS import_batch_id VARCHAR(100),
ADD COLUMN IF NOT EXISTS surface_type VARCHAR(50);

-- Create sport ENUM type
DO $$ BEGIN
    CREATE TYPE sport_type AS ENUM ('basketball', 'tennis', 'soccer', 'volleyball', 'handball', 'other');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Alter sport column to use ENUM (only if it's not already an ENUM)
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'courts' 
        AND column_name = 'sport' 
        AND data_type = 'USER-DEFINED'
    ) THEN
        ALTER TABLE courts ALTER COLUMN sport TYPE sport_type USING sport::sport_type;
    END IF;
END $$;

-- Create surface_type ENUM
DO $$ BEGIN
    CREATE TYPE surface_type_enum AS ENUM ('asphalt', 'concrete', 'wood', 'synthetic', 'clay', 'grass', 'other');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Alter surface_type column to use ENUM (only if it's not already an ENUM)
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'courts' 
        AND column_name = 'surface_type' 
        AND data_type = 'USER-DEFINED'
    ) THEN
        ALTER TABLE courts ALTER COLUMN surface_type TYPE surface_type_enum USING surface_type::surface_type_enum;
    END IF;
END $$;

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_courts_osm_id ON courts (osm_id);
CREATE INDEX IF NOT EXISTS idx_courts_google_place_id ON courts (google_place_id);
CREATE INDEX IF NOT EXISTS idx_courts_sport ON courts (sport);
CREATE INDEX IF NOT EXISTS idx_courts_import_batch_id ON courts (import_batch_id);
CREATE INDEX IF NOT EXISTS idx_courts_surface_type ON courts (surface_type);

-- Create spatial index for geom column (if it doesn't exist)
CREATE INDEX IF NOT EXISTS idx_courts_geom ON courts USING GIST (geom);

-- Add constraints
ALTER TABLE courts 
ADD CONSTRAINT IF NOT EXISTS chk_hoops_positive CHECK (hoops IS NULL OR hoops > 0),
ADD CONSTRAINT IF NOT EXISTS chk_osm_id_not_empty CHECK (osm_id != '');

-- Add comments for documentation
COMMENT ON COLUMN courts.osm_id IS 'OpenStreetMap object ID (e.g., way/28283137)';
COMMENT ON COLUMN courts.google_place_id IS 'Google Places API place_id for enriched data';
COMMENT ON COLUMN courts.geom IS 'PostGIS polygon geometry from OSM data';
COMMENT ON COLUMN courts.sport IS 'Sport type played at this court';
COMMENT ON COLUMN courts.hoops IS 'Number of basketball hoops (for basketball courts)';
COMMENT ON COLUMN courts.fallback_name IS 'Fallback name from OSM data when no specific name exists';
COMMENT ON COLUMN courts.enriched_name IS 'Enriched name from Google Places API or other sources';
COMMENT ON COLUMN courts.import_batch_id IS 'Batch identifier for tracking data imports';
COMMENT ON COLUMN courts.surface_type IS 'Type of playing surface';

-- Down migration: Remove added columns and types
-- (This would be run if rolling back the migration)
/*
ALTER TABLE courts 
DROP COLUMN IF EXISTS osm_id,
DROP COLUMN IF EXISTS google_place_id,
DROP COLUMN IF EXISTS geom,
DROP COLUMN IF EXISTS sport,
DROP COLUMN IF EXISTS hoops,
DROP COLUMN IF EXISTS fallback_name,
DROP COLUMN IF EXISTS enriched_name,
DROP COLUMN IF EXISTS import_batch_id,
DROP COLUMN IF EXISTS surface_type;

DROP TYPE IF EXISTS sport_type;
DROP TYPE IF EXISTS surface_type_enum;

DROP INDEX IF EXISTS idx_courts_osm_id;
DROP INDEX IF EXISTS idx_courts_google_place_id;
DROP INDEX IF EXISTS idx_courts_sport;
DROP INDEX IF EXISTS idx_courts_import_batch_id;
DROP INDEX IF EXISTS idx_courts_surface_type;
DROP INDEX IF EXISTS idx_courts_geom;
*/
