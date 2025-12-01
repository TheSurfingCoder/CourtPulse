# Data Enrichment Pipeline

## Overview

• Scripts for enriching court data from OpenStreetMap using the Overpass API
• Queries facilities (parks, schools) and courts (leisure=pitch) separately
• Matches courts to facilities using PostGIS spatial containment
• Stores results in staging tables, then processes into production `courts` table

## Data Model & Schema

### Core Tables

**`courts`** (Production - 10 rows, 256 kB)
- **Purpose**: Production table serving backend API and frontend
- **Key Columns**: `id` (PK), `osm_id` (unique), `sport`, `geom` (PostGIS Polygon), `centroid` (geography Point), `cluster_id`, `individual_court_name`, `school` (boolean)
- **Indexes**: 16 indexes including spatial (GIST) on `geom`/`centroid`, B-tree on `sport`, `cluster_id`, `region`, etc.
- **Health**: ✅ Healthy (no dead tuples, recently analyzed, duplicate indexes removed)

**`osm_facilities`** (Reference - 856 rows, 848 kB)
- **Purpose**: Facilities (parks, playgrounds, schools) from Overpass API
- **Key Columns**: `id` (PK), `osm_id` (unique), `name`, `facility_type`, `geom` (PostGIS Polygon), `bbox` (bounding box)
- **Indexes**: GIST on `geom` and `bbox` for spatial queries
- **Health**: ✅ Healthy (no dead tuples, recently analyzed)

**`osm_courts_temp`** (Staging - 820 rows, 408 kB)
- **Purpose**: Raw court data from Overpass before processing
- **Key Columns**: `id` (PK), `osm_id` (unique), `sport`, `geom` (PostGIS Polygon), `centroid`, `facility_id` (FK → `osm_facilities`)
- **Indexes**: GIST on `centroid` for spatial matching
- **Health**: ✅ Healthy (no dead tuples, recently analyzed)

**`courts_backups`** (Metadata - 0 rows, 24 kB)
- **Purpose**: Tracks backup names and regions for rollback scripts
- **Key Columns**: `id`, `backup_name`, `region`, `created_at`

## Overpass API Data Structures

### Facilities Query Response

**Query**: Parks, playgrounds, schools, universities, colleges

**Response Structure**:
```json
{
  "elements": [
    {
      "type": "way" | "relation",
      "id": 123456789,
      "tags": {
        "leisure": "park" | "playground",
        "amenity": "school" | "university" | "college",
        "name": "Facility Name"
      },
      "geometry": [
        {"lat": 37.7890, "lon": -122.4090},
        {"lat": 37.7891, "lon": -122.4091},
        ...
      ]
    }
  ]
}
```


### Courts Query Response

**Query**: `leisure=pitch` with `sport` tags (basketball, tennis, soccer, volleyball, pickleball)

**Response Structure**:
```json
{
  "elements": [
    {
      "type": "way",
      "id": 987654321,
      "tags": {
        "leisure": "pitch",
        "sport": "basketball" | "tennis" | "soccer" | "volleyball" | "pickleball",
        "hoops": "2" (optional),
        "surface": "asphalt" (optional),
        ... (other OSM tags)
      },
      "geometry": [
        {"lat": 37.7890, "lon": -122.4090},
        {"lat": 37.7891, "lon": -122.4091},
        ...
      ]
    }
  ]
}
```

**Fields Used**:
• `type` - Always "way" for courts
• `id` - OSM element ID
• `tags.sport` - Required: sport type
• `tags.hoops` - Optional: number of hoops (basketball)
• `tags.surface` - Optional: surface type
• `geometry` - Array of coordinate objects forming polygon boundary

## Data Flow

• Overpass API → Query Facilities → `osm_facilities` table
• Overpass API → Query Courts → Validate → Match to facilities → `osm_courts_temp` table
• `osm_courts_temp` → Process/cluster → `courts` table (production)
• Frontend/Backend → Read from `courts` table

## Scripts

### `query_courts_and_facilities.py`

**Main import script**

**Usage**:
```bash
python3 query_courts_and_facilities.py "postgresql://user:pass@host:port/db"
```

**Steps**:
1. Query Overpass for facilities (parks, playgrounds, schools)
2. Insert facilities into `osm_facilities` table
3. Query Overpass for courts (leisure=pitch with sport tags)
4. For each court, find containing facility using PostGIS `ST_Contains` (spatial containment)
5. Insert courts into `osm_courts_temp` with matched `facility_name`
6. **Note**: This script does facility matching, not clustering. Clustering happens later based on `facility_name`

### Other Scripts

• `validation.py` - Validates court data structure, coordinates, and business logic
• `school_checker.py` - Checks if courts are within school facilities using PostGIS spatial queries
• `populate_cluster_metadata.py` - Database-side clustering: groups courts by `facility_name` AND `sport` using SQL, assigns shared `cluster_id` (UUID) in database, transfers to `courts` table
• `add_individual_court_names.py` - Database-side naming: uses SQL window functions to assign sequential names ("Court 1", "Court 2") within each cluster

## Processing Pipeline

1. **Import** - `query_courts_and_facilities.py` populates staging tables
2. **Validation** - Validate court data before further processing
   - GeoJSON structure (geometry, properties)
   - Coordinate validity (ranges, format)
   - Required fields (osm_id/@id, sport)
   - Data types (sport values, hoops as integers)
   - Business logic (basketball hoops, reasonable counts)
3. **Clustering** - Group courts by facility_name and sport
   - **When**: Post-processing step after data is in `osm_courts_temp` (standalone script)
   - **How**: `populate_cluster_metadata.py` uses SQL to group by `facility_name` AND `sport` in database, assigns shared `cluster_id` (UUID) via `gen_random_uuid()`, then transfers to `courts` table
   - **Location**: Database-side (SQL) - efficient single-query operation, no in-memory processing
   - **Result**: Courts with same `facility_name` AND `sport` share same `cluster_id` (e.g., all basketball courts at "Golden Gate Park" = one cluster, all tennis courts = separate cluster)
4. **School Detection** - `school_checker.py` identifies courts within schools
   - PostGIS spatial containment (ST_Contains)
   - Checks against school/university/college facilities
   - Updates facility matching for school courts
5. **Naming** - Assign individual court names within clusters
   - **Flow**: `add_individual_court_names.py` uses database-side SQL with window functions (`ROW_NUMBER()`) to assign sequential names ("Court 1", "Court 2", etc.) within each cluster
   - **Ordering**: Courts ordered by `id` for consistent naming within each cluster
   - **Location**: Database-side (SQL) - single UPDATE query with window functions, no Python loops
   - **Database → Frontend Mapping**:
     - `individual_court_name` → `name`
     - `facility_name` → `cluster_group_name`
     - *Fallback chain for `name`: `enriched_name` → `fallback_name` → `'Unknown Court'`*
     - *Fallback chain for `cluster_group_name`: `enriched_name` → `fallback_name` → `NULL`*
   - **Frontend Display**:
     - **Popup**: Shows `cluster_group_name` as main heading, `name` as subtitle (if different)
     - **Marker tooltip**: Shows `name` for individual courts, point count for clusters
     - **Marker icon**: Sport emoji for individual courts, number for clusters
   - **Examples**:
     - **Single court cluster**: `individual_court_name = NULL` → `name = "basketball court (2 hoops)"` (from `fallback_name`)
     - **Multi-court cluster** (Golden Gate Park, 3 basketball courts, same `facility_name` + `sport`):
       - Court 1: `name = "Court 1"`, `cluster_group_name = "Golden Gate Park"`, `sport = "basketball"`
       - Court 2: `name = "Court 2"`, `cluster_group_name = "Golden Gate Park"`, `sport = "basketball"`
       - Court 3: `name = "Court 3"`, `cluster_group_name = "Golden Gate Park"`, `sport = "basketball"`
     - **Mixed facility** (Lowell High School, 2 basketball + 1 tennis):
       - Basketball Court 1: `name = "Court 1"`, `cluster_id = "uuid-456"`, `sport = "basketball"`
       - Basketball Court 2: `name = "Court 2"`, `cluster_id = "uuid-456"`, `sport = "basketball"`
       - Tennis Court: `name = "Court 1"`, `cluster_id = "uuid-789"`, `sport = "tennis"` (different cluster due to different sport)
6. **Transfer** - Move processed data to `courts` table


