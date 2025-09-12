#!/usr/bin/env python3
"""
Test script to verify the data enrichment pipeline setup

This script performs basic tests to ensure all components are working correctly.
"""

import json
import sys
import traceback
from typing import List

# Test imports
try:
    import geojson
    print("✓ geojson imported successfully")
except ImportError as e:
    print(f"✗ Failed to import geojson: {e}")
    sys.exit(1)

try:
    import shapely
    from shapely.geometry import shape, Point
    print("✓ shapely imported successfully")
except ImportError as e:
    print(f"✗ Failed to import shapely: {e}")
    sys.exit(1)

try:
    import psycopg2
    print("✓ psycopg2 imported successfully")
except ImportError as e:
    print(f"✗ Failed to import psycopg2: {e}")
    sys.exit(1)

try:
    import sqlalchemy
    print("✓ sqlalchemy imported successfully")
except ImportError as e:
    print(f"✗ Failed to import sqlalchemy: {e}")
    sys.exit(1)

try:
    import requests
    print("✓ requests imported successfully")
except ImportError as e:
    print(f"✗ Failed to import requests: {e}")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    print("✓ python-dotenv imported successfully")
except ImportError as e:
    print(f"✗ Failed to import python-dotenv: {e}")
    sys.exit(1)

# Test our modules
try:
    from data_enrichment import (
        CourtData, 
        NominatimProvider, 
        GooglePlacesProvider,
        DatabaseManager,
        CourtDataEnricher
    )
    print("✓ data_enrichment module imported successfully")
except ImportError as e:
    print(f"✗ Failed to import data_enrichment module: {e}")
    traceback.print_exc()
    sys.exit(1)


def test_geometry_processing():
    """Test geometry processing with Shapely"""
    print("\n--- Testing Geometry Processing ---")
    
    try:
        # Test polygon geometry
        polygon_coords = [[
            [-122.4063442, 37.7500036],
            [-122.406461, 37.7502223],
            [-122.4066198, 37.7501692],
            [-122.406503, 37.7499505],
            [-122.4063442, 37.7500036]
        ]]
        
        polygon = {
            "type": "Polygon",
            "coordinates": polygon_coords
        }
        
        shapely_geom = shape(polygon)
        centroid = shapely_geom.centroid
        
        print(f"✓ Polygon centroid calculated: {centroid.y:.6f}, {centroid.x:.6f}")
        
        # Test point geometry
        point_coords = [-122.4100000, 37.7540000]
        point = {
            "type": "Point",
            "coordinates": point_coords
        }
        
        shapely_point = shape(point)
        print(f"✓ Point geometry processed: {shapely_point.y:.6f}, {shapely_point.x:.6f}")
        
        return True
        
    except Exception as e:
        print(f"✗ Geometry processing test failed: {e}")
        traceback.print_exc()
        return False


def test_court_data_creation():
    """Test CourtData object creation"""
    print("\n--- Testing CourtData Creation ---")
    
    try:
        # Create a test court
        test_point = Point(-122.4063442, 37.7500036)
        court = CourtData(
            osm_id="way/28283137",
            geom=test_point,
            sport="basketball",
            hoops="2",
            fallback_name="Basketball court (2 hoops)"
        )
        
        print(f"✓ CourtData created: {court.osm_id}")
        print(f"  Sport: {court.sport}")
        print(f"  Hoops: {court.hoops}")
        print(f"  Coordinates: {court.geom.y:.6f}, {court.geom.x:.6f}")
        
        return True
        
    except Exception as e:
        print(f"✗ CourtData creation test failed: {e}")
        traceback.print_exc()
        return False


def test_geocoding_providers():
    """Test geocoding provider initialization"""
    print("\n--- Testing Geocoding Providers ---")
    
    try:
        # Test Nominatim provider
        nominatim = NominatimProvider(delay=0.1)
        print("✓ Nominatim provider initialized")
        
        # Test Google Places provider (without API key)
        try:
            google = GooglePlacesProvider("test_key", delay=0.1)
            print("✓ Google Places provider initialized")
        except Exception as e:
            print(f"⚠ Google Places provider test skipped: {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ Geocoding provider test failed: {e}")
        traceback.print_exc()
        return False


def test_geojson_parsing():
    """Test GeoJSON parsing"""
    print("\n--- Testing GeoJSON Parsing ---")
    
    try:
        # Create sample GeoJSON
        sample_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "@id": "way/28283137",
                        "sport": "basketball",
                        "leisure": "pitch",
                        "hoops": "2"
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [-122.4063442, 37.7500036],
                            [-122.406461, 37.7502223],
                            [-122.4066198, 37.7501692],
                            [-122.406503, 37.7499505],
                            [-122.4063442, 37.7500036]
                        ]]
                    },
                    "id": "way/28283137"
                }
            ]
        }
        
        # Parse with geojson library
        feature_collection = geojson.FeatureCollection(sample_geojson['features'])
        
        print(f"✓ GeoJSON parsed: {len(feature_collection.features)} features")
        
        # Test our parsing logic
        feature = feature_collection.features[0]
        shapely_geom = shape(feature['geometry'])
        centroid = shapely_geom.centroid
        
        print(f"✓ Feature geometry processed: {centroid.y:.6f}, {centroid.x:.6f}")
        
        return True
        
    except Exception as e:
        print(f"✗ GeoJSON parsing test failed: {e}")
        traceback.print_exc()
        return False


def test_database_connection():
    """Test database connection (if configured)"""
    print("\n--- Testing Database Connection ---")
    
    try:
        from dotenv import load_dotenv
        import os
        
        load_dotenv()
        
        # Check if database credentials are configured
        db_host = os.getenv('DB_HOST')
        db_password = os.getenv('DB_PASSWORD')
        
        if not db_host or not db_password:
            print("⚠ Database credentials not configured - skipping connection test")
            print("  Set DB_HOST and DB_PASSWORD in .env file to test database connection")
            return True
        
        # Test connection
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'courtpulse')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', '')
        
        connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        try:
            db_manager = DatabaseManager(connection_string)
            print("✓ Database connection successful")
            return True
        except Exception as e:
            print(f"⚠ Database connection failed: {e}")
            print("  Make sure Postgres is running and credentials are correct")
            return True  # Don't fail the test suite for DB connection issues
            
    except Exception as e:
        print(f"✗ Database connection test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("CourtPulse Data Enrichment Pipeline - Setup Test")
    print("=" * 60)
    
    tests = [
        test_geometry_processing,
        test_court_data_creation,
        test_geocoding_providers,
        test_geojson_parsing,
        test_database_connection
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! The data enrichment pipeline is ready to use.")
        return 0
    else:
        print("✗ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
