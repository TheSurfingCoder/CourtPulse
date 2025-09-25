import pino from 'pino';
declare const logger: pino.Logger<never, boolean>;
export declare const logEvent: (event: string, data?: Record<string, any>) => void;
export declare const logError: (error: Error, context?: Record<string, any>) => void;
export declare const logBusinessEvent: (event: string, data?: Record<string, any>) => void;
export declare const logLifecycleEvent: (event: string, data?: Record<string, any>) => void;
export default logger;
//# sourceMappingURL=logger.d.ts.map