-- Up Migration
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Profile
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    avatar_url TEXT,

    -- Role
    role VARCHAR(50) NOT NULL DEFAULT 'contributor',

    -- OAuth providers
    oauth_provider VARCHAR(50),
    oauth_provider_id VARCHAR(255),

    -- Magic link (passwordless)
    magic_link_enabled BOOLEAN DEFAULT true,

    -- Account status
    is_active BOOLEAN DEFAULT true,
    email_verified BOOLEAN DEFAULT false,

    -- Stats
    edits_count INTEGER DEFAULT 0,
    last_login_at TIMESTAMP WITH TIME ZONE,

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deactivated_at TIMESTAMP WITH TIME ZONE,
    deactivated_by UUID REFERENCES users(id)
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_oauth ON users(oauth_provider, oauth_provider_id);
CREATE INDEX idx_users_active ON users(is_active);

COMMENT ON TABLE users IS 'User accounts for contributors and admins';
COMMENT ON COLUMN users.oauth_provider IS 'OAuth provider used for login (google, github, or null for magic link)';
COMMENT ON COLUMN users.role IS 'User role: contributor (can edit) or admin (full access)';

-- Down Migration
DROP INDEX IF EXISTS idx_users_active;
DROP INDEX IF EXISTS idx_users_oauth;
DROP INDEX IF EXISTS idx_users_role;
DROP INDEX IF EXISTS idx_users_email;
DROP TABLE IF EXISTS users;