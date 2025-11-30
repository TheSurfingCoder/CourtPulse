# Database Tables Audit

## Tables in Local PostgreSQL Database (courtpulse-dev)

### Production Tables

1. **`courts`** (21 columns)
   - **Purpose**: Main production table - source of truth
   - **Used by**: Backend API, Frontend
   - **Status**: ✅ Keep - This is the primary table
   - **Data**: Final processed court data with all metadata

### Staging/Processing Tables

2. **`osm_facilities`** (9 columns)
   - **Purpose**: Stores facilities (parks, playgrounds, schools) from Overpass API
   - **Used by**: `query_courts_and_facilities.py` for matching courts
   - **Status**: ✅ Keep - Useful for facility reference and re-matching
   - **Data**: Facilities with names, geometry, bounding boxes

3. **`osm_courts_temp`** (9 columns)
   - **Purpose**: Temporary staging table for raw Overpass court data
   - **Used by**: `query_courts_and_facilities.py`
   - **Status**: ⚠️ Review - May be redundant if we insert directly into `courts`
   - **Recommendation**: Remove after migrating to direct `courts` insertion

### Legacy/Backup Tables

4. **`courts_post_photon`** (16 columns)
   - **Purpose**: Legacy table from Photon import attempt (Photon doesn't have pitch data)
   - **Used by**: None (Photon approach abandoned)
   - **Status**: ❌ Delete - No longer needed
   - **Note**: Photon JSON import was attempted but Photon doesn't index leisure=pitch

5. **`courts_backups`** (4 columns)
   - **Purpose**: Backup table
   - **Used by**: Unknown
   - **Status**: ⚠️ Review - Keep if needed for safety, otherwise can delete

### System Tables (Keep)

- `pgmigrations` - Tracks database migrations
- `spatial_ref_sys` - PostGIS system table
- `geography_columns`, `geometry_columns` - PostGIS system tables

## Summary

**Keep:**
- `courts` - Production table
- `osm_facilities` - Facility reference data

**Review:**
- `osm_courts_temp` - Remove after migration to direct `courts` insertion
- `courts_backups` - Keep for safety or delete if not needed

**Delete:**
- `courts_post_photon` - Legacy from failed Photon import approach

