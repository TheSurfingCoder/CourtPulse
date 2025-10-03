import pino from 'pino';

// Environment-based configuration
const isDevelopment = process.env.NODE_ENV === 'development';
const isProduction = process.env.NODE_ENV === 'production';

// No-op functions for production
const noOpLogEvent = (event: string, data: Record<string, any> = {}) => {
  // No-op in production
};

const noOpLogError = (error: Error, context: Record<string, any> = {}) => {
  // No-op in production
};

const noOpLogBusinessEvent = (event: string, data: Record<string, any> = {}) => {
  // No-op in production
};

const noOpLogLifecycleEvent = (event: string, data: Record<string, any> = {}) => {
  // No-op in production
};

const noOpLogger = {
  info: () => {},
  error: () => {},
  warn: () => {},
  debug: () => {},
};

// Development configuration
const baseConfig = {
  level: process.env.LOG_LEVEL || 'debug',
  timestamp: pino.stdTimeFunctions.isoTime,
  formatters: {
    level: (label: string) => {
      return { level: label };
    },
  },
  serializers: {
    req: pino.stdSerializers.req,
    res: pino.stdSerializers.res,
    err: pino.stdSerializers.err,
  },
};

const developmentConfig = {
  ...baseConfig,
  // Removed pino-pretty transport to avoid worker thread conflicts with Sentry
};

// Create logger based on environment
const logger = isProduction ? noOpLogger : pino(developmentConfig);

// Function to send logs to backend (development only)
const sendToBackend = async (event: string, data: Record<string, any>, level: string = 'info') => {
  if (isProduction) return;
  
  try {
    await fetch('/api/logs', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ event, data, level }),
    });
  } catch (error) {
    // Silently fail in development - don't spam console
    // console.error('Failed to send log to backend:', error);
  }
};

// Export functions based on environment
export const logEvent = isProduction ? noOpLogEvent : (event: string, data: Record<string, any> = {}) => {
  // Log to browser console
  logger.info({
    event,
    timestamp: new Date().toISOString(),
    ...data,
  });
  
  // Send to backend (async, don't wait)
  sendToBackend(event, data, 'info');
};

export const logError = isProduction ? noOpLogError : (error: Error, context: Record<string, any> = {}) => {
  // Log to browser console
  logger.error({
    event: 'error',
    error: {
      message: error.message,
      stack: error.stack,
      name: error.name,
    },
    timestamp: new Date().toISOString(),
    ...context,
  });
  
  // Send to backend (async, don't wait)
  sendToBackend('error', {
    message: error.message,
    stack: error.stack,
    name: error.name,
    ...context
  }, 'error');
};

export const logBusinessEvent = isProduction ? noOpLogBusinessEvent : (event: string, data: Record<string, any> = {}) => {
  // Log to browser console
  logger.info({
    event,
    level: 'info',
    timestamp: new Date().toISOString(),
    ...data,
  });
  
  // Send to backend (async, don't wait)
  sendToBackend(event, data, 'info');
};

export const logLifecycleEvent = isProduction ? noOpLogLifecycleEvent : (event: string, data: Record<string, any> = {}) => {
  // Log to browser console
  logger.info({
    event,
    level: 'info',
    timestamp: new Date().toISOString(),
    ...data,
  });
  
  // Send to backend (async, don't wait)
  sendToBackend(event, data, 'info');
};

export default logger;
