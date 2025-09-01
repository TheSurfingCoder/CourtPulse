

export default {
    database: {
        host: process.env.DB_HOST || 'localhost',
        port: parseInt(process.env.DB_PORT || '5432'),
        database: process.env.DB_NAME || 'courtpulse',
        user: process.env.DB_USER || 'postgres',
        password: process.env.DB_PASSWORD || 'password',
        ssl: { rejectUnauthorized: false }
    },
    server: {
        port: parseInt(process.env.PORT || '5000'),
        corsOrigin: process.env.CORS_ORIGIN || 'https://yourdomain.com'
    },
    jwt: {
        secret: process.env.JWT_SECRET || 'production-secret-key-required'
    }
};