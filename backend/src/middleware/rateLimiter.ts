import rateLimit from 'express-rate-limit';
import * as Sentry from '@sentry/node';

// Rate limiter for search endpoints
export const searchRateLimit = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 20, // 20 requests per minute
  message: {
    success: false,
    message: 'Too many requests. Please try again later.',
    retryAfter: 60
  },
  standardHeaders: true, // Return rate limit info in the `RateLimit-*` headers
  legacyHeaders: false, // Disable the `X-RateLimit-*` headers
  handler: (req, res) => {
    Sentry.metrics.count('rate_limit.exceeded', 1, {
      attributes: { endpoint: req.path }
    });
    Sentry.logger.warn('Rate limit exceeded', {
      ip: req.ip,
      endpoint: req.path,
      retryAfter: 60
    });
    res.status(429).json({
      success: false,
      message: 'Too many requests. Please try again later.',
      retryAfter: 60
    });
  }
});
