-- Up migration: Enrich courts table schema for data enrichment pipeline
-- This migration adds columns for OSM data, Google Places integration, and enhanced metadata

-- Add new columns
ALTER TABLE courts 
ADD COLUMN IF NOT EXISTS source VARCHAR(50) NOT NULL DEFAULT 'osm',
ADD COLUMN IF NOT EXISTS osm_id VARCHAR(255) UNIQUE,
ADD COLUMN IF NOT EXISTS google_place_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS geom GEOMETRY(POLYGON, 4326),
ADD COLUMN IF NOT EXISTS sport VARCHAR(50) NOT NULL,
ADD COLUMN IF NOT EXISTS hoops INTEGER,
ADD COLUMN IF NOT EXISTS fallback_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS enriched_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS import_batch_id VARCHAR(100),
ADD COLUMN IF NOT EXISTS surface_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS location_point GEOGRAPHY(POINT, 4326),
ADD COLUMN IF NOT EXISTS centroid_point GEOGRAPHY(POINT, 4326);

-- Create ENUM types
DO $$ BEGIN
    CREATE TYPE court_source_enum AS ENUM ('osm', 'user', 'google', 'other');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE sport_type AS ENUM ('basketball', 'tennis', 'soccer', 'volleyball', 'handball', 'other');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE surface_type_enum AS ENUM ('asphalt', 'concrete', 'wood', 'synthetic', 'clay', 'grass', 'other');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- If source column is still VARCHAR, upgrade to ENUM
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'courts'
        AND column_name = 'source'
        AND data_type = 'USER-DEFINED'
    ) THEN
        -- Remove default before converting to ENUM
        ALTER TABLE courts ALTER COLUMN source DROP DEFAULT;
        ALTER TABLE courts 
        ALTER COLUMN source TYPE court_source_enum USING source::court_source_enum;
        -- Set default after conversion
        ALTER TABLE courts ALTER COLUMN source SET DEFAULT 'osm';
    END IF;
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
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'courts' 
        AND column_name = 'surface_type' 
        AND data_type = 'USER-DEFINED'
    ) THEN
        ALTER TABLE courts ALTER COLUMN surface_type TYPE surface_type_enum USING surface_type::surface_type_enum;
    END IF;
END $$;

-- Generate centroid automatically from geom if available
ALTER TABLE courts 
ADD COLUMN IF NOT EXISTS centroid_generated GEOGRAPHY(POINT, 4326);

-- Optional: backfill centroid for existing rows
UPDATE courts
SET centroid_generated = ST_Centroid(geom)::GEOGRAPHY
WHERE geom IS NOT NULL AND centroid_generated IS NULL;

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_courts_source ON courts (source);
CREATE INDEX IF NOT EXISTS idx_courts_osm_id ON courts (osm_id);
CREATE INDEX IF NOT EXISTS idx_courts_google_place_id ON courts (google_place_id);
CREATE INDEX IF NOT EXISTS idx_courts_sport ON courts (sport);
CREATE INDEX IF NOT EXISTS idx_courts_import_batch_id ON courts (import_batch_id);
CREATE INDEX IF NOT EXISTS idx_courts_surface_type ON courts (surface_type);
CREATE INDEX IF NOT EXISTS idx_courts_location_point ON courts USING GIST (location_point);
CREATE INDEX IF NOT EXISTS idx_courts_centroid_generated ON courts USING GIST (centroid_generated);

-- Create spatial index for geom column (if it doesn't exist)
CREATE INDEX IF NOT EXISTS idx_courts_geom ON courts USING GIST (geom);

-- Add constraints (only if they don't exist)
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'chk_hoops_positive'
    ) THEN
        ALTER TABLE courts ADD CONSTRAINT chk_hoops_positive CHECK (hoops IS NULL OR hoops > 0);
    END IF;
END $$;


-- Add comments for documentation
COMMENT ON COLUMN courts.source IS 'Data source for this court (e.g., osm, user, google, other)';
COMMENT ON COLUMN courts.osm_id IS 'OpenStreetMap object ID (e.g., way/28283137)';
COMMENT ON COLUMN courts.google_place_id IS 'Google Places API place_id for enriched data';
COMMENT ON COLUMN courts.geom IS 'PostGIS polygon geometry from OSM data';
COMMENT ON COLUMN courts.sport IS 'Sport type played at this court';
COMMENT ON COLUMN courts.hoops IS 'Number of basketball hoops (for basketball courts)';
COMMENT ON COLUMN courts.fallback_name IS 'Fallback name from OSM data when no specific name exists';
COMMENT ON COLUMN courts.enriched_name IS 'Enriched name from Google Places API or other sources';
COMMENT ON COLUMN courts.import_batch_id IS 'Batch identifier for tracking data imports';
COMMENT ON COLUMN courts.surface_type IS 'Type of playing surface';
COMMENT ON COLUMN courts.location_point IS 'User-provided or simplified point location';
COMMENT ON COLUMN courts.centroid_point IS 'Optional manual centroid if needed';
COMMENT ON COLUMN courts.centroid_generated IS 'Auto-calculated centroid from polygon geom';
