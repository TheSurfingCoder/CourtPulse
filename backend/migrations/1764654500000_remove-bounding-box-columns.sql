-- Up migration: Remove bounding_box columns from courts table
-- These columns are not part of the clustering logic (which uses facility_name + sport → cluster_id)
-- Frontend calculates bounding boxes dynamically for viewport queries

-- Remove bounding_box columns
ALTER TABLE courts DROP COLUMN IF EXISTS bounding_box_id;
ALTER TABLE courts DROP COLUMN IF EXISTS bounding_box_coords;




