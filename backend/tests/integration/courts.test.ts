import request from 'supertest';
import express from 'express';
import courtRoutes from '../../src/routes/courts';

// Mock the database
jest.mock('../../config/database', () => ({
  __esModule: true,
  default: {
    query: jest.fn(),
    connect: jest.fn(),
    end: jest.fn()
  }
}));

// Create a test app
const app = express();
app.use(express.json());
app.use('/api/courts', courtRoutes);

describe('Courts API Integration Tests', () => {
  let mockPool: any;

  beforeEach(() => {
    jest.clearAllMocks();
    mockPool = require('../../config/database').default;
  });

  describe('GET /api/courts', () => {
    it('should return all courts', async () => {
      const mockCourts = [
        {
          id: 1,
          name: 'Test Court',
          type: 'basketball',
          lat: 40.7589,
          lng: -73.9851,
          address: 'Test Address',
          surface: 'asphalt',
          is_public: true,
          created_at: new Date(),
          updated_at: new Date()
        }
      ];

      mockPool.query.mockResolvedValue({ rows: mockCourts });

      const response = await request(app)
        .get('/api/courts')
        .expect(200);

      expect(response.body).toHaveProperty('success', true);
      expect(response.body).toHaveProperty('data');
      expect(response.body).toHaveProperty('count');
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
      const mockCourt = {
        id: 1,
        name: 'New Court',
        type: 'basketball',
        lat: 40.7589,
        lng: -73.9851,
        address: 'Test Address',
        surface: 'asphalt',
        is_public: true,
        created_at: new Date(),
        updated_at: new Date()
      };

      mockPool.query.mockResolvedValue({ rows: [mockCourt] });

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
