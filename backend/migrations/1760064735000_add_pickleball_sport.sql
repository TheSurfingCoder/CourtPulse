-- Up migration: Add pickleball to sport_type enum
-- This migration adds pickleball as a valid sport type

-- Add pickleball to sport_type enum
DO $$ 
BEGIN
    -- Check if 'pickleball' value already exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'pickleball' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'sport_type')
    ) THEN
        ALTER TYPE sport_type ADD VALUE 'pickleball';
        RAISE NOTICE 'Added pickleball to sport_type enum';
    ELSE
        RAISE NOTICE 'pickleball already exists in sport_type enum';
    END IF;
END $$;

-- Down migration would require recreating the enum type, which is complex
-- For now, we'll leave pickleball in the enum even on rollback
-- This is safe as it won't break existing functionality

