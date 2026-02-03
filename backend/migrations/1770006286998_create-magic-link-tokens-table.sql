-- Up Migration
-- One-time tokens for magic link sign-in: we store only the hash in the database; the raw (secret) token is created by generateMagicLinkToken() in backend/src/services/email.ts and is sent to the user via an email URL.
-- When a user clicks the link, the raw token is sent back to the server in a query parameter; the server hashes this token and looks up the hash in the database for validation.
-- This design ensures that even if the database is compromised, the raw token (which grants authentication) cannot be reconstructed from the hashed value.
-- The token hash allows secure, one-time-use sign-in authentication without exposing sensitive data.
CREATE TABLE IF NOT EXISTS magic_link_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,                    -- Email the link was requested for
    token_hash VARCHAR(64) NOT NULL UNIQUE,         -- SHA256 of token in URL (?token=...)
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,   -- Short expiry (e.g. 15 min); verify rejects if past
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Lookup by hash when user clicks verify link; cleanup expired rows
CREATE INDEX idx_magic_link_tokens_token_hash ON magic_link_tokens(token_hash);
CREATE INDEX idx_magic_link_tokens_expires_at ON magic_link_tokens(expires_at);

COMMENT ON TABLE magic_link_tokens IS 'One-time tokens for magic link sign-in';

-- Down Migration
DROP INDEX IF EXISTS idx_magic_link_tokens_expires_at;
DROP INDEX IF EXISTS idx_magic_link_tokens_token_hash;
DROP TABLE IF EXISTS magic_link_tokens;