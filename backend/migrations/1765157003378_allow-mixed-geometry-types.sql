-- Up Migration
-- Allow mixed geometry types in osm_facilities (Point, Polygon, MultiPolygon)
-- This enables storing OSM nodes (schools mapped as points) alongside ways/relations
ALTER TABLE osm_facilities 
    ALTER COLUMN geom TYPE geometry(GEOMETRY, 4326) 
    USING geom::geometry(GEOMETRY, 4326);

COMMENT ON COLUMN osm_facilities.geom IS 'Geometry column accepting Point (node), Polygon (way), or MultiPolygon (relation) types';

-- Down Migration
-- Revert to POLYGON only (will fail if Points exist in the table)
ALTER TABLE osm_facilities 
    ALTER COLUMN geom TYPE geometry(POLYGON, 4326) 
    USING geom::geometry(POLYGON, 4326);