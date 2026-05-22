import { APIError, NetworkError, parseAPIError } from './exceptions';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001';

export interface AuthUser {
  id: string;
  email: string;
  name: string | null;
  role: 'contributor' | 'admin';
}

export interface AuthSession {
  token: string;
  expiresAt: string;
  user: AuthUser;
}

export async function requestMagicLink(email: string): Promise<void> {
  try {
    const response = await fetch(`${API_URL}/api/auth/magic-link`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw parseAPIError(response.status, data);
    }
  } catch (error) {
    if (error instanceof APIError) throw error;
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new NetworkError('Unable to connect to server.');
    }
    throw new NetworkError('An unexpected error occurred');
  }
}

export async function verifyMagicLink(token: string): Promise<AuthSession> {
  try {
    const response = await fetch(
      `${API_URL}/api/auth/verify-magic-link?token=${encodeURIComponent(token)}`,
      { method: 'GET', headers: { 'Content-Type': 'application/json' } }
    );
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw parseAPIError(response.status, data);
    }
    const result = await response.json();
    if (!result.success || !result.token || !result.user) {
      throw new APIError('Invalid response from server', 'INVALID_RESPONSE', 500);
    }
    return { token: result.token, expiresAt: result.expiresAt, user: result.user };
  } catch (error) {
    if (error instanceof APIError) throw error;
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new NetworkError('Unable to connect to server.');
    }
    throw new NetworkError('An unexpected error occurred');
  }
}

export async function getMe(sessionToken: string): Promise<AuthUser> {
  try {
    const response = await fetch(`${API_URL}/api/auth/me`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${sessionToken}`,
      },
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw parseAPIError(response.status, data);
    }
    const result = await response.json();
    return result.user as AuthUser;
  } catch (error) {
    if (error instanceof APIError) throw error;
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new NetworkError('Unable to connect to server.');
    }
    throw new NetworkError('An unexpected error occurred');
  }
}

export async function logoutSession(sessionToken: string): Promise<void> {
  try {
    await fetch(`${API_URL}/api/auth/logout`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${sessionToken}`,
      },
    });
  } catch {
    // Best-effort — client clears local state regardless
  }
}
