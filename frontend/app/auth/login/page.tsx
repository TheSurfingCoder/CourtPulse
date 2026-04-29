'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Activity } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '../../../lib/auth/AuthContext';
import { requestMagicLink } from '../../../lib/api/authApi';
import { APIError } from '../../../lib/api/exceptions';

export default function LoginPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!isLoading && user) {
      router.replace('/');
    }
  }, [isLoading, user, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    setSubmitting(true);
    try {
      await requestMagicLink(email.trim().toLowerCase());
      setSent(true);
    } catch (error) {
      if (error instanceof APIError) {
        toast.error('Failed to send link', { description: error.message });
      } else {
        toast.error('Unable to connect to server. Please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (isLoading) return null;

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 w-full max-w-sm">
        <div className="flex items-center gap-2 mb-6">
          <div className="bg-gradient-to-r from-orange-500 to-red-500 p-2 rounded-lg shadow-sm">
            <Activity className="h-5 w-5 text-white" />
          </div>
          <span className="text-xl font-bold text-gray-800">CourtPulse</span>
        </div>

        {sent ? (
          <div className="text-center">
            <h1 className="text-lg font-semibold text-gray-800 mb-2">Check your email</h1>
            <p className="text-sm text-gray-500">
              We sent a sign-in link to <span className="font-medium text-gray-700">{email}</span>.
              Click it to sign in — it expires in 15 minutes.
            </p>
            <button
              onClick={() => setSent(false)}
              className="mt-4 text-sm text-orange-500 hover:underline"
            >
              Use a different email
            </button>
          </div>
        ) : (
          <>
            <h1 className="text-lg font-semibold text-gray-800 mb-1">Sign in</h1>
            <p className="text-sm text-gray-500 mb-5">
              Enter your email and we&apos;ll send you a sign-in link.
            </p>
            <form onSubmit={handleSubmit} className="flex flex-col gap-3">
              <input
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-400"
              />
              <button
                type="submit"
                disabled={submitting}
                className="w-full py-2 text-sm font-medium bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-lg hover:opacity-90 disabled:opacity-60"
              >
                {submitting ? 'Sending…' : 'Send sign-in link'}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
