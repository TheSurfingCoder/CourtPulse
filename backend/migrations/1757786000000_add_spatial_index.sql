-- Migration: Add spatial indexes for efficient viewport queries
-- This migration was already run in the database but the file was missing

-- Spatial index for efficient viewport queries on centroid
CREATE INDEX IF NOT EXISTS idx_courts_centroid ON courts USING GIST (centroid);

-- Spatial index for efficient viewport queries on centroid (alternative)
CREATE INDEX IF NOT EXISTS idx_courts_centroid_spatial ON courts USING GIST (centroid);
