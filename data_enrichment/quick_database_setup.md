# Quick Database Setup for Testing

## Option 1: Docker (Recommended for testing)

```bash
# Run Postgres with PostGIS in Docker
docker run --name courtpulse-db \
  -e POSTGRES_PASSWORD=yourpassword \
  -e POSTGRES_DB=courtpulse \
  -p 5432:5432 \
  -d postgis/postgis:15-3.3
```

Then update your `.env` file:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=courtpulse
DB_USER=postgres
DB_PASSWORD=yourpassword
```

## Option 2: Local Postgres Installation

If you have Postgres installed locally:

```sql
-- Connect to postgres and create database
CREATE DATABASE courtpulse;
\c courtpulse

-- Enable PostGIS extension
CREATE EXTENSION postgis;
```

## Option 3: Skip Database for Testing

You can test the GeoJSON parsing and geocoding without a database by modifying the main script.
