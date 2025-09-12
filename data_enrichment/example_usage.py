#!/usr/bin/env python3
"""
Example usage of the CourtPulse Data Enrichment Pipeline

This script demonstrates how to use the data enrichment pipeline
with different geocoding providers and custom configurations.
"""

import os
import json
from data_enrichment import (
    CourtDataEnricher, 
    DatabaseManager, 
    HybridGeocodingProvider, 
    GooglePlacesProvider,
    CourtData
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def create_sample_geojson_file():
    """Create a sample GeoJSON file with multiple court features"""
    sample_data = {
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
            },
            {
                "type": "Feature",
                "properties": {
                    "@id": "way/12345678",
                    "sport": "tennis",
                    "leisure": "pitch",
                    "surface": "hard"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-122.4080000, 37.7520000],
                        [-122.4081000, 37.7521000],
                        [-122.4082000, 37.7520000],
                        [-122.4081000, 37.7519000],
                        [-122.4080000, 37.7520000]
                    ]]
                },
                "id": "way/12345678"
            },
            {
                "type": "Feature",
                "properties": {
                    "@id": "way/87654321",
                    "sport": "basketball",
                    "leisure": "pitch",
                    "hoops": "1"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [-122.4100000, 37.7540000]
                },
                "id": "way/87654321"
            }
        ]
    }
    
    filename = 'sample_courts.geojson'
    with open(filename, 'w') as f:
        json.dump(sample_data, f, indent=2)
    
    print(f"Created sample GeoJSON file: {filename}")
    return filename


def example_with_nominatim():
    """Example using Nominatim geocoding provider"""
    print("\n=== Example with Nominatim Provider ===")
    
    # Database connection
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'courtpulse')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', '')
    
    connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Initialize components
    db_manager = DatabaseManager(connection_string)
    geocoding_provider = HybridGeocodingProvider(delay=0.5)  # Faster for demo
    enricher = CourtDataEnricher(db_manager, geocoding_provider)
    
    # Create sample data
    geojson_file = create_sample_geojson_file()
    
    try:
        # Create database table
        db_manager.create_table_if_not_exists()
        
        # Load and process courts
        courts = enricher.load_geojson(geojson_file)
        
        print(f"Loaded {len(courts)} courts from GeoJSON")
        
        # Process each court
        for i, court in enumerate(courts, 1):
            print(f"\n--- Processing Court {i}/{len(courts)} ---")
            print(f"OSM ID: {court.osm_id}")
            print(f"Sport: {court.sport}")
            print(f"Hoops: {court.hoops}")
            print(f"Coordinates: {court.geom.y:.6f}, {court.geom.x:.6f}")
            
            # Enrich with reverse geocoding
            enriched_court = enricher.enrich_court(court)
            
            print(f"Address: {enriched_court.address}")
            print(f"Place ID: {enriched_court.google_place_id}")
            print(f"Enriched Name: {enriched_court.enriched_name}")
            
            # Insert into database
            success = db_manager.insert_court(enriched_court)
            print(f"Database Insertion: {'✓ Success' if success else '✗ Failed'}")
        
        print(f"\n✓ Successfully processed {len(courts)} courts with Nominatim")
        
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        # Clean up
        if os.path.exists(geojson_file):
            os.remove(geojson_file)


def example_with_google_places():
    """Example using Google Places API (requires API key)"""
    print("\n=== Example with Google Places Provider ===")
    
    google_api_key = os.getenv('GOOGLE_PLACES_API_KEY')
    if not google_api_key:
        print("⚠️  Google Places API key not found in environment variables")
        print("   Set GOOGLE_PLACES_API_KEY to use this example")
        return
    
    # Database connection
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'courtpulse')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', '')
    
    connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Initialize components with Google Places
    db_manager = DatabaseManager(connection_string)
    geocoding_provider = GooglePlacesProvider(google_api_key, delay=0.1)
    enricher = CourtDataEnricher(db_manager, geocoding_provider)
    
    # Create sample data
    geojson_file = create_sample_geojson_file()
    
    try:
        # Create database table
        db_manager.create_table_if_not_exists()
        
        # Load and process courts
        courts = enricher.load_geojson(geojson_file)
        
        print(f"Loaded {len(courts)} courts from GeoJSON")
        
        # Process first court only (to avoid API costs)
        court = courts[0]
        print(f"\n--- Processing Court with Google Places ---")
        print(f"OSM ID: {court.osm_id}")
        print(f"Sport: {court.sport}")
        print(f"Coordinates: {court.geom.y:.6f}, {court.geom.x:.6f}")
        
        # Enrich with reverse geocoding
        enriched_court = enricher.enrich_court(court)
        
        print(f"Address: {enriched_court.address}")
        print(f"Place ID: {enriched_court.google_place_id}")
        print(f"Enriched Name: {enriched_court.enriched_name}")
        
        # Insert into database
        success = db_manager.insert_court(enriched_court)
        print(f"Database Insertion: {'✓ Success' if success else '✗ Failed'}")
        
        print(f"\n✓ Successfully processed court with Google Places")
        
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        # Clean up
        if os.path.exists(geojson_file):
            os.remove(geojson_file)


def example_batch_processing():
    """Example of batch processing multiple courts"""
    print("\n=== Example Batch Processing ===")
    
    # Database connection
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'courtpulse')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', '')
    
    connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Initialize components
    db_manager = DatabaseManager(connection_string)
    geocoding_provider = HybridGeocodingProvider(delay=0.3)  # Moderate delay
    enricher = CourtDataEnricher(db_manager, geocoding_provider)
    
    # Create sample data
    geojson_file = create_sample_geojson_file()
    
    try:
        # Create database table
        db_manager.create_table_if_not_exists()
        
        # Load courts
        courts = enricher.load_geojson(geojson_file)
        
        print(f"Processing {len(courts)} courts in batch...")
        
        # Batch process: enrich all courts first
        enriched_courts = []
        for i, court in enumerate(courts, 1):
            print(f"Enriching court {i}/{len(courts)}: {court.osm_id}")
            enriched_court = enricher.enrich_court(court)
            enriched_courts.append(enriched_court)
        
        # Batch insert: insert all courts
        print(f"\nInserting {len(enriched_courts)} courts into database...")
        success_count = 0
        for enriched_court in enriched_courts:
            if db_manager.insert_court(enriched_court):
                success_count += 1
        
        print(f"✓ Successfully processed {success_count}/{len(enriched_courts)} courts")
        
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        # Clean up
        if os.path.exists(geojson_file):
            os.remove(geojson_file)


if __name__ == "__main__":
    print("CourtPulse Data Enrichment Pipeline - Usage Examples")
    print("=" * 60)
    
    # Run examples
    example_with_nominatim()
    example_with_google_places()
    example_batch_processing()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
