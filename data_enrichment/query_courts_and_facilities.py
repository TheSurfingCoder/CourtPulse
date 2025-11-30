#!/usr/bin/env python3
"""
Query OpenStreetMap Overpass API for:
1. Courts (leisure=pitch with sport tags)
2. Facilities (parks, playgrounds, schools)
3. Match courts to facilities by bounding box containment
4. Store results in PostGIS database
"""

import json
import logging
import requests
import psycopg2
from psycopg2.extras import Json
from typing import Dict, List, Any, Optional, Tuple
from shapely.geometry import Point, Polygon, box
from shapely.prepared import prep
import sys
import os
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# San Francisco bounding box: south, west, north, east
SF_BBOX = (37.7, -122.52, 37.83, -122.35)

class OverpassQuerier:
    """Handles Overpass API queries"""
    
    def __init__(self, base_url: str = 'https://overpass-api.de/api/interpreter'):
        self.base_url = base_url
    
    def query_courts(self, bbox: Tuple[float, float, float, float], sports: List[str] = None) -> Dict[str, Any]:
        """Query for courts: leisure=pitch with sport tags"""
        if sports is None:
            sports = ['basketball', 'tennis', 'soccer', 'volleyball', 'pickleball']
        
        south, west, north, east = bbox
        sport_queries = []
        for sport in sports:
            sport_queries.append(f'  way["leisure"="pitch"]["sport"="{sport}"]({south},{west},{north},{east});')
        
        query = f"""[out:json][timeout:90];
(
{chr(10).join(sport_queries)}
);
out geom;"""
        
        logger.info(f"Querying courts with sports: {sports}")
        return self._execute_query(query)
    
    def query_facilities(self, bbox: Tuple[float, float, float, float]) -> Dict[str, Any]:
        """Query for facilities: parks, playgrounds, schools"""
        south, west, north, east = bbox
        
        query = f"""[out:json][timeout:90];
(
  // Parks
  way["leisure"="park"]({south},{west},{north},{east});
  relation["leisure"="park"]({south},{west},{north},{east});
  // Playgrounds
  way["leisure"="playground"]({south},{west},{north},{east});
  relation["leisure"="playground"]({south},{west},{north},{east});
  // Schools
  way["amenity"="school"]({south},{west},{north},{east});
  relation["amenity"="school"]({south},{west},{north},{east});
  // Universities/colleges
  way["amenity"="university"]({south},{west},{north},{east});
  relation["amenity"="university"]({south},{west},{north},{east});
  way["amenity"="college"]({south},{west},{north},{east});
  relation["amenity"="college"]({south},{west},{north},{east});
);
out geom;"""
        
        logger.info("Querying facilities (parks, playgrounds, schools)")
        return self._execute_query(query)
    
    def _execute_query(self, query: str) -> Dict[str, Any]:
        """Execute Overpass query"""
        try:
            response = requests.post(
                self.base_url,
                data={'data': query},
                timeout=120
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise

class CourtFacilityMatcher:
    """Matches courts to facilities using bounding box containment"""
    
    def __init__(self, connection_string: str):
        self.conn = psycopg2.connect(connection_string)
        self.cursor = self.conn.cursor()
        self._setup_tables()
    
    def _setup_tables(self):
        """Create tables for courts and facilities"""
        # Enable PostGIS
        self.cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        
        # Create facilities table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS osm_facilities (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                osm_id TEXT NOT NULL UNIQUE,
                osm_type TEXT NOT NULL,  -- 'way' or 'relation'
                name TEXT,
                facility_type TEXT,  -- 'park', 'playground', 'school', etc.
                geom GEOMETRY(Polygon, 4326),
                bbox GEOMETRY(Polygon, 4326),  -- Bounding box for fast containment checks
                tags JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)
        
        # Create courts table (temporary, for matching)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS osm_courts_temp (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                osm_id TEXT NOT NULL UNIQUE,
                sport TEXT,
                geom GEOMETRY(Polygon, 4326),
                centroid GEOMETRY(Point, 4326),
                tags JSONB,
                facility_id BIGINT REFERENCES osm_facilities(id),
                facility_name TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)
        
        # Create indexes
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_facilities_geom ON osm_facilities USING GIST(geom);
            CREATE INDEX IF NOT EXISTS idx_facilities_bbox ON osm_facilities USING GIST(bbox);
            CREATE INDEX IF NOT EXISTS idx_courts_centroid ON osm_courts_temp USING GIST(centroid);
        """)
        
        self.conn.commit()
        logger.info("Database tables created/verified")
    
    def extract_geometry(self, element: Dict[str, Any]) -> Optional[Polygon]:
        """Extract polygon geometry from Overpass element"""
        if element.get('type') != 'way':
            # Relations are more complex, skip for now
            return None
        
        geometry = element.get('geometry', [])
        if len(geometry) < 4:
            return None
        
        coords = []
        for node in geometry:
            if 'lat' in node and 'lon' in node:
                coords.append((node['lon'], node['lat']))
        
        if len(coords) < 4:
            return None
        
        # Close polygon if not closed
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        
        try:
            return Polygon(coords)
        except:
            return None
    
    def insert_facilities(self, facilities_data: Dict[str, Any]) -> int:
        """Insert facilities from Overpass response"""
        count = 0
        elements = facilities_data.get('elements', [])
        
        for element in elements:
            try:
                geom = self.extract_geometry(element)
                if not geom:
                    continue
                
                tags = element.get('tags', {})
                name = tags.get('name')
                
                # Determine facility type
                facility_type = None
                if tags.get('leisure') == 'park':
                    facility_type = 'park'
                elif tags.get('leisure') == 'playground':
                    facility_type = 'playground'
                elif tags.get('amenity') == 'school':
                    facility_type = 'school'
                elif tags.get('amenity') == 'university':
                    facility_type = 'university'
                elif tags.get('amenity') == 'college':
                    facility_type = 'college'
                
                if not facility_type:
                    continue
                
                osm_type = 'way' if element.get('type') == 'way' else 'relation'
                osm_id = f"{osm_type}/{element.get('id')}"
                
                # Create bounding box
                bounds = geom.bounds  # (minx, miny, maxx, maxy)
                bbox_poly = box(bounds[0], bounds[1], bounds[2], bounds[3])
                
                # Insert into database
                self.cursor.execute("""
                    INSERT INTO osm_facilities (osm_id, osm_type, name, facility_type, geom, bbox, tags)
                    VALUES (%s, %s, %s, %s, ST_GeomFromText(%s, 4326), ST_GeomFromText(%s, 4326), %s)
                    ON CONFLICT (osm_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        geom = EXCLUDED.geom,
                        bbox = EXCLUDED.bbox,
                        tags = EXCLUDED.tags
                    RETURNING id;
                """, (
                    osm_id,
                    osm_type,
                    name,
                    facility_type,
                    geom.wkt,
                    bbox_poly.wkt,
                    Json(tags)
                ))
                
                count += 1
                
            except Exception as e:
                logger.warning(f"Error inserting facility: {e}")
                continue
        
        self.conn.commit()
        logger.info(f"Inserted {count} facilities")
        return count
    
    def insert_courts(self, courts_data: Dict[str, Any]) -> int:
        """Insert courts from Overpass response"""
        count = 0
        elements = courts_data.get('elements', [])
        
        for element in elements:
            try:
                geom = self.extract_geometry(element)
                if not geom:
                    continue
                
                tags = element.get('tags', {})
                sport = tags.get('sport')
                osm_id = f"way/{element.get('id')}"
                
                # Get centroid
                centroid = geom.centroid
                
                # Find matching facility using PostGIS
                self.cursor.execute("""
                    SELECT id, name
                    FROM osm_facilities
                    WHERE ST_Contains(geom, ST_GeomFromText(%s, 4326))
                    LIMIT 1;
                """, (centroid.wkt,))
                
                result = self.cursor.fetchone()
                facility_id = result[0] if result else None
                facility_name = result[1] if result else None
                
                # Insert court
                self.cursor.execute("""
                    INSERT INTO osm_courts_temp (osm_id, sport, geom, centroid, tags, facility_id, facility_name)
                    VALUES (%s, %s, ST_GeomFromText(%s, 4326), ST_GeomFromText(%s, 4326), %s, %s, %s)
                    ON CONFLICT (osm_id) DO UPDATE SET
                        sport = EXCLUDED.sport,
                        geom = EXCLUDED.geom,
                        centroid = EXCLUDED.centroid,
                        tags = EXCLUDED.tags,
                        facility_id = EXCLUDED.facility_id,
                        facility_name = EXCLUDED.facility_name
                    RETURNING id;
                """, (
                    osm_id,
                    sport,
                    geom.wkt,
                    centroid.wkt,
                    Json(tags),
                    facility_id,
                    facility_name
                ))
                
                count += 1
                
            except Exception as e:
                logger.warning(f"Error inserting court: {e}")
                continue
        
        self.conn.commit()
        logger.info(f"Inserted {count} courts")
        return count
    
    def get_results(self) -> Dict[str, Any]:
        """Get matching results"""
        # Get courts with facility matches
        self.cursor.execute("""
            SELECT 
                c.osm_id,
                c.sport,
                c.facility_name,
                f.name as facility_full_name,
                f.facility_type,
                ST_AsText(c.centroid) as location
            FROM osm_courts_temp c
            LEFT JOIN osm_facilities f ON c.facility_id = f.id
            ORDER BY c.sport, c.facility_name;
        """)
        
        results = []
        for row in self.cursor.fetchall():
            results.append({
                'osm_id': row[0],
                'sport': row[1],
                'facility_name': row[2],
                'facility_full_name': row[3],
                'facility_type': row[4],
                'location': row[5]
            })
        
        return results
    
    def close(self):
        """Close database connection"""
        self.cursor.close()
        self.conn.close()

def main():
    """Main execution"""
    # Get connection string
    connection_string = os.getenv('DATABASE_URL') or (sys.argv[1] if len(sys.argv) > 1 else None)
    
    if not connection_string:
        print("Error: DATABASE_URL environment variable not set, or provide as argument")
        print("Usage: python3 query_courts_and_facilities.py 'postgresql://user:pass@host:port/db'")
        sys.exit(1)
    
    querier = OverpassQuerier()
    matcher = CourtFacilityMatcher(connection_string)
    
    total_start = time.time()
    
    try:
        # Step 1: Query facilities first (parks, playgrounds, schools)
        step1_start = time.time()
        logger.info("Step 1: Querying facilities...")
        facilities_data = querier.query_facilities(SF_BBOX)
        query1_time = time.time() - step1_start
        
        step1_insert_start = time.time()
        facilities_count = matcher.insert_facilities(facilities_data)
        insert1_time = time.time() - step1_insert_start
        step1_total = time.time() - step1_start
        
        logger.info(f"   ✓ Query took {query1_time:.2f}s, Insert took {insert1_time:.2f}s, Total: {step1_total:.2f}s")
        
        # Step 2: Query courts
        step2_start = time.time()
        logger.info("Step 2: Querying courts...")
        courts_data = querier.query_courts(SF_BBOX)
        query2_time = time.time() - step2_start
        
        step2_insert_start = time.time()
        courts_count = matcher.insert_courts(courts_data)
        insert2_time = time.time() - step2_insert_start
        step2_total = time.time() - step2_start
        
        logger.info(f"   ✓ Query took {query2_time:.2f}s, Insert took {insert2_time:.2f}s, Total: {step2_total:.2f}s")
        
        # Step 3: Get results
        step3_start = time.time()
        logger.info("Step 3: Getting matched results...")
        results = matcher.get_results()
        step3_time = time.time() - step3_start
        
        total_time = time.time() - total_start
        
        print(f"\n✅ Complete!")
        print(f"   Facilities found: {facilities_count}")
        print(f"   Courts found: {courts_count}")
        matched_count = len([r for r in results if r['facility_name']])
        print(f"   Courts with facility matches: {matched_count}")
        print(f"\n⏱️  Performance:")
        print(f"   Facilities query: {query1_time:.2f}s")
        print(f"   Facilities insert: {insert1_time:.2f}s ({facilities_count/insert1_time:.1f} records/sec)")
        print(f"   Courts query: {query2_time:.2f}s")
        print(f"   Courts insert: {insert2_time:.2f}s ({courts_count/insert2_time:.1f} records/sec)")
        print(f"   Results retrieval: {step3_time:.2f}s")
        print(f"   Total time: {total_time:.2f}s")
        
        # Show sample results
        print(f"\n📊 Sample matched courts:")
        for result in results[:10]:
            if result['facility_name']:
                print(f"   {result['sport']}: {result['facility_name']} ({result['facility_type']})")
        
    finally:
        matcher.close()

if __name__ == '__main__':
    main()

