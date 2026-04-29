'use client';

import React, { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Activity } from 'lucide-react';
import { useAuth } from '../../../lib/auth/AuthContext';
import { verifyMagicLink } from '../../../lib/api/authApi';
import { APIError } from '../../../lib/api/exceptions';

type State = 'verifying' | 'error';

export default function VerifyMagicLinkPage() {
  const { login } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [state, setState] = useState<State>('verifying');
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    const token = searchParams.get('token');
    if (!token) {
      setErrorMessage('No token found in the link. Please request a new one.');
      setState('error');
      return;
    }

    verifyMagicLink(token)
      .then((session) => {
        login(session.token, session.user);
        router.replace('/');
      })
      .catch((error) => {
        if (error instanceof APIError && error.statusCode === 401) {
          setErrorMessage('This link has expired or already been used. Please request a new one.');
        } else {
          setErrorMessage('Something went wrong. Please try again.');
        }
        setState('error');
      });
  }, [searchParams, login, router]);

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 w-full max-w-sm text-center">
        <div className="flex items-center justify-center gap-2 mb-6">
          <div className="bg-gradient-to-r from-orange-500 to-red-500 p-2 rounded-lg shadow-sm">
            <Activity className="h-5 w-5 text-white" />
          </div>
          <span className="text-xl font-bold text-gray-800">CourtPulse</span>
        </div>

        {state === 'verifying' && (
          <>
            <div className="w-6 h-6 border-2 border-orange-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-sm text-gray-500">Signing you in…</p>
          </>
        )}

        {state === 'error' && (
          <>
            <h1 className="text-lg font-semibold text-gray-800 mb-2">Link invalid</h1>
            <p className="text-sm text-gray-500 mb-4">{errorMessage}</p>
            <Link
              href="/auth/login"
              className="inline-block px-4 py-2 text-sm font-medium bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-lg hover:opacity-90"
            >
              Request a new link
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
