-- Up migration: Create courts table with PostGIS support
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE courts (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  type VARCHAR(50) NOT NULL,
  location GEOMETRY(POINT, 4326) NOT NULL,
  address TEXT,
  surface VARCHAR(50),
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

-- Down migration: Drop courts table and PostGIS extension
DROP TABLE IF EXISTS courts;
DROP EXTENSION IF EXISTS postgis;