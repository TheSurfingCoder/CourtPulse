// This file configures the initialization of Sentry on the server.
// The config you add here will be used whenever the server handles a request.
// https://docs.sentry.io/platforms/javascript/guides/nextjs/

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: "https://43488f7a7b85fd5b5c29acacd6dbeb81@o4509916737503237.ingest.us.sentry.io/4510126327070720",
  
  // Environment-based configuration
  environment: process.env.SENTRY_ENVIRONMENT || process.env.NODE_ENV || 'development',

  // Define how likely traces are sampled. Adjust this value in production, or use tracesSampler for greater control.
  tracesSampleRate: 1,

  // Disable logs to avoid conflict with Pino logging
  enableLogs: false,

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
