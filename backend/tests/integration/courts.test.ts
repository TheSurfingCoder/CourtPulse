import request from 'supertest';
import express from 'express';
import courtRoutes from '../../src/routes/courts';
import { setupTestDatabase, teardownTestDatabase, clearTestData, testPool } from '../helpers/database';

// Create a test app
const app = express();
app.use(express.json());
app.use('/api/courts', courtRoutes);

describe('Courts API Integration Tests', () => {
  // Set up test database before all tests
  beforeAll(async () => {
    await setupTestDatabase();
  });

  // Clean up after all tests
  afterAll(async () => {
    await teardownTestDatabase();
  });

  // Clear test data before each test
  beforeEach(async () => {
    await clearTestData();
  });


  describe('GET /api/courts', () => {
    it('should return all courts', async () => {
      // Insert test data directly into the database using PostGIS
      await testPool.query(`
        INSERT INTO courts (name, type, location, address, surface, is_public)
        VALUES ($1, $2, ST_SetSRID(ST_MakePoint($3, $4), 4326), $5, $6, $7)
      `, ['Test Court', 'basketball', -73.9851, 40.7589, 'Test Address', 'asphalt', true]);

      const response = await request(app)
        .get('/api/courts')
        .expect(200);

      expect(response.body).toHaveProperty('success', true);
      expect(response.body).toHaveProperty('data');
      expect(response.body).toHaveProperty('count');
      expect(response.body.data).toHaveLength(1);
      expect(response.body.data[0].name).toBe('Test Court');
    });
  });

  describe('GET /api/courts/:id', () => {
    it('should return 400 for invalid ID', async () => {
      const response = await request(app)
        .get('/api/courts/invalid')
        .expect(400);

      expect(response.body).toHaveProperty('success', false);
      expect(response.body).toHaveProperty('message', 'Invalid court ID');
    });
  });

  describe('POST /api/courts', () => {
    it('should return 400 for missing required fields', async () => {
      const response = await request(app)
        .post('/api/courts')
        .send({ name: 'Test Court' })
        .expect(400);

      expect(response.body).toHaveProperty('success', false);
      expect(response.body.message).toContain('Missing required fields');
    });

    it('should return 400 for missing location data', async () => {
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
      const response = await request(app)
        .put('/api/courts/invalid')
        .send({ name: 'Updated Court' })
        .expect(400);

      expect(response.body).toHaveProperty('success', false);
      expect(response.body).toHaveProperty('message', 'Invalid court ID');
    });
  });

  describe('DELETE /api/courts/:id', () => {
    it('should return 400 for invalid ID', async () => {
      const response = await request(app)
        .delete('/api/courts/invalid')
        .expect(400);

      expect(response.body).toHaveProperty('success', false);
      expect(response.body).toHaveProperty('message', 'Invalid court ID');
    });
  });
});
