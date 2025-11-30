# Flow Examples: How Each Component Works

## 1. Validation.py Flow Example

### How validation.py would be used in the Overpass import flow:

```python
# In query_courts_and_facilities.py - insert_courts() method

from validation import CourtDataValidator

def insert_courts(self, courts_data: Dict[str, Any]) -> int:
    validator = CourtDataValidator()
    count = 0
    elements = courts_data.get('elements', [])
    
    for element in elements:
        # Convert Overpass element to GeoJSON-like format for validation
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[(lon, lat), ...]]  # Converted from Overpass geometry
            },
            "properties": {
                "osm_id": f"way/{element.get('id')}",
                "sport": element.get('tags', {}).get('sport'),
                "hoops": element.get('tags', {}).get('hoops')
            }
        }
        
        # Validate the court data BEFORE inserting
        is_valid, results = validator.validate_court_data(feature)
        
        if not is_valid:
            # Log validation errors and skip this court
            validator.log_validation_results(feature['properties']['osm_id'])
            logger.warning(f"Skipping invalid court: {feature['properties']['osm_id']}")
            continue
        
        # Only insert if validation passes
        # ... rest of insertion logic ...
```

### Example Validation Scenarios:

**Scenario 1: Valid Court**
```python
feature = {
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[-122.4, 37.7], [-122.4, 37.8], [-122.3, 37.8], [-122.3, 37.7], [-122.4, 37.7]]]
    },
    "properties": {
        "osm_id": "way/12345",
        "sport": "basketball",
        "hoops": 2
    }
}
# ✅ Validation passes - all checks OK
```

**Scenario 2: Invalid Coordinates**
```python
feature = {
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[-200, 100], ...]]  # Invalid longitude
    },
    "properties": {"osm_id": "way/12345", "sport": "basketball"}
}
# ❌ Validation fails - longitude out of range (-180 to 180)
```

**Scenario 3: Missing Required Field**
```python
feature = {
    "geometry": {...},
    "properties": {
        "osm_id": "way/12345"
        # Missing "sport" field
    }
}
# ❌ Validation fails - missing required field: sport
```

**Scenario 4: Invalid Sport Type**
```python
feature = {
    "geometry": {...},
    "properties": {
        "osm_id": "way/12345",
        "sport": "cricket"  # Not in valid sports list
    }
}
# ❌ Validation fails - invalid sport: cricket
```

---

## 2. Fallback Name Generation - Why It's Useful

### Current Flow (from clustering.py):

```python
def _generate_fallback_name(self, properties: Dict[str, Any]) -> str:
    sport = properties.get('sport', 'basketball')
    hoops = properties.get('hoops')
    
    if sport == 'basketball' and hoops:
        return f"basketball court ({hoops} hoops)"
    elif sport == 'basketball':
        return "basketball court"
    elif sport == 'tennis':
        return "tennis court"
    # ... etc
```

### Why We Still Need It:

**Scenario 1: Court with no facility_name**
```
Court Location: 37.7890, -122.4090 (Golden Gate Park area)
facility_name: NULL  (Court not matched to a facility, or facility has no name)
enriched_name: NULL
individual_court_name: NULL

→ Fallback: "basketball court (2 hoops)"
```

**Scenario 2: Court with facility_name but no individual name**
```
Court Location: Inside "Washington High School"
facility_name: "Washington High School"  ✅ Has facility name
individual_court_name: NULL

Frontend displays:
- cluster_group_name: "Washington High School"
- name: "basketball court (2 hoops)"  ← Uses fallback
```

**Scenario 3: Multiple courts in same facility**
```
Facility: "Golden Gate Park - Basketball Courts"
Court 1: individual_court_name = "Court 1"
Court 2: individual_court_name = "Court 2"  
Court 3: individual_court_name = NULL  ← This one would use fallback

Frontend displays:
- Court 1: cluster_group_name = "Golden Gate Park - Basketball Courts", name = "Court 1"
- Court 2: cluster_group_name = "Golden Gate Park - Basketball Courts", name = "Court 2"
- Court 3: cluster_group_name = "Golden Gate Park - Basketball Courts", name = "basketball court (2 hoops)"
```

### Current Backend Mapping:
```typescript
// From Court.ts
COALESCE(individual_court_name, enriched_name, fallback_name, 'Unknown Court') as name
```

**Decision Point**: 
- ✅ **Keep fallback name** - It provides useful context when facility_name exists but individual_court_name doesn't
- The fallback tells users the sport type and hoops count, which is valuable information

---

## 3. Clustering Algorithm - Clustering Courts Within Same Facility

### Current Clustering Logic:

```python
# In clustering.py
class CoordinateClusterer:
    def cluster_courts(self, courts: List[CourtClusterData]) -> List[List[CourtClusterData]]:
        # Groups courts within 0.05km (~160 feet) that have same sport
        clusters = []
        
        for court in courts:
            # Find all nearby courts of same sport
            nearby_courts = [c for c in courts 
                           if distance(court, c) <= 0.05km 
                           and court.sport == c.sport]
            clusters.append(nearby_courts)
```

### Modified Flow for Facility-Based Clustering:

```python
# New approach: Cluster courts WITHIN the same facility

def cluster_courts_within_facility(self, courts: List[Dict]) -> List[Dict]:
    """
    Group courts that:
    1. Have the same facility_name
    2. Are within 0.05km of each other (optional - for large facilities)
    3. Have the same sport (optional - or cluster all sports together?)
    """
    clusters = []
    
    # First group by facility_name
    by_facility = {}
    for court in courts:
        facility = court.get('facility_name') or 'unmatched'
        if facility not in by_facility:
            by_facility[facility] = []
        by_facility[facility].append(court)
    
    # Then cluster within each facility by distance
    for facility_name, facility_courts in by_facility.items():
        if len(facility_courts) == 1:
            # Single court - no clustering needed
            clusters.append({
                'cluster_id': str(uuid.uuid4()),
                'facility_name': facility_name,
                'courts': facility_courts
            })
        else:
            # Multiple courts - cluster by distance and sport
            sub_clusters = self._cluster_by_distance(facility_courts)
            clusters.extend(sub_clusters)
    
    return clusters
```

### Example Scenario:

```
Facility: "Golden Gate Park"

Court A: basketball, 37.7890, -122.4090, facility_name = "Golden Gate Park"
Court B: basketball, 37.7891, -122.4091, facility_name = "Golden Gate Park"  (50m from A)
Court C: basketball, 37.7900, -122.4100, facility_name = "Golden Gate Park"  (200m from A)
Court D: tennis, 37.7890, -122.4090, facility_name = "Golden Gate Park"

Clustering Result:
- Cluster 1 (basketball, nearby): [Court A, Court B]  ← Same facility, same sport, close together
- Cluster 2 (basketball, separate): [Court C]  ← Same facility, same sport, but far away
- Cluster 3 (tennis): [Court D]  ← Same facility, different sport

Each cluster gets a unique cluster_id for frontend grouping
```

### Frontend Benefit:
- Courts A and B would be grouped together on the map (same cluster_id)
- When zoomed out, shows as "Golden Gate Park - 2 basketball courts"
- When zoomed in, shows as "Court 1" and "Court 2"

---

## 4. What is `facility_name`? (The New Overpass Approach)

### Yes, this is the newest approach!

### How it works:

1. **Query Overpass for Facilities** (parks, playgrounds, schools):
   ```python
   # Returns facilities like:
   {
     "id": 12345,
     "type": "way",
     "tags": {
       "leisure": "park",
       "name": "Golden Gate Park"  ← This becomes facility_name
     },
     "geometry": [...]  # Polygon boundary
   }
   ```

2. **Query Overpass for Courts** (leisure=pitch with sport tags):
   ```python
   # Returns courts like:
   {
     "id": 67890,
     "type": "way",
     "tags": {
       "leisure": "pitch",
       "sport": "basketball"
     },
     "geometry": [...]  # Court polygon
   }
   ```

3. **Spatial Join** (PostGIS):
   ```sql
   -- Find which facility contains each court's centroid
   SELECT f.name as facility_name
   FROM osm_facilities f
   WHERE ST_Contains(f.geom, court_centroid)
   ```

4. **Result**:
   - Court at 37.7890, -122.4090 → Matched to "Golden Gate Park"
   - `facility_name` = "Golden Gate Park"

### Difference from Old Approach:

**Old (Photon)**:
- Used Photon API to reverse geocode court coordinates
- Photon would return nearby places (could be wrong)
- No guarantee court was actually IN the facility

**New (Overpass)**:
- Gets actual facility polygons from OpenStreetMap
- Uses spatial containment (ST_Contains) to verify court is INSIDE facility
- More accurate because it uses OSM's actual facility boundaries

### Example Data Flow:

```
Overpass Query → Facilities (parks, schools)
                ↓
                Store in osm_facilities table
                ↓
Overpass Query → Courts (leisure=pitch)
                ↓
                For each court:
                  1. Calculate centroid
                  2. Find facility that contains centroid (ST_Contains)
                  3. Set facility_name = facility.name
                ↓
                Store in courts table with facility_name
```

---

## 5. Keeping add_individual_court_names.py

### Current Logic:
- Groups courts by `cluster_id`
- Assigns sequential names: "Court 1", "Court 2", etc.

### Modified Logic for New Approach:
- Group by `facility_name` + `cluster_id` (or just by cluster_id, which should already represent facility grouping)
- Assign sequential names within each cluster

### Example:
```python
# After clustering courts within "Golden Gate Park":
cluster_id = "uuid-123"
facility_name = "Golden Gate Park"
courts = [
    {id: 1, sport: "basketball", ...},
    {id: 2, sport: "basketball", ...},
    {id: 3, sport: "tennis", ...}
]

# After add_individual_court_names.py:
court 1 → individual_court_name = "Court 1"
court 2 → individual_court_name = "Court 2"
court 3 → individual_court_name = "Court 1"  # New cluster (different sport)
```

---

## Summary Flow: Complete Data Pipeline

```
1. Query Overpass → Facilities (parks, schools) → osm_facilities table
2. Query Overpass → Courts (pitches) → Validate each court (validation.py)
3. Spatial Join → Match courts to facilities → Set facility_name
4. Cluster courts within facilities → Assign cluster_id
5. Add individual court names → Assign "Court 1", "Court 2", etc.
6. Insert into courts table with:
   - facility_name (from Overpass matching)
   - cluster_id (from clustering)
   - individual_court_name (from add_individual_court_names.py)
   - fallback_name (generated, used if individual_court_name is NULL)
```

### Frontend Display Logic:
```
name = COALESCE(individual_court_name, fallback_name, 'Unknown Court')
cluster_group_name = COALESCE(facility_name, NULL)
```

Example displays:
- "Court 1" at "Golden Gate Park"
- "basketball court (2 hoops)" at "Washington High School"  (no individual name)
- "tennis court" at NULL  (no facility match)

