"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const promises_1 = __importDefault(require("fs/promises"));
const path_1 = __importDefault(require("path"));
const database_1 = __importDefault(require("../../config/database"));
const __dirname = process.cwd();
const MIGRATIONS_DIR = path_1.default.join(__dirname, 'database/migrations');
// Create migrations tracking table if it doesn't exist
async function createMigrationsTable() {
    const query = `
    CREATE TABLE IF NOT EXISTS migrations (
      id INTEGER PRIMARY KEY,
      filename VARCHAR(255) NOT NULL UNIQUE,
      executed_at TIMESTAMP DEFAULT NOW()
    );
  `;
    await database_1.default.query(query);
}
// Get list of executed migrations
async function getExecutedMigrations() {
    const result = await database_1.default.query('SELECT id, filename, executed_at FROM migrations ORDER BY id');
    return result.rows;
}
// Get list of migration files
async function getMigrationFiles() {
    try {
        const files = await promises_1.default.readdir(MIGRATIONS_DIR);
        return files
            .filter(file => file.endsWith('.sql'))
            .sort();
    }
    catch (error) {
        console.error('Error reading migrations directory:', error);
        return [];
    }
}
// Execute a single migration
async function executeMigration(filename) {
    const filePath = path_1.default.join(MIGRATIONS_DIR, filename);
    const sql = await promises_1.default.readFile(filePath, 'utf8');
    // Extract migration ID from filename (assumes format: 001_name.sql)
    const match = filename.match(/^(\d+)_/);
    const migrationId = match ? parseInt(match[1]) : 0;
    const client = await database_1.default.connect();
    try {
        await client.query('BEGIN');
        // Execute the migration SQL
        await client.query(sql);
        // Record the migration as executed
        await client.query('INSERT INTO migrations (id, filename) VALUES ($1, $2)', [migrationId, filename]);
        await client.query('COMMIT');
        console.log(`✓ Executed migration: ${filename}`);
    }
    catch (error) {
        await client.query('ROLLBACK');
        throw error;
    }
    finally {
        client.release();
    }
}
// Main migration function
async function migrate() {
    try {
        console.log('🔄 Starting database migration...');
        // Ensure migrations table exists
        await createMigrationsTable();
        // Get executed and available migrations
        const executedMigrations = await getExecutedMigrations();
        const availableMigrations = await getMigrationFiles();
        const executedFilenames = executedMigrations.map(m => m.filename);
        const pendingMigrations = availableMigrations.filter(filename => !executedFilenames.includes(filename));
        if (pendingMigrations.length === 0) {
            console.log('✅ All migrations are up to date!');
            return;
        }
        console.log(`📋 Found ${pendingMigrations.length} pending migration(s):`);
        pendingMigrations.forEach(filename => console.log(`  - ${filename}`));
        // Execute pending migrations
        for (const filename of pendingMigrations) {
            await executeMigration(filename);
        }
        console.log('✅ All migrations completed successfully!');
    }
    catch (error) {
        console.error('❌ Migration failed:', error);
        process.exit(1);
    }
    finally {
        await database_1.default.end();
    }
}
// Run migrations if this script is executed directly
if (require.main === module) {
    migrate();
}
//# sourceMappingURL=migrate.js.map