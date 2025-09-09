// backend/config/database.ts
import { Pool } from 'pg';
import dotenv from 'dotenv';
dotenv.config();
const pool = new Pool({
    host: process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DB_PORT || '5432'),
    database: process.env.DB_NAME || 'courtpulse',
    user: process.env.DB_USER || 'postgres',
    password: process.env.DB_PASSWORD || 'password',
    ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
});
// Test the connection
pool.on('connect', () => {
    console.log(JSON.stringify({
        level: 'info',
        message: 'Database connection established',
        environment: process.env.NODE_ENV || 'development',
        database: process.env.DB_NAME || 'courtpulse',
        timestamp: new Date().toISOString()
    }));
});
pool.on('error', (err) => {
    console.error(JSON.stringify({
        level: 'error',
        message: 'Unexpected error on idle database client',
        error: {
            message: err.message,
            stack: err.stack
        },
        timestamp: new Date().toISOString()
    }));
    process.exit(-1);
});
export default pool;
//# sourceMappingURL=database.js.map