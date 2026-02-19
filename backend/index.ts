// Import this first!
import "./instrument.js";
// Now import other modules
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import dotenv from 'dotenv';
import swaggerUi from 'swagger-ui-express';

import courtRoutes from './src/routes/courts.js';
import authRoutes from './src/routes/auth.js';
import { specs } from './src/config/swagger.js';
import { errorHandler, notFound } from './src/middleware/errorHandler.js';

//loads env variables from .env into process.env
dotenv.config();

const app = express(); 
const PORT = process.env.PORT || 5001;

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
  'https://courtpulse.vercel.app',
  'https://courtpulse.vercel.app', 
  'https://courtpulse.app'
];
allowedOrigins.push(...productionOrigins);

// Legacy support for FRONTEND_URL
if (process.env.FRONTEND_URL) {
  allowedOrigins.push(process.env.FRONTEND_URL);
}


app.use(cors({
  origin: allowedOrigins,
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'sentry-trace', 'baggage']
}));

app.use(express.json());

// Swagger API Documentation
//When user visits http://localhost:5001/api-docs swagger UI loads with API docs
//Developers can see all endpoints, test them, and understand API
app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(specs));

app.get('/health', (req: express.Request, res: express.Response) => {
    res.json({ status: 'OK', timestamp: new Date().toISOString() });
  });

app.use('/api/auth', authRoutes);
app.use('/api/courts', courtRoutes);

// Error handling middleware (must be last)
app.use(notFound);
app.use(errorHandler);

// Start the server
app.listen(PORT, () => {
  console.log(`Server started on port ${PORT} (${process.env.NODE_ENV || 'development'})`);
  console.log(`API docs: http://localhost:${PORT}/api-docs`);
});


