import request from 'supertest';
import express from 'express';
import courtRoutes from '../../src/routes/courts.js';
import { setupTestDatabase, teardownTestDatabase, clearTestData, testPool } from '../helpers/database.js';

// Create a test app
const app = express();
app.use(express.json());
app.use('/api/courts', courtRoutes);

describe('Courts API Integration Tests', () => {
  // Set up test database before all tests - creates PostGIS-enabled test database
  beforeAll(async () => {
    await setupTestDatabase();
  });

  // Clean up after all tests - closes database connections
  afterAll(async () => {
    await teardownTestDatabase();
  });

  // Clear test data before each test - ensures clean state for each test
  beforeEach(async () => {
    await clearTestData();
  });


  describe('GET /api/courts', () => {
    it('should return all courts', async () => {
      // Test: GET all courts endpoint
      // What it does: Tests the complete flow of fetching all courts from database
      // 1. Inserts test data directly into database using PostGIS geometry
      // 2. Makes HTTP GET request to /api/courts
      // 3. Verifies response structure and data
      
      // Insert test data directly into the database using PostGIS
      await testPool.query(`
        INSERT INTO courts (name, type, location, address, surface, is_public)
        VALUES ($1, $2, ST_SetSRID(ST_MakePoint($3, $4), 4326), $5, $6, $7)
      `, ['Test Court', 'basketball', -73.9851, 40.7589, 'Test Address', 'asphalt', true]);

      const response = await request(app)
        .get('/api/courts')
        .expect(200);

      // Verify API response structure
      expect(response.body).toHaveProperty('success', true);
      expect(response.body).toHaveProperty('data');
      expect(response.body).toHaveProperty('count');
      expect(response.body.data).toHaveLength(1);
      expect(response.body.data[0].name).toBe('Test Court');
    });
  });

  describe('GET /api/courts/:id', () => {
    it('should return 400 for invalid ID', async () => {
      // Test: GET court by ID with invalid input
      // What it does: Tests input validation for the get-by-id endpoint
      // 1. Sends request with non-numeric ID ('invalid')
      // 2. Verifies server returns 400 Bad Request
      // 3. Checks error message is appropriate
      
      const response = await request(app)
        .get('/api/courts/invalid')
        .expect(400);

      expect(response.body).toHaveProperty('success', false);
      expect(response.body).toHaveProperty('message', 'Invalid court ID');
    });

    it('should return court by valid ID', async () => {
      // Test: GET court by ID with valid input
      // What it does: Tests successful retrieval of court by ID
      // 1. Inserts test court into database
      // 2. Makes GET request with valid ID
      // 3. Verifies correct court is returned
      
      // Insert test court
      const result = await testPool.query(`
        INSERT INTO courts (name, type, location, address, surface, is_public)
        VALUES ($1, $2, ST_SetSRID(ST_MakePoint($3, $4), 4326), $5, $6, $7)
        RETURNING id
      `, ['Test Court', 'basketball', -73.9851, 40.7589, 'Test Address', 'asphalt', true]);

      const courtId = result.rows[0].id;

      const response = await request(app)
        .get(`/api/courts/${courtId}`)
        .expect(200);

      expect(response.body).toHaveProperty('success', true);
      expect(response.body).toHaveProperty('data');
      expect(response.body.data.name).toBe('Test Court');
      expect(response.body.data.type).toBe('basketball');
    });

    it('should return 404 for non-existent court', async () => {
      // Test: GET court by ID that doesn't exist
      // What it does: Tests handling of non-existent court ID
      // 1. Makes GET request with valid ID that doesn't exist
      // 2. Verifies server returns 404 Not Found
      
      const response = await request(app)
        .get('/api/courts/999')
        .expect(404);

      expect(response.body).toHaveProperty('success', false);
      expect(response.body).toHaveProperty('message', 'Court not found');
    });
  });

  describe('GET /api/courts/type/:type', () => {
    it('should return courts by type', async () => {
      // Test: GET courts by type
      // What it does: Tests filtering courts by type
      // 1. Inserts test courts of different types
      // 2. Makes GET request for specific type
      // 3. Verifies only courts of that type are returned
      
      // Insert test courts
      await testPool.query(`
        INSERT INTO courts (name, type, location, address, surface, is_public)
        VALUES ($1, $2, ST_SetSRID(ST_MakePoint($3, $4), 4326), $5, $6, $7)
      `, ['Basketball Court 1', 'basketball', -73.9851, 40.7589, 'Test Address 1', 'asphalt', true]);

      await testPool.query(`
        INSERT INTO courts (name, type, location, address, surface, is_public)
        VALUES ($1, $2, ST_SetSRID(ST_MakePoint($3, $4), 4326), $5, $6, $7)
      `, ['Tennis Court 1', 'tennis', -73.9851, 40.7589, 'Test Address 2', 'clay', true]);

      const response = await request(app)
        .get('/api/courts/type/basketball')
        .expect(200);

      expect(response.body).toHaveProperty('success', true);
      expect(response.body).toHaveProperty('data');
      expect(response.body).toHaveProperty('count');
      expect(response.body.data).toHaveLength(1);
      expect(response.body.data[0].type).toBe('basketball');
    });
  });

  describe('POST /api/courts', () => {
    it('should return 400 for missing required fields', async () => {
      // Test: POST court with incomplete data
      // What it does: Tests validation when required fields are missing
      // 1. Sends request with only 'name' field (missing type, location)
      // 2. Verifies server returns 400 Bad Request
      // 3. Checks error message mentions missing fields
      
      const response = await request(app)
        .post('/api/courts')
        .send({ name: 'Test Court' })
        .expect(400);

      expect(response.body).toHaveProperty('success', false);
      expect(response.body.message).toContain('Missing required fields');
    });

    it('should return 400 for missing location data', async () => {
      // Test: POST court with invalid location data
      // What it does: Tests validation when location data is incomplete
      // 1. Sends request with null latitude (invalid location)
      // 2. Verifies server returns 400 Bad Request
      // 3. Checks error message mentions missing fields
      
      const response = await request(app)
        .post('/api/courts')
        .send({
          name: 'Test Court',
          type: 'basketball',
          location: { lat: null, lng: -73.9851 },
          address: 'Test Address',
          surface: 'asphalt'
        })
        .expect(400);

      expect(response.body).toHaveProperty('success', false);
      expect(response.body.message).toContain('Missing required fields');
    });

    it('should create court with valid data', async () => {
      // Test: POST court with complete valid data
      // What it does: Tests successful court creation end-to-end
      // 1. Sends request with all required fields
      // 2. Verifies server returns 201 Created
      // 3. Checks response contains created court data
      // 4. Verifies data was actually saved to database
      
      const response = await request(app)
        .post('/api/courts')
        .send({
          name: 'New Court',
          type: 'basketball',
          location: { lat: 40.7589, lng: -73.9851 },
          address: 'Test Address',
          surface: 'asphalt'
        })
        .expect(201);

      // Verify API response
      expect(response.body).toHaveProperty('success', true);
      expect(response.body).toHaveProperty('data');
      expect(response.body.data.name).toBe('New Court');
      expect(response.body.data.type).toBe('basketball');

      // Verify the court was actually saved to the database
      const dbResult = await testPool.query('SELECT * FROM courts WHERE name = $1', ['New Court']);
      expect(dbResult.rows).toHaveLength(1);
      expect(dbResult.rows[0].name).toBe('New Court');
    });
  });

  describe('PUT /api/courts/:id', () => {
    it('should return 400 for invalid ID', async () => {
      // Test: PUT court with invalid ID
      // What it does: Tests input validation for the update endpoint
      // 1. Sends request with non-numeric ID ('invalid')
      // 2. Verifies server returns 400 Bad Request
      // 3. Checks error message is appropriate
      
      const response = await request(app)
        .put('/api/courts/invalid')
        .send({ name: 'Updated Court' })
        .expect(400);

      expect(response.body).toHaveProperty('success', false);
      expect(response.body).toHaveProperty('message', 'Invalid court ID');
    });

    it('should update court with valid data', async () => {
      // Test: PUT court with valid data
      // What it does: Tests successful court update
      // 1. Inserts test court into database
      // 2. Makes PUT request with update data
      // 3. Verifies court is updated and returned
      
      // Insert test court
      const result = await testPool.query(`
        INSERT INTO courts (name, type, location, address, surface, is_public)
        VALUES ($1, $2, ST_SetSRID(ST_MakePoint($3, $4), 4326), $5, $6, $7)
        RETURNING id
      `, ['Original Court', 'basketball', -73.9851, 40.7589, 'Original Address', 'asphalt', true]);

      const courtId = result.rows[0].id;

      const response = await request(app)
        .put(`/api/courts/${courtId}`)
        .send({
          name: 'Updated Court',
          type: 'tennis',
          surface: 'clay'
        })
        .expect(200);

      expect(response.body).toHaveProperty('success', true);
      expect(response.body).toHaveProperty('data');
      expect(response.body.data.name).toBe('Updated Court');
      expect(response.body.data.type).toBe('tennis');
      expect(response.body.data.surface).toBe('clay');
    });

    it('should return 404 for non-existent court', async () => {
      // Test: PUT court that doesn't exist
      // What it does: Tests handling of update on non-existent court
      // 1. Makes PUT request with valid ID that doesn't exist
      // 2. Verifies server returns 404 Not Found
      
      const response = await request(app)
        .put('/api/courts/999')
        .send({ name: 'Updated Court' })
        .expect(404);

      expect(response.body).toHaveProperty('success', false);
      expect(response.body).toHaveProperty('message', 'Court not found');
    });
  });

  describe('DELETE /api/courts/:id', () => {
    it('should return 400 for invalid ID', async () => {
      // Test: DELETE court with invalid ID
      // What it does: Tests input validation for the delete endpoint
      // 1. Sends request with non-numeric ID ('invalid')
      // 2. Verifies server returns 400 Bad Request
      // 3. Checks error message is appropriate
      
      const response = await request(app)
        .delete('/api/courts/invalid')
        .expect(400);

      expect(response.body).toHaveProperty('success', false);
      expect(response.body).toHaveProperty('message', 'Invalid court ID');
    });

    it('should delete court successfully', async () => {
      // Test: DELETE court with valid ID
      // What it does: Tests successful court deletion
      // 1. Inserts test court into database
      // 2. Makes DELETE request with valid ID
      // 3. Verifies court is deleted and success message returned
      
      // Insert test court
      const result = await testPool.query(`
        INSERT INTO courts (name, type, location, address, surface, is_public)
        VALUES ($1, $2, ST_SetSRID(ST_MakePoint($3, $4), 4326), $5, $6, $7)
        RETURNING id
      `, ['Court to Delete', 'basketball', -73.9851, 40.7589, 'Test Address', 'asphalt', true]);

      const courtId = result.rows[0].id;

      const response = await request(app)
        .delete(`/api/courts/${courtId}`)
        .expect(200);

      expect(response.body).toHaveProperty('success', true);
      expect(response.body).toHaveProperty('message', 'Court deleted successfully');

      // Verify court was actually deleted
      const dbResult = await testPool.query('SELECT * FROM courts WHERE id = $1', [courtId]);
      expect(dbResult.rows).toHaveLength(0);
    });

    it('should return 404 for non-existent court', async () => {
      // Test: DELETE court that doesn't exist
      // What it does: Tests handling of delete on non-existent court
      // 1. Makes DELETE request with valid ID that doesn't exist
      // 2. Verifies server returns 404 Not Found
      
      const response = await request(app)
        .delete('/api/courts/999')
        .expect(404);

      expect(response.body).toHaveProperty('success', false);
      expect(response.body).toHaveProperty('message', 'Court not found');
    });
  });
});
