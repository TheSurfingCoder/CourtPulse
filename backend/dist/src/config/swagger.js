// @ts-ignore
import swaggerJsdoc from 'swagger-jsdoc';
const options = {
    definition: {
        openapi: '3.0.0',
        info: {
            title: 'CourtPulse API',
            version: '1.0.0',
            description: 'API for CourtPulse - a sports court discovery and management platform',
            contact: {
                name: 'CourtPulse Team',
                email: 'support@courtpulse.com'
            }
        },
        servers: [
            {
                url: 'http://localhost:5000',
                description: 'Development server'
            },
            {
                url: 'https://api.courtpulse.com',
                description: 'Production server'
            }
        ],
        components: {
            schemas: {
                Court: {
                    type: 'object',
                    properties: {
                        id: { type: 'integer', example: 1 },
                        name: { type: 'string', example: 'Central Park Basketball Court' },
                        type: { type: 'string', example: 'basketball' },
                        location: {
                            type: 'object',
                            properties: {
                                lat: { type: 'number', example: 40.7589 },
                                lng: { type: 'number', example: -73.9851 }
                            }
                        },
                        address: { type: 'string', example: '123 Central Park, NY' },
                        surface: { type: 'string', example: 'asphalt' },
                        is_public: { type: 'boolean', example: true },
                        created_at: { type: 'string', format: 'date-time' },
                        updated_at: { type: 'string', format: 'date-time' }
                    }
                },
                Error: {
                    type: 'object',
                    properties: {
                        success: { type: 'boolean', example: false },
                        message: { type: 'string', example: 'Error message' },
                        error: { type: 'string', example: 'Detailed error information' }
                    }
                }
            }
        }
    },
    apis: ['./src/routes/*.ts', './src/models/*.ts']
};
export const specs = swaggerJsdoc(options);
//# sourceMappingURL=swagger.js.map