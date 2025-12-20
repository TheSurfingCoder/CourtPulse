-- Up migration: Remove unused columns and materialized views from courts table
-- Removes columns and views that are no longer used in the application

-- Remove google_place_id (not used, no Google Places integration)
ALTER TABLE courts DROP COLUMN IF EXISTS google_place_id;

-- Drop unused materialized views (never used in application)
DROP MATERIALIZED VIEW IF EXISTS court_aggregates_city;
DROP MATERIALIZED VIEW IF EXISTS court_aggregates_state;
DROP MATERIALIZED VIEW IF EXISTS court_aggregates_country;

-- Drop the refresh function since we're removing the views
DROP FUNCTION IF EXISTS refresh_court_aggregates();

-- Remove photon_name (replaced by facility_name)
ALTER TABLE courts DROP COLUMN IF EXISTS photon_name;
