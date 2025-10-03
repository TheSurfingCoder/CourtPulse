import rateLimit from 'express-rate-limit';
import { logEvent, logBusinessEvent } from '../../logger';

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
    // Log the rate limit violation
    logBusinessEvent('rate_limit_exceeded', {
      message: 'Rate limit exceeded for search endpoint',
      ip: req.ip,
      userAgent: req.get('User-Agent'),
      endpoint: req.path,
      method: req.method,
      timestamp: new Date().toISOString()
    });

    // Return 429 with Retry-After header
    res.status(429).json({
      success: false,
      message: 'Too many requests. Please try again later.',
      retryAfter: 60
    });
  }
});
