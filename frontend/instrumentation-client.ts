// This file configures the initialization of Sentry on the client.
// The added config here will be used whenever a users loads a page in their browser.
// https://docs.sentry.io/platforms/javascript/guides/nextjs/

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  
  // Environment-based configuration
  environment: process.env.SENTRY_ENVIRONMENT || process.env.NODE_ENV || 'development',
  
  // Explicit release identifier for frontend client-side
  release: `client@${process.env.npm_package_version || '1.2.0'}`,

  // Add optional integrations for additional features
  integrations: [
    Sentry.replayIntegration(),
    // Console logging integration - send console.log, console.warn, and console.error to Sentry
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

  // Define how likely Replay events are sampled.
  // This sets the sample rate to be 10%. You may want this to be 100% while
  // in development and sample at a lower rate in production
  replaysSessionSampleRate: 0.1,

  // Define how likely Replay events are sampled when an error occurs.
  replaysOnErrorSampleRate: 1.0,

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

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;