import { CourtModel, Court } from '../../../src/models/Court';

// Mock the database pool - this replaces the real database with fake functions
jest.mock('../../../config/database', () => ({
  __esModule: true,
  default: {
    query: jest.fn(),    // Mock the database query function
    connect: jest.fn(),  // Mock the database connection function
    end: jest.fn()       // Mock the database close function
  }
}));

describe('CourtModel', () => {
  let mockPool: any;

  // This runs before each test to reset the mock functions
  beforeEach(() => {
    jest.clearAllMocks();
    mockPool = require('../../../config/database').default;
  });

  describe('findAll', () => {
    it('should return all courts', async () => {
      // Arrange: Create fake court data that the database would return
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

      // Arrange: Tell the mock database to return our fake data
      mockPool.query.mockResolvedValue({ rows: mockCourts });

      // Act: Call the actual method we're testing
      const result = await CourtModel.findAll();

      // Assert: Check that we got the expected result
      expect(result).toEqual(mockCourts);
      // Assert: Check that the database was called with a SELECT query
      expect(mockPool.query).toHaveBeenCalledWith(
        expect.stringContaining('SELECT')
      );
    });

    it('should handle database errors', async () => {
      // Arrange: Create a fake database error
      const error = new Error('Database connection failed');
      mockPool.query.mockRejectedValue(error);

      // Act & Assert: Check that the method throws the expected error
      await expect(CourtModel.findAll()).rejects.toThrow('Database connection failed');
    });
  });

  describe('findById', () => {
    it('should return court by id', async () => {
      // Arrange: Create fake court data
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

      // Arrange: Mock database to return our fake court
      mockPool.query.mockResolvedValue({ rows: [mockCourt] });

      // Act: Call the method with ID 1
      const result = await CourtModel.findById(1);

      // Assert: Check we got the expected court
      expect(result).toEqual(mockCourt);
      // Assert: Check the database was called with correct query and parameters
      expect(mockPool.query).toHaveBeenCalledWith(
        expect.stringContaining('WHERE id = $1'),
        [1]
      );
    });

    it('should return null for non-existent court', async () => {
      // Arrange: Mock database to return empty results (no court found)
      mockPool.query.mockResolvedValue({ rows: [] });

      // Act: Try to find a court that doesn't exist
      const result = await CourtModel.findById(999);

      // Assert: Should return null when no court is found
      expect(result).toBeNull();
    });
  });

  describe('create', () => {
    it('should create a new court', async () => {
      // Arrange: Create court data to insert
      const courtData = {
        name: 'New Court',
        type: 'tennis',
        location: { lat: 40.7589, lng: -73.9851 },
        address: 'New Address',
        surface: 'clay',
        is_public: true
      };

      // Arrange: Create what the database should return after insertion
      const createdCourt = { ...courtData, id: 1, created_at: new Date(), updated_at: new Date() };
      mockPool.query.mockResolvedValue({ rows: [createdCourt] });

      // Act: Call the create method
      const result = await CourtModel.create(courtData);

      // Assert: Check we got the created court back
      expect(result).toEqual(createdCourt);
      // Assert: Check the database was called with INSERT query and correct parameters
      expect(mockPool.query).toHaveBeenCalledWith(
        expect.stringContaining('INSERT INTO courts'),
        ['New Court', 'tennis', -73.9851, 40.7589, 'New Address', 'clay', true]
      );
    });
  });
});
