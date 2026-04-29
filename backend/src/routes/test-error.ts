// TEMPORARY - remove before merging to main
import express from 'express';
import * as Sentry from '@sentry/node';
import { DatabaseException, ValidationException } from '../exceptions/index.js';
import { asyncHandler } from '../middleware/errorHandler.js';

const router = express.Router();

// 1. Unhandled error — caught by Sentry.setupExpressErrorHandler
router.get('/unhandled', (_req, _res) => {
  throw new Error('Test unhandled Express error');
});

// 2. Unhandled async error — caught by Sentry.setupExpressErrorHandler
router.get('/async', async (_req, _res) => {
  await Promise.reject(new Error('Test unhandled async Express error'));
});

// 3. Manual captureException
router.get('/manual', (_req, res) => {
  try {
    throw new Error('Test manual captureException');
  } catch (err) {
    Sentry.captureException(err, {
      tags: { route: '/api/test-error/manual' },
    });
    res.json({ captured: true, message: 'Check Sentry for "Test manual captureException"' });
  }
});

// 4. Unhandled promise rejection (process-level)
router.get('/rejection', (_req, res) => {
  Promise.reject(new Error('Test unhandled promise rejection'));
  res.json({ triggered: true, message: 'Check Sentry for unhandled promise rejection' });
});

// 5. DatabaseException via errorHandler — should appear in Sentry
router.get('/database-error', asyncHandler(async (_req, _res) => {
  throw new DatabaseException('Test database error via global error handler');
}));

// 6. ValidationException via errorHandler — should be DROPPED by beforeSend
router.get('/validation-error', asyncHandler(async (_req, _res) => {
  throw new ValidationException('Test validation error — should NOT appear in Sentry');
}));

export default router;
