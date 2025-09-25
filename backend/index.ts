import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import dotenv from 'dotenv';
import swaggerUi from 'swagger-ui-express';
import pinoHttp from 'pino-http';

import courtRoutes from './src/routes/courts.js';
import logRoutes from './src/routes/logs.js';
import { specs } from './src/config/swagger.js';
import { errorHandler, notFound } from './src/middleware/errorHandler.js';
import logger, { logEvent, logError, logLifecycleEvent } from '../shared/logger.js';

//loads env variables from .env into process.env
dotenv.config();

// Import migration function
async function runMigrations() {
  try {
    logLifecycleEvent('database_migration_started', {
      message: 'Starting database migrations'
    });

    const { exec } = await import('child_process');
    const { promisify } = await import('util');
    const execAsync = promisify(exec);

    // Construct DATABASE_URL from individual environment variables
    const dbHost = process.env.DB_HOST;
    const dbPort = process.env.DB_PORT;
    const dbName = process.env.DB_NAME;
    const dbUser = process.env.DB_USER;
    const dbPassword = process.env.DB_PASSWORD;

    if (!dbHost || !dbPort || !dbName || !dbUser || !dbPassword) {
      throw new Error('Missing required database environment variables');
    }

    const databaseUrl = `postgresql://${dbUser}:${dbPassword}@${dbHost}:${dbPort}/${dbName}`;
    
    // Set DATABASE_URL environment variable for the migration command
    const env = { ...process.env, DATABASE_URL: databaseUrl };

    // Run migrations using node-pg-migrate
    const { stdout } = await execAsync('npx node-pg-migrate up -c migrate.json', { env });

    logLifecycleEvent('database_migration_completed', {
      message: 'Database migrations completed successfully',
      output: stdout
    });

  } catch (error) {
    logError(error instanceof Error ? error : new Error(String(error)), {
      message: 'Database migration failed'
    });

    // Don't exit the process - let the app start anyway
    // This allows the app to run even if migrations fail
  }
}

const app = express();
const PORT = process.env.PORT || 5000;

app.use(helmet());
app.use(cors({
  origin: ['http://localhost:3000', 'http://127.0.0.1:3000'],
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

// Error handling middleware (must be last)
app.use(notFound);
app.use(errorHandler);

// Start the server with migrations
async function startServer() {
  // Run migrations first
  await runMigrations();

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


