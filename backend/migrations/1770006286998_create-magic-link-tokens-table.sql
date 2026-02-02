-- Up Migration
CREATE TABLE IF NOT EXISTS magic_link_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_magic_link_tokens_token_hash ON magic_link_tokens(token_hash);
CREATE INDEX idx_magic_link_tokens_expires_at ON magic_link_tokens(expires_at);

COMMENT ON TABLE magic_link_tokens IS 'One-time tokens for magic link sign-in';

-- Down Migration
DROP INDEX IF EXISTS idx_magic_link_tokens_expires_at;
DROP INDEX IF EXISTS idx_magic_link_tokens_token_hash;
DROP TABLE IF EXISTS magic_link_tokens;