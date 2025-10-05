-- Up migration: Fix courts table structure
-- This migration safely fixes the courts table structure without modifying existing data

-- First, let's check if the courts table exists and what columns it has
DO $$ 
BEGIN
    -- If courts table doesn't exist, create it
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'courts') THEN
        -- Enable PostGIS extension
        CREATE EXTENSION IF NOT EXISTS postgis;
        
        -- Create the courts table with the final structure
        CREATE TABLE courts (
            id SERIAL PRIMARY KEY,
            address VARCHAR(500),
            surface VARCHAR(50),
            is_public BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            source VARCHAR(50) NOT NULL DEFAULT 'osm',
            osm_id VARCHAR(255) UNIQUE,
            google_place_id VARCHAR(255),
            geom GEOMETRY(POLYGON, 4326),
            sport VARCHAR(50) NOT NULL,
            hoops INTEGER,
            fallback_name VARCHAR(255),
            enriched_name VARCHAR(255),
            surface_type VARCHAR(50),
            centroid GEOGRAPHY(POINT, 4326)
        );
    ELSE
        -- Table exists, add missing columns if they don't exist
        -- Add source column if it doesn't exist
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'source') THEN
            ALTER TABLE courts ADD COLUMN source VARCHAR(50) NOT NULL DEFAULT 'osm';
        END IF;
        
        -- Add other missing columns
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'osm_id') THEN
            ALTER TABLE courts ADD COLUMN osm_id VARCHAR(255) UNIQUE;
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'google_place_id') THEN
            ALTER TABLE courts ADD COLUMN google_place_id VARCHAR(255);
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'geom') THEN
            ALTER TABLE courts ADD COLUMN geom GEOMETRY(POLYGON, 4326);
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'sport') THEN
            ALTER TABLE courts ADD COLUMN sport VARCHAR(50) NOT NULL DEFAULT 'basketball';
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'hoops') THEN
            ALTER TABLE courts ADD COLUMN hoops INTEGER;
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'fallback_name') THEN
            ALTER TABLE courts ADD COLUMN fallback_name VARCHAR(255);
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'enriched_name') THEN
            ALTER TABLE courts ADD COLUMN enriched_name VARCHAR(255);
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'surface_type') THEN
            ALTER TABLE courts ADD COLUMN surface_type VARCHAR(50);
        END IF;
        
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'centroid') THEN
            ALTER TABLE courts ADD COLUMN centroid GEOGRAPHY(POINT, 4326);
        END IF;
    END IF;
END $$;

-- Create ENUM types if they don't exist
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

-- Convert columns to use ENUMs (only if they exist and are not already ENUMs)
DO $$ 
BEGIN
    -- Convert source column to ENUM if it exists and is not already an ENUM
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'source' AND data_type = 'character varying') THEN
        ALTER TABLE courts ALTER COLUMN source DROP DEFAULT;
        ALTER TABLE courts ALTER COLUMN source TYPE court_source_enum USING source::court_source_enum;
        ALTER TABLE courts ALTER COLUMN source SET DEFAULT 'osm'::court_source_enum;
    END IF;
    
    -- Convert sport column to ENUM if it exists and is not already an ENUM
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'sport' AND data_type = 'character varying') THEN
        ALTER TABLE courts ALTER COLUMN sport TYPE sport_type USING sport::sport_type;
    END IF;
    
    -- Convert surface_type column to ENUM if it exists and is not already an ENUM
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'surface_type' AND data_type = 'character varying') THEN
        ALTER TABLE courts ALTER COLUMN surface_type TYPE surface_type_enum USING surface_type::surface_type_enum;
    END IF;
END $$;

-- Create indexes if they don't exist
CREATE INDEX IF NOT EXISTS idx_courts_source ON courts (source);
CREATE INDEX IF NOT EXISTS idx_courts_osm_id ON courts (osm_id);
CREATE INDEX IF NOT EXISTS idx_courts_google_place_id ON courts (google_place_id);
CREATE INDEX IF NOT EXISTS idx_courts_sport ON courts (sport);
CREATE INDEX IF NOT EXISTS idx_courts_surface_type ON courts (surface_type);
CREATE INDEX IF NOT EXISTS idx_courts_geom ON courts USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_courts_centroid ON courts USING GIST (centroid);

-- Add constraints if they don't exist
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'chk_hoops_positive'
    ) THEN
        ALTER TABLE courts ADD CONSTRAINT chk_hoops_positive CHECK (hoops IS NULL OR hoops > 0);
    END IF;
END $$;