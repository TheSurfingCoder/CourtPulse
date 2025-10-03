-- Add region column to courts table
ALTER TABLE courts ADD COLUMN region VARCHAR(50) DEFAULT 'sf_bay';

-- Add index for region queries
CREATE INDEX idx_courts_region ON courts(region);

-- Create backup tracking table
CREATE TABLE courts_backups (
    id SERIAL PRIMARY KEY,
    backup_name VARCHAR(255) NOT NULL,
    region VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Add indexes for backup queries
CREATE INDEX idx_courts_backups_region ON courts_backups(region);
CREATE INDEX idx_courts_backups_created_at ON courts_backups(created_at);
