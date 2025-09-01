import { CourtModel, Court } from '../../../src/models/Court';

// Mock the database pool
jest.mock('../../../config/database', () => ({
  __esModule: true,
  default: {
    query: jest.fn(),
    connect: jest.fn(),
    end: jest.fn()
  }
}));

describe('CourtModel', () => {
  let mockPool: any;

  beforeEach(() => {
    jest.clearAllMocks();
    mockPool = require('../../../config/database').default;
  });

  describe('findAll', () => {
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

      const result = await CourtModel.findAll();

      expect(result).toEqual(mockCourts);
      expect(mockPool.query).toHaveBeenCalledWith(
        expect.stringContaining('SELECT')
      );
    });

    it('should handle database errors', async () => {
      const error = new Error('Database connection failed');
      mockPool.query.mockRejectedValue(error);

      await expect(CourtModel.findAll()).rejects.toThrow('Database connection failed');
    });
  });

  describe('findById', () => {
    it('should return court by id', async () => {
      const mockCourt = {
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
      };

      mockPool.query.mockResolvedValue({ rows: [mockCourt] });

      const result = await CourtModel.findById(1);

      expect(result).toEqual(mockCourt);
      expect(mockPool.query).toHaveBeenCalledWith(
        expect.stringContaining('WHERE id = $1'),
        [1]
      );
    });

    it('should return null for non-existent court', async () => {
      mockPool.query.mockResolvedValue({ rows: [] });

      const result = await CourtModel.findById(999);

      expect(result).toBeNull();
    });
  });

  describe('create', () => {
    it('should create a new court', async () => {
      const courtData = {
        name: 'New Court',
        type: 'tennis',
        location: { lat: 40.7589, lng: -73.9851 },
        address: 'New Address',
        surface: 'clay',
        is_public: true
      };

      const createdCourt = { ...courtData, id: 1, created_at: new Date(), updated_at: new Date() };
      mockPool.query.mockResolvedValue({ rows: [createdCourt] });

      const result = await CourtModel.create(courtData);

      expect(result).toEqual(createdCourt);
      expect(mockPool.query).toHaveBeenCalledWith(
        expect.stringContaining('INSERT INTO courts'),
        ['New Court', 'tennis', -73.9851, 40.7589, 'New Address', 'clay', true]
      );
    });
  });
});
