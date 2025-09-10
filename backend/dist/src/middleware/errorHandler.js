export class CustomError extends Error {
    statusCode;
    isOperational;
    constructor(message, statusCode = 500) {
        super(message);
        this.statusCode = statusCode;
        this.isOperational = true;
        Error.captureStackTrace(this, this.constructor);
    }
}
export const errorHandler = (err, req, res) => {
    let error = { ...err };
    error.message = err.message;
    // Log error for debugging
    console.error(JSON.stringify({
        level: 'error',
        message: 'Request error occurred',
        error: {
            name: err.name,
            message: err.message,
            stack: err.stack
        },
        request: {
            method: req.method,
            url: req.url,
            userAgent: req.get('User-Agent'),
            ip: req.ip
        },
        timestamp: new Date().toISOString()
    }));
    // Handle specific error types
    if (err.name === 'ValidationError') {
        const message = Object.values(err).map((val) => val.message).join(', ');
        error = new CustomError(message, 400);
    }
    if (err.name === 'CastError') {
        const message = 'Resource not found';
        error = new CustomError(message, 404);
    }
    if (err.code === 11000) {
        const message = 'Duplicate field value entered';
        error = new CustomError(message, 400);
    }
    if (err.name === 'JsonWebTokenError') {
        const message = 'Invalid token';
        error = new CustomError(message, 401);
    }
    if (err.name === 'TokenExpiredError') {
        const message = 'Token expired';
        error = new CustomError(message, 401);
    }
    res.status(error.statusCode || 500).json({
        success: false,
        message: error.message || 'Internal Server Error',
        ...(process.env.NODE_ENV === 'development' && { stack: err.stack })
    });
};
export const notFound = (req, res, next) => {
    const error = new CustomError(`Route ${req.originalUrl} not found`, 404);
    next(error);
};
//# sourceMappingURL=errorHandler.js.map