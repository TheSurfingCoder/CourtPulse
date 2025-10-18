#!/usr/bin/env python3
"""
Debug script to investigate why Moscone Recreation Center wasn't found in park search
"""

import json
import requests
import time
from typing import Dict, Any, List

def test_park_search(lat: float, lon: float):
    """Test park search with the same parameters as the pipeline"""
    
    base_url = "https://photon.komoot.io"
    
    # Same park search parameters as in the pipeline
    leisure_types = [
        {'osm_tag': 'leisure:park', 'q': 'park'},
        {'osm_tag': 'leisure:playground', 'q': 'playground'},
        {'osm_tag': 'leisure:recreation_ground', 'q': 'recreation'}
    ]
    
    # Test different zoom levels to find Moscone Recreation Center
    zoom_levels = [16, 17, 18, 19, 20]  # Different search radii
    
    print(f"🔍 Testing park search for coordinates: {lat}, {lon}")
    print("="*80)
    
    all_results = []
    
    for leisure_type in leisure_types:
        print(f"\n📋 Testing: {leisure_type['osm_tag']} with q='{leisure_type['q']}'")
        
        # Test different zoom levels to find Moscone Recreation Center
        for zoom in zoom_levels:
            print(f"\n   🔍 Testing zoom {zoom} (radius: ~{300 * (2**(18-zoom)):.0f}m)")
            
            try:
                params = {
                    'q': leisure_type['q'],
                    'lat': lat,
                    'lon': lon,
                    'osm_tag': leisure_type['osm_tag'],
                    'location_bias_scale': 0.2,  # Default prominence bias
                    'zoom': zoom,
                    'limit': 10  # Get more results for debugging
                }
            
                print(f"      📡 API URL: {base_url}/api")
                print(f"      📋 Params: {params}")
                
                response = requests.get(f"{base_url}/api", params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                features = data.get('features', [])
                print(f"      📊 Found {len(features)} results")
                
                found_moscone = False
                for i, feature in enumerate(features):
                    properties = feature.get('properties', {})
                    name = properties.get('name', 'Unknown')
                    osm_id = properties.get('osm_id', 'Unknown')
                    extent = properties.get('extent', [])
                    
                    # Calculate distance
                    coords = feature.get('geometry', {}).get('coordinates', [])
                    if coords:
                        result_lon, result_lat = coords[0], coords[1]
                        distance = calculate_distance(lat, lon, result_lat, result_lon)
                        
                        # Check if inside bounding box
                        is_inside = False
                        if extent and len(extent) == 4:
                            min_lon, max_lat, max_lon, min_lat = extent
                            is_inside = (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon)
                        
                        # Only show results if they're close or if it's Moscone
                        if distance < 0.5 or 'moscone' in name.lower() or 'recreation' in name.lower():
                            print(f"         {i+1}. {name}")
                            print(f"            OSM ID: {osm_id}")
                            print(f"            Distance: {distance:.3f} km")
                            print(f"            Extent: {extent}")
                            print(f"            Inside bbox: {is_inside}")
                            
                            # Check if this is Moscone Recreation Center
                            if 'moscone' in name.lower() and 'recreation' in name.lower():
                                print(f"            🎯 FOUND MOSCONE RECREATION CENTER!")
                                found_moscone = True
                            elif 'moscone' in name.lower() or 'recreation' in name.lower():
                                print(f"            🎯 POTENTIAL MATCH: {name}")
                        
                        all_results.append({
                            'name': name,
                            'osm_id': osm_id,
                            'distance': distance,
                            'extent': extent,
                            'is_inside': is_inside,
                            'search_type': leisure_type['osm_tag'],
                            'zoom': zoom
                        })
                
                if found_moscone:
                    print(f"      ✅ Found Moscone Recreation Center at zoom {zoom}!")
                    break  # Stop testing other zoom levels for this search type
                
                time.sleep(1)  # Rate limiting
            
            except Exception as e:
                print(f"      ❌ Error: {e}")
    
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    
    # Look for Moscone specifically
    moscone_results = [r for r in all_results if 'moscone' in r['name'].lower()]
    recreation_results = [r for r in all_results if 'recreation' in r['name'].lower()]
    inside_results = [r for r in all_results if r['is_inside']]
    
    print(f"Total results found: {len(all_results)}")
    print(f"Results inside bounding box: {len(inside_results)}")
    print(f"Moscone-related results: {len(moscone_results)}")
    print(f"Recreation-related results: {len(recreation_results)}")
    
    if inside_results:
        print("\n🎯 Results inside bounding box:")
        for result in inside_results:
            print(f"   - {result['name']} ({result['distance']:.3f} km)")
    
    if moscone_results:
        print("\n🎯 Moscone results:")
        for result in moscone_results:
            print(f"   - {result['name']} ({result['distance']:.3f} km)")
    
    return all_results

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in kilometers"""
    from math import radians, cos, sin, asin, sqrt
    
    # Haversine formula
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Earth's radius in kilometers
    return c * r

if __name__ == "__main__":
    # Test coordinates for Way 32649024
    court_lat = 37.80209232
    court_lon = -122.43441733999998
    
    print("🔍 Debugging Park Search for Way 32649024")
    print("📍 Court coordinates:", court_lat, court_lon)
    print("🎯 Expected: Moscone Recreation Center should be found")
    print()
    
    results = test_park_search(court_lat, court_lon)
