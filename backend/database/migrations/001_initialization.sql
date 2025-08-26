-- Migration: 001_create_courts_table.sql
-- Enable PostGIS extension for spatial data
CREATE EXTENSION IF NOT EXISTS postgis;

-- Create courts table with spatial indexing
CREATE TABLE courts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL, -- 'basketball', 'tennis', 'soccer', etc.
    location GEOMETRY(POINT, 4326) NOT NULL, -- Lat/lng coordinates
    address TEXT,
    surface VARCHAR(50), -- 'asphalt', 'concrete', 'grass', etc.
    is_public BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create spatial index for fast geographic queries
CREATE INDEX idx_courts_location ON courts USING GIST (location);

-- Create index for court type filtering
CREATE INDEX idx_courts_type ON courts (type);

-- Create index for public/private filtering
CREATE INDEX idx_courts_is_public ON courts (is_public);