#!/usr/bin/env python3
"""
Full data enrichment pipeline - runs all steps in sequence:
1. Query facilities and courts from Overpass API
2. Match courts to facilities
3. Cluster courts by facility_name + sport
4. Assign individual court names
5. Transfer to production courts table
"""

import sys
import os
import json
import logging
import psycopg2
from query_courts_and_facilities import OverpassQuerier, CourtFacilityMatcher
from populate_cluster_metadata import ClusterMetadataPopulator
from add_individual_court_names import IndividualCourtNameManager
from school_checker import SchoolChecker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# San Francisco bounding box
SF_BBOX = (37.7, -122.52, 37.83, -122.35)

def record_coverage_area(connection_string, bbox, region, name, court_count):
    """
    Record or update coverage area in the database

    Args:
        connection_string: PostgreSQL connection string
        bbox: Tuple of (min_lat, min_lon, max_lat, max_lon)
        region: Region identifier (e.g., 'sf_bay')
        name: Coverage area name (e.g., 'San Francisco')
        court_count: Number of courts in this area
    """
    min_lat, min_lon, max_lat, max_lon = bbox

    # Create GeoJSON polygon from bounding box
    # Polygon coordinates are [lon, lat] and must close (first point == last point)
    boundary_geojson = {
        "type": "Polygon",
        "coordinates": [[
            [min_lon, min_lat],  # Bottom-left
            [max_lon, min_lat],  # Bottom-right
            [max_lon, max_lat],  # Top-right
            [min_lon, max_lat],  # Top-left
            [min_lon, min_lat]   # Close polygon
        ]]
    }

    conn = psycopg2.connect(connection_string)
    cursor = conn.cursor()

    try:
        # Upsert coverage area
        cursor.execute("""
            INSERT INTO coverage_areas (name, region, boundary, court_count, last_updated)
            VALUES (%s, %s, ST_GeomFromGeoJSON(%s), %s, NOW())
            ON CONFLICT (region, name)
                DO UPDATE SET
                    boundary = ST_GeomFromGeoJSON(%s),
                    court_count = %s,
                    last_updated = NOW()
        """, (name, region, json.dumps(boundary_geojson), court_count,
              json.dumps(boundary_geojson), court_count))

        conn.commit()
        logger.info(f"   ✅ Coverage area '{name}' recorded with {court_count} courts")

    except Exception as e:
        conn.rollback()
        logger.error(f"   ❌ Failed to record coverage area: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

def main():
    """Run the complete data enrichment pipeline"""
    
    # Get connection string
    connection_string = os.getenv('DATABASE_URL') or (sys.argv[1] if len(sys.argv) > 1 else None)
    
    if not connection_string:
        print("Error: DATABASE_URL environment variable not set, or provide as argument")
        print("Usage: python3 run_full_pipeline.py 'postgresql://user:pass@host:port/db' [sports] [bbox] [region] [area_name]")
        print("\nArguments:")
        print("  connection_string  - PostgreSQL connection string (or set DATABASE_URL env var)")
        print("  sports            - Comma-separated sports (optional, default: all)")
        print("  bbox              - Bounding box as 'min_lat,min_lon,max_lat,max_lon' (optional, default: SF)")
        print("  region            - Region identifier (optional, default: 'sf_bay')")
        print("  area_name         - Coverage area name (optional, default: 'San Francisco')")
        print("\nExamples:")
        print("  python3 run_full_pipeline.py 'postgresql://postgres@localhost:5432/courtpulse-dev'")
        print("  python3 run_full_pipeline.py 'postgresql://postgres@localhost:5432/courtpulse-dev' basketball")
        print("  python3 run_full_pipeline.py 'postgresql://postgres@localhost:5432/courtpulse-dev' basketball '37.86,-122.15,37.94,-122.00' sf_bay 'Walnut Creek'")
        sys.exit(1)
    
    # Get sports filter (optional)
    sports = None
    if len(sys.argv) > 2:
        sports = [s.strip() for s in sys.argv[2].split(',')]
        print(f"🎯 Filtering for sports: {sports}")
    else:
        print("🎯 Processing all sports")
    
    # Get bounding box (optional, default to SF)
    bbox = SF_BBOX
    region = 'sf_bay'
    area_name = 'San Francisco'
    
    if len(sys.argv) > 3:
        try:
            bbox_parts = [float(x.strip()) for x in sys.argv[3].split(',')]
            if len(bbox_parts) != 4:
                raise ValueError("Bounding box must have exactly 4 values")
            bbox = tuple(bbox_parts)
            print(f"📍 Using custom bounding box: {bbox}")
        except (ValueError, IndexError) as e:
            print(f"Error: Invalid bounding box format: {e}")
            print("Expected format: 'min_lat,min_lon,max_lat,max_lon'")
            sys.exit(1)
    
    if len(sys.argv) > 4:
        region = sys.argv[4]
        print(f"🗺️  Using region: {region}")
    
    if len(sys.argv) > 5:
        area_name = sys.argv[5]
        print(f"📌 Using area name: {area_name}")
    
    print("\n" + "="*60)
    print("🏀 COURT PULSE - FULL DATA ENRICHMENT PIPELINE")
    print("="*60)
    print()
    
    try:
        # Step 1: Query and import facilities and courts
        print("📥 STEP 1: Querying Overpass API and importing data...")
        print("-" * 60)
        querier = OverpassQuerier()
        matcher = CourtFacilityMatcher(connection_string)
        
        # Query facilities
        facilities_data = querier.query_facilities(bbox)
        facilities_count = matcher.insert_facilities(facilities_data)
        print(f"   ✅ Imported {facilities_count} facilities")
        
        # Query courts (with optional sport filter)
        courts_data = querier.query_courts(bbox, sports=sports)
        courts_count = matcher.insert_courts(courts_data)
        print(f"   ✅ Imported {courts_count} courts")
        print()
        
        # Step 2: Detect schools
        print("🏫 STEP 2: Detecting courts within schools...")
        print("-" * 60)
        school_checker = SchoolChecker(connection_string)
        school_summary = school_checker.batch_check_courts_in_schools()
        print(f"   ✅ Checked {school_summary['total_courts_checked']} courts")
        print(f"   ✅ Found {school_summary['courts_in_schools']} courts within schools")
        school_checker.close()
        print()
        
        # Step 3: Cluster courts
        print("🔗 STEP 3: Clustering courts by facility_name + sport...")
        print("-" * 60)
        populator = ClusterMetadataPopulator(connection_string)
        cluster_summary = populator.populate_cluster_metadata()
        print(f"   ✅ Created {cluster_summary['total_clusters']} clusters")
        print(f"   ✅ {cluster_summary['multi_court_clusters']} multi-court clusters")
        print(f"   ✅ Largest cluster: {cluster_summary['largest_cluster_size']} courts")
        
        # Transfer courts to production table
        transfer_summary = populator.transfer_courts_to_production(region=region)
        print(f"   ✅ Transferred {transfer_summary['inserted_or_updated_courts']} courts to production table")
        print()
        
        # Step 4: Assign individual court names
        print("🏷️  STEP 4: Assigning individual court names...")
        print("-" * 60)
        name_manager = IndividualCourtNameManager(connection_string)
        if not name_manager.verify_individual_court_name_column():
            print("   ❌ Column 'individual_court_name' does not exist. Please run migrations first.")
            return False
        name_summary = name_manager.populate_individual_court_names()
        print(f"   ✅ Assigned names to {name_summary.get('updated_courts', 0)} courts")
        if name_summary.get('clusters_with_names', 0) > 0:
            print(f"   ✅ {name_summary['clusters_with_names']} clusters have named courts")
        print()

        # Step 5: Record coverage area
        print("📍 STEP 5: Recording coverage area...")
        print("-" * 60)
        record_coverage_area(
            connection_string=connection_string,
            bbox=bbox,
            region=region,
            name=area_name,
            court_count=courts_count
        )
        print()

        # Cleanup
        matcher.close()

        # Final summary
        print("="*60)
        print("✅ PIPELINE COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"   Facilities: {facilities_count}")
        print(f"   Courts: {courts_count}")
        print(f"   Clusters: {cluster_summary['total_clusters']}")
        print(f"   Named courts: {name_summary['updated_courts']}")
        print()
        print("🎉 Your courts are ready to display on the map!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)




