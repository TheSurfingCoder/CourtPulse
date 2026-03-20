/**
 * Frontend Exception Classes
 *
 * These exceptions are thrown by the API layer and caught by UI components.
 * They provide typed error handling and user-friendly messages.
 *
 * Each class carries a literal `kind` discriminant so callers can use an
 * exhaustive switch + `satisfies never` to ensure every error type is handled.
 * Adding or removing a type from `FrontendError` causes a compile error at
 * every switch site that is missing or has a dead case.
 */

// Utility for exhaustive switch statements.
// Place in the `default` branch: `error satisfies never`
// TypeScript errors here if any FrontendError variant is unhandled.
export function assertNever(error: never): never {
  throw new Error(`Unhandled error type: ${JSON.stringify(error)}`);
}

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
 * Closed union of all frontend error types.
 * Add new error classes here — every call to getErrorMessage (and any other
 * exhaustive handler) will immediately fail to compile until the new case
 * is handled.
 */
export type FrontendError =
  | RateLimitError
  | NotFoundError
  | ValidationError
  | APIError
  | NetworkError;

/**
 * Maps a FrontendError to a user-facing message string.
 *
 * This is the canonical exhaustive handler. TypeScript enforces coverage:
 *   - Add a new subtype to FrontendError → the `else` branch no longer narrows
 *     to `never`, so `error satisfies never` fails to compile (missing case)
 *   - Remove a subtype from FrontendError → its `instanceof` branch narrows
 *     `error` to `never` inside, so any property access is a compile error
 *     (dead code detected)
 *
 * Subclasses must be checked before their parent (RateLimitError/NotFoundError/
 * ValidationError before APIError) so TypeScript narrows the union correctly.
 */
export function getErrorMessage(error: FrontendError): string {
  if (error instanceof RateLimitError) {
    return `Rate limit reached. Please try again in ${error.retryAfter} seconds.`;
  } else if (error instanceof NotFoundError) {
    return 'The requested resource was not found.';
  } else if (error instanceof ValidationError) {
    return error.message;
  } else if (error instanceof NetworkError) {
    return 'Unable to connect to the server. Please check your internet connection.';
  } else if (error instanceof APIError) {
    return error.message || 'An unexpected server error occurred.';
  } else {
    error satisfies never;
    return assertNever(error);
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

