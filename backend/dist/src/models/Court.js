"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.CourtModel = void 0;
const database_1 = __importDefault(require("../../config/database"));
class CourtModel {
    static async findById(id) {
        const result = await database_1.default.query(`
            SELECT 
                id, 
                COALESCE(individual_court_name, enriched_name, fallback_name, 'Unknown Court') as name,
                photon_name as cluster_group_name,
                sport as type, 
                ST_X(centroid::geometry) as lat, 
                ST_Y(centroid::geometry) as lng,
                COALESCE(surface_type::text, 'Unknown') as surface, 
                is_public, 
                cluster_id,
                created_at, 
                updated_at
            FROM courts 
            WHERE id = $1 AND centroid IS NOT NULL
        `, [id]);
        return result.rows[0] || null;
    }
    static async findByType(type) {
        const result = await database_1.default.query(`
            SELECT 
                id, 
                COALESCE(individual_court_name, enriched_name, fallback_name, 'Unknown Court') as name,
                photon_name as cluster_group_name,
                sport as type, 
                ST_X(centroid::geometry) as lat, 
                ST_Y(centroid::geometry) as lng,
                COALESCE(surface_type::text, 'Unknown') as surface, 
                is_public, 
                cluster_id,
                created_at, 
                updated_at
            FROM courts 
            WHERE sport = $1 AND centroid IS NOT NULL
            ORDER BY COALESCE(individual_court_name, enriched_name, fallback_name, 'Unknown Court')
        `, [type]);
        return result.rows;
    }
    static async create(courtData) {
        const { name, type, lat, lng, surface, is_public } = courtData;
        const result = await database_1.default.query(`
            INSERT INTO courts (enriched_name, sport, centroid, surface_type, is_public)
            VALUES ($1, $2, ST_SetSRID(ST_MakePoint($3, $4), 4326), $5, $6)
            RETURNING 
                id, 
                COALESCE(individual_court_name, enriched_name, fallback_name, 'Unknown Court') as name,
                photon_name as cluster_group_name,
                sport as type, 
                ST_X(centroid::geometry) as lat, 
                ST_Y(centroid::geometry) as lng,
                COALESCE(surface_type::text, 'Unknown') as surface, 
                is_public, 
                cluster_id,
                created_at, 
                updated_at
        `, [name, type, lng, lat, surface, is_public]);
        return result.rows[0];
    }
    static async update(id, courtData) {
        const fields = [];
        const values = [];
        let paramCount = 1;
        if (courtData.name) {
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
        if (fields.length === 0)
            return null;
        fields.push(`updated_at = NOW()`);
        values.push(id);
        const result = await database_1.default.query(`
            UPDATE courts 
            SET ${fields.join(', ')}
            WHERE id = $${paramCount}
            RETURNING 
                id, 
                COALESCE(individual_court_name, enriched_name, fallback_name, 'Unknown Court') as name,
                photon_name as cluster_group_name,
                sport as type, 
                ST_X(centroid::geometry) as lat, 
                ST_Y(centroid::geometry) as lng,
                COALESCE(surface_type::text, 'Unknown') as surface, 
                is_public, 
                cluster_id,
                created_at, 
                updated_at
        `, values);
        return result.rows[0] || null;
    }
    static async delete(id) {
        const result = await database_1.default.query('DELETE FROM courts WHERE id = $1', [id]);
        return (result.rowCount ?? 0) > 0;
    }
    static async searchCourts(filters) {
        // Build dynamic query with filters
        let query = `
            SELECT
                id, 
                COALESCE(individual_court_name, enriched_name, fallback_name, 'Unknown Court') as name,
                photon_name as cluster_group_name,
                sport as type,
                ST_Y(centroid::geometry) as lat, 
                ST_X(centroid::geometry) as lng,  
                COALESCE(surface_type::text, 'Unknown') as surface, 
                is_public, 
                cluster_id,
                created_at, 
                updated_at
            FROM courts
            WHERE centroid IS NOT NULL
        `;
        const queryParams = [];
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
        // Add zoom-based limit (optional performance optimization)
        if (filters.zoom && filters.zoom > 15) {
            // For very high zoom levels, limit results to prevent overload
            query += ` LIMIT 1000`;
        }
        query += ` ORDER BY created_at DESC`;
        const result = await database_1.default.query(query, queryParams);
        return result.rows;
    }
}
exports.CourtModel = CourtModel;
//# sourceMappingURL=Court.js.map