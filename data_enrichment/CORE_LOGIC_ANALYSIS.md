# Core Logic Analysis: Remaining Files

This document analyzes the 4 remaining files to determine what core logic should be kept for the new Overpass approach.

## 1. `validation.py` - ✅ **KEEP MOST LOGIC**

### Purpose
Validates court data structure, coordinates, required fields, and business logic before database insertion.

### Core Logic to Keep
- ✅ **`validate_geojson_structure()`** - Validates GeoJSON feature structure (geometry, properties)
- ✅ **`validate_coordinates()`** - Validates Point and Polygon coordinates (still relevant for Overpass data)
- ✅ **`validate_required_fields()`** - Validates osm_id and sport fields
- ✅ **`validate_data_types()`** - Validates osm_id format, sport enum, hoops count
- ✅ **`validate_business_logic()`** - Validates basketball courts have hoops, reasonable hoops counts

### Logic to Remove/Modify
- ⚠️ **`validate_photon_data()`** - Not needed anymore (photon_name validation)
  - Can be removed or replaced with `validate_facility_data()` for facility_name from Overpass

### Recommendation
**Keep 90% of this file** - Just remove/modify the Photon-specific validation. The coordinate, GeoJSON, and business logic validation is still highly relevant for Overpass data.

---

## 2. `clustering.py` - ⚠️ **PARTIALLY KEEP**

### Purpose
Groups nearby courts (by distance) into clusters for consistent naming. Used to reduce API calls by clustering courts before geocoding.

### Current Logic
- Extracts court data from GeoJSON features
- Clusters courts within 0.05km (~160 feet) of each other
- Only clusters courts of the same sport
- Generates fallback names for courts

### Core Logic to Keep
- ✅ **Distance calculation (`_calculate_distance()`)** - Haversine formula for distance between coordinates
- ✅ **Clustering algorithm (`cluster_courts()`)** - May still be useful if we want to group multiple courts within the same facility
- ⚠️ **Fallback name generation (`_generate_fallback_name()`)** - Could be useful but may be redundant with facility_name

### Logic to Remove/Modify
- ❌ **`extract_court_data()`** - May need modification since Overpass data structure differs from old GeoJSON
- ❌ **Distance-based clustering may be redundant** - New approach already matches courts to facilities, which provides natural grouping

### Recommendation
**Keep clustering algorithm IF we need it** - With the new Overpass approach, courts are already matched to facilities. However, if a facility has multiple courts of the same sport, we might want to:
1. Keep them as separate records (current approach)
2. OR cluster them for display purposes

**Question to Answer**: Do we need to cluster courts within the same facility, or is the facility_name grouping sufficient?

---

## 3. `add_individual_court_names.py` - ⚠️ **KEEP BUT MODIFY**

### Purpose
Adds "Court 1", "Court 2", etc. names to courts within the same cluster (identified by `cluster_id`).

### Current Logic
- Groups courts by `cluster_id`
- For clusters with multiple courts, assigns sequential names: "Court 1", "Court 2", etc.
- Updates `individual_court_name` column

### Frontend Usage
Frontend currently uses:
- `name` = `COALESCE(individual_court_name, enriched_name, fallback_name, 'Unknown Court')`
- `cluster_group_name` = `COALESCE(photon_name, enriched_name, fallback_name, NULL)`

### Core Logic to Keep
- ✅ **Sequential naming logic** - Assigning "Court 1", "Court 2" to multiple courts
- ✅ **Grouping by cluster_id** - Still relevant if we keep clustering

### Logic to Modify
- ⚠️ **Dependencies on old columns** - Currently uses `photon_name`, `enriched_name`, `fallback_name`
- ⚠️ **Grouping strategy** - Should group by `facility_name` + `cluster_id` (or just `facility_name` if facility is the cluster)

### Recommendation
**Keep IF we decide to keep clustering** - Otherwise, we can rely on facility_name for grouping. However, if a facility has multiple courts of the same sport, sequential naming ("Court 1", "Court 2") is still useful.

**Modification needed**:
- Update to use `facility_name` instead of `photon_name` for grouping
- Or group by `facility_name` + same sport + nearby location

---

## 4. `populate_cluster_metadata.py` - ⚠️ **REVIEW/REPLACE**

### Purpose
Populates `cluster_id` for existing courts by grouping them by:
1. Same `photon_name` + same `bounding_box_id`
2. Same `photon_name` + nearby coordinates (within 0.05km)

### Current Logic
- Groups courts by `photon_name` + `bounding_box_id`
- For courts with same name but different bounding boxes, clusters by distance
- Assigns UUID `cluster_id` to each cluster

### Core Logic to Keep
- ✅ **Distance-based clustering** - Haversine distance calculation (same as clustering.py)
- ✅ **UUID generation for clusters** - Still needed for cluster_id

### Logic to Remove/Modify
- ❌ **`bounding_box_id` dependency** - New approach doesn't use bounding_box_id
- ❌ **`photon_name` dependency** - Should use `facility_name` instead
- ⚠️ **May be redundant** - If we're matching courts to facilities in the import script, clustering might already be handled

### Recommendation
**Replace with new version** - Create a new function that:
1. Groups courts by `facility_name` (from Overpass matching)
2. For courts with same facility_name, groups by same sport + nearby location (within 0.05km)
3. Assigns `cluster_id` to each group

**OR**: If facility_name is sufficient for grouping, we may not need this at all - just use facility_name as the grouping mechanism.

---

## Summary Recommendations

### Keep As-Is
1. **`validation.py`** - Remove only Photon-specific validation, keep everything else

### Keep and Modify
2. **`add_individual_court_names.py`** - Modify to use `facility_name` instead of `photon_name`
3. **`clustering.py`** - Keep distance calculation and clustering algorithm, but update to work with Overpass data structure

### Replace or Remove
4. **`populate_cluster_metadata.py`** - Replace with new version that uses `facility_name`, or remove if facility grouping is sufficient

## Decision Points

1. **Do we need clustering beyond facility matching?**
   - If facility_name is sufficient for grouping, we can simplify or remove clustering logic
   - If we want to group multiple courts within same facility (e.g., "Basketball Court 1", "Basketball Court 2"), keep clustering

2. **What should `cluster_id` represent?**
   - Option A: Courts within the same facility (facility_name)
   - Option B: Courts within same facility + same sport + nearby location
   - Option C: Remove cluster_id entirely and use facility_name for grouping

3. **What should `individual_court_name` represent?**
   - Option A: Sequential names within cluster ("Court 1", "Court 2")
   - Option B: Remove and rely on facility_name + sport for identification
   - Option C: Use OSM name or custom name if available

## Next Steps

1. Review frontend usage of `cluster_id` and `individual_court_name` to understand requirements
2. Decide on clustering strategy (facility-based vs. distance-based)
3. Update files based on decisions above
4. Test with Overpass import script

