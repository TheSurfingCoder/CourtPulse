-- Migration: Add materialized views for global aggregates (zoom 0-6)
-- These provide fast aggregated data for low zoom levels

-- Zoom Level 0-2: Country-Level Aggregates
CREATE MATERIALIZED VIEW IF NOT EXISTS court_aggregates_country AS
SELECT 
  'country' as zoom_type,
  'Global' as region_name,
  sport,
  surface_type,
  is_public,
  COUNT(*) as court_count,
  ST_Envelope(ST_Collect(centroid::geometry)) as bounds
FROM courts 
WHERE centroid IS NOT NULL
GROUP BY sport, surface_type, is_public
ORDER BY court_count DESC;

-- Zoom Level 3-4: State/Province-Level Aggregates
CREATE MATERIALIZED VIEW IF NOT EXISTS court_aggregates_state AS
SELECT 
  'state' as zoom_type,
  COALESCE(
    CASE 
      WHEN ST_X(centroid::geometry) BETWEEN -125 AND -66 AND ST_Y(centroid::geometry) BETWEEN 32 AND 49 THEN 'USA'
      WHEN ST_X(centroid::geometry) BETWEEN -141 AND -52 AND ST_Y(centroid::geometry) BETWEEN 42 AND 84 THEN 'Canada'
      WHEN ST_X(centroid::geometry) BETWEEN -118 AND -86 AND ST_Y(centroid::geometry) BETWEEN 14 AND 33 THEN 'Mexico'
      ELSE 'Other'
    END, 'Unknown'
  ) as region_name,
  sport,
  surface_type,
  is_public,
  COUNT(*) as court_count,
  ST_Envelope(ST_Collect(centroid::geometry)) as bounds
FROM courts 
WHERE centroid IS NOT NULL
GROUP BY region_name, sport, surface_type, is_public
ORDER BY court_count DESC;

-- Zoom Level 5-6: City-Level Aggregates
CREATE MATERIALIZED VIEW IF NOT EXISTS court_aggregates_city AS
SELECT 
  'city' as zoom_type,
  COALESCE(photon_name, 'Unknown City') as region_name,
  sport,
  surface_type,
  is_public,
  COUNT(*) as court_count,
  ST_Envelope(ST_Collect(centroid::geometry)) as bounds,
  ST_Centroid(ST_Collect(centroid::geometry)) as center_point
FROM courts 
WHERE centroid IS NOT NULL 
  AND photon_name IS NOT NULL
GROUP BY photon_name, sport, surface_type, is_public
HAVING COUNT(*) >= 5  -- Only include cities with 5+ courts
ORDER BY court_count DESC;

-- Create indexes on materialized views for efficient querying
CREATE INDEX IF NOT EXISTS idx_aggregates_country_region ON court_aggregates_country (region_name, sport, surface_type, is_public);
CREATE INDEX IF NOT EXISTS idx_aggregates_state_region ON court_aggregates_state (region_name, sport, surface_type, is_public);
CREATE INDEX IF NOT EXISTS idx_aggregates_city_region ON court_aggregates_city (region_name, sport, surface_type, is_public);

-- Create spatial indexes on bounds for viewport queries
CREATE INDEX IF NOT EXISTS idx_aggregates_country_bounds ON court_aggregates_country USING GIST (bounds);
CREATE INDEX IF NOT EXISTS idx_aggregates_state_bounds ON court_aggregates_state USING GIST (bounds);
CREATE INDEX IF NOT EXISTS idx_aggregates_city_bounds ON court_aggregates_city USING GIST (bounds);

-- Add comments for documentation
COMMENT ON MATERIALIZED VIEW court_aggregates_country IS 'Country-level court aggregates for zoom levels 0-2';
COMMENT ON MATERIALIZED VIEW court_aggregates_state IS 'State/province-level court aggregates for zoom levels 3-4';
COMMENT ON MATERIALIZED VIEW court_aggregates_city IS 'City-level court aggregates for zoom levels 5-6 (5+ courts only)';

-- Create function to refresh all materialized views
CREATE OR REPLACE FUNCTION refresh_court_aggregates()
RETURNS void AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY court_aggregates_country;
  REFRESH MATERIALIZED VIEW CONCURRENTLY court_aggregates_state;
  REFRESH MATERIALIZED VIEW CONCURRENTLY court_aggregates_city;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION refresh_court_aggregates() IS 'Refreshes all court aggregate materialized views concurrently';
