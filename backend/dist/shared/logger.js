"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.logLifecycleEvent = exports.logBusinessEvent = exports.logError = exports.logEvent = void 0;
const pino_1 = __importDefault(require("pino"));
// Environment-based configuration
const isDevelopment = process.env.NODE_ENV === 'development';
const isProduction = process.env.NODE_ENV === 'production';
// Base logger configuration
const baseConfig = {
    level: process.env.LOG_LEVEL || (isDevelopment ? 'debug' : 'info'),
    timestamp: pino_1.default.stdTimeFunctions.isoTime,
    formatters: {
        level: (label) => {
            return { level: label };
        },
    },
    serializers: {
        req: pino_1.default.stdSerializers.req,
        res: pino_1.default.stdSerializers.res,
        err: pino_1.default.stdSerializers.err,
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
const logger = (0, pino_1.default)(isDevelopment ? developmentConfig : productionConfig);
// Structured logging helpers following your workspace rules
const logEvent = (event, data = {}) => {
    logger.info({
        event,
        timestamp: new Date().toISOString(),
        ...data,
    });
};
exports.logEvent = logEvent;
const logError = (error, context = {}) => {
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
exports.logError = logError;
const logBusinessEvent = (event, data = {}) => {
    logger.info({
        event,
        level: 'info',
        timestamp: new Date().toISOString(),
        ...data,
    });
};
exports.logBusinessEvent = logBusinessEvent;
const logLifecycleEvent = (event, data = {}) => {
    logger.info({
        event,
        level: 'info',
        timestamp: new Date().toISOString(),
        ...data,
    });
};
exports.logLifecycleEvent = logLifecycleEvent;
exports.default = logger;
//# sourceMappingURL=logger.js.map