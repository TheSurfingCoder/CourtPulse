// This file configures the initialization of Sentry for edge features (middleware, edge routes, and so on).
// The config you add here will be used whenever one of the edge features is loaded.
// Note that this config is unrelated to the Vercel Edge Runtime and is also required when running locally.
// https://docs.sentry.io/platforms/javascript/guides/nextjs/

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: "https://43488f7a7b85fd5b5c29acacd6dbeb81@o4509916737503237.ingest.us.sentry.io/4510126327070720",
  
  // Environment-based configuration
  environment: process.env.SENTRY_ENVIRONMENT || process.env.NODE_ENV || 'development',

  //determines the release of the code that is being deployed. This will show up in the Sentry dashboard.
  release: process.env.npm_package_version,

  // Define how likely traces are sampled. Adjust this value in production, or use tracesSampler for greater control.
  tracesSampleRate: 1,

  // Enable logs to be sent to Sentry
  enableLogs: true,

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
