import pool from '../../config/database';

/**
 * Set PostgreSQL session variables for audit context.
 * When the audit trigger is attached to courts/facilities, it reads these values
 * to record who made the change (user, import_batch, or system).
 */
export async function setAuditContext(params: {
  changed_by_type: string; // 'user', 'import_batch', 'system'
  changed_by_id: string;
  changed_by_email?: string;
  changed_by_role?: string;
  change_source?: string;
  import_batch_id?: string;
}): Promise<void> {
  await pool.query(
    `
    SELECT 
      set_config('app.changed_by_type', $1, true),
      set_config('app.changed_by_id', $2, true),
      set_config('app.changed_by_email', $3, true),
      set_config('app.changed_by_role', $4, true),
      set_config('app.change_source', $5, true),
      set_config('app.import_batch_id', $6, true)
  `,
    [
      params.changed_by_type,
      params.changed_by_id,
      params.changed_by_email || '',
      params.changed_by_role || '',
      params.change_source || 'api',
      params.import_batch_id || ''
    ]
  );
}
