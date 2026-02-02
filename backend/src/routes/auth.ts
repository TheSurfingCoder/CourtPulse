import express, { Request, Response } from 'express';
import crypto from 'crypto';
import pool from '../../config/database';
import { authenticateUser, requireAuth, AuthenticatedRequest } from '../middleware/auth';
import { asyncHandler } from '../middleware/errorHandler';
import { sendMagicLinkEmail } from '../services/email';

const router = express.Router();

const SESSION_EXPIRY_DAYS = 7;
const MAGIC_LINK_EXPIRY_MINUTES = 15;

function getClientIp(req: Request): string | null {
  const forwarded = req.headers['x-forwarded-for'];
  if (typeof forwarded === 'string') {
    return forwarded.split(',')[0]?.trim() || null;
  }
  return req.ip || null;
}

function getClientUserAgent(req: Request): string | null {
  const ua = req.headers['user-agent'];
  return typeof ua === 'string' ? ua : null;
}

/**
 * Create a session for a user: generate token, store hash in DB, return raw token.
 * Used by magic-link verify and (later) OAuth callback.
 */
async function createSession(userId: string, req: Request): Promise<{ token: string; expiresAt: Date }> {
  const token = crypto.randomBytes(32).toString('hex');
  const tokenHash = crypto.createHash('sha256').update(token).digest('hex');
  const expiresAt = new Date(Date.now() + SESSION_EXPIRY_DAYS * 24 * 60 * 60 * 1000);
  const ip = getClientIp(req);
  const userAgent = getClientUserAgent(req);

  await pool.query(
    `INSERT INTO sessions (user_id, token_hash, expires_at, ip_address, user_agent)
     VALUES ($1, $2, $3, $4::inet, $5)`,
    [userId, tokenHash, expiresAt.toISOString(), ip, userAgent]
  );

  return { token, expiresAt };
}

/**
 * POST /api/auth/magic-link
 * Request a magic link. Creates one-time token and (in dev) logs the link.
 */
router.post(
  '/magic-link',
  asyncHandler(async (req: Request, res: Response) => {
    // Validate email from body
    const email = typeof req.body?.email === 'string' ? req.body.email.trim().toLowerCase() : '';
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      res.status(400).json({ error: 'Valid email is required', code: 'INVALID_EMAIL' });
      return;
    }

    // One-time magic link token:
    // - token: raw value we put in the URL (e.g. ?token=abc123...). User clicks the link; we never store this.
    // - tokenHash: we store only the hash in magic_link_tokens. When they hit verify-magic-link we hash the
    //   URL token and look it up; if it matches and isn't expired we get the email and create a session.
    //   Storing only the hash means a DB leak doesn't expose live magic links.
    const token = crypto.randomBytes(32).toString('hex');
    const tokenHash = crypto.createHash('sha256').update(token).digest('hex');
    const expiresAt = new Date(Date.now() + MAGIC_LINK_EXPIRY_MINUTES * 60 * 1000);

    await pool.query(
      `INSERT INTO magic_link_tokens (email, token_hash, expires_at) VALUES ($1, $2, $3)`,
      [email, tokenHash, expiresAt.toISOString()]
    );

    // Build link and send email (Resend when RESEND_API_KEY set); in dev without key, log link
    const baseUrl = process.env.FRONTEND_URL || process.env.PUBLIC_APP_URL || 'http://localhost:3000';
    const verifyUrl = `${baseUrl}/auth/verify-magic-link?token=${token}`;
    const sent = await sendMagicLinkEmail(email, verifyUrl);
    if (!sent.ok && process.env.NODE_ENV !== 'production') {
      console.log('[Auth] Magic link (dev, email not sent):', verifyUrl);
    }

    // Same message whether or not user exists (don't leak account existence)
    res.status(200).json({
      success: true,
      message: 'If an account exists for this email, we sent you a sign-in link.'
    });
  })
);

/**
 * GET /api/auth/verify-magic-link?token=...
 * Verify one-time token, find or create user, create session, return token and user.
 */
router.get(
  '/verify-magic-link',
  asyncHandler(async (req: Request, res: Response) => {
    // Token from URL query (?token=...)
    const token = typeof req.query.token === 'string' ? req.query.token : '';
    if (!token) {
      res.status(400).json({ error: 'Token is required', code: 'MISSING_TOKEN' });
      return;
    }

    // Look up one-time magic link by hash; must not be expired
    const tokenHash = crypto.createHash('sha256').update(token).digest('hex');
    const result = await pool.query(
      `SELECT email FROM magic_link_tokens WHERE token_hash = $1 AND expires_at > NOW()`,
      [tokenHash]
    );

    if (result.rows.length === 0) {
      res.status(401).json({ error: 'Invalid or expired link', code: 'INVALID_MAGIC_LINK' });
      return;
    }

    const { email } = result.rows[0];

    // Find existing user by email (or create below)
    let userId: string;
    const userResult = await pool.query(
      `SELECT id, email, name, role FROM users WHERE email = $1`,
      [email]
    );

    // Existing user: update last_login and email_verified
    if (userResult.rows.length > 0) {
      userId = userResult.rows[0].id;
      await pool.query(
        `UPDATE users SET last_login_at = NOW(), email_verified = true, updated_at = NOW() WHERE id = $1`,
        [userId]
      );
    } else {
      // New user: create contributor account
      const insertResult = await pool.query(
        `INSERT INTO users (email, role, email_verified) VALUES ($1, 'contributor', true) RETURNING id`,
        [email]
      );
      userId = insertResult.rows[0].id;
    }

    // One-time use: delete magic link token so the same link cannot be used again.
    // If someone else gets the link (e.g. forwarded email), they can't sign in after the first use.
    await pool.query(`DELETE FROM magic_link_tokens WHERE token_hash = $1`, [tokenHash]);

    // Create session (store hash in sessions, return raw token) and fetch user for response
    const { token: sessionToken, expiresAt } = await createSession(userId, req);
    const userRowResult = await pool.query(
      `SELECT id, email, name, role FROM users WHERE id = $1`,
      [userId]
    );
    const userRow = userRowResult.rows[0];

    // Return session token and user; client stores token and sends it as Authorization: Bearer
    res.status(200).json({
      success: true,
      token: sessionToken,
      expiresAt: expiresAt.toISOString(),
      user: {
        id: userRow.id,
        email: userRow.email,
        name: userRow.name,
        role: userRow.role
      }
    });
  })
);

/**
 * GET /api/auth/me
 * Return current user if authenticated.
 */
router.get(
  '/me',
  authenticateUser,
  (req: AuthenticatedRequest, res: Response) => {
    if (!req.user) {
      res.status(401).json({ error: 'Not authenticated', code: 'AUTH_REQUIRED' });
      return;
    }
    res.json({ success: true, user: req.user });
  }
);

/**
 * POST /api/auth/logout
 * Invalidate current session (delete from sessions).
 */
router.post(
  '/logout',
  authenticateUser,
  requireAuth,
  asyncHandler(async (req: AuthenticatedRequest, res: Response) => {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      res.status(204).end();
      return;
    }
    const sessionToken = authHeader.substring(7);
    const tokenHash = crypto.createHash('sha256').update(sessionToken).digest('hex');
    await pool.query(`DELETE FROM sessions WHERE token_hash = $1`, [tokenHash]);
    res.status(204).end();
  })
);

export default router;
