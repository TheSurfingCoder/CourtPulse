//courts model
import express from 'express';
import * as Sentry from '@sentry/node';
import pool from '../../config/database';
import { CourtModel } from '../models/Court';
import { CoverageAreaModel } from '../models/CoverageArea';
import { searchRateLimit } from '../middleware/rateLimiter';
import { asyncHandler } from '../middleware/errorHandler';
import { authenticateUser, requireAuth, requireAdmin, AuthenticatedRequest } from '../middleware/auth';
import { setAuditContext } from '../utils/auditContext';
import { sendDeletionRequestEmail } from '../services/email';
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
 * Public (authenticateUser sets req.user when token present; anonymous can read)
 */
router.get('/metadata', authenticateUser, asyncHandler(async (_req: express.Request, res: express.Response) => {
  const result = await CourtModel.getMetadata();

  return res.json({
    success: true,
    data: result
  });
}));

/**
 * GET /api/courts/coverage
 * Get coverage areas (regions where court data is available)
 * Optionally filter by region name
 * Public (anonymous can read)
 */
router.get('/coverage', authenticateUser, asyncHandler(async (req: express.Request, res: express.Response) => {
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
 * Requires zoom level > 11 for performance reasons
 * Public (anonymous can read)
 */
router.get('/search', authenticateUser, searchRateLimit, asyncHandler(async (req: express.Request, res: express.Response) => {
  const { bbox, zoom, sport, surface_type, is_public, has_lights } = req.query;
  
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
    has_lights?: boolean;
  } = {
    bbox: parsedBbox,
    zoom: zoomLevel,
    sport: sport as string | undefined,
    surface_type: surface_type as string | undefined,
    is_public: is_public !== undefined ? is_public === 'true' : undefined,
    has_lights: has_lights !== undefined ? has_lights === 'true' : undefined
  };
  
  // Remove undefined values
  Object.keys(filters).forEach(key => {
    if (filters[key as keyof typeof filters] === undefined) {
      delete filters[key as keyof typeof filters];
    }
  });
  
  const searchStart = Date.now();
  const courts = await CourtModel.searchCourts(filters);
  const searchDurationMs = Date.now() - searchStart;

  Sentry.metrics.count('court_search.count', 1, {
    attributes: { sport: filters.sport ?? 'any', zoom: String(Math.floor(zoomLevel)) }
  });
  Sentry.metrics.distribution('court_search.results', courts.length, {
    attributes: { sport: filters.sport ?? 'any', has_bbox: String(!!parsedBbox) }
  });
  // Duration metric: track p50/p95 query latency over time in the Metrics explorer.
  // Complements the per-request span (which shows one trace) with a trend view.
  Sentry.metrics.distribution('court_search.duration_ms', searchDurationMs, {
    unit: 'millisecond',
    attributes: { sport: filters.sport ?? 'any', has_bbox: String(!!parsedBbox) }
  });

  if (courts.length === 0) {
    Sentry.logger.warn('Court search returned zero results', {
      zoom: zoomLevel,
      sport: filters.sport,
      surface_type: filters.surface_type,
      is_public: filters.is_public,
      has_lights: filters.has_lights,
      bbox: parsedBbox?.join(',')
    });
  }

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
 * Public (anonymous can read)
 */
router.get('/:id', authenticateUser, asyncHandler(async (req: express.Request, res: express.Response) => {
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
 * Public (anonymous can read)
 */
router.get('/type/:type', authenticateUser, asyncHandler(async (req: express.Request, res: express.Response) => {
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
 * Requires auth (contributor or admin)
 */
router.post(
  '/',
  authenticateUser,
  requireAuth,
  asyncHandler(async (req: AuthenticatedRequest, res: express.Response) => {
    const { name, type, location, surface, is_public, has_lights } = req.body;

    // Validation - throw specific exceptions
    const missingFields: string[] = [];
    if (!name) missingFields.push('name');
    if (!type) missingFields.push('type');
    if (!location?.lat) missingFields.push('location.lat');
    if (!location?.lng) missingFields.push('location.lng');

    if (missingFields.length > 0) {
      throw new MissingFieldsException(missingFields);
    }

    await setAuditContext({
      changed_by_type: 'user',
      changed_by_id: req.user!.id,
      changed_by_email: req.user!.email,
      changed_by_role: req.user!.role,
      change_source: 'web_ui'
    });

    const court = await CourtModel.create({
      name,
      type,
      lat: location.lat,
      lng: location.lng,
      surface: surface || 'other',
      is_public: is_public ?? true,
      has_lights: has_lights ?? null
    });

    await pool.query(`UPDATE users SET edits_count = edits_count + 1 WHERE id = $1`, [req.user!.id]);

    Sentry.metrics.count('court_create.count', 1, {
      attributes: { sport: type, is_public: String(is_public ?? true) }
    });
    Sentry.logger.info('Court created', {
      courtId: court.id,
      sport: type,
      is_public: is_public ?? true
    });

    return res.status(201).json({
      success: true,
      data: court
    });
  })
);

/**
 * PUT /api/courts/:id
 * Update court
 * Requires auth (contributor or admin); sets audit context and increments user edits_count
 */
router.put(
  '/:id',
  authenticateUser,
  requireAuth,
  asyncHandler(async (req: AuthenticatedRequest, res: express.Response) => {
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

      if (
        'cluster_group_name' in cluster_fields &&
        cluster_fields.cluster_group_name !== null &&
        typeof cluster_fields.cluster_group_name !== 'string'
      ) {
        throw new ValidationException(
          'cluster_fields.cluster_group_name must be a string or null',
          'INVALID_CLUSTER_FIELDS'
        );
      }
    }

    const clusterFields =
      cluster_fields && typeof cluster_fields === 'object' && !Array.isArray(cluster_fields)
        ? cluster_fields
        : undefined;

    await setAuditContext({
      changed_by_type: 'user',
      changed_by_id: req.user!.id,
      changed_by_email: req.user!.email,
      changed_by_role: req.user!.role,
      change_source: 'web_ui'
    });

    const court = await CourtModel.update(id, courtPayload, clusterFields);
    if (!court) {
      throw new CourtNotFoundException(id);
    }

    await pool.query(`UPDATE users SET edits_count = edits_count + 1 WHERE id = $1`, [req.user!.id]);

    // Completes the CRUD metric picture alongside court_create.count and court_search.count.
    // has_cluster_fields tells you how often users are bulk-editing cluster names vs. individual courts.
    Sentry.metrics.count('court_update.count', 1, {
      attributes: {
        has_cluster_fields: String(!!clusterFields),
      }
    });

    return res.json({
      success: true,
      data: court
    });
  })
);

/**
 * POST /api/courts/:id/deletion-request
 * Request deletion of a court (contributor flow — emails admin for review)
 */
router.post(
  '/:id/deletion-request',
  authenticateUser,
  requireAuth,
  asyncHandler(async (req: AuthenticatedRequest, res: express.Response) => {
    const id = parseInt(req.params.id);
    if (isNaN(id)) throw new InvalidIdException('court');

    const court = await CourtModel.findById(id);
    if (!court) throw new CourtNotFoundException(id);

    const { reason } = req.body;
    const requester = req.user!;

    await sendDeletionRequestEmail({
      courtId: id,
      courtName: court.cluster_group_name || court.name || `Court #${id}`,
      requesterEmail: requester.email,
      reason: reason || null,
    });

    Sentry.logger.info('Court deletion requested', {
      courtId: id,
      requestedBy: requester.email,
    });

    return res.json({ success: true, message: 'Deletion request submitted' });
  })
);

/**
 * DELETE /api/courts/:id
 * Delete court
 * Requires admin
 */
router.delete(
  '/:id',
  authenticateUser,
  requireAdmin,
  asyncHandler(async (req: AuthenticatedRequest, res: express.Response) => {
    const id = parseInt(req.params.id);
    if (isNaN(id)) {
      throw new InvalidIdException('court');
    }

    await setAuditContext({
      changed_by_type: 'user',
      changed_by_id: req.user!.id,
      changed_by_email: req.user!.email,
      changed_by_role: 'admin',
      change_source: 'web_ui'
    });

    const deleted = await CourtModel.delete(id);
    if (!deleted) {
      throw new CourtNotFoundException(id);
    }

    Sentry.logger.info('Court deleted', { courtId: id });

    return res.json({
      success: true,
      message: 'Court deleted successfully'
    });
  })
);

export default router;
