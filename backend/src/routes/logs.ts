import express from 'express';
import { logEvent, logError, logBusinessEvent } from '../../../shared/logger.js';

const router = express.Router();

// POST /api/logs - Receive logs from frontend (development only)
router.post('/', async (req: express.Request, res: express.Response) => {
  // Only process logs in development
  if (process.env.NODE_ENV !== 'development') {
    return res.status(404).json({ success: false, message: 'Not found' });
  }
  
  try {
    const { event, data, level = 'info' } = req.body;
    
    // Forward to Pino logger with frontend prefix
    if (level === 'error') {
      logError(new Error(data.message || 'Frontend error'), {
        source: 'frontend',
        ...data
      });
    } else {
      logEvent(event, {
        source: 'frontend',
        ...data
      });
    }
    
    res.json({ success: true });
  } catch (error) {
    logError(error instanceof Error ? error : new Error(String(error)), {
      message: 'Failed to process frontend log'
    });
    res.status(500).json({ success: false });
  }
});

export default router;
