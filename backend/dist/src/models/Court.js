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
                COALESCE(surface_type::text, 'Unknown') as surface, 
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
                COALESCE(surface_type::text, 'Unknown') as surface, 
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
                COALESCE(surface_type::text, 'Unknown') as surface, 
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
        const { name, type, lat, lng, surface, is_public } = courtData;
        const result = await database_1.default.query(`
            INSERT INTO courts (enriched_name, sport, centroid, surface_type, is_public)
            VALUES ($1, $2, ST_SetSRID(ST_MakePoint($3, $4), 4326), $5, $6)
            RETURNING 
                id, 
                COALESCE(enriched_name, fallback_name, 'Unknown Court') as name,
                sport as type, 
                ST_X(centroid::geometry) as lat, 
                ST_Y(centroid::geometry) as lng,
                COALESCE(surface_type::text, 'Unknown') as surface, 
                is_public, 
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
                COALESCE(enriched_name, fallback_name, 'Unknown Court') as name,
                sport as type, 
                ST_X(centroid::geometry) as lat, 
                ST_Y(centroid::geometry) as lng,
                COALESCE(surface_type::text, 'Unknown') as surface, 
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
    static async findAllClustered() {
        const result = await database_1.default.query(`
            SELECT 
                cluster_id,
                representative_osm_id,
                photon_name,
                total_courts,
                total_hoops,
                sports,
                centroid_lat,
                centroid_lon,
                cluster_bounds
            FROM get_clustered_courts_for_map()
            ORDER BY photon_name
        `);
        return result.rows;
    }
    static async findClusterDetails(clusterId) {
        const result = await database_1.default.query(`
            SELECT
                id, 
                COALESCE(photon_name, enriched_name, fallback_name, 'Unknown Court') as name,
                sport as type,
                ST_Y(centroid::geometry) as lat, 
                ST_X(centroid::geometry) as lng,  
                COALESCE(surface_type::text, 'Unknown') as surface, 
                is_public, 
                created_at, 
                updated_at,
                hoops,
                osm_id
            FROM courts
            WHERE cluster_id = $1
            ORDER BY cluster_representative DESC, osm_id
        `, [clusterId]);
        return result.rows;
    }
    /**
     * Get courts within a viewport for different zoom levels
     * @param bbox - Bounding box [west, south, east, north]
     * @param zoom - Zoom level to determine data source
     * @param filters - Optional filters for sport, surface_type, is_public
     */
    static async getCourtsInViewport(bbox, zoom, filters = {}) {
        const [west, south, east, north] = bbox;
        // Determine data source based on zoom level
        if (zoom <= 6) {
            // Use materialized views for low zoom levels
            return this.getAggregatedCourts(bbox, zoom, filters);
        }
        else if (zoom <= 12) {
            // Use dynamic clustering for medium zoom levels
            return this.getClusteredCourts(bbox, zoom, filters);
        }
        else {
            // Return individual courts for high zoom levels
            return this.getIndividualCourts(bbox, filters);
        }
    }
    /**
     * Get aggregated courts from materialized views (zoom 0-6)
     */
    static async getAggregatedCourts(bbox, zoom, filters) {
        const [west, south, east, north] = bbox;
        const bboxGeometry = `ST_MakeEnvelope(${west}, ${south}, ${east}, ${north}, 4326)`;
        let viewName = 'court_aggregates_country';
        if (zoom >= 3)
            viewName = 'court_aggregates_state';
        if (zoom >= 5)
            viewName = 'court_aggregates_city';
        const whereConditions = [];
        const queryParams = [west, south, east, north];
        let paramIndex = 5;
        if (filters.sport) {
            whereConditions.push(`sport = $${paramIndex++}`);
            queryParams.push(filters.sport);
        }
        if (filters.surface_type) {
            whereConditions.push(`surface_type = $${paramIndex++}`);
            queryParams.push(filters.surface_type);
        }
        if (filters.is_public !== undefined) {
            whereConditions.push(`is_public = $${paramIndex++}`);
            queryParams.push(filters.is_public);
        }
        const whereClause = whereConditions.length > 0 ? `AND ${whereConditions.join(' AND ')}` : '';
        const query = `
            SELECT 
                zoom_type,
                region_name,
                sport,
                surface_type,
                is_public,
                court_count,
                ST_AsGeoJSON(bounds) as bounds_geojson,
                ST_AsGeoJSON(center_point) as center_point_geojson
            FROM ${viewName}
            WHERE ST_Intersects(bounds, ${bboxGeometry})
            ${whereClause}
            ORDER BY court_count DESC
            LIMIT 1000
        `;
        const result = await database_1.default.query(query, queryParams);
        return result.rows;
    }
    /**
     * Get clustered courts for medium zoom levels (7-12)
     */
    static async getClusteredCourts(bbox, zoom, filters) {
        const [west, south, east, north] = bbox;
        const bboxGeometry = `ST_MakeEnvelope(${west}, ${south}, ${east}, ${north}, 4326)`;
        const whereConditions = ['centroid IS NOT NULL'];
        const queryParams = [west, south, east, north];
        let paramIndex = 5;
        if (filters.sport) {
            whereConditions.push(`sport = $${paramIndex++}`);
            queryParams.push(filters.sport);
        }
        if (filters.surface_type) {
            whereConditions.push(`surface_type = $${paramIndex++}`);
            queryParams.push(filters.surface_type);
        }
        if (filters.is_public !== undefined) {
            whereConditions.push(`is_public = $${paramIndex++}`);
            queryParams.push(filters.is_public);
        }
        const whereClause = whereConditions.join(' AND ');
        // Use existing clustered courts or create dynamic clusters
        const query = `
            SELECT 
                cluster_id,
                representative_osm_id,
                photon_name,
                total_courts,
                total_hoops,
                sports,
                centroid_lat,
                centroid_lon,
                ST_AsGeoJSON(cluster_bounds) as cluster_bounds_geojson
            FROM courts
            WHERE ${whereClause}
            AND ST_Intersects(centroid, ${bboxGeometry})
            AND cluster_id IS NOT NULL
            ORDER BY total_courts DESC
            LIMIT 500
        `;
        const result = await database_1.default.query(query, queryParams);
        return result.rows;
    }
    /**
     * Get individual courts for high zoom levels (13+)
     */
    static async getIndividualCourts(bbox, filters) {
        const [west, south, east, north] = bbox;
        const bboxGeometry = `ST_MakeEnvelope(${west}, ${south}, ${east}, ${north}, 4326)`;
        const whereConditions = ['centroid IS NOT NULL'];
        const queryParams = [west, south, east, north];
        let paramIndex = 5;
        if (filters.sport) {
            whereConditions.push(`sport = $${paramIndex++}`);
            queryParams.push(filters.sport);
        }
        if (filters.surface_type) {
            whereConditions.push(`surface_type = $${paramIndex++}`);
            queryParams.push(filters.surface_type);
        }
        if (filters.is_public !== undefined) {
            whereConditions.push(`is_public = $${paramIndex++}`);
            queryParams.push(filters.is_public);
        }
        const whereClause = whereConditions.join(' AND ');
        const query = `
            SELECT 
                id,
                name,
                sport,
                surface_type,
                is_public,
                created_at,
                updated_at,
                hoops,
                osm_id,
                ST_X(centroid::geometry) as lng,
                ST_Y(centroid::geometry) as lat
            FROM courts
            WHERE ${whereClause}
            AND ST_Intersects(centroid, ${bboxGeometry})
            ORDER BY name
            LIMIT 1000
        `;
        const result = await database_1.default.query(query, queryParams);
        return result.rows;
    }
}
exports.CourtModel = CourtModel;
//# sourceMappingURL=Court.js.map