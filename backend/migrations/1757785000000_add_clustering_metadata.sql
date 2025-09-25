-- Migration: Add clustering metadata for frontend display
-- This enables geographic clustering on the frontend while keeping separate records

-- Add cluster identification columns
ALTER TABLE courts ADD COLUMN IF NOT EXISTS cluster_id UUID;
ALTER TABLE courts ADD COLUMN IF NOT EXISTS cluster_representative BOOLEAN DEFAULT FALSE;
ALTER TABLE courts ADD COLUMN IF NOT EXISTS cluster_size INTEGER DEFAULT 1;

-- Create index for efficient cluster queries
CREATE INDEX IF NOT EXISTS idx_courts_cluster_id ON courts (cluster_id);
CREATE INDEX IF NOT EXISTS idx_courts_cluster_representative ON courts (cluster_representative);

-- Add comments
COMMENT ON COLUMN courts.cluster_id IS 'UUID identifying courts that should be clustered together on frontend';
COMMENT ON COLUMN courts.cluster_representative IS 'True if this court represents the cluster for frontend display';
COMMENT ON COLUMN courts.cluster_size IS 'Total number of courts in this cluster';

-- Create function to generate cluster aggregated data for frontend
CREATE OR REPLACE FUNCTION get_clustered_courts_for_map()
RETURNS TABLE (
    cluster_id UUID,
    representative_osm_id VARCHAR(255),
    photon_name VARCHAR(255),
    total_courts INTEGER,
    total_hoops INTEGER,
    sports TEXT[],
    centroid_lat DECIMAL,
    centroid_lon DECIMAL,
    cluster_bounds JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.cluster_id,
        c.osm_id as representative_osm_id,
        c.photon_name,
        c.cluster_size as total_courts,
        SUM(COALESCE(cluster_courts.hoops, 0))::INTEGER as total_hoops,
        ARRAY_AGG(DISTINCT cluster_courts.sport::TEXT) as sports,
        ST_Y(c.centroid::geometry)::DECIMAL as centroid_lat,
        ST_X(c.centroid::geometry)::DECIMAL as centroid_lon,
        jsonb_build_object(
            'bounds', ST_AsGeoJSON(ST_Envelope(ST_Collect(cluster_courts.geom)))::jsonb,
            'center', ST_AsGeoJSON(ST_Centroid(ST_Collect(cluster_courts.geom)))::jsonb
        ) as cluster_bounds
    FROM courts c
    JOIN courts cluster_courts ON cluster_courts.cluster_id = c.cluster_id
    WHERE c.cluster_representative = true
    GROUP BY c.cluster_id, c.osm_id, c.photon_name, c.cluster_size, c.centroid;
END;
$$ LANGUAGE plpgsql;


