'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { getMe, logoutSession, type AuthUser } from '../api/authApi';
import {
  getStoredToken,
  setStoredToken,
  clearStoredToken,
  getStoredUser,
  setStoredUser,
  clearStoredUser,
} from './storage';

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  isLoading: boolean;
  login: (token: string, user: AuthUser) => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const storedToken = getStoredToken();
    if (!storedToken) {
      setIsLoading(false);
      return;
    }

    // Optimistically restore user from localStorage, then validate with server
    const storedUser = getStoredUser();
    if (storedUser) {
      setUser(storedUser);
      setToken(storedToken);
    }

    getMe(storedToken)
      .then((freshUser) => {
        setUser(freshUser);
        setToken(storedToken);
        setStoredUser(freshUser);
      })
      .catch(() => {
        // Token invalid or expired — clear everything
        clearStoredToken();
        clearStoredUser();
        setUser(null);
        setToken(null);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  const login = useCallback((newToken: string, newUser: AuthUser) => {
    setStoredToken(newToken);
    setStoredUser(newUser);
    setToken(newToken);
    setUser(newUser);
  }, []);

  const logout = useCallback(async () => {
    const currentToken = getStoredToken();
    if (currentToken) {
      await logoutSession(currentToken);
    }
    clearStoredToken();
    clearStoredUser();
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
