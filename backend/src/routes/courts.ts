//courts model
import express from 'express';
import { CourtModel } from '../models/Court';
import { searchRateLimit } from '../middleware/rateLimiter';

const router = express.Router();

// GET /api/courts/metadata - Get available sports and surface types from database
router.get('/metadata', async (req: express.Request, res: express.Response) => {
  try {
    const result = await CourtModel.getMetadata();
    
    return res.json({
      success: true,
      data: result
    });
  } catch (error) {
    console.error(JSON.stringify({
      event: 'metadata_fetch_error',
      timestamp: new Date().toISOString(),
      error: {
        message: error instanceof Error ? error.message : 'Unknown error',
        stack: error instanceof Error ? error.stack : undefined
      }
    }));
    return res.status(500).json({
      success: false,
      message: 'Failed to fetch metadata',
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// GET /api/courts/search - Search courts with viewport and filters
router.get('/search', searchRateLimit, async (req: express.Request, res: express.Response) => {
  try {
    const { bbox, zoom, sport, surface_type, is_public } = req.query;
    
    // Validate zoom level (must be > 11 for search)
    const zoomLevel = parseFloat(zoom as string);
    if (zoomLevel <= 11) {
      return res.status(400).json({
        success: false,
        message: 'Zoom level must be greater than 11 to search courts'
      });
    }
    
    // Parse bbox parameter
    let parsedBbox: [number, number, number, number] | undefined;
    if (bbox) {
      const bboxArray = (bbox as string).split(',').map(coord => parseFloat(coord));
      if (bboxArray.length === 4 && bboxArray.every(coord => !isNaN(coord))) {
        parsedBbox = bboxArray as [number, number, number, number];
      } else {
        return res.status(400).json({
          success: false,
          message: 'Invalid bbox format. Expected: west,south,east,north'
        });
      }
    }
    
    // Parse filters
    const filters: any = {
      bbox: parsedBbox,
      zoom: zoomLevel,
      sport: sport as string,
      surface_type: surface_type as string,
      is_public: is_public !== undefined ? is_public === 'true' : undefined
    };
    
    // Remove undefined values
    Object.keys(filters).forEach(key => {
      if (filters[key] === undefined) {
        delete filters[key];
      }
    });
    
    const courts = await CourtModel.searchCourts(filters);
    
    return res.json({
      success: true,
      count: courts.length,
      data: courts,
      filters: filters
    });
  } catch (error) {
    console.error(JSON.stringify({
      event: 'courts_search_error',
      timestamp: new Date().toISOString(),
      error: {
        message: error instanceof Error ? error.message : 'Unknown error',
        stack: error instanceof Error ? error.stack : undefined
      },
      request: {
        method: req.method,
        url: req.url,
        query: req.query
      }
    }));
    return res.status(500).json({
      success: false,
      message: 'Failed to search courts',
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
    const { name, type, location, surface, is_public } = req.body;

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
      lat: location.lat,
      lng: location.lng,
      surface: surface || 'Unknown',
      is_public: is_public ?? true
    });

    console.log('Court created:', court.id, court.name);

    return res.status(201).json({
      success: true,
      data: court
    });
  } catch (error) {
    console.error(JSON.stringify({
      level: 'error',
      message: 'Failed to create court',
      error: {
        message: error instanceof Error ? error.message : 'Unknown error',
        stack: error instanceof Error ? error.stack : undefined
      },
      request: {
        method: req.method,
        url: req.url,
        body: req.body
      },
      timestamp: new Date().toISOString()
    }));
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

    const body = req.body || {}; // raw payload from client (per-court + optional cluster fields)
    // Separate optional cluster-level updates (cluster_fields) from per-court fields (courtPayload)
    const { cluster_fields, ...courtPayload } = body;
    
    // Validate cluster_fields if provided
    if (cluster_fields !== undefined) {
      if (typeof cluster_fields !== 'object' || cluster_fields === null || Array.isArray(cluster_fields)) {
        return res.status(400).json({
          success: false,
          message: 'cluster_fields must be an object'
        });
      }
      
      // Validate that cluster_fields only contains allowed keys
      const allowedClusterFields = ['cluster_group_name'];
      const invalidKeys = Object.keys(cluster_fields).filter(key => !allowedClusterFields.includes(key));
      
      if (invalidKeys.length > 0) {
        return res.status(400).json({
          success: false,
          message: `Invalid cluster_fields keys: ${invalidKeys.join(', ')}. Allowed keys: ${allowedClusterFields.join(', ')}`
        });
      }
      
      // Validate types of cluster field values
      if ('cluster_group_name' in cluster_fields && cluster_fields.cluster_group_name !== null && typeof cluster_fields.cluster_group_name !== 'string') {
        return res.status(400).json({
          success: false,
          message: 'cluster_fields.cluster_group_name must be a string or null'
        });
      }
    }
    
    const clusterFields = cluster_fields && typeof cluster_fields === 'object' && !Array.isArray(cluster_fields)
      ? cluster_fields
      : undefined;

    const court = await CourtModel.update(id, courtPayload, clusterFields);
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