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

  describe('findByType', () => {
    it('should return courts by type', async () => {
      // Arrange: Create fake courts of specific type
      const mockCourts = [
        {
          id: 1,
          name: 'Basketball Court 1',
          type: 'basketball',
          lat: 40.7589,
          lng: -73.9851,
          address: 'Test Address 1',
          surface: 'asphalt',
          is_public: true,
          created_at: new Date(),
          updated_at: new Date()
        },
        {
          id: 2,
          name: 'Basketball Court 2',
          type: 'basketball',
          lat: 40.7589,
          lng: -73.9851,
          address: 'Test Address 2',
          surface: 'asphalt',
          is_public: true,
          created_at: new Date(),
          updated_at: new Date()
        }
      ];

      // Arrange: Mock database to return courts of specific type
      mockPool.query.mockResolvedValue({ rows: mockCourts });

      // Act: Call the method with type 'basketball'
      const result = await CourtModel.findByType('basketball');

      // Assert: Check we got the expected courts
      expect(result).toEqual(mockCourts);
      // Assert: Check the database was called with correct query and parameters
      expect(mockPool.query).toHaveBeenCalledWith(
        expect.stringContaining('WHERE type = $1'),
        ['basketball']
      );
    });

    it('should return empty array for non-existent type', async () => {
      // Arrange: Mock database to return empty results
      mockPool.query.mockResolvedValue({ rows: [] });

      // Act: Try to find courts of non-existent type
      const result = await CourtModel.findByType('nonexistent');

      // Assert: Should return empty array
      expect(result).toEqual([]);
    });
  });

  describe('update', () => {
    it('should update court with valid data', async () => {
      // Arrange: Create update data
      const updateData = {
        name: 'Updated Court',
        type: 'tennis',
        surface: 'clay'
      };

      const updatedCourt = {
        id: 1,
        name: 'Updated Court',
        type: 'tennis',
        lat: 40.7589,
        lng: -73.9851,
        address: 'Original Address',
        surface: 'clay',
        is_public: true,
        created_at: new Date(),
        updated_at: new Date()
      };

      mockPool.query.mockResolvedValue({ rows: [updatedCourt] });

      // Act: Call the update method
      const result = await CourtModel.update(1, updateData);

      // Assert: Check we got the updated court back
      expect(result).toEqual(updatedCourt);
      // Assert: Check the database was called with UPDATE query
      expect(mockPool.query).toHaveBeenCalledWith(
        expect.stringContaining('UPDATE courts'),
        expect.arrayContaining(['Updated Court', 'tennis', 'clay', 1])
      );
    });

    it('should return null when no fields to update', async () => {
      // Arrange: Empty update data
      const updateData = {};

      // Act: Call the update method with empty data
      const result = await CourtModel.update(1, updateData);

      // Assert: Should return null
      expect(result).toBeNull();
      // Assert: Database should not be called
      expect(mockPool.query).not.toHaveBeenCalled();
    });

    it('should return null when court not found', async () => {
      // Arrange: Mock database to return no rows (court not found)
      mockPool.query.mockResolvedValue({ rows: [] });

      // Act: Try to update non-existent court
      const result = await CourtModel.update(999, { name: 'Updated' });

      // Assert: Should return null
      expect(result).toBeNull();
    });
  });

  describe('delete', () => {
    it('should delete court successfully', async () => {
      // Arrange: Mock database to return successful deletion (rowCount > 0)
      mockPool.query.mockResolvedValue({ rowCount: 1 });

      // Act: Call the delete method
      const result = await CourtModel.delete(1);

      // Assert: Should return true
      expect(result).toBe(true);
      // Assert: Check the database was called with DELETE query
      expect(mockPool.query).toHaveBeenCalledWith(
        'DELETE FROM courts WHERE id = $1',
        [1]
      );
    });

    it('should return false when court not found', async () => {
      // Arrange: Mock database to return no rows deleted (rowCount = 0)
      mockPool.query.mockResolvedValue({ rowCount: 0 });

      // Act: Try to delete non-existent court
      const result = await CourtModel.delete(999);

      // Assert: Should return false
      expect(result).toBe(false);
    });
  });
});
