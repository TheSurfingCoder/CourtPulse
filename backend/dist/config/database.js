"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
// backend/config/database.ts
const pg_1 = require("pg");
const dotenv_1 = __importDefault(require("dotenv"));
const logger_js_1 = require("../../shared/logger.js");
// In test environment, load from .env.test
if (process.env.NODE_ENV === 'test') {
    dotenv_1.default.config({ path: '.env.test' });
}
else {
    dotenv_1.default.config();
}
// Use DATABASE_URL if available (for production/staging), otherwise use individual env vars
const pool = new pg_1.Pool(process.env.DATABASE_URL
    ? {
        connectionString: process.env.DATABASE_URL,
        ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
    }
    : {
        host: process.env.DB_HOST || 'localhost',
        port: parseInt(process.env.DB_PORT || '5432'),
        database: process.env.DB_NAME || 'courtpulse',
        user: process.env.DB_USER || 'postgres',
        password: process.env.DB_PASSWORD || 'password',
        ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
    });
// Test the connection
pool.on('connect', () => {
    (0, logger_js_1.logLifecycleEvent)('database_connection_established', {
        message: 'Database connection established',
        environment: process.env.NODE_ENV || 'development',
        connectionMethod: process.env.DATABASE_URL ? 'DATABASE_URL' : 'individual_env_vars',
        database: process.env.DB_NAME || 'courtpulse'
    });
});
pool.on('error', (err) => {
    (0, logger_js_1.logError)(err, {
        message: 'Unexpected error on idle database client'
    });
    process.exit(-1);
});
exports.default = pool;
//# sourceMappingURL=database.js.map