export interface Court {
    id: number;
    name: string;
    cluster_group_name: string | null;
    type: string;
    lat: number;
    lng: number;
    surface: string;
    is_public: boolean;
    cluster_id: string | null;
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
}
export declare class CourtModel {
    static findById(id: number): Promise<Court | null>;
    static findByType(type: string): Promise<Court[]>;
    static create(courtData: CourtInput): Promise<Court>;
    static update(id: number, courtData: Partial<CourtInput>): Promise<Court | null>;
    static delete(id: number): Promise<boolean>;
    static searchCourts(filters: {
        bbox?: [number, number, number, number];
        sport?: string;
        surface_type?: string;
        is_public?: boolean;
        zoom?: number;
    }): Promise<Court[]>;
}
//# sourceMappingURL=Court.d.ts.map