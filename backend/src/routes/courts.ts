//courts model
import express from 'express';
import { CourtModel } from '../models/Court';
import { CoverageAreaModel } from '../models/CoverageArea';
import { searchRateLimit } from '../middleware/rateLimiter';
import { asyncHandler } from '../middleware/errorHandler';
import {
  InvalidIdException,
  InvalidBboxException,
  MissingFieldsException,
  ZoomLevelException,
  CourtNotFoundException,
  ValidationException
} from '../exceptions';

const router = express.Router();

/**
 * GET /api/courts/metadata
 * Get available sports and surface types from database
 * Returns metadata for filtering courts in the UI
 */
router.get('/metadata', asyncHandler(async (_req: express.Request, res: express.Response) => {
  const result = await CourtModel.getMetadata();

  return res.json({
    success: true,
    data: result
  });
}));

/**
 * GET /api/courts/coverage
 * Get coverage areas (regions where court data is available)
 */
router.get('/coverage', asyncHandler(async (req: express.Request, res: express.Response) => {
  const { region } = req.query;

  const coverageAreas = region
    ? await CoverageAreaModel.getByRegion(region as string)
    : await CoverageAreaModel.getAll();

  return res.json({
    success: true,
    count: coverageAreas.length,
    data: coverageAreas
  });
}));

/**
 * GET /api/courts/search
 * Search courts with viewport and filters
 */
router.get('/search', searchRateLimit, asyncHandler(async (req: express.Request, res: express.Response) => {
  const { bbox, zoom, sport, surface_type, is_public } = req.query;
  
  // Validate zoom level (must be > 11 for search)
  const zoomLevel = parseFloat(zoom as string);
  if (isNaN(zoomLevel) || zoomLevel <= 11) {
    throw new ZoomLevelException(11);
  }
  
  // Parse bbox parameter
  let parsedBbox: [number, number, number, number] | undefined;
  if (bbox) {
    const bboxArray = (bbox as string).split(',').map(coord => parseFloat(coord));
    if (bboxArray.length !== 4 || bboxArray.some(coord => isNaN(coord))) {
      throw new InvalidBboxException();
    }
    parsedBbox = bboxArray as [number, number, number, number];
  }
  
  // Parse filters
  const filters: {
    bbox?: [number, number, number, number];
    zoom: number;
    sport?: string;
    surface_type?: string;
    is_public?: boolean;
  } = {
    bbox: parsedBbox,
    zoom: zoomLevel,
    sport: sport as string | undefined,
    surface_type: surface_type as string | undefined,
    is_public: is_public !== undefined ? is_public === 'true' : undefined
  };
  
  // Remove undefined values
  Object.keys(filters).forEach(key => {
    if (filters[key as keyof typeof filters] === undefined) {
      delete filters[key as keyof typeof filters];
    }
  });
  
  const courts = await CourtModel.searchCourts(filters);
  
  return res.json({
    success: true,
    count: courts.length,
    data: courts,
    filters: filters
  });
}));

/**
 * GET /api/courts/:id
 * Get court by ID
 */
router.get('/:id', asyncHandler(async (req: express.Request, res: express.Response) => {
  const id = parseInt(req.params.id);
  if (isNaN(id)) {
    throw new InvalidIdException('court');
  }

  const court = await CourtModel.findById(id);
  if (!court) {
    throw new CourtNotFoundException(id);
  }

  return res.json({
    success: true,
    data: court
  });
}));

/**
 * GET /api/courts/type/:type
 * Get courts by type
 */
router.get('/type/:type', asyncHandler(async (req: express.Request, res: express.Response) => {
  const { type } = req.params;
  const courts = await CourtModel.findByType(type);
  
  return res.json({
    success: true,
    count: courts.length,
    data: courts
  });
}));

/**
 * POST /api/courts
 * Create new court
 */
router.post('/', asyncHandler(async (req: express.Request, res: express.Response) => {
  const { name, type, location, surface, is_public } = req.body;

  // Validation - throw specific exceptions
  const missingFields: string[] = [];
  if (!name) missingFields.push('name');
  if (!type) missingFields.push('type');
  if (!location?.lat) missingFields.push('location.lat');
  if (!location?.lng) missingFields.push('location.lng');
  
  if (missingFields.length > 0) {
    throw new MissingFieldsException(missingFields);
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
}));

/**
 * PUT /api/courts/:id
 * Update court
 */
router.put('/:id', asyncHandler(async (req: express.Request, res: express.Response) => {
  const id = parseInt(req.params.id);
  if (isNaN(id)) {
    throw new InvalidIdException('court');
  }

  const body = req.body || {};
  const { cluster_fields, ...courtPayload } = body;
  
  // Validate cluster_fields if provided
  if (cluster_fields !== undefined) {
    if (typeof cluster_fields !== 'object' || cluster_fields === null || Array.isArray(cluster_fields)) {
      throw new ValidationException('cluster_fields must be an object', 'INVALID_CLUSTER_FIELDS');
    }
    
    const allowedClusterFields = ['cluster_group_name'];
    const invalidKeys = Object.keys(cluster_fields).filter(key => !allowedClusterFields.includes(key));
    
    if (invalidKeys.length > 0) {
      throw new ValidationException(
        `Invalid cluster_fields keys: ${invalidKeys.join(', ')}. Allowed keys: ${allowedClusterFields.join(', ')}`,
        'INVALID_CLUSTER_FIELDS'
      );
    }
    
    if ('cluster_group_name' in cluster_fields && 
        cluster_fields.cluster_group_name !== null && 
        typeof cluster_fields.cluster_group_name !== 'string') {
      throw new ValidationException(
        'cluster_fields.cluster_group_name must be a string or null',
        'INVALID_CLUSTER_FIELDS'
      );
    }
  }
  
  const clusterFields = cluster_fields && typeof cluster_fields === 'object' && !Array.isArray(cluster_fields)
    ? cluster_fields
    : undefined;

  const court = await CourtModel.update(id, courtPayload, clusterFields);
  if (!court) {
    throw new CourtNotFoundException(id);
  }

  return res.json({
    success: true,
    data: court
  });
}));

/**
 * DELETE /api/courts/:id
 * Delete court
 */
router.delete('/:id', asyncHandler(async (req: express.Request, res: express.Response) => {
  const id = parseInt(req.params.id);
  if (isNaN(id)) {
    throw new InvalidIdException('court');
  }

  const deleted = await CourtModel.delete(id);
  if (!deleted) {
    throw new CourtNotFoundException(id);
  }

  return res.json({
    success: true,
    message: 'Court deleted successfully'
  });
}));

export default router;
