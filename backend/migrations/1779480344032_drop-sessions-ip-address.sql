-- Up Migration
--
-- Drops sessions.ip_address. Captured at session creation, stored indefinitely.
-- We aren't building a sessions-list UI (Sign Out always signs out everywhere now,
-- so per-session visibility has no user-facing value), the data has near-zero use
-- for CourtPulse's threat model, and IP is PII under GDPR. Simpler and safer to
-- not have it.
--
-- user_agent is kept — lower-risk, useful for debugging ("bug only on Safari iOS").

ALTER TABLE sessions DROP COLUMN IF EXISTS ip_address;


-- Down Migration
--
-- Restoring the column is straightforward; previously-captured values cannot
-- be recovered (they're gone with the column on Up).
ALTER TABLE sessions ADD COLUMN ip_address INET;
