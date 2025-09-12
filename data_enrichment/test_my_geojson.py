#!/usr/bin/env python3
"""
Simple script to test your local GeoJSON file

This script will:
1. Load your GeoJSON file
2. Parse the first few features
3. Show you what data was extracted
4. Optionally test geocoding (without database)
"""

import json
import sys
import os
from typing import List

# Add current directory to path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_enrichment import CourtDataEnricher, HybridGeocodingProvider, CourtData
from shapely.geometry import shape


def load_and_preview_geojson(file_path: str, max_features: int = 5):
    """Load GeoJSON and show preview of features"""
    print(f"Loading GeoJSON file: {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return None
    
    print(f"✅ File loaded successfully")
    print(f"📊 Total features: {len(data.get('features', []))}")
    
    # Preview first few features
    features = data.get('features', [])
    for i, feature in enumerate(features[:max_features]):
        print(f"\n--- Feature {i+1} ---")
        print(f"ID: {feature.get('id', 'No ID')}")
        print(f"Type: {feature.get('type', 'Unknown')}")
        
        # Show properties
        props = feature.get('properties', {})
        print("Properties:")
        for key, value in props.items():
            print(f"  {key}: {value}")
        
        # Show geometry info
        geom = feature.get('geometry', {})
        print(f"Geometry Type: {geom.get('type', 'Unknown')}")
        
        # Try to calculate centroid
        try:
            shapely_geom = shape(geom)
            if hasattr(shapely_geom, 'centroid'):
                centroid = shapely_geom.centroid
                print(f"Centroid: {centroid.y:.6f}, {centroid.x:.6f}")
            else:
                print(f"Point: {shapely_geom.y:.6f}, {shapely_geom.x:.6f}")
        except Exception as e:
            print(f"⚠️  Geometry processing error: {e}")
    
    return data


def test_geocoding_only(file_path: str, max_features: int = 3):
    """Test geocoding without database"""
    print(f"\n{'='*50}")
    print("TESTING GEOCODING (No Database Required)")
    print(f"{'='*50}")
    
    # Initialize geocoding provider
    provider = HybridGeocodingProvider(delay=0.5)  # Slower delay to be respectful
    
    # Load and parse GeoJSON
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return
    
    features = data.get('features', [])
    print(f"Testing geocoding for first {min(max_features, len(features))} features...")
    
    for i, feature in enumerate(features[:max_features]):
        print(f"\n--- Geocoding Feature {i+1} ---")
        print(f"OSM ID: {feature.get('id', 'Unknown')}")
        
        try:
            # Parse geometry and get centroid
            geom = feature.get('geometry', {})
            shapely_geom = shape(geom)
            
            if hasattr(shapely_geom, 'centroid'):
                centroid = shapely_geom.centroid
                lat, lon = centroid.y, centroid.x
            else:
                lat, lon = shapely_geom.y, shapely_geom.x
            
            print(f"Coordinates: {lat:.6f}, {lon:.6f}")
            
            # Test reverse geocoding
            print("🌍 Reverse geocoding...")
            address, place_id = provider.reverse_geocode(lat, lon)
            
            if address:
                print(f"✅ Address found: {address}")
                if place_id:
                    print(f"📍 Place ID: {place_id}")
            else:
                print("❌ No address found")
                
        except Exception as e:
            print(f"❌ Error processing feature: {e}")


def test_full_pipeline(file_path: str, max_features: int = 3):
    """Test full pipeline with database"""
    print(f"\n{'='*50}")
    print("TESTING FULL PIPELINE (Database Required)")
    print(f"{'='*50}")
    
    # Check if database is configured
    from dotenv import load_dotenv
    load_dotenv()
    
    db_password = os.getenv('DB_PASSWORD')
    if not db_password:
        print("❌ Database not configured. Set DB_PASSWORD in .env file")
        print("   Or use test_geocoding_only() for testing without database")
        return
    
    try:
        from data_enrichment import DatabaseManager, CourtDataEnricher
        
        # Initialize components
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'courtpulse')
        db_user = os.getenv('DB_USER', 'postgres')
        
        connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        db_manager = DatabaseManager(connection_string)
        provider = HybridGeocodingProvider(delay=0.5)
        enricher = CourtDataEnricher(db_manager, provider)
        
        # Create table
        print("Creating database table...")
        db_manager.create_table_if_not_exists()
        
        # Load and process courts
        print(f"Loading and processing first {max_features} courts...")
        courts = enricher.load_geojson(file_path)
        
        for i, court in enumerate(courts[:max_features]):
            print(f"\n--- Processing Court {i+1} ---")
            print(f"OSM ID: {court.osm_id}")
            print(f"Sport: {court.sport}")
            print(f"Coordinates: {court.geom.y:.6f}, {court.geom.x:.6f}")
            
            # Enrich with geocoding
            enriched_court = enricher.enrich_court(court)
            
            print(f"Address: {enriched_court.address}")
            print(f"Place ID: {enriched_court.google_place_id}")
            
            # Insert into database
            success = db_manager.insert_court(enriched_court)
            print(f"Database: {'✅ Success' if success else '❌ Failed'}")
        
        print(f"\n✅ Successfully processed {min(max_features, len(courts))} courts")
        
    except Exception as e:
        print(f"❌ Pipeline error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python3 test_my_geojson.py <path_to_your_geojson_file>")
        print("\nExample:")
        print("  python3 test_my_geojson.py /path/to/your/courts.geojson")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        sys.exit(1)
    
    print("🏀 CourtPulse GeoJSON Tester")
    print("=" * 50)
    
    # Step 1: Preview the GeoJSON file
    data = load_and_preview_geojson(file_path, max_features=3)
    if not data:
        sys.exit(1)
    
    # Ask user what they want to test
    print(f"\n{'='*50}")
    print("What would you like to test?")
    print("1. Geocoding only (no database required)")
    print("2. Full pipeline (database required)")
    print("3. Both")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice in ['1', '3']:
        test_geocoding_only(file_path, max_features=2)
    
    if choice in ['2', '3']:
        test_full_pipeline(file_path, max_features=2)
    
    print(f"\n{'='*50}")
    print("✅ Testing completed!")
    print("Check the output above to see if everything worked correctly.")


if __name__ == "__main__":
    main()
