import pool from '../../config/database';

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

        if (courtData.cluster_group_name !== undefined) {
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
                    identifierClause = `cluster_id = $${clusterParamIndex}`;
                    clusterValues.push(existingCourt.cluster_id);
                } else if (existingCourt.photon_name) {
                    identifierClause = `photon_name = $${clusterParamIndex}`;
                    clusterValues.push(existingCourt.photon_name);
                }

                if (identifierClause) {
                    await client.query(`
                        UPDATE courts 
                        SET ${clusterAssignments.join(', ')}
                        WHERE ${identifierClause}
                    `, clusterValues);
                }
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