'use client';

// TEMPORARY - remove before deploying to production
import * as Sentry from '@sentry/nextjs';
import { useState } from 'react';

function BrokenComponent(): never {
  throw new Error('Test render error — caught by error.tsx');
}

export default function TestErrorPage() {
  const [triggerRenderError, setTriggerRenderError] = useState(false);

  const handleUnhandledRejection = () => {
    Promise.reject(new Error('Test unhandled rejection — caught by window.onunhandledrejection'));
  };

  const handleManualCapture = () => {
    try {
      throw new Error('Test manual captureException');
    } catch (err) {
      Sentry.captureException(err, {
        tags: { component: 'TestErrorPage', action: 'manual_capture' },
      });
      alert('Captured — check Sentry for "Test manual captureException"');
    }
  };

  const handleUnhandledError = () => {
    setTimeout(() => {
      throw new Error('Test uncaught exception — caught by window.onerror');
    }, 0);
  };

  if (triggerRenderError) {
    return <BrokenComponent />;
  }

  return (
    <div style={{ padding: '2rem', fontFamily: 'monospace', display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: '480px' }}>
      <h1 style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>Sentry Error Tests</h1>
      <p style={{ fontSize: '0.875rem', color: '#666' }}>Each button tests a different capture path. Check Sentry after each.</p>

      <button onClick={handleManualCapture} style={btnStyle('#2563eb')}>
        1. Manual captureException
      </button>

      <button onClick={handleUnhandledRejection} style={btnStyle('#7c3aed')}>
        2. Unhandled promise rejection (window.onunhandledrejection)
      </button>

      <button onClick={handleUnhandledError} style={btnStyle('#d97706')}>
        3. Uncaught exception (window.onerror)
      </button>

      <button onClick={() => setTriggerRenderError(true)} style={btnStyle('#dc2626')}>
        4. Render error → error.tsx (shows fallback UI)
      </button>
    </div>
  );
}

function btnStyle(bg: string): React.CSSProperties {
  return {
    backgroundColor: bg,
    color: 'white',
    padding: '0.75rem 1rem',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '0.875rem',
    textAlign: 'left',
  };
}
