import pool from '../../config/database';
import { logBusinessEvent } from '../../logger';

export interface Court {
    id: number;
    name: string; // Maps to individual_court_name or fallback
    cluster_group_name: string | null; // Maps to photon_name (cluster group name)
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
    bounding_box_id?: string | null;
    bounding_box_coords?: Record<string, unknown> | null;
}

export class CourtModel {



    static async findById(id: number): Promise<Court | null> {
        const result = await pool.query(`
            SELECT 
                id, 
                COALESCE(individual_court_name, enriched_name, fallback_name, 'Unknown Court') as name,
                COALESCE(photon_name, enriched_name, fallback_name, NULL) as cluster_group_name,
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
                COALESCE(individual_court_name, enriched_name, fallback_name, 'Unknown Court') as name,
                COALESCE(photon_name, enriched_name, fallback_name, NULL) as cluster_group_name,
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
            ORDER BY COALESCE(individual_court_name, enriched_name, fallback_name, 'Unknown Court')
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
                COALESCE(individual_court_name, enriched_name, fallback_name, 'Unknown Court') as name,
                COALESCE(photon_name, enriched_name, fallback_name, NULL) as cluster_group_name,
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
        const fields = [];
        const values = [];
        let paramCount = 1;
        const sanitizedClusterFields = clusterFields || {};
        const hasClusterFieldUpdates = Object.keys(sanitizedClusterFields).some(
            (key) => (sanitizedClusterFields as any)[key] !== undefined
        );

        // Only process cluster_group_name from courtData if it's NOT in clusterFields
        // Cluster-level updates take precedence over per-court updates
        if (courtData.cluster_group_name !== undefined && sanitizedClusterFields.cluster_group_name === undefined) {
            const trimmedClusterName = courtData.cluster_group_name && courtData.cluster_group_name.trim() !== '' ? courtData.cluster_group_name.trim() : null;
            fields.push(`photon_name = $${paramCount++}`);
            values.push(trimmedClusterName);
        }

        if (courtData.name !== undefined && courtData.name !== null && courtData.name.trim() !== '') {
            fields.push(`enriched_name = $${paramCount++}`);
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

        const client = await pool.connect();

        try {
            await client.query('BEGIN');

            const existingCourtResult = await client.query(`
                SELECT id, cluster_id, photon_name
                FROM courts
                WHERE id = $1
                FOR UPDATE
            `, [id]);

            if (existingCourtResult.rows.length === 0) {
                await client.query('ROLLBACK');
                return null;
            }

            const existingCourt = existingCourtResult.rows[0];

            // Track if we're updating photon_name in the per-court update and capture the new value
            let updatedPhotonName: string | null = null;
            const photonNameFieldIndex = fields.findIndex(field => field.startsWith('photon_name ='));
            if (photonNameFieldIndex !== -1) {
                // Extract the parameter index from the field (e.g., "photon_name = $2" -> 2)
                const match = fields[photonNameFieldIndex].match(/\$(\d+)/);
                if (match) {
                    const paramIndex = parseInt(match[1]);
                    // values array is 0-indexed, but params are 1-indexed, so subtract 1
                    updatedPhotonName = values[paramIndex - 1] as string | null;
                }
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
                clusterAssignments.push(`photon_name = $${clusterParamIndex++}`);
                clusterValues.push(newClusterName);
            }

            if (sanitizedClusterFields.bounding_box_id !== undefined) {
                clusterAssignments.push(`bounding_box_id = $${clusterParamIndex++}`);
                clusterValues.push(sanitizedClusterFields.bounding_box_id);
            }

            if (sanitizedClusterFields.bounding_box_coords !== undefined) {
                clusterAssignments.push(`bounding_box_coords = $${clusterParamIndex++}`);
                clusterValues.push(sanitizedClusterFields.bounding_box_coords);
            }

            if (clusterAssignments.length > 0) {
                clusterAssignments.push(`updated_at = NOW()`);

                let identifierClause = '';
                if (existingCourt.cluster_id) {
                    // Use cluster_id if available (most reliable, unaffected by photon_name updates)
                    identifierClause = `cluster_id = $${clusterParamIndex}`;
                    clusterValues.push(existingCourt.cluster_id);
                    clusterParamIndex++;
                } else if (updatedPhotonName !== null && existingCourt.photon_name) {
                    // If we just updated photon_name, we need to find courts with EITHER the old or new name
                    // This ensures we update all courts in the cluster, including the one we just updated
                    // and any others that still have the old name
                    identifierClause = `(photon_name = $${clusterParamIndex} OR photon_name = $${clusterParamIndex + 1} OR id = $${clusterParamIndex + 2})`;
                    clusterValues.push(existingCourt.photon_name); // Old name
                    clusterValues.push(updatedPhotonName); // New name
                    clusterValues.push(existingCourt.id); // Ensure this court is included
                    clusterParamIndex += 3;
                } else if (updatedPhotonName !== null) {
                    // Updated photon_name but no old name (was null) - use new name or id
                    identifierClause = `(photon_name = $${clusterParamIndex} OR id = $${clusterParamIndex + 1})`;
                    clusterValues.push(updatedPhotonName);
                    clusterValues.push(existingCourt.id);
                    clusterParamIndex += 2;
                } else if (existingCourt.photon_name) {
                    // Use original photon_name if we didn't update it
                    identifierClause = `photon_name = $${clusterParamIndex}`;
                    clusterValues.push(existingCourt.photon_name);
                    clusterParamIndex++;
                } else {
                    // Fallback: if this court is not yet associated with a cluster identifier,
                    // apply the cluster field updates directly to this court record.
                    logBusinessEvent('cluster_update_fallback_to_single_court', {
                        courtId: existingCourt.id,
                        reason: 'no_cluster_identifiers',
                        clusterFields: Object.keys(sanitizedClusterFields),
                        message: 'Cluster fields provided but court has no cluster_id or photon_name. Updating single court only.'
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
        } catch (error) {
            await client.query('ROLLBACK');
            throw error;
        } finally {
            client.release();
        }

        return await this.findById(id);
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
                COALESCE(individual_court_name, enriched_name, fallback_name, 'Unknown Court') as name,
                COALESCE(photon_name, enriched_name, fallback_name, NULL) as cluster_group_name,
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