import express from 'express';
import { CourtModel } from '../models/Court.js';

const router = express.Router();

// GET /api/courts - Get all courts
router.get('/', async (req: express.Request, res: express.Response) => {
  try {
    const courts = await CourtModel.findAll();
    return res.json({
      success: true,
      count: courts.length,
      data: courts
    });
  } catch (error) {
    console.error('Error fetching courts:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to fetch courts',
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// GET /api/courts/:id - Get court by ID
router.get('/:id', async (req: express.Request, res: express.Response) => {
  try {
    const id = parseInt(req.params.id);
    if (isNaN(id)) {
      return res.status(400).json({
        success: false,
        message: 'Invalid court ID'
      });
    }

    const court = await CourtModel.findById(id);
    if (!court) {
      return res.status(404).json({
        success: false,
        message: 'Court not found'
      });
    }

    return res.json({
      success: true,
      data: court
    });
  } catch (error) {
    console.error('Error fetching court:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to fetch court',
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// GET /api/courts/type/:type - Get courts by type
router.get('/type/:type', async (req: express.Request, res: express.Response) => {
  try {
    const { type } = req.params;
    const courts = await CourtModel.findByType(type);
    
    return res.json({
      success: true,
      count: courts.length,
      data: courts
    });
  } catch (error) {
    console.error('Error fetching courts by type:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to fetch courts by type',
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// POST /api/courts - Create new court
router.post('/', async (req: express.Request, res: express.Response) => {
  try {
    const { name, type, location, address, surface, is_public } = req.body;

    // Basic validation
    if (!name || !type || !location || !location.lat || !location.lng) {
      return res.status(400).json({
        success: false,
        message: 'Missing required fields: name, type, location (lat/lng)'
      });
    }

    const court = await CourtModel.create({
      name,
      type,
      location,
      address,
      surface,
      is_public: is_public ?? true
    });

    return res.status(201).json({
      success: true,
      data: court
    });
  } catch (error) {
    console.error('Error creating court:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to create court',
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// PUT /api/courts/:id - Update court
router.put('/:id', async (req: express.Request, res: express.Response) => {
  try {
    const id = parseInt(req.params.id);
    if (isNaN(id)) {
      return res.status(400).json({
        success: false,
        message: 'Invalid court ID'
      });
    }

    const court = await CourtModel.update(id, req.body);
    if (!court) {
      return res.status(404).json({
        success: false,
        message: 'Court not found'
      });
    }

    return res.json({
      success: true,
      data: court
    });
  } catch (error) {
    console.error('Error updating court:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to update court',
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// DELETE /api/courts/:id - Delete court
router.delete('/:id', async (req: express.Request, res: express.Response) => {
  try {
    const id = parseInt(req.params.id);
    if (isNaN(id)) {
      return res.status(400).json({
        success: false,
        message: 'Invalid court ID'
      });
    }

    const deleted = await CourtModel.delete(id);
    if (!deleted) {
      return res.status(404).json({
        success: false,
        message: 'Court not found'
      });
    }

    return res.json({
      success: true,
      message: 'Court deleted successfully'
    });
  } catch (error) {
    console.error('Error deleting court:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to delete court',
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

export default router;