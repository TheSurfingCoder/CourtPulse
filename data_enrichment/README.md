# Data Enrichment Pipeline

## Overview

This directory contains scripts and tools for enriching court data from OpenStreetMap using the Overpass API.

## Table Strategy

### Current Tables

1. **`osm_facilities`** - Raw facility data from Overpass queries
   - **Purpose**: Stores parks, playgrounds, schools, and other facilities queried from Overpass API
   - **Data**: Facilities with names, geometry, and bounding boxes
   - **Lifecycle**: Populated by `query_courts_and_facilities.py` before courts are matched
   - **Use**: Temporary staging table for matching courts to facilities

2. **`osm_courts_temp`** - Raw court data from Overpass queries  
   - **Purpose**: Stores raw court data (leisure=pitch with sport tags) from Overpass API
   - **Data**: Courts with geometry, sport type, and matched facility names
   - **Lifecycle**: Populated by `query_courts_and_facilities.py`, then matched to facilities
   - **Use**: Temporary staging table for processing Overpass results

3. **`courts`** - Source of truth (production table)
   - **Purpose**: Main production table used by backend API and frontend
   - **Data**: Final processed court data with all metadata
   - **Lifecycle**: Populated by data enrichment pipeline, updated by user edits
   - **Use**: This is the table the application queries from

### Strategy Decision

**Question**: Do we keep separate tables for raw Overpass queries, or consolidate everything into `courts`?

**Current Approach**:
- ✅ **Keep `osm_facilities`** - Useful for:
  - Re-matching courts if needed
  - Updating facility data without re-running full pipeline
  - Debugging matching issues
  - Potential future use cases (showing facilities on map, etc.)

- ❓ **`osm_courts_temp`** - Decision needed:
  - **Option A (Keep)**: Keep as staging table for processing, then copy to `courts`
    - Pros: Can re-process data without affecting production, easier debugging
    - Cons: Data duplication, need to sync
  
  - **Option B (Remove)**: Insert directly into `courts` table
    - Pros: Single source of truth, no sync needed, simpler
    - Cons: Harder to debug, data directly in production table

**Recommendation**: **Option B** - Insert directly into `courts` table
- The `query_courts_and_facilities.py` script should insert matched courts directly into `courts`
- Keep `osm_facilities` for facility reference data
- Remove `osm_courts_temp` after migration complete

### Migration Plan

1. Update `query_courts_and_facilities.py` to insert into `courts` instead of `osm_courts_temp`
2. Map `facility_name` from Overpass to appropriate column in `courts` (likely `photon_name` or new `facility_name`)
3. Test with San Francisco data
4. Once verified, drop `osm_courts_temp` table (optional cleanup)

## Scripts

### `query_courts_and_facilities.py`
Main script for querying Overpass API and matching courts to facilities.

**Usage**:
```bash
python3 query_courts_and_facilities.py "postgresql://user:pass@host:port/db"
```

**What it does**:
1. Queries Overpass for facilities (parks, playgrounds, schools)
2. Queries Overpass for courts (leisure=pitch with sport tags)
3. Matches courts to facilities using PostGIS spatial containment
4. Inserts results into database tables

### Other Scripts
- `court_pipeline.py` - Old data enrichment pipeline (using Photon API)
- `fetch_courts_data.py` - Fetches court data from Overpass (legacy)
- Various test scripts for debugging and validation

## Data Flow

```
Overpass API
    ↓
[Query Facilities] → osm_facilities (staging)
    ↓
[Query Courts] → Match with osm_facilities → courts (production)
    ↓
Frontend/Backend reads from → courts table
```

## Tables Strategy Summary

### Keep Separate vs Consolidate

**Recommendation: Hybrid Approach**

1. **Keep `osm_facilities` separate** ✅
   - Facilities are reference data that change infrequently
   - Useful for re-matching courts without re-running full pipeline
   - Can be queried independently for future features (show facilities on map)

2. **Insert directly into `courts` table** ✅
   - No need for `osm_courts_temp` as intermediate staging
   - Courts are the source of truth - insert matched data directly
   - Simpler architecture, no sync needed

3. **Final Structure:**
   - `osm_facilities` → Staging/reference table (kept separate)
   - `courts` → Production source of truth (direct insertion)
   - ~~`osm_courts_temp`~~ → Remove after migration

### Migration Strategy

The `query_courts_and_facilities.py` script should:
1. Query and insert facilities into `osm_facilities`
2. Query courts from Overpass
3. Match courts to facilities using PostGIS
4. **Insert matched courts directly into `courts` table** (not `osm_courts_temp`)

This gives us:
- Single source of truth (`courts`)
- Facility reference data available separately (`osm_facilities`)
- No intermediate staging table needed

## Notes

- `courts_post_photon` - Legacy table from Photon import attempt (can be dropped - Photon doesn't have pitch data)
- `courts_backups` - Backup table (can be kept for safety)
- See `TABLE_AUDIT.md` for full database table analysis
