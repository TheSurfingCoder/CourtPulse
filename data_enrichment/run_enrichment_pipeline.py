#!/usr/bin/env python3
"""
Run the full data enrichment pipeline with the refined POI approach
"""

import json
import geojson
from shapely.geometry import Polygon
from data_enrichment import CourtDataEnricher, HybridGeocodingProvider, DatabaseManager
import os
from dotenv import load_dotenv

load_dotenv()

def run_pipeline(num_features=10):
    """Run the enrichment pipeline for specified number of features"""
    
    print("🏀 CourtPulse Data Enrichment Pipeline")
    print("=" * 60)
    print(f"Processing {num_features} features with refined POI approach")
    print("=" * 60)
    
    # Load the GeoJSON file
    with open('export.geojson', 'r') as f:
        data = json.load(f)
    
    # Get specified number of features
    features = data['features'][:num_features]
    
    try:
        # Create database connection string from environment variables
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'courtpulse-dev')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', '')
        
        connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        # Initialize the database manager and geocoding provider
        db_manager = DatabaseManager(connection_string)
        geocoding_provider = HybridGeocodingProvider()
        
        # Initialize the enricher
        enricher = CourtDataEnricher(db_manager, geocoding_provider)
        
        # Process each feature
        results = []
        
        for i, feature in enumerate(features, 1):
            print(f"\n📍 Processing Feature {i}/{num_features}")
            
            # Get coordinates
            coords = feature['geometry']['coordinates'][0]
            
            # Calculate centroid
            poly = Polygon(coords)
            centroid = poly.centroid
            
            # Get properties
            props = feature.get('properties', {})
            sport = props.get('sport', 'unknown')
            hoops = props.get('hoops', 'unknown')
            osm_id = feature.get('id', 'unknown')
            
            print(f"OSM ID: {osm_id}")
            print(f"Coordinates: {centroid.y:.6f}, {centroid.x:.6f}")
            print(f"Sport: {sport}, Hoops: {hoops}")
            
            # Create court data object
            court_data = {
                'osm_id': osm_id,
                'geometry': feature['geometry'],
                'sport': sport,
                'hoops': hoops,
                'fallback_name': f"Basketball Court ({hoops} hoops)" if hoops != 'unknown' else "Basketball Court"
            }
            
            # Create CourtData object
            from data_enrichment import CourtData
            from shapely.geometry import Point
            import json as json_lib
            
            # Extract original polygon geometry from GeoJSON
            polygon_geojson = json_lib.dumps(feature['geometry'])
            
            court = CourtData(
                osm_id=court_data['osm_id'],
                geom=Point(centroid.x, centroid.y),
                polygon_geojson=polygon_geojson,
                sport=court_data['sport'],
                hoops=court_data['hoops'],
                fallback_name=court_data['fallback_name']
            )
            
            # Enrich with geocoding
            print("🔍 Reverse geocoding...")
            enriched_court = enricher.enrich_court(court)
            
            # Convert back to dictionary for results
            enriched_data = {
                'osm_id': enriched_court.osm_id,
                'sport': enriched_court.sport,
                'hoops': enriched_court.hoops,
                'fallback_name': enriched_court.fallback_name,
                'google_place_id': enriched_court.google_place_id,
                'enriched_name': enriched_court.enriched_name,
                'address': enriched_court.address
            }
            
            if enriched_data:
                print(f"✅ Result: {enriched_data.get('enriched_name', 'N/A')}")
                print(f"📍 Address: {enriched_data.get('address', 'N/A')}")
                print(f"🆔 Place ID: {enriched_data.get('google_place_id', 'N/A')}")
                
                # Insert into database
                print("💾 Inserting into database...")
                try:
                    db_manager.insert_court(enriched_court)
                    print("✅ Database insertion successful")
                except Exception as db_error:
                    print(f"❌ Database insertion failed: {db_error}")
                
                results.append(enriched_data)
            else:
                print("❌ Failed to enrich data")
            
            print("-" * 40)
        
        # Summary
        print(f"\n{'='*60}")
        print("PIPELINE SUMMARY")
        print(f"{'='*60}")
        print(f"Total features processed: {len(features)}")
        print(f"Successfully enriched: {len(results)}")
        print(f"Success rate: {len(results)/len(features)*100:.1f}%")
        
        # Show sample results
        print(f"\nSample Results:")
        for i, result in enumerate(results[:3], 1):
            print(f"{i}. {result.get('enriched_name', 'N/A')}")
            print(f"   Address: {result.get('address', 'N/A')}")
            print(f"   Place ID: {result.get('google_place_id', 'N/A')}")
        
        return results
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    # Process all 401 basketball courts
    results = run_pipeline(num_features=401)

