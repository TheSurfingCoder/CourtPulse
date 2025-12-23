/**
 * Frontend Exception Classes
 * 
 * These exceptions are thrown by the API layer and caught by UI components.
 * They provide typed error handling and user-friendly messages.
 */

// Base exception for network/API errors
export class NetworkError extends Error {
  constructor(message: string, public statusCode?: number) {
    super(message);
    this.name = 'NetworkError';
  }
}

// API errors returned from backend
export class APIError extends Error {
  constructor(
    message: string,
    public code: string,
    public statusCode: number
  ) {
    super(message);
    this.name = 'APIError';
  }
}

// Specific API errors for typed handling
export class ValidationError extends APIError {
  constructor(message: string, code: string) {
    super(message, code, 400);
    this.name = 'ValidationError';
  }
}

export class NotFoundError extends APIError {
  constructor(message: string, code: string) {
    super(message, code, 404);
    this.name = 'NotFoundError';
  }
}

export class RateLimitError extends APIError {
  public retryAfter: number;
  
  constructor(message: string, retryAfter: number) {
    super(message, 'RATE_LIMIT_EXCEEDED', 429);
    this.name = 'RateLimitError';
    this.retryAfter = retryAfter;
  }
}

/**
 * Parse API error response and return appropriate exception
 * Sentry handles trace linking automatically via sentry-trace header
 */
export function parseAPIError(
  statusCode: number,
  data: { error?: string; code?: string },
  retryAfter?: string
): APIError {
  const message = data.error || 'An error occurred';
  const code = data.code || 'UNKNOWN_ERROR';

  if (statusCode === 429) {
    const retrySeconds = retryAfter ? parseInt(retryAfter, 10) : 60;
    return new RateLimitError(message, retrySeconds);
  }

  if (statusCode === 404) {
    return new NotFoundError(message, code);
  }

  if (statusCode >= 400 && statusCode < 500) {
    return new ValidationError(message, code);
  }

  return new APIError(message, code, statusCode);
}

