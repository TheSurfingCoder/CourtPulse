-- Up Migration
-- Remove unused columns: import_timestamp, cluster_representative, cluster_size, photon_distance_km, photon_source

-- Drop unused function that references removed columns
DROP FUNCTION IF EXISTS get_clustered_courts_for_map();

-- Drop indexes first
DROP INDEX IF EXISTS idx_courts_photon_source;
DROP INDEX IF EXISTS idx_courts_cluster_representative;

-- Drop constraints
ALTER TABLE courts DROP CONSTRAINT IF EXISTS chk_photon_distance_positive;
ALTER TABLE courts DROP CONSTRAINT IF EXISTS chk_photon_source_valid;

-- Remove columns
ALTER TABLE courts DROP COLUMN IF EXISTS import_timestamp;
ALTER TABLE courts DROP COLUMN IF EXISTS cluster_representative;
ALTER TABLE courts DROP COLUMN IF EXISTS cluster_size;
ALTER TABLE courts DROP COLUMN IF EXISTS photon_distance_km;
ALTER TABLE courts DROP COLUMN IF EXISTS photon_source;

-- Down Migration
-- Re-add columns if needed to rollback

ALTER TABLE courts ADD COLUMN IF NOT EXISTS import_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW();
ALTER TABLE courts ADD COLUMN IF NOT EXISTS cluster_representative BOOLEAN DEFAULT FALSE;
ALTER TABLE courts ADD COLUMN IF NOT EXISTS cluster_size INTEGER DEFAULT 1;
ALTER TABLE courts ADD COLUMN IF NOT EXISTS photon_distance_km DECIMAL(10,6);
ALTER TABLE courts ADD COLUMN IF NOT EXISTS photon_source VARCHAR(50) DEFAULT 'search_api';

-- Re-create indexes
CREATE INDEX IF NOT EXISTS idx_courts_photon_source ON courts (photon_source);
CREATE INDEX IF NOT EXISTS idx_courts_cluster_representative ON courts (cluster_representative);

-- Re-create constraints
ALTER TABLE courts ADD CONSTRAINT chk_photon_distance_positive 
    CHECK (photon_distance_km IS NULL OR photon_distance_km >= 0);
ALTER TABLE courts ADD CONSTRAINT chk_photon_source_valid 
    CHECK (photon_source IN ('search_api', 'reverse_geocoding', 'fallback'));
