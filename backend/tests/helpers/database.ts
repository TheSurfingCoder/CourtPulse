import { Pool } from 'pg';
import dotenv from 'dotenv';

// Load test environment variables
dotenv.config({ path: '.env.test' });

// Create a separate test database connection
const testPool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT || '5432'),
  database: process.env.DB_NAME || 'courtpulse_test',
  user: process.env.DB_USER || 'postgres',
  password: process.env.DB_PASSWORD || 'password',
  ssl: false
});

// Database setup and teardown functions
// This function creates a test database with PostGIS support
// It handles database creation and PostGIS extension setup
export const setupTestDatabase = async () => {
  try {
    // Create the test database if it doesn't exist
    const adminPool = new Pool({
      host: process.env.DB_HOST || 'localhost',
      port: parseInt(process.env.DB_PORT || '5432'),
      database: 'postgres', // Connect to default postgres database
      user: process.env.DB_USER || 'postgres',
      password: process.env.DB_PASSWORD || 'password',
      ssl: false
    });

    await adminPool.query(`CREATE DATABASE ${process.env.DB_NAME || 'courtpulse_test'}`);
    await adminPool.end();
  } catch (error) {
    // Database might already exist, that's okay
    console.log('Test database already exists or creation failed:', error);
  }

  // Enable PostGIS extension in the test database
  try {
    await testPool.query('CREATE EXTENSION IF NOT EXISTS postgis;');
    console.log('PostGIS extension enabled successfully');
  } catch (error) {
    console.log('PostGIS extension error:', error);
    throw new Error('PostGIS extension is required but not available');
  }

  // Drop existing table if it exists and create with PostGIS geometry
  try {
    await testPool.query('DROP TABLE IF EXISTS courts CASCADE;');
    await testPool.query(`
      CREATE TABLE courts (
        id SERIAL PRIMARY KEY,
        address VARCHAR(500),
        surface VARCHAR(50),
        is_public BOOLEAN NOT NULL DEFAULT true,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        source VARCHAR(50) NOT NULL DEFAULT 'osm',
        osm_id VARCHAR(255) UNIQUE,
        google_place_id VARCHAR(255),
        geom GEOMETRY(POLYGON, 4326),
        sport VARCHAR(50) NOT NULL,
        hoops INTEGER,
        fallback_name VARCHAR(255),
        surface_type VARCHAR(50),
        centroid GEOGRAPHY(POINT, 4326)
      )
    `);
    console.log('Courts table created successfully with PostGIS');
  } catch (error) {
    console.log('Table creation error:', error);
    throw error;
  }
};

export const teardownTestDatabase = async () => {
  try {
    // Clear all data from courts table
    await testPool.query('DELETE FROM courts');
  } catch (error) {
    // Table might not exist, that's okay
    console.log('Table cleanup failed:', error);
  }
  await testPool.end();
};

export const clearTestData = async () => {
  // Clear all data but keep the table structure
  await testPool.query('DELETE FROM courts');
};

export { testPool };
// Test comment
