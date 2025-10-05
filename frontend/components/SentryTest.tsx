'use client';

import { useState } from 'react';
import * as Sentry from '@sentry/nextjs';

export default function SentryTest() {
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const testBackendError = async () => {
    setIsLoading(true);
    setResult(null);

    try {
      console.log('Testing backend error endpoint...');
      
      // Add some frontend context
      Sentry.setContext('frontend_test', {
        component: 'SentryTest',
        action: 'test_backend_error',
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent
      });

      const response = await fetch('/api/test/error', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setResult(`Success: ${JSON.stringify(data)}`);
    } catch (error) {
      console.error('Frontend caught error:', error);
      
      // Capture the error in Sentry from frontend perspective
      Sentry.captureException(error);
      
      setResult(`Error caught: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsLoading(false);
    }
  };

  const testFrontendError = () => {
    console.log('Throwing frontend error for Sentry...');
    
    // Add context before throwing
    Sentry.setContext('frontend_error_test', {
      component: 'SentryTest',
      action: 'throw_frontend_error',
      timestamp: new Date().toISOString()
    });

    // Throw a frontend error
    throw new Error('This is a frontend test error for Sentry!');
  };

  const testSuccessEndpoint = async () => {
    setIsLoading(true);
    setResult(null);

    try {
      console.log('Testing success endpoint...');
      
      const response = await fetch('/api/test/success', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setResult(`Success: ${JSON.stringify(data)}`);
    } catch (error) {
      console.error('Error calling success endpoint:', error);
      setResult(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="p-6 bg-white rounded-lg shadow-md max-w-md mx-auto">
      <h2 className="text-xl font-bold mb-4 text-gray-800">Sentry Test Panel</h2>
      
      <div className="space-y-3">
        <button
          onClick={testBackendError}
          disabled={isLoading}
          className="w-full px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Testing...' : 'Test Backend Error (Distributed Tracing)'}
        </button>

        <button
          onClick={testFrontendError}
          className="w-full px-4 py-2 bg-orange-600 text-white rounded hover:bg-orange-700"
        >
          Test Frontend Error
        </button>

        <button
          onClick={testSuccessEndpoint}
          disabled={isLoading}
          className="w-full px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Testing...' : 'Test Success Endpoint'}
        </button>
      </div>

      {result && (
        <div className="mt-4 p-3 bg-gray-100 rounded">
          <p className="text-sm text-gray-700">{result}</p>
        </div>
      )}

      <div className="mt-4 text-xs text-gray-500">
        <p>• Backend Error: Tests distributed tracing through frontend → backend</p>
        <p>• Frontend Error: Tests client-side error capture</p>
        <p>• Success Endpoint: Verifies API connectivity</p>
      </div>
    </div>
  );
}
