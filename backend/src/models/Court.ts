import pool from '../../config/database';
import { logBusinessEvent, logError } from '../../logger';
import * as Sentry from '@sentry/node';

export interface Court {
    id: number;
    name: string; // Maps to individual_court_name or fallback
    cluster_group_name: string | null; // Maps to facility_name (cluster group name)
    type: string; // Maps to sport
    lat: number; // From centroid
    lng: number; // From centroid
    surface: string; // Maps to surface_type
    is_public: boolean;
    school: boolean; // True when court name was derived from a school
    cluster_id: string | null; // UUID for clustering
    region: string | null; // Region identifier
    created_at: Date;
    updated_at: Date;
}


export interface CourtInput {
    name: string;
    type: string;
    lat: number;
    lng: number;
    surface: string;
    is_public: boolean;
    cluster_group_name?: string | null;
    school?: boolean;
}

export interface ClusterFieldsInput {
    cluster_group_name?: string | null;
}

export class CourtModel {



    static async findById(id: number): Promise<Court | null> {
        const result = await pool.query(`
            SELECT 
                id, 
                COALESCE(individual_court_name, fallback_name, 'Unknown Court') as name,
                COALESCE(facility_name, 'Unknown') as cluster_group_name,
                sport as type, 
                ST_X(centroid::geometry) as lat, 
                ST_Y(centroid::geometry) as lng,
                COALESCE(surface_type::text, 'Unknown') as surface, 
                is_public,
                school,
                cluster_id,
                region,
                created_at, 
                updated_at
            FROM courts 
            WHERE id = $1 AND centroid IS NOT NULL
        `, [id]);
        return result.rows[0] || null;
    }

    static async findByType(type: string): Promise<Court[]> {
        const result = await pool.query(`
            SELECT 
                id, 
                COALESCE(individual_court_name, fallback_name, 'Unknown Court') as name,
                COALESCE(facility_name, 'Unknown') as cluster_group_name,
                sport as type, 
                ST_X(centroid::geometry) as lat, 
                ST_Y(centroid::geometry) as lng,
                COALESCE(surface_type::text, 'Unknown') as surface, 
                is_public,
                school,
                cluster_id,
                region,
                created_at, 
                updated_at
            FROM courts 
            WHERE sport = $1 AND centroid IS NOT NULL
            ORDER BY COALESCE(individual_court_name, fallback_name, 'Unknown Court')
        `, [type]);
        return result.rows;
    }

    static async create(courtData: CourtInput): Promise<Court> {
        const { name, type, lat, lng, surface, is_public } = courtData;
        const result = await pool.query(`
            INSERT INTO courts (enriched_name, sport, centroid, surface_type, is_public, region)
            VALUES ($1, $2, ST_SetSRID(ST_MakePoint($3, $4), 4326), $5, $6, 'sf_bay')
            RETURNING 
                id, 
                COALESCE(individual_court_name, fallback_name, 'Unknown Court') as name,
                COALESCE(facility_name, 'Unknown') as cluster_group_name,
                sport as type, 
                ST_X(centroid::geometry) as lat, 
                ST_Y(centroid::geometry) as lng,
                COALESCE(surface_type::text, 'Unknown') as surface, 
                is_public,
                school,
                cluster_id,
                region,
                created_at, 
                updated_at
        `, [name, type, lng, lat, surface, is_public]);
        return result.rows[0];
    }

    static async update(id: number, courtData: Partial<CourtInput>, clusterFields?: ClusterFieldsInput): Promise<Court | null> {
        const fields: string[] = [];
        const values: any[] = [];
        let paramCount = 1;
        const sanitizedClusterFields = clusterFields || {};
        const hasClusterFieldUpdates = Object.keys(sanitizedClusterFields).some(
            (key) => (sanitizedClusterFields as any)[key] !== undefined
        );

        // Track facility_name parameter index directly when building fields array
        // This avoids fragile regex parsing later
        let facilityNameParamIndex: number | null = null;

        // Only process cluster_group_name from courtData if it's NOT in clusterFields
        // Cluster-level updates take precedence over per-court updates
        if (courtData.cluster_group_name !== undefined && sanitizedClusterFields.cluster_group_name === undefined) {
            const trimmedClusterName = courtData.cluster_group_name && courtData.cluster_group_name.trim() !== '' ? courtData.cluster_group_name.trim() : null;
            facilityNameParamIndex = paramCount;
            fields.push(`facility_name = $${paramCount++}`);
            values.push(trimmedClusterName);
        }

        if (courtData.name !== undefined && courtData.name !== null && courtData.name.trim() !== '') {
            fields.push(`fallback_name = $${paramCount++}`);
            values.push(courtData.name);
        }

        if (courtData.type) {
            fields.push(`sport = $${paramCount++}`);
            values.push(courtData.type);
        }
        if (courtData.lat !== undefined && courtData.lng !== undefined) {
            fields.push(`centroid = ST_SetSRID(ST_MakePoint($${paramCount++}, $${paramCount++}), 4326)`);
            values.push(courtData.lng, courtData.lat);
        }
        if (courtData.surface) {
            fields.push(`surface_type = $${paramCount++}`);
            values.push(courtData.surface);
        }
        if (courtData.is_public !== undefined) {
            fields.push(`is_public = $${paramCount++}`);
            values.push(courtData.is_public);
        }
        if (courtData.school !== undefined) {
            fields.push(`school = $${paramCount++}`);
            values.push(courtData.school);
        }

        if (fields.length === 0 && !hasClusterFieldUpdates) return null;

        // Retry configuration for deadlock handling
        const MAX_RETRIES = 3;
        const LOCK_TIMEOUT_MS = 5000; // 5 seconds
        const INITIAL_RETRY_DELAY_MS = 100; // Start with 100ms

        // Helper function to execute the transaction
        const executeTransaction = async (): Promise<Court | null> => {
            const client = await pool.connect();

            try {
                await client.query('BEGIN');
                
                // Set lock timeout to prevent indefinite waits
                await client.query(`SET LOCAL lock_timeout = '${LOCK_TIMEOUT_MS}ms'`);

                const existingCourtResult = await client.query(`
                    SELECT id, cluster_id, facility_name
                    FROM courts
                    WHERE id = $1
                    FOR UPDATE
                `, [id]);

                if (existingCourtResult.rows.length === 0) {
                    await client.query('ROLLBACK');
                    return null;
                }

                const existingCourt = existingCourtResult.rows[0];

                // Track if we're updating facility_name in the per-court update and capture the new value
                // Use the directly tracked parameter index instead of fragile regex parsing
                let updatedFacilityName: string | null = null;
                if (facilityNameParamIndex !== null) {
                    // values array is 0-indexed, but params are 1-indexed, so subtract 1
                    updatedFacilityName = values[facilityNameParamIndex - 1] as string | null;
                }

                if (fields.length > 0) {
                    fields.push(`updated_at = NOW()`);
                    values.push(id);

                    await client.query(`
                        UPDATE courts 
                        SET ${fields.join(', ')}
                        WHERE id = $${paramCount}
                    `, values);
                }

                const clusterAssignments = [];
                const clusterValues = [];
                let clusterParamIndex = 1;

                if (sanitizedClusterFields.cluster_group_name !== undefined) {
                    const newClusterName = sanitizedClusterFields.cluster_group_name && sanitizedClusterFields.cluster_group_name.trim() !== ''
                        ? sanitizedClusterFields.cluster_group_name.trim()
                        : null;
                    clusterAssignments.push(`facility_name = $${clusterParamIndex++}`);
                    clusterValues.push(newClusterName);
                }


                if (clusterAssignments.length > 0) {
                    clusterAssignments.push(`updated_at = NOW()`);

                    let identifierClause = '';
                    if (existingCourt.cluster_id) {
                        // Use cluster_id if available (most reliable, unaffected by facility_name updates)
                        identifierClause = `cluster_id = $${clusterParamIndex}`;
                        clusterValues.push(existingCourt.cluster_id);
                        clusterParamIndex++;
                    } else {
                        // Without cluster_id, we cannot safely identify other courts in the cluster.
                        // Matching by facility_name alone is unsafe because multiple unrelated courts
                        // in different locations can share the same name. Fall back to updating
                        // only this specific court to avoid unintended matches.
                        logBusinessEvent('cluster_update_fallback_to_single_court', {
                            courtId: existingCourt.id,
                            reason: 'no_cluster_id',
                            oldFacilityName: existingCourt.facility_name || null,
                            newFacilityName: updatedFacilityName,
                            clusterFields: Object.keys(sanitizedClusterFields),
                            message: 'Cannot safely update cluster without cluster_id. Updating single court only to prevent unintended matches.'
                        });
                        identifierClause = `id = $${clusterParamIndex}`;
                        clusterValues.push(existingCourt.id);
                        clusterParamIndex++;
                    }

                    if (identifierClause) {
                        await client.query(`
                            UPDATE courts 
                            SET ${clusterAssignments.join(', ')}
                            WHERE ${identifierClause}
                        `, clusterValues);
                    }
                }

                // Explicitly update the individual court's updated_at if only cluster fields were updated
                // This ensures the court's timestamp reflects any changes, even if it wasn't part of the cluster update
                // We check fields.length === 0 to ensure no per-court update occurred, and clusterAssignments.length > 0
                // to ensure a cluster update did occur
                if (fields.length === 0 && clusterAssignments.length > 0) {
                    await client.query(`
                        UPDATE courts 
                        SET updated_at = NOW()
                        WHERE id = $1
                    `, [id]);
                }

                await client.query('COMMIT');
                return await this.findById(id);
            } catch (error: any) {
                await client.query('ROLLBACK');
                throw error;
            } finally {
                client.release();
            }
        };

        // Retry logic with exponential backoff for deadlocks
        let lastError: Error | null = null;
        for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
            try {
                return await executeTransaction();
            } catch (error: any) {
                lastError = error;
                
                // Check if it's a deadlock (PostgreSQL error code 40P01) or lock timeout
                const isDeadlock = error.code === '40P01';
                const isLockTimeout = error.message?.includes('lock timeout') || 
                                     error.message?.includes('timeout') ||
                                     error.code === '55P03';
                
                if ((isDeadlock || isLockTimeout) && attempt < MAX_RETRIES - 1) {
                    const delay = INITIAL_RETRY_DELAY_MS * Math.pow(2, attempt);
                    logBusinessEvent('court_update_retry', {
                        courtId: id,
                        attempt: attempt + 1,
                        maxRetries: MAX_RETRIES,
                        errorCode: error.code,
                        errorMessage: error.message,
                        retryDelayMs: delay,
                        reason: isDeadlock ? 'deadlock' : 'lock_timeout'
                    });
                    
                    // Wait before retrying with exponential backoff
                    await new Promise(resolve => setTimeout(resolve, delay));
                    continue;
                }
                
                // If not a retryable error or max retries reached, log and capture in Sentry
                logError(error, {
                    event: 'court_update_failed',
                    courtId: id,
                    attempt: attempt + 1,
                    maxRetries: MAX_RETRIES,
                    errorCode: error.code,
                    isDeadlock,
                    isLockTimeout
                });

                // Capture in Sentry with rich context for lock timeout/deadlock errors
                if (isDeadlock || isLockTimeout) {
                    Sentry.withScope((scope) => {
                        // Set tags for filtering in Sentry
                        scope.setTag('error_type', isDeadlock ? 'database_deadlock' : 'database_lock_timeout');
                        scope.setTag('operation', 'court_update');
                        scope.setTag('court_id', id.toString());
                        scope.setTag('retry_exhausted', 'true');
                        
                        // Set context for structured data
                        scope.setContext('database_error', {
                            error_code: error.code,
                            error_message: error.message,
                            is_deadlock: isDeadlock,
                            is_lock_timeout: isLockTimeout,
                            lock_timeout_ms: LOCK_TIMEOUT_MS,
                            retry_attempts: attempt + 1,
                            max_retries: MAX_RETRIES,
                            court_id: id
                        });
                        
                        // Set additional context about the operation
                        scope.setContext('operation_details', {
                            has_per_court_updates: fields.length > 0,
                            has_cluster_updates: hasClusterFieldUpdates,
                            operation: 'update_court'
                        });
                        
                        // Set level to warning for lock timeouts (expected under load)
                        // but error for deadlocks (indicates potential issue)
                        scope.setLevel(isDeadlock ? 'error' : 'warning');
                        
                        // Capture the exception
                        Sentry.captureException(error);
                    });
                } else {
                    // For other errors, still capture but with less specific context
                    Sentry.withScope((scope) => {
                        scope.setTag('operation', 'court_update');
                        scope.setTag('court_id', id.toString());
                        scope.setContext('database_error', {
                            error_code: error.code,
                            error_message: error.message,
                            court_id: id
                        });
                        Sentry.captureException(error);
                    });
                }
                
                throw error;
            }
        }

        // This should never be reached, but TypeScript requires it
        if (lastError) {
            throw lastError;
        }
        return null;
    }

    static async delete(id: number): Promise<boolean> {
        const result = await pool.query('DELETE FROM courts WHERE id = $1', [id]);
        return (result.rowCount ?? 0) > 0;
    }

    static async searchCourts(filters: {
        bbox?: [number, number, number, number];
        sport?: string;
        surface_type?: string;
        is_public?: boolean;
        zoom?: number;
    }): Promise<Court[]> {
        // Build dynamic query with filters
        let query = `
            SELECT
                id, 
                COALESCE(individual_court_name, fallback_name, 'Unknown Court') as name,
                COALESCE(facility_name, 'Unknown') as cluster_group_name,
                sport as type,
                ST_Y(centroid::geometry) as lat, 
                ST_X(centroid::geometry) as lng,  
                COALESCE(surface_type::text, 'Unknown') as surface, 
                is_public,
                school,
                cluster_id,
                region,
                created_at, 
                updated_at
            FROM courts
            WHERE centroid IS NOT NULL
        `;
        
        const queryParams: any[] = [];
        let paramIndex = 1;
        
        // Add bbox filter (viewport-based query)
        if (filters.bbox && filters.bbox.length === 4) {
            const [west, south, east, north] = filters.bbox;
            query += ` AND ST_Within(centroid::geometry, ST_MakeEnvelope($${paramIndex}, $${paramIndex + 1}, $${paramIndex + 2}, $${paramIndex + 3}, 4326))`;
            queryParams.push(west, south, east, north);
            paramIndex += 4;
        }
        
        // Add sport filter
        if (filters.sport) {
            query += ` AND sport = $${paramIndex}`;
            queryParams.push(filters.sport);
            paramIndex++;
        }
        
        // Add surface_type filter
        if (filters.surface_type) {
            query += ` AND surface_type = $${paramIndex}`;
            queryParams.push(filters.surface_type);
            paramIndex++;
        }
        
        // Add is_public filter
        if (filters.is_public !== undefined) {
            query += ` AND is_public = $${paramIndex}`;
            queryParams.push(filters.is_public);
            paramIndex++;
        }
        
        query += ` ORDER BY created_at DESC`;
        
        // Add zoom-based limit (optional performance optimization)
        if (filters.zoom && filters.zoom > 15) {
            // For very high zoom levels, limit results to prevent overload
            query += ` LIMIT 1000`;
        }
        
        const result = await pool.query(query, queryParams);
        return result.rows;
    }

    static async getMetadata(): Promise<{ sports: string[]; surfaceTypes: string[] }> {
        const sportsResult = await pool.query(`SELECT DISTINCT sport FROM courts ORDER BY sport`);
        const surfaceTypesResult = await pool.query(`SELECT DISTINCT surface_type FROM courts WHERE surface_type IS NOT NULL ORDER BY surface_type`);
        
        return {
            sports: sportsResult.rows.map(row => row.sport),
            surfaceTypes: surfaceTypesResult.rows.map(row => row.surface_type)
        };
    }

}