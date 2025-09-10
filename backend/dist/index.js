import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import dotenv from 'dotenv';
import swaggerUi from 'swagger-ui-express';
import courtRoutes from './src/routes/courts.js';
import { specs } from './src/config/swagger.js';
import { errorHandler, notFound } from './src/middleware/errorHandler.js';
//loads env variables from .env into process.env
dotenv.config();
// Import migration function
async function runMigrations() {
    try {
        console.log(JSON.stringify({
            level: 'info',
            message: 'Starting database migrations',
            timestamp: new Date().toISOString()
        }));
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
        const { stdout } = await execAsync('npx node-pg-migrate up -m database/migrations -j sql', { env });
        console.log(JSON.stringify({
            level: 'info',
            message: 'Database migrations completed successfully',
            output: stdout,
            timestamp: new Date().toISOString()
        }));
    }
    catch (error) {
        console.error(JSON.stringify({
            level: 'error',
            message: 'Database migration failed',
            error: error instanceof Error ? error.message : 'Unknown error',
            timestamp: new Date().toISOString()
        }));
        // Don't exit the process - let the app start anyway
        // This allows the app to run even if migrations fail
    }
}
const app = express();
const PORT = process.env.PORT || 5000;
app.use(helmet());
app.use(cors());
app.use(morgan('combined'));
app.use(express.json());
// Swagger API Documentation
//When user visits http://localhost:5000/api-docs swagger UI loads with API docs
//Developers can see all endpoints, test them, and understand API
app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(specs));
app.get('/health', (req, res) => {
    res.json({ status: 'OK', timestamp: new Date().toISOString() });
});
app.use('/api/courts', courtRoutes);
// Error handling middleware (must be last)
app.use(notFound);
app.use(errorHandler);
// Start the server with migrations
async function startServer() {
    // Run migrations first
    await runMigrations();
    // Start the server
    app.listen(PORT, () => {
        console.log(JSON.stringify({
            level: 'info',
            message: 'Server started successfully',
            port: PORT,
            environment: process.env.NODE_ENV || 'development',
            timestamp: new Date().toISOString()
        }));
        console.log(JSON.stringify({
            level: 'info',
            message: 'API documentation available',
            url: `http://localhost:${PORT}/api-docs`,
            timestamp: new Date().toISOString()
        }));
    });
}
// Start the application
startServer().catch((error) => {
    console.error(JSON.stringify({
        level: 'error',
        message: 'Failed to start server',
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date().toISOString()
    }));
    process.exit(1);
});
//# sourceMappingURL=index.js.map