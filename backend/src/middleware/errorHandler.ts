import { Request, Response, NextFunction } from 'express';
import * as Sentry from '@sentry/node';
import { 
  AppException, 
  ValidationException, 
  NotFoundException, 
  DatabaseException,
  TransientException,
  RateLimitException 
} from '../exceptions';

/**
 * Central error handler for all exceptions.
 * 
 * This is the HTTP BOUNDARY - all errors flow here and get:
 * 1. Captured in Sentry with tags (Sentry handles trace linking via sentry-trace header)
 * 2. Transformed into consistent HTTP responses
 * 3. Logged with appropriate context for debugging
 */
export const errorHandler = (
  err: Error,
  req: Request,
  res: Response,
  _next: NextFunction
) => {
  // Determine if this is an operational error (expected) vs programming error (bug)
  const isOperational = err instanceof AppException && err.isOperational;

  // Capture in Sentry with rich context
  // Sentry automatically links traces via sentry-trace/baggage headers
  Sentry.withScope((scope: Sentry.Scope) => {
    scope.setTag('errorType', err.name);
    scope.setTag('isOperational', String(isOperational));
    
    if (err instanceof AppException) {
      scope.setTag('errorCode', err.code);
      scope.setTag('statusCode', String(err.statusCode));
    }
    
    scope.setContext('request', {
      method: req.method,
      url: req.url,
      path: req.path,
      query: req.query,
      userAgent: req.get('User-Agent'),
      ip: req.ip
    });
    
    // Skip capturing validation/not-found errors - these are user errors, not bugs
    if (err instanceof ValidationException || err instanceof NotFoundException) {
      return; // Don't send to Sentry
    }
    
    // Set severity based on error type
    if (err instanceof DatabaseException || !isOperational) {
      scope.setLevel('error');
    } else {
      scope.setLevel('warning');
    }
    
    Sentry.captureException(err);
  });

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
