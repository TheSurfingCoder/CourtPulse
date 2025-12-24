-- Up Migration
CREATE TABLE IF NOT EXISTS coverage_areas (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    region VARCHAR(50) NOT NULL,
    boundary GEOMETRY(POLYGON, 4326) NOT NULL,
    court_count INTEGER DEFAULT 0,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add spatial index for efficient querying
CREATE INDEX idx_coverage_areas_boundary ON coverage_areas USING GIST(boundary);

-- Add index on region for filtering
CREATE INDEX idx_coverage_areas_region ON coverage_areas(region);

-- Down Migration
DROP INDEX IF EXISTS idx_coverage_areas_region;
DROP INDEX IF EXISTS idx_coverage_areas_boundary;
DROP TABLE IF EXISTS coverage_areas;
