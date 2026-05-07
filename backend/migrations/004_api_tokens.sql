-- API tokens for programmatic / agent-friendly auth.
--
-- Token is generated server-side as `cnt_<32 random base64url chars>`,
-- shown to the user exactly once at creation, then stored as SHA-256 hex.
-- The `prefix` column stores the first 12 chars (`cnt_` + 8 of the random
-- portion) for identification in listings — non-secret.
--
-- Auth flow on the wire: `Authorization: Bearer cnt_<...>`. The dependency
-- hashes the bearer token, looks up by token_hash, validates not-revoked
-- and not-expired, returns the owning User.

CREATE TABLE api_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    token_hash VARCHAR(64) NOT NULL UNIQUE,    -- SHA-256 hex of raw token
    prefix VARCHAR(16) NOT NULL,                -- e.g. "cnt_abc12345" — for display only
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,                     -- NULL = no expiry
    revoked_at TIMESTAMPTZ,                     -- NULL = active
    last_used_at TIMESTAMPTZ
);

CREATE INDEX idx_api_tokens_hash ON api_tokens (token_hash) WHERE revoked_at IS NULL;
CREATE INDEX idx_api_tokens_user ON api_tokens (user_id, revoked_at);
