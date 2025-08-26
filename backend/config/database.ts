// backend/src/config/database.ts
import { Pool } from 'pg';
import dotenv from 'dotenv';
import developmentConfig from './environments/development.js';
import productionConfig from './environments/production.js';

dotenv.config();

const env = process.env.NODE_ENV || 'development';

// Select configuration based on environment
const config = env === 'production' ? productionConfig : developmentConfig;
const pool = new Pool(config.database);

// Test the connection
pool.on('connect', () => {
  console.log(`Connected to ${env} database`);
});

pool.on('error', (err) => {
  console.error('Unexpected error on idle client', err);
  process.exit(-1);
});

export default pool;
