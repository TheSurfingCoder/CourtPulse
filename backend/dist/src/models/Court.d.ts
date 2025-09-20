export interface Court {
    id: number;
    name: string;
    type: string;
    lat: number;
    lng: number;
    surface: string;
    is_public: boolean;
    created_at: Date;
    updated_at: Date;
}
export interface ClusteredCourt {
    cluster_id: string;
    representative_osm_id: string;
    photon_name: string;
    total_courts: number;
    total_hoops: number;
    sports: string[];
    centroid_lat: number;
    centroid_lon: number;
    cluster_bounds: {
        bounds: any;
        center: any;
    };
}
export interface CourtInput {
    name: string;
    type: string;
    lat: number;
    lng: number;
    surface: string;
    is_public: boolean;
}
export declare class CourtModel {
    static findAll(): Promise<Court[]>;
    static findById(id: number): Promise<Court | null>;
    static findByType(type: string): Promise<Court[]>;
    static create(courtData: CourtInput): Promise<Court>;
    static update(id: number, courtData: Partial<CourtInput>): Promise<Court | null>;
    static delete(id: number): Promise<boolean>;
    static findAllClustered(): Promise<ClusteredCourt[]>;
    static findClusterDetails(clusterId: string): Promise<Court[]>;
    /**
     * Get courts within a viewport for different zoom levels
     * @param bbox - Bounding box [west, south, east, north]
     * @param zoom - Zoom level to determine data source
     * @param filters - Optional filters for sport, surface_type, is_public
     */
    static getCourtsInViewport(bbox: [number, number, number, number], zoom: number, filters?: {
        sport?: string;
        surface_type?: string;
        is_public?: boolean;
    }): Promise<any[]>;
    /**
     * Get aggregated courts from materialized views (zoom 0-6)
     */
    private static getAggregatedCourts;
    /**
     * Get clustered courts for medium zoom levels (7-12)
     */
    private static getClusteredCourts;
    /**
     * Get individual courts for high zoom levels (13+)
     */
    private static getIndividualCourts;
}
//# sourceMappingURL=Court.d.ts.map