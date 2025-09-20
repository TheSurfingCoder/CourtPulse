"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const Court_1 = require("../models/Court");
const router = express_1.default.Router();
// GET /api/courts/clustered - Get clustered courts for map display
router.get('/clustered', async (req, res) => {
    try {
        const clusteredCourts = await Court_1.CourtModel.findAllClustered();
        console.log(JSON.stringify({
            level: 'info',
            message: 'Successfully fetched clustered courts',
            count: clusteredCourts.length,
            request: {
                method: req.method,
                url: req.url
            },
            timestamp: new Date().toISOString()
        }));
        return res.json({
            success: true,
            count: clusteredCourts.length,
            data: clusteredCourts
        });
    }
    catch (error) {
        console.error(JSON.stringify({
            level: 'error',
            message: 'Failed to fetch clustered courts',
            error: {
                message: error instanceof Error ? error.message : 'Unknown error',
                stack: error instanceof Error ? error.stack : undefined
            },
            request: {
                method: req.method,
                url: req.url
            },
            timestamp: new Date().toISOString()
        }));
        return res.status(500).json({
            success: false,
            message: 'Failed to fetch clustered courts',
            error: error instanceof Error ? error.message : 'Unknown error'
        });
    }
});
// GET /api/courts - Get all courts (individual records)
router.get('/', async (req, res) => {
    try {
        const courts = await Court_1.CourtModel.findAll();
        console.log(JSON.stringify({
            level: 'info',
            message: 'Successfully fetched courts',
            count: courts.length,
            request: {
                method: req.method,
                url: req.url
            },
            timestamp: new Date().toISOString()
        }));
        return res.json({
            success: true,
            count: courts.length,
            data: courts
        });
    }
    catch (error) {
        console.error(JSON.stringify({
            level: 'error',
            message: 'Failed to fetch courts',
            error: {
                message: error instanceof Error ? error.message : 'Unknown error',
                stack: error instanceof Error ? error.stack : undefined
            },
            request: {
                method: req.method,
                url: req.url
            },
            timestamp: new Date().toISOString()
        }));
        return res.status(500).json({
            success: false,
            message: 'Failed to fetch courts',
            error: error instanceof Error ? error.message : 'Unknown error'
        });
    }
});
// GET /api/courts/cluster/:clusterId - Get all courts in a cluster
router.get('/cluster/:clusterId', async (req, res) => {
    try {
        const { clusterId } = req.params;
        const courts = await Court_1.CourtModel.findClusterDetails(clusterId);
        console.log(JSON.stringify({
            level: 'info',
            message: 'Successfully fetched cluster details',
            cluster_id: clusterId,
            count: courts.length,
            request: {
                method: req.method,
                url: req.url
            },
            timestamp: new Date().toISOString()
        }));
        return res.json({
            success: true,
            cluster_id: clusterId,
            count: courts.length,
            data: courts
        });
    }
    catch (error) {
        console.error(JSON.stringify({
            level: 'error',
            message: 'Failed to fetch cluster details',
            cluster_id: req.params.clusterId,
            error: {
                message: error instanceof Error ? error.message : 'Unknown error',
                stack: error instanceof Error ? error.stack : undefined
            },
            request: {
                method: req.method,
                url: req.url
            },
            timestamp: new Date().toISOString()
        }));
        return res.status(500).json({
            success: false,
            message: 'Failed to fetch cluster details',
            error: error instanceof Error ? error.message : 'Unknown error'
        });
    }
});
// GET /api/courts/:id - Get court by ID
router.get('/:id', async (req, res) => {
    try {
        const id = parseInt(req.params.id);
        if (isNaN(id)) {
            return res.status(400).json({
                success: false,
                message: 'Invalid court ID'
            });
        }
        const court = await Court_1.CourtModel.findById(id);
        if (!court) {
            return res.status(404).json({
                success: false,
                message: 'Court not found'
            });
        }
        return res.json({
            success: true,
            data: court
        });
    }
    catch (error) {
        console.error('Error fetching court:', error);
        return res.status(500).json({
            success: false,
            message: 'Failed to fetch court',
            error: error instanceof Error ? error.message : 'Unknown error'
        });
    }
});
// GET /api/courts/type/:type - Get courts by type
router.get('/type/:type', async (req, res) => {
    try {
        const { type } = req.params;
        const courts = await Court_1.CourtModel.findByType(type);
        return res.json({
            success: true,
            count: courts.length,
            data: courts
        });
    }
    catch (error) {
        console.error('Error fetching courts by type:', error);
        return res.status(500).json({
            success: false,
            message: 'Failed to fetch courts by type',
            error: error instanceof Error ? error.message : 'Unknown error'
        });
    }
});
// POST /api/courts - Create new court
router.post('/', async (req, res) => {
    try {
        const { name, type, location, surface, is_public } = req.body;
        // Basic validation
        if (!name || !type || !location || !location.lat || !location.lng) {
            return res.status(400).json({
                success: false,
                message: 'Missing required fields: name, type, location (lat/lng)'
            });
        }
        const court = await Court_1.CourtModel.create({
            name,
            type,
            lat: location.lat,
            lng: location.lng,
            surface: surface || 'Unknown',
            is_public: is_public ?? true
        });
        console.log(JSON.stringify({
            level: 'info',
            message: 'Successfully created court',
            courtId: court.id,
            courtName: court.name,
            request: {
                method: req.method,
                url: req.url
            },
            timestamp: new Date().toISOString()
        }));
        return res.status(201).json({
            success: true,
            data: court
        });
    }
    catch (error) {
        console.error(JSON.stringify({
            level: 'error',
            message: 'Failed to create court',
            error: {
                message: error instanceof Error ? error.message : 'Unknown error',
                stack: error instanceof Error ? error.stack : undefined
            },
            request: {
                method: req.method,
                url: req.url,
                body: req.body
            },
            timestamp: new Date().toISOString()
        }));
        return res.status(500).json({
            success: false,
            message: 'Failed to create court',
            error: error instanceof Error ? error.message : 'Unknown error'
        });
    }
});
// PUT /api/courts/:id - Update court
router.put('/:id', async (req, res) => {
    try {
        const id = parseInt(req.params.id);
        if (isNaN(id)) {
            return res.status(400).json({
                success: false,
                message: 'Invalid court ID'
            });
        }
        const court = await Court_1.CourtModel.update(id, req.body);
        if (!court) {
            return res.status(404).json({
                success: false,
                message: 'Court not found'
            });
        }
        return res.json({
            success: true,
            data: court
        });
    }
    catch (error) {
        console.error('Error updating court:', error);
        return res.status(500).json({
            success: false,
            message: 'Failed to update court',
            error: error instanceof Error ? error.message : 'Unknown error'
        });
    }
});
// DELETE /api/courts/:id - Delete court
router.delete('/:id', async (req, res) => {
    try {
        const id = parseInt(req.params.id);
        if (isNaN(id)) {
            return res.status(400).json({
                success: false,
                message: 'Invalid court ID'
            });
        }
        const deleted = await Court_1.CourtModel.delete(id);
        if (!deleted) {
            return res.status(404).json({
                success: false,
                message: 'Court not found'
            });
        }
        return res.json({
            success: true,
            message: 'Court deleted successfully'
        });
    }
    catch (error) {
        console.error('Error deleting court:', error);
        return res.status(500).json({
            success: false,
            message: 'Failed to delete court',
            error: error instanceof Error ? error.message : 'Unknown error'
        });
    }
});
// GET /api/courts/viewport - Get courts within a viewport based on zoom level
router.get('/viewport', async (req, res) => {
    try {
        const { west, south, east, north, zoom, sport, surface_type, is_public } = req.query;
        // Validate required parameters
        if (!west || !south || !east || !north || !zoom) {
            return res.status(400).json({
                success: false,
                message: 'Missing required parameters: west, south, east, north, zoom'
            });
        }
        // Parse and validate coordinates
        const bbox = [
            parseFloat(west),
            parseFloat(south),
            parseFloat(east),
            parseFloat(north)
        ];
        const zoomLevel = parseFloat(zoom);
        // Validate bbox
        if (bbox.some(coord => isNaN(coord))) {
            return res.status(400).json({
                success: false,
                message: 'Invalid coordinates provided'
            });
        }
        // Validate zoom level
        if (isNaN(zoomLevel) || zoomLevel < 0 || zoomLevel > 20) {
            return res.status(400).json({
                success: false,
                message: 'Invalid zoom level. Must be between 0 and 20'
            });
        }
        // Parse filters
        const filters = {};
        if (sport)
            filters.sport = sport;
        if (surface_type)
            filters.surface_type = surface_type;
        if (is_public !== undefined) {
            filters.is_public = is_public === 'true';
        }
        console.log(JSON.stringify({
            event: 'viewport_query_started',
            timestamp: new Date().toISOString(),
            bbox: bbox,
            zoom: zoomLevel,
            filters: filters
        }));
        // Get courts based on viewport and zoom level
        const courts = await Court_1.CourtModel.getCourtsInViewport(bbox, zoomLevel, filters);
        console.log(JSON.stringify({
            event: 'viewport_query_completed',
            timestamp: new Date().toISOString(),
            courtCount: courts.length,
            zoom: zoomLevel,
            bbox: bbox
        }));
        return res.json({
            success: true,
            data: courts,
            meta: {
                count: courts.length,
                zoom: zoomLevel,
                bbox: bbox,
                filters: filters
            }
        });
    }
    catch (error) {
        console.error(JSON.stringify({
            event: 'viewport_query_error',
            timestamp: new Date().toISOString(),
            error: error instanceof Error ? error.message : 'Unknown error',
            stack: error instanceof Error ? error.stack : undefined
        }));
        return res.status(500).json({
            success: false,
            message: 'Failed to fetch courts in viewport',
            error: error instanceof Error ? error.message : 'Unknown error'
        });
    }
});
exports.default = router;
//# sourceMappingURL=courts.js.map