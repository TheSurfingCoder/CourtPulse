#!/usr/bin/env python3
"""
Quick test of the integrated refined POI approach
"""

import json
import geojson
from shapely.geometry import Polygon
from data_enrichment import HybridGeocodingProvider
import os
from dotenv import load_dotenv

load_dotenv()

def test_integration():
    """Test the integrated approach with first 3 features"""
    
    print("🏀 Quick Integration Test - Refined POI Approach")
    print("=" * 60)
    
    # Load the GeoJSON file
    with open('export.geojson', 'r') as f:
        data = json.load(f)
    
    # Get first 3 features
    features = data['features'][:3]
    
    try:
        provider = HybridGeocodingProvider(delay=0.2)
        
        for i, feature in enumerate(features, 1):
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
            
            print(f"\n📍 Test {i}/3: {osm_id}")
            print(f"Coordinates: {centroid.y:.6f}, {centroid.x:.6f}")
            print(f"Sport: {sport}, Hoops: {hoops}")
            print("-" * 40)
            
            # Test reverse geocoding
            address, place_id = provider.reverse_geocode(centroid.y, centroid.x)
            
            print(f"Result: {address}")
            print(f"Place ID: {place_id}")
            
            if address:
                if any(keyword in address.lower() for keyword in ['basketball', 'court']):
                    print("✅ Found basketball court name!")
                elif any(keyword in address.lower() for keyword in ['park', 'playground', 'center', 'recreation']):
                    print("✅ Found relevant POI name!")
                else:
                    print("⚠️  Found generic POI name")
            else:
                print("❌ No result found")
            
            print("-" * 40)
        
        print(f"\n{'='*60}")
        print("Integration test completed!")
        print(f"{'='*60}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_integration()

