# File Cleanup Analysis

## Files to DELETE (Old Photon API Approach)

All these files use the Photon API which we've replaced with Overpass:

1. **test_bbox_search.py** - Tests Photon bounding box search API
2. **test_photon_geocoding.py** - Photon geocoding provider (1,553 lines - used by old pipeline)
3. **test_single_court.py** - Tests Photon geocoding for single court
4. **test_way_1106815330.py** - Tests Photon bounding box search for specific way
5. **debug_park_search.py** - Debugs Photon park search issues
6. **analyze_bounding_boxes.py** - Analyzes Photon bounding box matches
7. **bbox_search_example.py** - Example of Photon bounding box search
8. **bounding_box_geocoding.py** - Bounding box geocoding using Photon API
9. **court_pipeline.py** - Main pipeline using Photon API (37KB, 847 lines)
10. **data_mapper.py** - Maps Photon API data to database format
11. **run_full_pipeline.py** - Runs old Photon-based pipeline
12. **database_operations.py** - Database operations for old pipeline
13. **create_courts_post_photon_table.sql** - SQL schema for Photon table (we're not using Photon)

## Files to REVIEW (May Still Be Useful)

1. **add_individual_court_names.py** - Adds "Court 1", "Court 2" names to clustered courts
   - **Decision**: ⚠️ Keep for now - May still be useful with new approach if we cluster courts
   
2. **populate_cluster_metadata.py** - Populates cluster metadata in database
   - **Decision**: ⚠️ Keep for now - May still be useful for clustering functionality

3. **validation.py** - Court data validation
   - **Decision**: ✅ Keep - Validation logic is still useful for new Overpass data

4. **clustering.py** - Court clustering logic
   - **Decision**: ⚠️ Keep for now - May still be useful if clustering is needed

5. **fetch_courts_data.py** - Fetches courts from Overpass API
   - **Decision**: ⚠️ Review - Functionality may be superseded by `query_courts_and_facilities.py`
   - **Note**: This only fetches courts, doesn't match to facilities

6. **export.geojson** - Sample court data (61KB)
   - **Decision**: ⚠️ Keep - May be useful for testing/debugging

## Files to KEEP (New Approach)

1. **query_courts_and_facilities.py** - ✅ NEW Overpass approach (queries both courts and facilities, matches them)
2. **README.md** - ✅ Documentation
3. **TABLE_AUDIT.md** - ✅ Table documentation  
4. **requirements.txt** - ✅ Dependencies
5. **setup.sh** - ✅ Setup script

## Summary

**Delete: 13 files** (all Photon-related)
**Review: 6 files** (may still be useful)
**Keep: 5 files** (core functionality + docs)

