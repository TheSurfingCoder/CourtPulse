import { Pool } from 'pg';
declare const testPool: Pool;
export declare const setupTestDatabase: () => Promise<void>;
export declare const teardownTestDatabase: () => Promise<void>;
export declare const clearTestData: () => Promise<void>;
export { testPool };
//# sourceMappingURL=database.d.ts.map