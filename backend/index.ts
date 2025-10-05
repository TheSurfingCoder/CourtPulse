// Import this first!
import "./instrument.js";
// Now import other modules
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import dotenv from 'dotenv';
import swaggerUi from 'swagger-ui-express';
import pinoHttp from 'pino-http';
import * as Sentry from '@sentry/node';

import courtRoutes from './src/routes/courts.js';
import logRoutes from './src/routes/logs.js';
import { specs } from './src/config/swagger.js';
import { errorHandler, notFound } from './src/middleware/errorHandler.js';
import logger, { logEvent, logError, logLifecycleEvent } from './logger';

//loads env variables from .env into process.env
dotenv.config();


const app = express();
const PORT = process.env.PORT || 5000;

app.use(helmet());
// CORS configuration with environment-based origins
const allowedOrigins: string[] = [];

// Add origins from CORS_ORIGIN environment variable (comma-separated)
if (process.env.CORS_ORIGIN) {
  const corsOrigins = process.env.CORS_ORIGIN.split(',').map(origin => origin.trim());
  allowedOrigins.push(...corsOrigins);
}

// Add production origins (always included)
const productionOrigins = [
  'https://courtpulse-staging.vercel.app',
  'https://courtpulse.vercel.app'
];
allowedOrigins.push(...productionOrigins);

// Legacy support for FRONTEND_URL
if (process.env.FRONTEND_URL) {
  allowedOrigins.push(process.env.FRONTEND_URL);
}

// CORS debugging middleware
app.use((req, res, next) => {
  const origin = req.headers.origin;
  logEvent('cors_request_received', {
    origin,
    allowedOrigins,
    isAllowed: allowedOrigins.includes(origin || ''),
    method: req.method,
    url: req.url
  });
  next();
});

app.use(cors({
  origin: allowedOrigins,
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));

// Custom middleware to skip pino-http for /api/logs
app.use((req, res, next) => {
  if (req.url === '/api/logs') {
    // Skip pino-http for log forwarding endpoint
    return next();
  }
  // Use pino-http for all other routes
  return pinoHttp({ logger })(req, res, next);
});

app.use(express.json());

// Swagger API Documentation
//When user visits http://localhost:5000/api-docs swagger UI loads with API docs
//Developers can see all endpoints, test them, and understand API
app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(specs));

app.get('/health', (req: express.Request, res: express.Response) => {
    res.json({ status: 'OK', timestamp: new Date().toISOString() });
  });

app.use('/api/courts', courtRoutes);
app.use('/api/logs', logRoutes);

// Sentry error handler must be registered before any other error-handling middlewares
Sentry.setupExpressErrorHandler(app);

// Error handling middleware (must be last)
app.use(notFound);
app.use(errorHandler);

// Start the server
async function startServer() {
  // Start the server
  app.listen(PORT, () => {
    logLifecycleEvent('server_started', {
      message: 'Server started successfully',
      port: PORT,
      environment: process.env.NODE_ENV || 'development'
    });
    logLifecycleEvent('api_docs_available', {
      message: 'API documentation available',
      url: `http://localhost:${PORT}/api-docs`
    });
  });
}

// Start the application
startServer().catch((error) => {
  logError(error instanceof Error ? error : new Error(String(error)), {
    message: 'Failed to start server'
  });
  process.exit(1);
});


