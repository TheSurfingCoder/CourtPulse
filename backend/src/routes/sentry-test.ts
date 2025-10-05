import express from 'express';
import * as Sentry from '@sentry/node';

const router = express.Router();

// Test endpoint that throws an error for Sentry testing
router.get('/error', (req, res) => {
  console.log('Test error endpoint called');
  
  // Add some context to the error
  Sentry.setContext('test_endpoint', {
    endpoint: '/api/test/error',
    timestamp: new Date().toISOString(),
    userAgent: req.headers['user-agent'],
    ip: req.ip
  });

  // Throw a test error
  const error = new Error('This is a test error for Sentry distributed tracing!');
  error.name = 'TestError';
  
  // Capture the error with Sentry
  Sentry.captureException(error);
  
  // Also throw it to trigger the error handler
  throw error;
});

// Test endpoint that returns success (for comparison)
router.get('/success', (req, res) => {
  res.json({ 
    message: 'Test endpoint working correctly',
    timestamp: new Date().toISOString(),
    environment: process.env.NODE_ENV || 'development'
  });
});

export default router;
