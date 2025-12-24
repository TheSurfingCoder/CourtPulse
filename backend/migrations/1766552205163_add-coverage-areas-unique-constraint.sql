-- Up Migration
-- Add unique constraint on (region, name) to support upsert operations
ALTER TABLE coverage_areas ADD CONSTRAINT coverage_areas_region_name_key UNIQUE (region, name);

-- Down Migration
ALTER TABLE coverage_areas DROP CONSTRAINT IF EXISTS coverage_areas_region_name_key;
