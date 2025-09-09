export interface Court {
    id: number;
    name: string;
    type: string;
    location: {
        lat: number;
        lng: number;
    };
    address: string;
    surface: string;
    is_public: boolean;
    created_at: Date;
    updated_at: Date;
}
export declare class CourtModel {
    static findAll(): Promise<Court[]>;
    static findById(id: number): Promise<Court | null>;
    static findByType(type: string): Promise<Court[]>;
    static create(courtData: Omit<Court, 'id' | 'created_at' | 'updated_at'>): Promise<Court>;
    static update(id: number, courtData: Partial<Omit<Court, 'id' | 'created_at' | 'updated_at'>>): Promise<Court | null>;
    static delete(id: number): Promise<boolean>;
}
//# sourceMappingURL=Court.d.ts.map