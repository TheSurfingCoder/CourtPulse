import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import dotenv from 'dotenv';


import courtRoutes from './src/routes/courts'

dotenv.config();


const app = express();
const PORT = process.env.PORT || 3003;

app.use(helmet());
app.use(cors());
app.use(morgan('combined'));
app.use(express.json());


app.get('/health', (req: express.Request, res: express.Response) => {
    res.json({ status: 'OK', timestamp: new Date().toISOString() });
  });

app.use('/api/courts', courtRoutes)


app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
  });


