# Database Tables Audit

*Last updated: December 2024*

## Tables in Local PostgreSQL Database (courtpulse-dev)

### Production Tables

1. **`courts`** (17 columns)
   - **Purpose**: Main production table - source of truth
   - **Used by**: Backend API, Frontend
   - **Status**: ✅ Active
   - **Data**: Final processed court data with all metadata

### Staging/Processing Tables

2. **`osm_facilities`** (9 columns)
   - **Purpose**: Stores facilities (parks, playgrounds, schools) from Overpass API
   - **Used by**: `query_courts_and_facilities.py` for matching courts to facilities
   - **Status**: ✅ Active
   - **Data**: Facilities with names, geometry, bounding boxes

3. **`osm_courts_temp`** (10 columns)
   - **Purpose**: Temporary staging table for raw Overpass court data
   - **Used by**: `query_courts_and_facilities.py`, `populate_cluster_metadata.py`
   - **Status**: ✅ Active - Used by data enrichment pipeline
   - **Note**: This table only exists during data pipeline runs; may not exist in production

### Backup Tables

4. **`courts_backups`** (4 columns)
   - **Purpose**: Backup snapshots of courts table
   - **Status**: ⚠️ Review - Keep for safety or delete if not needed

### System Tables (Keep)

- `pgmigrations` - Tracks database migrations
- `spatial_ref_sys` - PostGIS system table
- `geography_columns`, `geometry_columns` - PostGIS system tables

## Removed Items

### Deleted Tables
- `courts_post_photon` - Legacy from failed Photon import approach (Photon doesn't index leisure=pitch)

### Removed Materialized Views
The following materialized views were created but never used in the application and have been removed:
- `court_aggregates_country` - Country-level aggregates (unused)
- `court_aggregates_state` - State-level aggregates (unused)
- `court_aggregates_city` - City-level aggregates (unused)
- `refresh_court_aggregates()` - Refresh function (unused)

## Summary

| Table | Columns | Status |
|-------|---------|--------|
| `courts` | 17 | ✅ Production |
| `osm_facilities` | 9 | ✅ Active |
| `osm_courts_temp` | 10 | ✅ Staging |
| `courts_backups` | 4 | ⚠️ Review |
