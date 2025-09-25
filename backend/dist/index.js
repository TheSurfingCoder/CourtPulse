"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const cors_1 = __importDefault(require("cors"));
const helmet_1 = __importDefault(require("helmet"));
const dotenv_1 = __importDefault(require("dotenv"));
const swagger_ui_express_1 = __importDefault(require("swagger-ui-express"));
const pino_http_1 = __importDefault(require("pino-http"));
const courts_js_1 = __importDefault(require("./src/routes/courts.js"));
const logs_js_1 = __importDefault(require("./src/routes/logs.js"));
const swagger_js_1 = require("./src/config/swagger.js");
const errorHandler_js_1 = require("./src/middleware/errorHandler.js");
const logger_js_1 = __importStar(require("../shared/logger.js"));
//loads env variables from .env into process.env
dotenv_1.default.config();
// Import migration function
async function runMigrations() {
    try {
        (0, logger_js_1.logLifecycleEvent)('database_migration_started', {
            message: 'Starting database migrations'
        });
        const { exec } = await Promise.resolve().then(() => __importStar(require('child_process')));
        const { promisify } = await Promise.resolve().then(() => __importStar(require('util')));
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
        (0, logger_js_1.logLifecycleEvent)('database_migration_completed', {
            message: 'Database migrations completed successfully',
            output: stdout
        });
    }
    catch (error) {
        (0, logger_js_1.logError)(error instanceof Error ? error : new Error(String(error)), {
            message: 'Database migration failed'
        });
        // Don't exit the process - let the app start anyway
        // This allows the app to run even if migrations fail
    }
}
const app = (0, express_1.default)();
const PORT = process.env.PORT || 5000;
app.use((0, helmet_1.default)());
app.use((0, cors_1.default)({
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
    return (0, pino_http_1.default)({ logger: logger_js_1.default })(req, res, next);
});
app.use(express_1.default.json());
// Swagger API Documentation
//When user visits http://localhost:5000/api-docs swagger UI loads with API docs
//Developers can see all endpoints, test them, and understand API
app.use('/api-docs', swagger_ui_express_1.default.serve, swagger_ui_express_1.default.setup(swagger_js_1.specs));
app.get('/health', (req, res) => {
    res.json({ status: 'OK', timestamp: new Date().toISOString() });
});
app.use('/api/courts', courts_js_1.default);
app.use('/api/logs', logs_js_1.default);
// Error handling middleware (must be last)
app.use(errorHandler_js_1.notFound);
app.use(errorHandler_js_1.errorHandler);
// Start the server with migrations
async function startServer() {
    // Run migrations first
    await runMigrations();
    // Start the server
    app.listen(PORT, () => {
        (0, logger_js_1.logLifecycleEvent)('server_started', {
            message: 'Server started successfully',
            port: PORT,
            environment: process.env.NODE_ENV || 'development'
        });
        (0, logger_js_1.logLifecycleEvent)('api_docs_available', {
            message: 'API documentation available',
            url: `http://localhost:${PORT}/api-docs`
        });
    });
}
// Start the application
startServer().catch((error) => {
    (0, logger_js_1.logError)(error instanceof Error ? error : new Error(String(error)), {
        message: 'Failed to start server'
    });
    process.exit(1);
});
//# sourceMappingURL=index.js.map