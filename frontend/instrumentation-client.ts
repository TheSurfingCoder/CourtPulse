// This file configures the initialization of Sentry on the client.
// The added config here will be used whenever a users loads a page in their browser.
// https://docs.sentry.io/platforms/javascript/guides/nextjs/

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: "https://43488f7a7b85fd5b5c29acacd6dbeb81@o4509916737503237.ingest.us.sentry.io/4510126327070720",
  
  // Environment-based configuration
  environment: process.env.SENTRY_ENVIRONMENT || process.env.NODE_ENV || 'development',

  // Add optional integrations for additional features
  integrations: [
    Sentry.replayIntegration(),
  ],

  // Define how likely traces are sampled. Adjust this value in production, or use tracesSampler for greater control.
  tracesSampleRate: 1,
  // Disable logs to avoid conflict with Pino logging
  enableLogs: false,

  // Define how likely Replay events are sampled.
  // This sets the sample rate to be 10%. You may want this to be 100% while
  // in development and sample at a lower rate in production
  replaysSessionSampleRate: 0.1,

  // Define how likely Replay events are sampled when an error occurs.
  replaysOnErrorSampleRate: 1.0,

  // Setting this option to true will print useful information to the console while you're setting up Sentry.
  debug: false,

  // Disable Sentry in development environment
  beforeSend(event) {
    if (process.env.SENTRY_ENVIRONMENT === "development" || process.env.NODE_ENV === "development") {
      return null; // Drop event in development
    }
    return event;
  },
});

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;