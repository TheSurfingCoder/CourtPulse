import pool from '../../config/database';

export interface Court {
    id: number;
    name: string; // Maps to enriched_name or fallback_name
    type: string; // Maps to sport
    lat: number; // From centroid
    lng: number; // From centroid
    address: string;
    surface: string; // Maps to surface_type
    is_public: boolean;
    created_at: Date;
    updated_at: Date;
}

export class CourtModel {

    static async findAll(): Promise<Court[]> {
        const result = await pool.query(`
            SELECT
                id, 
                COALESCE(enriched_name, fallback_name, 'Unknown Court') as name,
                sport as type,
                ST_X(centroid::geometry) as lat, 
                ST_Y(centroid::geometry) as lng,  
                address, 
                COALESCE(surface_type::text, surface) as surface, 
                is_public, 
                created_at, 
                updated_at
            FROM courts
            WHERE centroid IS NOT NULL
            ORDER BY created_at DESC
        `);
        
        return result.rows;
    }

    static async findById(id: number): Promise<Court | null> {
        const result = await pool.query(`
            SELECT 
                id, 
                COALESCE(enriched_name, fallback_name, 'Unknown Court') as name,
                sport as type, 
                ST_X(centroid::geometry) as lat, 
                ST_Y(centroid::geometry) as lng,
                address, 
                COALESCE(surface_type::text, surface) as surface, 
                is_public, 
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
                COALESCE(enriched_name, fallback_name, 'Unknown Court') as name,
                sport as type, 
                ST_X(centroid::geometry) as lat, 
                ST_Y(centroid::geometry) as lng,
                address, 
                COALESCE(surface_type::text, surface) as surface, 
                is_public, 
                created_at, 
                updated_at
            FROM courts 
            WHERE sport = $1 AND centroid IS NOT NULL
            ORDER BY COALESCE(enriched_name, fallback_name, 'Unknown Court')
        `, [type]);
        return result.rows;
    }

    static async create(courtData: Omit<Court, 'id' | 'created_at' | 'updated_at'>): Promise<Court> {
        const { name, type, location, address, surface, is_public } = courtData;
        const result = await pool.query(`
            INSERT INTO courts (name, type, location, address, surface, is_public)
            VALUES ($1, $2, ST_SetSRID(ST_MakePoint($3, $4), 4326), $5, $6, $7)
            RETURNING 
                id, name, type, 
                ST_X(location) as lat, 
                ST_Y(location) as lng,
                address, surface, is_public, 
                created_at, updated_at
        `, [name, type, location.lng, location.lat, address, surface, is_public]);
        return result.rows[0];
    }

    static async update(id: number, courtData: Partial<Omit<Court, 'id' | 'created_at' | 'updated_at'>>): Promise<Court | null> {
        const fields = [];
        const values = [];
        let paramCount = 1;

        if (courtData.name) {
            fields.push(`name = $${paramCount++}`);
            values.push(courtData.name);
        }
        if (courtData.type) {
            fields.push(`type = $${paramCount++}`);
            values.push(courtData.type);
        }
        if (courtData.location) {
            fields.push(`location = ST_SetSRID(ST_MakePoint($${paramCount++}, $${paramCount++}), 4326)`);
            values.push(courtData.location.lng, courtData.location.lat);
        }
        if (courtData.address) {
            fields.push(`address = $${paramCount++}`);
            values.push(courtData.address);
        }
        if (courtData.surface) {
            fields.push(`surface = $${paramCount++}`);
            values.push(courtData.surface);
        }
        if (courtData.is_public !== undefined) {
            fields.push(`is_public = $${paramCount++}`);
            values.push(courtData.is_public);
        }

        if (fields.length === 0) return null;

        fields.push(`updated_at = NOW()`);
        values.push(id);

        const result = await pool.query(`
            UPDATE courts 
            SET ${fields.join(', ')}
            WHERE id = $${paramCount}
            RETURNING 
                id, name, type, 
                ST_X(location) as lat, 
                ST_Y(location) as lng,
                address, surface, is_public, 
                created_at, updated_at
        `, values);

        return result.rows[0] || null;
    }

    static async delete(id: number): Promise<boolean> {
        const result = await pool.query('DELETE FROM courts WHERE id = $1', [id]);
        return (result.rowCount ?? 0) > 0;
    }

}