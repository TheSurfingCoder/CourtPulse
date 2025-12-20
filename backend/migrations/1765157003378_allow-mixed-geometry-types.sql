-- Up Migration
-- Allow mixed geometry types in osm_facilities (Point, Polygon, MultiPolygon)
-- This enables storing OSM nodes (schools mapped as points) alongside ways/relations
-- Note: osm_facilities is a staging table that may not exist in production
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'osm_facilities') THEN
        ALTER TABLE osm_facilities 
            ALTER COLUMN geom TYPE geometry(GEOMETRY, 4326) 
            USING geom::geometry(GEOMETRY, 4326);
        COMMENT ON COLUMN osm_facilities.geom IS 'Geometry column accepting Point (node), Polygon (way), or MultiPolygon (relation) types';
    END IF;
END $$;