"""
Test script to verify naming conventions for clustered courts
"""

import json
import logging
import psycopg2
from typing import Dict, Any, List
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NamingConventionTester:
    """Test and verify naming conventions for court data"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
    
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.connection_string)
    
    def test_current_naming(self):
        """Test current naming conventions"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get the Gateway High School cluster
            cursor.execute("""
                SELECT 
                    id, osm_id, photon_name, enriched_name, fallback_name,
                    cluster_id, ST_AsText(ST_Centroid(geom)) as centroid
                FROM courts 
                WHERE cluster_id = '458bf3f2-ba6b-4c2a-a883-1bb62139d3b4' 
                ORDER BY id
            """)
            
            results = cursor.fetchall()
            
            print("🔍 CURRENT NAMING CONVENTION TEST")
            print("=" * 60)
            print(f"Found {len(results)} courts in Gateway High School cluster")
            print()
            
            for row in results:
                id, osm_id, photon_name, enriched_name, fallback_name, cluster_id, centroid = row
                print(f"Court ID: {id}")
                print(f"  OSM ID: {osm_id}")
                print(f"  Photon Name: {photon_name}")
                print(f"  Enriched Name: {enriched_name}")
                print(f"  Fallback Name: {fallback_name}")
                print(f"  Cluster ID: {cluster_id}")
                print(f"  Centroid: {centroid}")
                print()
            
            # Test current API response
            print("🌐 TESTING CURRENT API RESPONSE")
            print("=" * 60)
            
            cursor.execute("""
                SELECT 
                    id, 
                    COALESCE(photon_name, enriched_name, fallback_name, 'Unknown Court') as name,
                    sport as type
                FROM courts 
                WHERE cluster_id = '458bf3f2-ba6b-4c2a-a883-1bb62139d3b4'
                LIMIT 1
            """)
            
            api_result = cursor.fetchone()
            if api_result:
                id, name, type = api_result
                print(f"API returns: {name} (type: {type})")
                print()
            
            return results
            
        except Exception as e:
            logger.error(f"Error testing current naming: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def test_proposed_naming(self):
        """Test proposed naming conventions"""
        print("🎯 PROPOSED NAMING CONVENTION")
        print("=" * 60)
        
        # Simulate the proposed structure
        proposed_structure = {
            "cluster_group": {
                "photon_name": "Gateway High School",  # No court count
                "enriched_name": "Outdoor Basketball Courts - Western Addition",
                "fallback_name": "Basketball Courts"
            },
            "individual_courts": [
                {
                    "id": 167,
                    "individual_name": "Court 1",
                    "osm_id": "way/1091052491"
                },
                {
                    "id": 168,
                    "individual_name": "Court 2", 
                    "osm_id": "way/1091052492"
                },
                {
                    "id": 169,
                    "individual_name": "Court 3",
                    "osm_id": "way/1091052493"
                },
                {
                    "id": 170,
                    "individual_name": "Court 4",
                    "osm_id": "way/1091052494"
                }
            ]
        }
        
        print("Cluster Group Name:", proposed_structure["cluster_group"]["photon_name"])
        print("Individual Courts:")
        for court in proposed_structure["individual_courts"]:
            print(f"  - {court['individual_name']} (ID: {court['id']})")
        print()
        
        return proposed_structure
    
    def generate_test_data(self):
        """Generate test data for the new naming convention"""
        print("📊 GENERATING TEST DATA")
        print("=" * 60)
        
        # This would be the new database structure
        test_cases = [
            {
                "scenario": "School with multiple courts",
                "cluster_group_name": "Gateway High School",
                "courts": [
                    {"individual_name": "Court 1", "type": "basketball"},
                    {"individual_name": "Court 2", "type": "basketball"},
                    {"individual_name": "Court 3", "type": "basketball"},
                    {"individual_name": "Court 4", "type": "basketball"}
                ]
            },
            {
                "scenario": "Park with mixed courts",
                "cluster_group_name": "Golden Gate Park",
                "courts": [
                    {"individual_name": "Court 1", "type": "basketball"},
                    {"individual_name": "Court 2", "type": "tennis"}
                ]
            },
            {
                "scenario": "Single court (no clustering needed)",
                "cluster_group_name": None,
                "courts": [
                    {"individual_name": "Basketball Court", "type": "basketball"}
                ]
            }
        ]
        
        for i, case in enumerate(test_cases, 1):
            print(f"Test Case {i}: {case['scenario']}")
            if case['cluster_group_name']:
                print(f"  Group Name: {case['cluster_group_name']}")
            else:
                print(f"  Group Name: None (individual court)")
            
            for court in case['courts']:
                print(f"  - {court['individual_name']} ({court['type']})")
            print()
        
        return test_cases

def main():
    """Main test function"""
    print("🏀 COURT NAMING CONVENTION TESTER")
    print("=" * 60)
    
    # Database connection
    connection_string = os.getenv('DATABASE_URL')
    if not connection_string:
        print("❌ DATABASE_URL not found in environment variables")
        return
    
    tester = NamingConventionTester(connection_string)
    
    # Test current naming
    current_results = tester.test_current_naming()
    
    # Test proposed naming
    proposed_structure = tester.test_proposed_naming()
    
    # Generate test data
    test_cases = tester.generate_test_data()
    
    print("✅ TEST COMPLETED")
    print("=" * 60)
    print("Next steps:")
    print("1. Update data enrichment pipeline to remove court count from photon_name")
    print("2. Add individual court naming logic")
    print("3. Update database schema if needed")
    print("4. Update frontend display logic")

if __name__ == "__main__":
    main()
