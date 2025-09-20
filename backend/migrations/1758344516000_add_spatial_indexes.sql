-- Migration: Add spatial indexes for efficient viewport queries
-- This optimizes database performance for the new viewport-based API

-- Spatial index for efficient viewport queries on centroid
-- This is the most important index for bounding box queries
CREATE INDEX IF NOT EXISTS idx_courts_centroid_gist ON courts USING GIST (centroid);

-- Composite index for filtering by sport, surface_type, and is_public
-- Only includes records with valid centroids for better performance
CREATE INDEX IF NOT EXISTS idx_courts_sport_surface_public ON courts (sport, surface_type, is_public) 
WHERE centroid IS NOT NULL;

-- Index for cluster_id lookups (used in cluster details queries)
-- Helps with the existing clustered courts functionality
CREATE INDEX IF NOT EXISTS idx_courts_cluster_id ON courts (cluster_id) 
WHERE cluster_id IS NOT NULL;

-- Index for sport-based filtering (commonly used filter)
-- Optimizes queries that filter by sport type
CREATE INDEX IF NOT EXISTS idx_courts_sport ON courts (sport) 
WHERE centroid IS NOT NULL;

-- Index for is_public filtering (public vs private courts)
-- Optimizes queries that filter by public/private status
CREATE INDEX IF NOT EXISTS idx_courts_is_public ON courts (is_public) 
WHERE centroid IS NOT NULL;

-- Add comments for documentation
COMMENT ON INDEX idx_courts_centroid_gist IS 'Spatial index for efficient viewport/bounding box queries';
COMMENT ON INDEX idx_courts_sport_surface_public IS 'Composite index for filtering by sport, surface, and public status';
COMMENT ON INDEX idx_courts_cluster_id IS 'Index for cluster-based queries and details';
COMMENT ON INDEX idx_courts_sport IS 'Index for sport-based filtering';
COMMENT ON INDEX idx_courts_is_public IS 'Index for public/private court filtering';
