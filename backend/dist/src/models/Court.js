"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.CourtModel = void 0;
const database_1 = __importDefault(require("../../config/database"));
class CourtModel {
    static async findAll() {
        const result = await database_1.default.query(`
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
    static async findById(id) {
        const result = await database_1.default.query(`
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
    static async findByType(type) {
        const result = await database_1.default.query(`
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
    static async create(courtData) {
        const { name, type, lat, lng, address, surface, is_public } = courtData;
        const result = await database_1.default.query(`
            INSERT INTO courts (enriched_name, sport, centroid, address, surface_type, is_public)
            VALUES ($1, $2, ST_SetSRID(ST_MakePoint($3, $4), 4326), $5, $6, $7)
            RETURNING 
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
        `, [name, type, lng, lat, address, surface, is_public]);
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
        if (courtData.address) {
            fields.push(`address = $${paramCount++}`);
            values.push(courtData.address);
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
                COALESCE(enriched_name, fallback_name, 'Unknown Court') as name,
                sport as type, 
                ST_X(centroid::geometry) as lat, 
                ST_Y(centroid::geometry) as lng,
                address, 
                COALESCE(surface_type::text, surface) as surface, 
                is_public, 
                created_at, 
                updated_at
        `, values);
        return result.rows[0] || null;
    }
    static async delete(id) {
        const result = await database_1.default.query('DELETE FROM courts WHERE id = $1', [id]);
        return (result.rowCount ?? 0) > 0;
    }
}
exports.CourtModel = CourtModel;
//# sourceMappingURL=Court.js.map