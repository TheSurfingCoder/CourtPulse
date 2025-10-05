import * as Sentry from "@sentry/node";
// profiling
import { nodeProfilingIntegration } from "@sentry/profiling-node";

// Ensure to call this before importing any other modules!
Sentry.init({
  dsn: process.env.SENTRY_DSN,
  
  // Environment-based configuration
  environment: process.env.SENTRY_ENVIRONMENT || process.env.NODE_ENV || 'development',
  
  // Adds request headers and IP for users, for more info visit:
  // https://docs.sentry.io/platforms/javascript/guides/node/configuration/options/#sendDefaultPii
  sendDefaultPii: true,
  
  // profiling
  integrations: [
    // Add our Profiling integration
    nodeProfilingIntegration(),
  ],
  
  // performance
  // Set tracesSampleRate to 1.0 to capture 100%
  // of transactions for tracing.
  // We recommend adjusting this value in production
  tracesSampleRate: (process.env.NODE_ENV === 'production' || process.env.NODE_ENV === 'staging') ? 0.1 : 1.0,
  
  // profiling
  // Set profilesSampleRate to 1.0 to profile 100%
  // of sampled transactions.
  // This is relative to tracesSampleRate
  profilesSampleRate: (process.env.NODE_ENV === 'production' || process.env.NODE_ENV === 'staging') ? 0.1 : 1.0,
  
  // logs
  // Enable logs to be sent to Sentry
  enableLogs: true,
  
  // Disable Sentry in development environment
  beforeSend(event) {
    if (process.env.SENTRY_ENVIRONMENT === "development" || process.env.NODE_ENV === "development") {
      return null; // Drop event in development
    }
    return event;
  },
});
