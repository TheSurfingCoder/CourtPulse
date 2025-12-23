// This file configures the initialization of Sentry for edge features (middleware, edge routes, and so on).
// The config you add here will be used whenever one of the edge features is loaded.
// Note that this config is unrelated to the Vercel Edge Runtime and is also required when running locally.
// https://docs.sentry.io/platforms/javascript/guides/nextjs/

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  
  // Environment-based configuration
  environment: process.env.SENTRY_ENVIRONMENT || process.env.NODE_ENV || 'development',

  // Explicit release identifier for frontend edge-side
  release: `edge@${process.env.npm_package_version || '1.2.0'}`,

  // Console logging integration - send console.log, console.warn, and console.error to Sentry
  integrations: [
    Sentry.consoleLoggingIntegration({ levels: ["log", "warn", "error"] }),
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

  // Setting this option to true will print useful information to the console while you're setting up Sentry.
  debug: false,

  // Disable Sentry in development environment
  // TODO: Uncomment after testing to disable dev events
  // beforeSend(event) {
  //   if (process.env.SENTRY_ENVIRONMENT === "development" || process.env.NODE_ENV === "development") {
  //     return null; // Drop event in development
  //   }
  //   return event;
  // },
});
