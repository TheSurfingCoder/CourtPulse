-- Up migration: Create courts table with final structure
-- This migration creates the courts table with the structure after all other migrations

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Create the courts table with the final structure
CREATE TABLE IF NOT EXISTS courts (
    id SERIAL PRIMARY KEY,
    address VARCHAR(500),
    surface VARCHAR(50),
    is_public BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    -- Columns from enrich_courts_schema migration
    source VARCHAR(50) NOT NULL DEFAULT 'osm',
    osm_id VARCHAR(255) UNIQUE,
    google_place_id VARCHAR(255),
    geom GEOMETRY(POLYGON, 4326),
    sport VARCHAR(50) NOT NULL,
    hoops INTEGER,
    fallback_name VARCHAR(255),
    enriched_name VARCHAR(255),
    surface_type VARCHAR(50),
    -- Final structure from clean_courts_schema migration
    centroid GEOGRAPHY(POINT, 4326)
);

-- Create ENUM types (from enrich_courts_schema)
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

-- Convert columns to use ENUMs (only if they exist)
-- First check if source column exists and convert it
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'source') THEN
        ALTER TABLE courts ALTER COLUMN source DROP DEFAULT;
        ALTER TABLE courts ALTER COLUMN source TYPE court_source_enum USING source::court_source_enum;
        ALTER TABLE courts ALTER COLUMN source SET DEFAULT 'osm'::court_source_enum;
    END IF;
END $$;

DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'sport') THEN
        ALTER TABLE courts ALTER COLUMN sport TYPE sport_type USING sport::sport_type;
    END IF;
END $$;

DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'surface_type') THEN
        ALTER TABLE courts ALTER COLUMN surface_type TYPE surface_type_enum USING surface_type::surface_type_enum;
    END IF;
END $$;

-- Create indexes (only if columns exist)
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'source') THEN
        CREATE INDEX IF NOT EXISTS idx_courts_source ON courts (source);
    END IF;
END $$;

DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'osm_id') THEN
        CREATE INDEX IF NOT EXISTS idx_courts_osm_id ON courts (osm_id);
    END IF;
END $$;

DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'google_place_id') THEN
        CREATE INDEX IF NOT EXISTS idx_courts_google_place_id ON courts (google_place_id);
    END IF;
END $$;

DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'sport') THEN
        CREATE INDEX IF NOT EXISTS idx_courts_sport ON courts (sport);
    END IF;
END $$;

DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'surface_type') THEN
        CREATE INDEX IF NOT EXISTS idx_courts_surface_type ON courts (surface_type);
    END IF;
END $$;

DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'geom') THEN
        CREATE INDEX IF NOT EXISTS idx_courts_geom ON courts USING GIST (geom);
    END IF;
END $$;

DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'centroid') THEN
        CREATE INDEX IF NOT EXISTS idx_courts_centroid ON courts USING GIST (centroid);
    END IF;
END $$;

-- Add constraints (only if columns exist)
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'hoops') THEN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint 
            WHERE conname = 'chk_hoops_positive'
        ) THEN
            ALTER TABLE courts ADD CONSTRAINT chk_hoops_positive CHECK (hoops IS NULL OR hoops > 0);
        END IF;
    END IF;
END $$;

-- Add comments for documentation (only if columns exist)
COMMENT ON TABLE courts IS 'Sports courts and recreational facilities';
COMMENT ON COLUMN courts.id IS 'Unique identifier for the court';
COMMENT ON COLUMN courts.address IS 'Physical address of the court';
COMMENT ON COLUMN courts.surface IS 'Playing surface type (asphalt, concrete, etc.)';
COMMENT ON COLUMN courts.is_public IS 'Whether the court is publicly accessible';

DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'source') THEN
        COMMENT ON COLUMN courts.source IS 'Data source for this court (e.g., osm, user, google, other)';
    END IF;
END $$;

DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'osm_id') THEN
        COMMENT ON COLUMN courts.osm_id IS 'OpenStreetMap object ID (e.g., way/28283137)';
    END IF;
END $$;

DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'google_place_id') THEN
        COMMENT ON COLUMN courts.google_place_id IS 'Google Places API place_id for enriched data';
    END IF;
END $$;

DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'geom') THEN
        COMMENT ON COLUMN courts.geom IS 'PostGIS polygon geometry from OSM data';
    END IF;
END $$;

DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'sport') THEN
        COMMENT ON COLUMN courts.sport IS 'Sport type played at this court';
    END IF;
END $$;

DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'hoops') THEN
        COMMENT ON COLUMN courts.hoops IS 'Number of basketball hoops (for basketball courts)';
    END IF;
END $$;

DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'fallback_name') THEN
        COMMENT ON COLUMN courts.fallback_name IS 'Fallback name from OSM data when no specific name exists';
    END IF;
END $$;

DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'enriched_name') THEN
        COMMENT ON COLUMN courts.enriched_name IS 'Enriched name from Google Places API or other sources';
    END IF;
END $$;

DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'surface_type') THEN
        COMMENT ON COLUMN courts.surface_type IS 'Type of playing surface';
    END IF;
END $$;

DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'centroid') THEN
        COMMENT ON COLUMN courts.centroid IS 'Calculated center point from polygon geometry';
    END IF;
END $$;
