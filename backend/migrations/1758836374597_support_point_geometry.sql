-- Support both Point and Polygon geometry in geom column
-- Change from geometry(Polygon,4326) to geometry(Geometry,4326)

-- First, drop the existing constraint and index
DROP INDEX IF EXISTS idx_courts_geom;
ALTER TABLE courts DROP CONSTRAINT IF EXISTS chk_geom_polygon;

-- Change the column type to accept any geometry type
ALTER TABLE courts ALTER COLUMN geom TYPE geometry(Geometry,4326);

-- Recreate the spatial index
CREATE INDEX idx_courts_geom ON courts USING GIST (geom);
