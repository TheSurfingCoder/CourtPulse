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

    static async update(id: number, courtData: Partial<CourtInput>): Promise<Court | null> {
        const fields = [];
        const values = [];
        let paramCount = 1;

        if (courtData.name) {
            fields.push(`enriched_name = $${paramCount++}`);
            values.push(courtData.name);
        }
        if (courtData.cluster_group_name !== undefined) {
            fields.push(`photon_name = $${paramCount++}`);
            values.push(courtData.cluster_group_name);
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

        if (fields.length === 0) return null;

        fields.push(`updated_at = NOW()`);
        values.push(id);

        const result = await pool.query(`
            UPDATE courts 
            SET ${fields.join(', ')}
            WHERE id = $${paramCount}
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
        `, values);

        return result.rows[0] || null;
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

}