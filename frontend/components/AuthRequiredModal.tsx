'use client';

import React from 'react';
import { Lock, X } from 'lucide-react';
import Link from 'next/link';

interface AuthRequiredModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function AuthRequiredModal({ isOpen, onClose }: AuthRequiredModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-xl p-6 w-full max-w-sm mx-4">
        <button
          onClick={onClose}
          className="absolute top-3 right-3 text-gray-400 hover:text-gray-600"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="flex flex-col items-center text-center gap-4">
          <div className="bg-orange-100 p-3 rounded-full">
            <Lock className="h-6 w-6 text-orange-500" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-800">Sign in required</h2>
            <p className="text-sm text-gray-500 mt-1">
              You need to sign in to edit courts.
            </p>
          </div>
          <div className="flex gap-3 w-full">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2 text-sm border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50"
            >
              Cancel
            </button>
            <Link
              href="/auth/login"
              className="flex-1 px-4 py-2 text-sm bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-lg text-center hover:opacity-90"
            >
              Sign In
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
