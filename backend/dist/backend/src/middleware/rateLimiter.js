"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.searchRateLimit = void 0;
const express_rate_limit_1 = __importDefault(require("express-rate-limit"));
const logger_js_1 = require("../../../shared/logger.js");
// Rate limiter for search endpoints
exports.searchRateLimit = (0, express_rate_limit_1.default)({
    windowMs: 60 * 1000, // 1 minute
    max: 20, // 20 requests per minute
    message: {
        success: false,
        message: 'Too many requests. Please try again later.',
        retryAfter: 60
    },
    standardHeaders: true, // Return rate limit info in the `RateLimit-*` headers
    legacyHeaders: false, // Disable the `X-RateLimit-*` headers
    handler: (req, res) => {
        // Log the rate limit violation
        (0, logger_js_1.logBusinessEvent)('rate_limit_exceeded', {
            message: 'Rate limit exceeded for search endpoint',
            ip: req.ip,
            userAgent: req.get('User-Agent'),
            endpoint: req.path,
            method: req.method,
            timestamp: new Date().toISOString()
        });
        // Return 429 with Retry-After header
        res.status(429).json({
            success: false,
            message: 'Too many requests. Please try again later.',
            retryAfter: 60
        });
    }
});
//# sourceMappingURL=rateLimiter.js.map