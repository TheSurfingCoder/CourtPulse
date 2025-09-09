import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import dotenv from 'dotenv';
import swaggerUi from 'swagger-ui-express';

import courtRoutes from './src/routes/courts';
import { specs } from './src/config/swagger';
import { errorHandler, notFound } from './src/middleware/errorHandler';

//loads env variables from .env into process.env
dotenv.config();

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

app.get('/health', (req: express.Request, res: express.Response) => {
    res.json({ status: 'OK', timestamp: new Date().toISOString() });
  });

app.use('/api/courts', courtRoutes);

// Error handling middleware (must be last)
app.use(notFound);
app.use(errorHandler);

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


