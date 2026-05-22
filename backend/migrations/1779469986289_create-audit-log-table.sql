-- Up Migration
--
-- Creates the audit_log table and a generic trigger function that records every
-- INSERT / UPDATE / DELETE on tables it's attached to. The trigger reads the
-- session-level variables written by setAuditContext() (backend/src/utils/auditContext.ts)
-- so we know *who* made each change, not just what changed.
--
-- Note: setAuditContext writes these vars per-transaction (third arg = true).
-- current_setting(key, TRUE) here returns '' (we NULLIF it) when a process didn't
-- set context (e.g. a manual SQL fix), so the trigger never blocks the write.

CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,

    -- What was changed
    table_name VARCHAR(64) NOT NULL,
    row_id TEXT NOT NULL,                              -- TEXT to accept both int and uuid PKs
    operation VARCHAR(10) NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),

    -- Who changed it (populated from session vars set by setAuditContext)
    changed_by_type VARCHAR(32),                       -- 'user' | 'import_batch' | 'system'
    changed_by_id TEXT,                                -- user UUID, batch UUID, or null for system
    changed_by_email VARCHAR(255),
    changed_by_role VARCHAR(50),
    change_source VARCHAR(50),                         -- 'web_ui' | 'api' | 'import' | etc.
    import_batch_id TEXT,

    -- What the change looked like. Full row snapshots in JSONB so we can reconstruct
    -- history without joining against application code.
    old_data JSONB,                                    -- NULL on INSERT
    new_data JSONB,                                    -- NULL on DELETE

    changed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes match the queries we'll actually run:
-- "history of this court"
CREATE INDEX idx_audit_log_table_row ON audit_log (table_name, row_id);
-- "everything this user changed"
CREATE INDEX idx_audit_log_changed_by ON audit_log (changed_by_id) WHERE changed_by_id IS NOT NULL;
-- "recent activity feed"
CREATE INDEX idx_audit_log_changed_at ON audit_log (changed_at DESC);

COMMENT ON TABLE audit_log IS 'Generic audit log for tracked tables. Populated by log_table_change() trigger.';
COMMENT ON COLUMN audit_log.row_id IS 'PK of the modified row, cast to text to support both integer and uuid PKs';
COMMENT ON COLUMN audit_log.old_data IS 'Full row before change (NULL on INSERT)';
COMMENT ON COLUMN audit_log.new_data IS 'Full row after change (NULL on DELETE)';


-- Trigger function: reads the session vars written by setAuditContext() and
-- inserts one audit_log row per affected row. Generic — works for any table
-- with an "id" column; relies on TG_TABLE_NAME and TG_OP to fill in the context.
CREATE OR REPLACE FUNCTION log_table_change() RETURNS TRIGGER AS $$
DECLARE
    row_id_text TEXT;
BEGIN
    -- DELETE has no NEW row; INSERT/UPDATE always have NEW. Pick whichever is non-null.
    IF TG_OP = 'DELETE' THEN
        row_id_text := OLD.id::TEXT;
    ELSE
        row_id_text := NEW.id::TEXT;
    END IF;

    INSERT INTO audit_log (
        table_name, row_id, operation,
        changed_by_type, changed_by_id, changed_by_email,
        changed_by_role, change_source, import_batch_id,
        old_data, new_data
    )
    VALUES (
        TG_TABLE_NAME,
        row_id_text,
        TG_OP,
        -- current_setting(key, TRUE): TRUE = missing_ok. Returns '' (which we coerce to NULL
        -- via NULLIF) when no audit context was set for this transaction. This prevents the
        -- trigger from blocking writes from background jobs / manual SQL.
        NULLIF(current_setting('app.changed_by_type',  TRUE), ''),
        NULLIF(current_setting('app.changed_by_id',    TRUE), ''),
        NULLIF(current_setting('app.changed_by_email', TRUE), ''),
        NULLIF(current_setting('app.changed_by_role',  TRUE), ''),
        NULLIF(current_setting('app.change_source',    TRUE), ''),
        NULLIF(current_setting('app.import_batch_id',  TRUE), ''),
        CASE WHEN TG_OP IN ('UPDATE', 'DELETE') THEN to_jsonb(OLD) ELSE NULL END,
        CASE WHEN TG_OP IN ('UPDATE', 'INSERT') THEN to_jsonb(NEW) ELSE NULL END
    );

    -- AFTER triggers ignore the return value, but plpgsql requires us to return a row.
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION log_table_change() IS 'Generic audit trigger. Attach to any table with an id column via CREATE TRIGGER ... EXECUTE FUNCTION log_table_change().';

-- Attach to the courts table (the only audited table for now).
-- AFTER: trigger fires only if the row change actually succeeds.
-- FOR EACH ROW: one audit_log row per affected row (multi-row UPDATEs produce N audit rows).
CREATE TRIGGER courts_audit
    AFTER INSERT OR UPDATE OR DELETE ON courts
    FOR EACH ROW EXECUTE FUNCTION log_table_change();


-- Down Migration
DROP TRIGGER IF EXISTS courts_audit ON courts;
DROP FUNCTION IF EXISTS log_table_change();
DROP INDEX IF EXISTS idx_audit_log_changed_at;
DROP INDEX IF EXISTS idx_audit_log_changed_by;
DROP INDEX IF EXISTS idx_audit_log_table_row;
DROP TABLE IF EXISTS audit_log;
