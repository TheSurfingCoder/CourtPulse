#!/usr/bin/env python3
"""
Run the full data enrichment pipeline with the refined POI approach
"""

import json
import geojson
from shapely.geometry import Polygon
from data_enrichment import CourtDataEnricher, HybridGeocodingProvider
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
        # Initialize the enricher
        enricher = CourtDataEnricher()
        
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
            
            # Enrich with geocoding
            print("🔍 Reverse geocoding...")
            enriched_data = enricher.enrich_court_data(court_data)
            
            if enriched_data:
                print(f"✅ Result: {enriched_data.get('enriched_name', 'N/A')}")
                print(f"📍 Address: {enriched_data.get('address', 'N/A')}")
                print(f"🆔 Place ID: {enriched_data.get('google_place_id', 'N/A')}")
                
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
    # Start with 10 features for testing
    results = run_pipeline(num_features=10)
