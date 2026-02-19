import { Request, Response, NextFunction } from 'express';
import crypto from 'crypto';
import pool from '../../config/database';

/**
 * ============================================================================
 * HOW MIDDLEWARE FLOW WORKS
 * ============================================================================
 * 
 * Express middleware functions form a CHAIN. Each function receives the same
 * `req` and `res` objects, and can modify them before passing control to the
 * next function in the chain by calling `next()`.
 * 
 * STEP-BY-STEP FLOW:
 * 
 * 1. Client sends HTTP request:
 *    GET /courts
 *    Headers: { Authorization: "Bearer abc123xyz" }
 * 
 * 2. Express receives request and creates req/res objects
 * 
 * 3. First middleware runs: authenticateUser(req, res, next)
 *    - Reads req.headers.authorization
 *    - Extracts token "abc123xyz"
 *    - Hashes it and looks up session in database
 *    - MODIFIES req object: req.user = { id: '...', email: '...', ... }
 *    - Calls next() to pass control to the next function
 * 
 * 4. Route handler runs: async (req, res) => { ... }
 *    - Receives THE SAME req object (now with req.user attached!)
 *    - TypeScript knows about req.user because we typed it as AuthenticatedRequest
 *    - Can access req.user.id safely
 *    - Sends response with res.json({ courts })
 * 
 * THE KEY INSIGHT:
 * - It's the SAME req object throughout the entire chain
 * - authenticateUser MUTATES req by adding the .user property
 * - The route handler receives the modified req
 * - TypeScript typing (AuthenticatedRequest) just tells TypeScript about the shape
 * 
 * ============================================================================
 * EXAMPLE USAGE IN ROUTE HANDLERS
 * ============================================================================
 * 
 * // 1. Optional auth - allows anonymous or authenticated users
 * router.get('/courts', authenticateUser, async (req: AuthenticatedRequest, res) => {
 *   // Flow: Request → authenticateUser modifies req → your handler receives modified req
 *   // req.user is available if Bearer token provided, undefined if anonymous
 *   const courts = await getCourts(req.user?.id);
 *   res.json({ courts });
 * });
 * 
 * // 2. Required auth - must be logged in (TWO middleware functions!)
 * router.post('/reservations', authenticateUser, requireAuth, async (req: AuthenticatedRequest, res) => {
 *   // Flow: Request → authenticateUser sets req.user → requireAuth checks req.user exists → your handler
 *   // req.user is GUARANTEED to exist here (requireAuth would 401 if not)
 *   const reservation = await createReservation(req.user.id, req.body);
 *   res.json({ reservation });
 * });
 * 
 * // 3. Admin only - must be logged in AND have admin role (THREE functions in the chain!)
 * router.delete('/courts/:id', authenticateUser, requireAdmin, async (req: AuthenticatedRequest, res) => {
 *   // Flow: Request → authenticateUser sets req.user → requireAdmin checks role → your handler
 *   // req.user exists and req.user.role === 'admin' (guaranteed by requireAdmin middleware)
 *   await deleteCourt(req.params.id);
 *   res.json({ success: true });
 * });
 * 
 * WHAT HAPPENS IF NO TOKEN IS PROVIDED?
 * - Example 1: authenticateUser sets req.user = undefined, calls next(), your handler runs with req.user = undefined
 * - Example 2: authenticateUser sets req.user = undefined, requireAuth sees no user, sends 401, STOPS THE CHAIN (never reaches your handler)
 * - Example 3: Same as example 2 - requireAdmin would also send 401 and stop
 */

/**
 * Extends Express Request to include optional authenticated user info.
 * Set by authenticateUser middleware if a valid Bearer token is present and resolves to a user.
 * Use AuthenticatedRequest in route handlers to access req.user, or leave undefined if anonymous.
 */
export interface AuthenticatedRequest extends Request {
  user?: {
    id: string;
    email: string;
    name: string | null;
    role: string;
  };
}

/**
 * Resolve Bearer token to user: hash token, look up session + user, set req.user.
 * No token or invalid/expired → req.user stays undefined or 401. Does not create sessions.
 */
export async function authenticateUser(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): Promise<void> {
  const authHeader = req.headers.authorization;

  // No Bearer token → anonymous; continue with req.user undefined
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    req.user = undefined;
    return next();
  }

  const sessionToken = authHeader.substring(7);
  const tokenHash = crypto.createHash('sha256').update(sessionToken).digest('hex');

  try {
    // Find session and user by token hash
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

    // Reject expired sessions
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

    // Touch session so last_accessed_at is updated
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

/** Require that authenticateUser has set req.user; otherwise 401. Use after authenticateUser. */
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

/** Require req.user and role === 'admin'; otherwise 401 or 403. Use after authenticateUser. */
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
