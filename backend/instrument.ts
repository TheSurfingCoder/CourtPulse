import dotenv from "dotenv";
dotenv.config();
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
    // Drop user errors (400/404) — these are not bugs, they are expected client mistakes
    const err = hint.originalException;
    if (err instanceof ValidationException || err instanceof NotFoundException) {
      return null;
    }

    return event;
  },

  beforeSendLog(log) {
    // Drop Node.js deprecation warnings from Sentry's own dependencies (e.g. DEP0169 url.parse)
    if (log.message?.includes('DEP0169') || log.message?.includes('url.parse')) {
      return null;
    }

    return log;
  },
});
