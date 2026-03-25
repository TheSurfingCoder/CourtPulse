'use client';

import * as Sentry from '@sentry/nextjs';
import { useEffect } from 'react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center h-screen gap-4 text-center px-4">
      <h2 className="text-xl font-semibold text-gray-800">Something went wrong</h2>
      <p className="text-sm text-gray-500 max-w-sm">
        An unexpected error occurred. Try again, or refresh the page if the problem persists.
      </p>
      <button
        onClick={reset}
        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
      >
        Try again
      </button>
    </div>
  );
}
