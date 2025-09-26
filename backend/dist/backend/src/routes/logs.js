"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const logger_js_1 = require("../../../shared/logger.js");
const router = express_1.default.Router();
// POST /api/logs - Receive logs from frontend (development only)
router.post('/', async (req, res) => {
    // Only process logs in development
    if (process.env.NODE_ENV !== 'development') {
        return res.status(404).json({ success: false, message: 'Not found' });
    }
    try {
        const { event, data, level = 'info' } = req.body;
        // Forward to Pino logger with frontend prefix
        if (level === 'error') {
            (0, logger_js_1.logError)(new Error(data.message || 'Frontend error'), {
                source: 'frontend',
                ...data
            });
        }
        else {
            (0, logger_js_1.logEvent)(event, {
                source: 'frontend',
                ...data
            });
        }
        return res.json({ success: true });
    }
    catch (error) {
        (0, logger_js_1.logError)(error instanceof Error ? error : new Error(String(error)), {
            message: 'Failed to process frontend log'
        });
        return res.status(500).json({ success: false });
    }
});
exports.default = router;
//# sourceMappingURL=logs.js.map