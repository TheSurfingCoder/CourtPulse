import { Request, Response, NextFunction } from 'express';
import crypto from 'crypto';
import pool from '../../config/database';

export interface AuthenticatedRequest extends Request {
  user?: {
    id: string;
    email: string;
    name: string | null;
    role: string;
  };
}

export async function authenticateUser(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): Promise<void> {
  const authHeader = req.headers.authorization;

  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    req.user = undefined;
    return next();
  }

  const sessionToken = authHeader.substring(7);
  const tokenHash = crypto.createHash('sha256').update(sessionToken).digest('hex');

  try {
    const result = await pool.query(
      `
      SELECT
        u.id, u.email, u.name, u.role, u.is_active,
        s.expires_at
      FROM sessions s
      JOIN users u ON s.user_id = u.id
      WHERE s.token_hash = $1
    `,
      [tokenHash]
    );

    if (result.rows.length === 0) {
      res.status(401).json({
        error: 'Invalid or expired session',
        code: 'INVALID_SESSION'
      });
      return;
    }

    const session = result.rows[0];

    if (new Date(session.expires_at) < new Date()) {
      res.status(401).json({
        error: 'Session expired',
        code: 'SESSION_EXPIRED'
      });
      return;
    }

    if (!session.is_active) {
      res.status(401).json({
        error: 'Account deactivated',
        code: 'ACCOUNT_DEACTIVATED'
      });
      return;
    }

    await pool.query(
      `UPDATE sessions SET last_accessed_at = NOW() WHERE token_hash = $1`,
      [tokenHash]
    );

    req.user = {
      id: session.id,
      email: session.email,
      name: session.name,
      role: session.role
    };

    next();
  } catch (error) {
    console.error('Auth error:', error);
    res.status(500).json({
      error: 'Authentication failed',
      code: 'AUTH_ERROR'
    });
  }
}

export function requireAuth(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): void {
  if (!req.user) {
    res.status(401).json({
      error: 'Authentication required',
      code: 'AUTH_REQUIRED'
    });
    return;
  }
  next();
}

export function requireAdmin(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): void {
  if (!req.user) {
    res.status(401).json({
      error: 'Authentication required',
      code: 'AUTH_REQUIRED'
    });
    return;
  }

  if (req.user.role !== 'admin') {
    res.status(403).json({
      error: 'Admin access required',
      code: 'FORBIDDEN',
      your_role: req.user.role
    });
    return;
  }

  next();
}
