# Photon Data Import: Cloud Server Setup

## Overview

Importing Photon JSON data dump into PostGIS database using a cloud VM (DigitalOcean/AWS EC2).

**Approach:** JSON Data Dump (5.1 GB compressed) → PostGIS database
**Performance:** 100-500x improvement (from 0.12 → 50-200+ features/sec)
**Where:** Cloud VM via SSH

## Download

**File:** JSON Data Dump (jsonl.zst) - 5.1 GB compressed
**URL:** https://download1.graphhopper.com/public/north-america/usa/photon-dump-usa-0.7-latest.jsonl.zst
**Format:** Newline-delimited JSON, compressed with zstd

## Setup: Cloud VM (DigitalOcean)

### Step 1: Create Droplet

**Recommended Specs:**
- **Plan:** Basic (Regular with SSD)
- **CPU:** 1 vCPU (sufficient for streaming/decompression)
- **RAM:** 1 GB (only needs ~100-200 MB, but 1 GB gives headroom)
- **Disk:** 25 GB SSD (only needs ~1-2 GB for packages/script)
- **Datacenter:** Choose closest to your database location
- **OS:** Ubuntu 22.04 (LTS)
- **Cost:** ~$6/month ($0.009/hour if you delete after)

**Why these specs:**
- RAM: Streaming processes only use ~50-100 MB at a time, 1 GB is plenty
- CPU: Single core is fine - decompression is lightweight
- Disk: Minimal storage needed (just Python packages + script)
- Network: More important than CPU/RAM - affects download speed

**Can you go cheaper?** 
- DigitalOcean's $4/month option (512 MB RAM) might work but is tight
- $6/month gives comfortable headroom and is recommended

**After import:** Delete droplet to save money, or keep for future imports

### Step 2: SSH into Server
```bash
ssh root@your-droplet-ip
```

### Step 3: Install Dependencies
```bash
apt update && apt upgrade -y
apt install -y python3 python3-pip
pip3 install zstandard psycopg2-binary shapely requests
```

### Step 4: Get Script on Server

**Option A: Clone repo**
```bash
git clone https://github.com/yourusername/CourtPulse.git
cd CourtPulse/data_enrichment
```

**Option B: Upload via SCP (from laptop)**
```bash
# On laptop:
scp import_photon_remote.py root@your-droplet-ip:/root/
```

**Option C: Create script on server**
```bash
nano import_photon_remote.py
# Paste script content
```

### Step 5: Create PostGIS Table Schema

Run this SQL on your remote database (via psql, pgAdmin, etc.):

```sql
-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- Create facilities table
CREATE TABLE photon_facilities (
    id SERIAL PRIMARY KEY,
    osm_id BIGINT,
    osm_key VARCHAR(255),
    osm_value VARCHAR(255),
    name VARCHAR(500),
    countrycode VARCHAR(2),
    city VARCHAR(255),
    state VARCHAR(255),
    country VARCHAR(255),
    locality VARCHAR(255),
    
    -- Geometry (facility center point)
    geom GEOMETRY(Point, 4326),
    
    -- Extent as bounding box (for containment checks)
    extent_box GEOMETRY(Polygon, 4326),
    extent_coords JSONB,
    
    -- Full feature data as JSONB
    feature_data JSONB,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create spatial indexes
CREATE INDEX idx_photon_facilities_geom ON photon_facilities USING GIST(geom);
CREATE INDEX idx_photon_facilities_extent ON photon_facilities USING GIST(extent_box);

-- Create filtering indexes
CREATE INDEX idx_photon_facilities_osm_value ON photon_facilities(osm_value);
CREATE INDEX idx_photon_facilities_name ON photon_facilities(name);
CREATE INDEX idx_photon_facilities_osm_id ON photon_facilities(osm_id);
```

### Step 6: Run Import Script

**On cloud server:**
```bash
# Set database connection
export DATABASE_URL="postgresql://user:password@your-db-host:5432/courtpulse"

# Run import (streams from URL to database)
python3 import_photon_remote.py
```

**What happens:**
- Downloads 5.1 GB file from Photon server
- Streams directly to your remote database
- Processes in chunks (~50-100 MB RAM usage)
- Takes 30-60 minutes for full USA dataset
- Shows progress logs every 10,000 features

### Step 7: Verify Import

Run on your database:
```sql
-- Check stats
SELECT 
    COUNT(*) as total_facilities,
    COUNT(DISTINCT osm_value) as unique_types,
    COUNT(DISTINCT state) as states_covered
FROM photon_facilities;
```

### Step 8: Clean Up (Optional)

**Keep droplet:** Useful for future imports or other tasks
**Delete droplet:** Save money if you won't need it again

## Data Flow

```
Photon Server (Internet)
    ↓ [5.1 GB download]
Cloud VM (processes in chunks)
    ↓ [decompress + parse + format SQL]
    ↓ [~50-100 MB upload - SQL commands]
Remote PostGIS Database (final storage)
```

**Memory usage:** ~50-100 MB at any time (streaming/chunked processing)

## Update Strategy

- **Frequency:** Monthly (when OSM data updates)
- **Process:** Re-run import script with new JSON dump
- **Impact:** Replace existing data (or update if script supports upserts)

## Next Steps

1. ✅ Setup complete: Cloud VM + PostGIS table
2. ⏳ Create Python import script
3. ⏳ Run import on cloud server
4. ⏳ Update geocoding provider to use PostGIS queries instead of API calls
