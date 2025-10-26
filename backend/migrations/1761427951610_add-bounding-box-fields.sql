-- Up Migration
ALTER TABLE courts ADD COLUMN bounding_box_id UUID;
ALTER TABLE courts ADD COLUMN bounding_box_coords JSONB;

-- Add index for clustering performance
CREATE INDEX idx_courts_bounding_box_id ON courts(bounding_box_id);

-- Down Migration
DROP INDEX IF EXISTS idx_courts_bounding_box_id;
ALTER TABLE courts DROP COLUMN IF EXISTS bounding_box_coords;
ALTER TABLE courts DROP COLUMN IF EXISTS bounding_box_id;