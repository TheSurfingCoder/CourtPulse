// This file configures the initialization of Sentry on the server.
// The config you add here will be used whenever the server handles a request.
// https://docs.sentry.io/platforms/javascript/guides/nextjs/

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  
  // Environment-based configuration
  environment: process.env.SENTRY_ENVIRONMENT || process.env.NODE_ENV || 'development',
  
  // Explicit release identifier for frontend server-side
  release: `frontend@${process.env.npm_package_version || '1.2.0'}`,

  integrations: [
    Sentry.consoleLoggingIntegration({ levels: ["warn", "error"] }),
  ],

  // Define how likely traces are sampled. Adjust this value in production, or use tracesSampler for greater control.
  tracesSampleRate: 1,

  // Enable distributed tracing - propagate trace headers to backend
  tracePropagationTargets: [
    "localhost",
    /^https:\/\/courtpulse-backend\.onrender\.com/,
  ],

  // Enable logs to be sent to Sentry
  enableLogs: true,

  debug: false,
});
