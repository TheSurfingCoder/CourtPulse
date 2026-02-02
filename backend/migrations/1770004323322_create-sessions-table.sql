-- Up Migration
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Session data
    token_hash VARCHAR(64) NOT NULL UNIQUE,

    -- Expiration
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Request metadata
    ip_address INET,
    user_agent TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_accessed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_token_hash ON sessions(token_hash);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);

COMMENT ON TABLE sessions IS 'User session tokens for authentication';
COMMENT ON COLUMN sessions.token_hash IS 'SHA256 hash of the Bearer token sent in Authorization header';

-- Down Migration
DROP INDEX IF EXISTS idx_sessions_expires_at;
DROP INDEX IF EXISTS idx_sessions_token_hash;
DROP INDEX IF EXISTS idx_sessions_user_id;
DROP TABLE IF EXISTS sessions;