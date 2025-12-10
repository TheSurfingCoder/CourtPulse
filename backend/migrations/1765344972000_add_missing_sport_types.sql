-- Up migration: Add missing sport types to sport_type enum
-- These sports are queried from OpenStreetMap but were not in the enum

-- Add american_football to sport_type enum
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumlabel = 'american_football'
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'sport_type')
    ) THEN
        ALTER TYPE sport_type ADD VALUE 'american_football';
        RAISE NOTICE 'Added american_football to sport_type enum';
    ELSE
        RAISE NOTICE 'american_football already exists in sport_type enum';
    END IF;
END
$$;

-- Add baseball to sport_type enum
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumlabel = 'baseball'
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'sport_type')
    ) THEN
        ALTER TYPE sport_type ADD VALUE 'baseball';
        RAISE NOTICE 'Added baseball to sport_type enum';
    ELSE
        RAISE NOTICE 'baseball already exists in sport_type enum';
    END IF;
END
$$;

-- Add beachvolleyball to sport_type enum
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        WHERE enumlabel = 'beachvolleyball'
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'sport_type')
    ) THEN
        ALTER TYPE sport_type ADD VALUE 'beachvolleyball';
        RAISE NOTICE 'Added beachvolleyball to sport_type enum';
    ELSE
        RAISE NOTICE 'beachvolleyball already exists in sport_type enum';
    END IF;
END
$$;

-- Down migration (not reversible - PostgreSQL doesn't support removing enum values easily)
-- To rollback, you would need to recreate the type without these values
