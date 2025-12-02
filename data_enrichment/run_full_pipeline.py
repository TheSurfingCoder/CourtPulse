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

def main():
    """Run the complete data enrichment pipeline"""
    
    # Get connection string
    connection_string = os.getenv('DATABASE_URL') or (sys.argv[1] if len(sys.argv) > 1 else None)
    
    if not connection_string:
        print("Error: DATABASE_URL environment variable not set, or provide as argument")
        print("Usage: python3 run_full_pipeline.py 'postgresql://user:pass@host:port/db' [sports]")
        print("Example: python3 run_full_pipeline.py 'postgresql://postgres@localhost:5432/courtpulse-dev' basketball")
        sys.exit(1)
    
    # Get sports filter (optional)
    sports = None
    if len(sys.argv) > 2:
        sports = [s.strip() for s in sys.argv[2].split(',')]
        print(f"🎯 Filtering for sports: {sports}")
    else:
        print("🎯 Processing all sports")
    
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
        facilities_data = querier.query_facilities(SF_BBOX)
        facilities_count = matcher.insert_facilities(facilities_data)
        print(f"   ✅ Imported {facilities_count} facilities")
        
        # Query courts (with optional sport filter)
        courts_data = querier.query_courts(SF_BBOX, sports=sports)
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
        transfer_summary = populator.transfer_courts_to_production()
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
