'use client';

import React from 'react';
import Link from 'next/link';
import { Activity } from 'lucide-react';
import { useAuth } from '../lib/auth/AuthContext';

export default function Header() {
  const { user, isLoading, logout } = useAuth();

  return (
    <header className="bg-white shadow-sm border-b border-gray-200 px-4 py-3">
      <div className="flex items-center">
        <div className="flex items-center gap-2">
          <div className="bg-gradient-to-r from-orange-500 to-red-500 p-2 rounded-lg shadow-sm">
            <Activity className="h-5 w-5 text-white" />
          </div>
          <h1 className="text-xl font-bold text-gray-800">CourtPulse</h1>
        </div>
        <p className="ml-4 text-sm text-gray-500 hidden sm:block">
          Discover and explore sports courts near you
        </p>
        <div className="ml-auto flex items-center gap-3">
          {!isLoading && (
            user ? (
              <>
                <span className="text-sm text-gray-600 hidden sm:block">{user.email}</span>
                <button
                  onClick={() => logout()}
                  className="text-sm text-gray-500 hover:text-gray-800 border border-gray-200 px-3 py-1.5 rounded-lg hover:bg-gray-50"
                >
                  Sign out
                </button>
              </>
            ) : (
              <Link
                href="/auth/login"
                className="text-sm font-medium bg-gradient-to-r from-orange-500 to-red-500 text-white px-3 py-1.5 rounded-lg hover:opacity-90"
              >
                Sign in
              </Link>
            )
          )}
        </div>
      </div>
    </header>
  );
}
