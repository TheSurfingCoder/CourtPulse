-- Up migration: Add has_lights column to courts table
-- This column tracks whether a court has lighting for night play

DO $$ 
BEGIN
    -- Add has_lights column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'courts' AND column_name = 'has_lights') THEN
        ALTER TABLE courts ADD COLUMN has_lights BOOLEAN DEFAULT NULL;
        
        -- Add index for filtering by has_lights
        CREATE INDEX idx_courts_has_lights ON courts (has_lights) WHERE has_lights IS NOT NULL;
        
        -- Add comment to document the column
        COMMENT ON COLUMN courts.has_lights IS 'Indicates whether the court has lighting for night play. NULL = unknown, TRUE = has lights, FALSE = no lights';
    END IF;
END $$;
