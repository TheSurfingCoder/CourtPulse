import rateLimit, { ipKeyGenerator } from 'express-rate-limit';
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

// Rate limiter for magic link requests.
// Keyed by normalized email rather than IP — one shared office IP shouldn't
// block legitimate users, but one email address being bombarded should.
// 1 request per email per minute is enough to stop email bombing while staying
// invisible to a user who fat-fingers the submit button.
export const magicLinkRateLimit = rateLimit({
  windowMs: 60 * 1000,
  max: 1,
  standardHeaders: true,
  legacyHeaders: false,
  keyGenerator: (req) => {
    const email = typeof req.body?.email === 'string' ? req.body.email.trim().toLowerCase() : '';
    // Fall back to IP if email is missing — the route handler will 400 anyway.
    // ipKeyGenerator normalizes IPv6 to a /64 subnet so a single IPv6 address can't bypass limits.
    return email || ipKeyGenerator(req.ip || '');
  },
  // Silent rate-limit: respond with the SAME generic success message rather than 429.
  // This prevents leaking "this email recently requested a link" (which would also
  // partially leak account existence to anyone watching the response). Legit users
  // who hit submit twice quickly just see "if an account exists…" and check their
  // first email; attackers learn nothing.
  handler: (_req, res) => {
    res.status(200).json({
      success: true,
      message: 'If an account exists for this email, we sent you a sign-in link.'
    });
  }
});
