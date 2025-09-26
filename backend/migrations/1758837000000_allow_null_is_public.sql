-- Allow NULL values for is_public column when access information is unknown
-- This provides more accurate data when we can't determine public/private status

-- Remove the NOT NULL constraint and default
ALTER TABLE courts 
ALTER COLUMN is_public DROP NOT NULL,
ALTER COLUMN is_public DROP DEFAULT;

-- Update comment to reflect the change
COMMENT ON COLUMN courts.is_public IS 'Whether the court is publicly accessible (true), private (false), or unknown (NULL)';
