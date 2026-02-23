import * as Sentry from "@sentry/node";
import { nodeProfilingIntegration } from "@sentry/profiling-node";
import { ValidationException, NotFoundException } from "./src/exceptions/index.js";

// Ensure to call this before importing any other modules!
Sentry.init({
  dsn: process.env.SENTRY_DSN,

  environment: process.env.SENTRY_ENVIRONMENT || process.env.NODE_ENV || 'development',

  release: `backend@${process.env.npm_package_version || '1.1.0'}`,

  // Adds request headers and IP for users
  sendDefaultPii: true,

  integrations: [
    nodeProfilingIntegration(),
    // Only forward warnings and errors to Sentry, not general console.log noise
    Sentry.consoleLoggingIntegration({ levels: ["warn", "error"] }),
  ],

  tracesSampleRate: process.env.NODE_ENV === 'production' ? 0.1 : 1.0,

  profilesSampleRate: process.env.NODE_ENV === 'production' ? 0.1 : 1.0,

  enableLogs: true,

  beforeSend(event, hint) {
    // Drop all events in development — prevents dev noise from reaching Sentry
    if (process.env.SENTRY_ENVIRONMENT === 'development' || process.env.NODE_ENV === 'development') {
      return null;
    }

    // Drop user errors (400/404) — these are not bugs, they are expected client mistakes
    const err = hint.originalException;
    if (err instanceof ValidationException || err instanceof NotFoundException) {
      return null;
    }

    return event;
  },
});
