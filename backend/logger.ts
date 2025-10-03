import pino from 'pino';

// Environment-based configuration
const isDevelopment = process.env.NODE_ENV === 'development';
const isProduction = process.env.NODE_ENV === 'production';

// Base logger configuration
const baseConfig = {
  level: process.env.LOG_LEVEL || (isDevelopment ? 'debug' : 'info'),
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

// Development configuration with pretty printing
const developmentConfig = {
  ...baseConfig,
  transport: {
    target: 'pino-pretty',
    options: {
      colorize: true,
      translateTime: 'SYS:standard',
      ignore: 'pid,hostname',
      singleLine: false,
    },
  },
};

// Production configuration
const productionConfig = {
  ...baseConfig,
  level: 'info',
};

// Create logger based on environment
const logger = pino(isDevelopment ? developmentConfig : productionConfig);

// Structured logging helpers following your workspace rules
export const logEvent = (event: string, data: Record<string, any> = {}) => {
  logger.info({
    event,
    timestamp: new Date().toISOString(),
    ...data,
  });
};

export const logError = (error: Error, context: Record<string, any> = {}) => {
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
};

export const logBusinessEvent = (event: string, data: Record<string, any> = {}) => {
  logger.info({
    event,
    level: 'info',
    timestamp: new Date().toISOString(),
    ...data,
  });
};

export const logLifecycleEvent = (event: string, data: Record<string, any> = {}) => {
  logger.info({
    event,
    level: 'info',
    timestamp: new Date().toISOString(),
    ...data,
  });
};

export default logger;
