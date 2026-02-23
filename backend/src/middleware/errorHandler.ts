import { Request, Response, NextFunction } from 'express';
import { 
  AppException,
  TransientException,
  RateLimitException 
} from '../exceptions';

/**
 * Central error handler for all exceptions.
 *
 * Responsible for transforming errors into consistent HTTP responses.
 * Sentry capture is handled upstream by Sentry.setupExpressErrorHandler,
 * with filtering (drop dev events, drop 400/404s) handled in instrument.ts beforeSend.
 */
export const errorHandler = (
  err: Error,
  req: Request,
  res: Response,
  _next: NextFunction
) => {
  // Build response based on exception type
  if (err instanceof AppException) {
    const response: Record<string, unknown> = {
      success: false,
      error: err.message,
      code: err.code
    };

    // Add stack trace in development
    if (process.env.NODE_ENV === 'development') {
      response.stack = err.stack;
    }

    // Add retry-after header for rate limiting
    if (err instanceof RateLimitException) {
      res.setHeader('Retry-After', err.retryAfter);
    }

    // Add retry-after header for transient errors
    if (err instanceof TransientException && err.retryAfter) {
      res.setHeader('Retry-After', err.retryAfter);
    }

    return res.status(err.statusCode).json(response);
  }

  // Handle unknown/programming errors
  // Don't expose internal details to clients
  const response: Record<string, unknown> = {
    success: false,
    error: 'An unexpected error occurred',
    code: 'INTERNAL_ERROR'
  };

  // Add details in development
  if (process.env.NODE_ENV === 'development') {
    response.message = err.message;
    response.stack = err.stack;
  }

  return res.status(500).json(response);
};

/**
 * 404 handler for unknown routes
 */
export const notFound = (req: Request, _res: Response, next: NextFunction) => {
  const { RouteNotFoundException } = require('../exceptions');
  next(new RouteNotFoundException(req.originalUrl));
};

/**
 * Async handler wrapper - catches async errors and passes to errorHandler
 * 
 * Usage:
 *   router.get('/courts', asyncHandler(async (req, res) => {
 *     const courts = await CourtModel.findAll();
 *     res.json({ success: true, data: courts });
 *   }));
 */
export const asyncHandler = (
  fn: (req: Request, res: Response, next: NextFunction) => Promise<unknown>
) => {
  return (req: Request, res: Response, next: NextFunction) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
};
