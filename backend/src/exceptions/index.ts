/**
 * Custom Exception Classes for CourtPulse Backend
 * 
 * Following the layer-by-layer exception handling pattern:
 * - Database layer throws raw errors
 * - Business logic transforms into domain exceptions
 * - Routes catch and pass to errorHandler via next(error)
 * - errorHandler maps exceptions to HTTP responses
 */

// Base exception for all app errors
export class AppException extends Error {
  public readonly isOperational: boolean;
  public readonly statusCode: number;
  public readonly code: string;

  constructor(message: string, statusCode: number = 500, code: string = 'INTERNAL_ERROR') {
    super(message);
    this.name = this.constructor.name;
    this.statusCode = statusCode;
    this.code = code;
    this.isOperational = true; // Distinguishes from programming errors
    Error.captureStackTrace(this, this.constructor);
  }
}

// ============================================
// Validation Exceptions (400 Bad Request)
// ============================================

export class ValidationException extends AppException {
  constructor(message: string, code: string = 'VALIDATION_ERROR') {
    super(message, 400, code);
  }
}

export class InvalidCoordinatesException extends ValidationException {
  constructor(lat?: number, lng?: number) {
    const coords = lat !== undefined && lng !== undefined ? `: ${lat}, ${lng}` : '';
    super(`Invalid coordinates${coords}`, 'INVALID_COORDINATES');
  }
}

export class InvalidBboxException extends ValidationException {
  constructor() {
    super('Invalid bbox format. Expected: west,south,east,north', 'INVALID_BBOX');
  }
}

export class InvalidIdException extends ValidationException {
  constructor(resourceType: string = 'resource') {
    super(`Invalid ${resourceType} ID`, 'INVALID_ID');
  }
}

export class MissingFieldsException extends ValidationException {
  constructor(fields: string[]) {
    super(`Missing required fields: ${fields.join(', ')}`, 'MISSING_FIELDS');
  }
}

export class ZoomLevelException extends ValidationException {
  constructor(minZoom: number) {
    super(`Zoom level must be greater than ${minZoom} to search courts`, 'ZOOM_TOO_LOW');
  }
}

// ============================================
// Not Found Exceptions (404)
// ============================================

export class NotFoundException extends AppException {
  constructor(message: string, code: string = 'NOT_FOUND') {
    super(message, 404, code);
  }
}

export class CourtNotFoundException extends NotFoundException {
  constructor(courtId?: number | string) {
    const idPart = courtId !== undefined ? ` with ID ${courtId}` : '';
    super(`Court${idPart} not found`, 'COURT_NOT_FOUND');
  }
}

export class RouteNotFoundException extends NotFoundException {
  constructor(path: string) {
    super(`Route ${path} not found`, 'ROUTE_NOT_FOUND');
  }
}

// ============================================
// Conflict Exceptions (409)
// ============================================

export class ConflictException extends AppException {
  constructor(message: string, code: string = 'CONFLICT') {
    super(message, 409, code);
  }
}

export class DuplicateCourtException extends ConflictException {
  constructor() {
    super('A court already exists at this location', 'DUPLICATE_COURT');
  }
}

// ============================================
// Database Exceptions (500, but with context)
// ============================================

export class DatabaseException extends AppException {
  public readonly originalError?: Error;
  public readonly query?: string;

  constructor(message: string, originalError?: Error, query?: string) {
    super(message, 500, 'DATABASE_ERROR');
    this.originalError = originalError;
    this.query = query;
  }
}

export class DeadlockException extends DatabaseException {
  constructor(operation: string, retryCount: number) {
    super(`Database deadlock during ${operation} after ${retryCount} retries`);
  }
}

export class LockTimeoutException extends DatabaseException {
  constructor(operation: string, timeoutMs: number) {
    super(`Lock timeout during ${operation} after ${timeoutMs}ms`);
  }
}

// ============================================
// Transient Exceptions (503 - retryable)
// ============================================

export class TransientException extends AppException {
  public readonly retryAfter?: number;

  constructor(message: string, retryAfter?: number) {
    super(message, 503, 'SERVICE_UNAVAILABLE');
    this.retryAfter = retryAfter;
  }
}

export class RateLimitException extends AppException {
  public readonly retryAfter: number;

  constructor(retryAfter: number = 60) {
    super('Rate limit exceeded. Please try again later.', 429, 'RATE_LIMIT_EXCEEDED');
    this.retryAfter = retryAfter;
  }
}

