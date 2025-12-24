import pool from '../../config/database';
import { Polygon } from 'geojson';

export interface CoverageArea {
    id: number;
    name: string;
    region: string;
    boundary: Polygon;
    court_count: number;
    last_updated: Date;
    created_at: Date;
}

export class CoverageAreaModel {
    /**
     * Get all coverage areas
     */
    static async getAll(): Promise<CoverageArea[]> {
        const result = await pool.query(`
            SELECT
                id,
                name,
                region,
                ST_AsGeoJSON(boundary)::json as boundary,
                court_count,
                last_updated,
                created_at
            FROM coverage_areas
            ORDER BY created_at DESC
        `);

        return result.rows;
    }

    /**
     * Get coverage areas by region
     */
    static async getByRegion(region: string): Promise<CoverageArea[]> {
        const result = await pool.query(`
            SELECT
                id,
                name,
                region,
                ST_AsGeoJSON(boundary)::json as boundary,
                court_count,
                last_updated,
                created_at
            FROM coverage_areas
            WHERE region = $1
            ORDER BY created_at DESC
        `, [region]);

        return result.rows;
    }

    /**
     * Create or update a coverage area
     */
    static async upsert(
        name: string,
        region: string,
        boundary: Polygon,
        courtCount: number
    ): Promise<CoverageArea> {
        const result = await pool.query(`
            INSERT INTO coverage_areas (name, region, boundary, court_count, last_updated)
            VALUES ($1, $2, ST_GeomFromGeoJSON($3), $4, NOW())
            ON CONFLICT (region, name)
                DO UPDATE SET
                    boundary = ST_GeomFromGeoJSON($3),
                    court_count = $4,
                    last_updated = NOW()
            RETURNING
                id,
                name,
                region,
                ST_AsGeoJSON(boundary)::json as boundary,
                court_count,
                last_updated,
                created_at
        `, [name, region, JSON.stringify(boundary), courtCount]);

        return result.rows[0];
    }
}
