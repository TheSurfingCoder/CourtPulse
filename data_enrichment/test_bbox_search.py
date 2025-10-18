#!/usr/bin/env python3
"""
Test Photon's bounding box search to find facilities around a specific court
"""

import json
import requests
import time
from typing import Dict, Any, List

def test_bbox_search(lat: float, lon: float, bbox_size_km: float = 0.5):
    """Test bounding box search around court coordinates"""
    
    base_url = "https://photon.komoot.io"
    
    # Calculate bounding box around the court
    # Convert km to degrees (rough approximation: 1 degree ≈ 111 km)
    lat_offset = bbox_size_km / 111.0
    lon_offset = bbox_size_km / (111.0 * abs(lat * 3.14159 / 180))  # Adjust for latitude
    
    min_lon = lon - lon_offset
    min_lat = lat - lat_offset
    max_lon = lon + lon_offset
    max_lat = lat + lat_offset
    
    bbox = f"{min_lon},{min_lat},{max_lon},{max_lat}"
    
    print(f"🔍 Testing bounding box search around: {lat}, {lon}")
    print(f"📦 Bounding box: {bbox} ({bbox_size_km}km radius)")
    print("="*80)
    
    # Test different search terms
    search_terms = [
        "moscone",
        "recreation",
        "park",
        "playground",
        "center"
    ]
    
    all_results = []
    
    for term in search_terms:
        print(f"\n🔍 Searching for: '{term}'")
        
        try:
            params = {
                'q': term,
                'bbox': bbox
            }
            
            print(f"   📡 API URL: {base_url}/api")
            print(f"   📋 Params: {params}")
            
            response = requests.get(f"{base_url}/api", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            features = data.get('features', [])
            print(f"   📊 Found {len(features)} results")
            
            for i, feature in enumerate(features):
                properties = feature.get('properties', {})
                name = properties.get('name', 'Unknown')
                osm_id = properties.get('osm_id', 'Unknown')
                osm_key = properties.get('osm_key', 'Unknown')
                osm_value = properties.get('osm_value', 'Unknown')
                extent = properties.get('extent', [])
                
                # Calculate distance from court
                coords = feature.get('geometry', {}).get('coordinates', [])
                if coords:
                    result_lon, result_lat = coords[0], coords[1]
                    distance = calculate_distance(lat, lon, result_lat, result_lon)
                    
                    # Check if inside bounding box
                    is_inside = False
                    if extent and len(extent) == 4:
                        min_lon_extent, max_lat_extent, max_lon_extent, min_lat_extent = extent
                        is_inside = (min_lat_extent <= lat <= max_lat_extent and min_lon_extent <= lon <= max_lon_extent)
                    
                    # Only show results within reasonable distance or if they're Moscone-related
                    if distance < 1.0 or 'moscone' in name.lower():
                        print(f"      {i+1}. {name}")
                        print(f"         OSM ID: {osm_id}")
                        print(f"         OSM Key/Value: {osm_key}:{osm_value}")
                        print(f"         Distance: {distance:.3f} km")
                        print(f"         Extent: {extent}")
                        print(f"         Inside bbox: {is_inside}")
                        
                        # Check if this is Moscone Recreation Center
                        if 'moscone' in name.lower() and 'recreation' in name.lower():
                            print(f"         🎯 FOUND MOSCONE RECREATION CENTER!")
                        elif 'moscone' in name.lower():
                            print(f"         🎯 MOSCONE-RELATED: {name}")
                    
                    all_results.append({
                        'name': name,
                        'osm_id': osm_id,
                        'osm_key': osm_key,
                        'osm_value': osm_value,
                        'distance': distance,
                        'extent': extent,
                        'is_inside': is_inside,
                        'search_term': term
                    })
            
            time.sleep(1)  # Rate limiting
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    
    # Look for Moscone specifically
    moscone_results = [r for r in all_results if 'moscone' in r['name'].lower()]
    inside_results = [r for r in all_results if r['is_inside']]
    close_results = [r for r in all_results if r['distance'] < 0.2]
    
    print(f"Total results found: {len(all_results)}")
    print(f"Results inside bounding box: {len(inside_results)}")
    print(f"Results within 200m: {len(close_results)}")
    print(f"Moscone-related results: {len(moscone_results)}")
    
    if inside_results:
        print("\n🎯 Results inside bounding box:")
        for result in inside_results:
            print(f"   - {result['name']} ({result['distance']:.3f} km)")
    
    if close_results:
        print("\n🎯 Results within 200m:")
        for result in close_results:
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
    
    print("🔍 Testing Photon Bounding Box Search for Way 32649024")
    print("📍 Court coordinates:", court_lat, court_lon)
    print("🎯 Looking for Moscone Recreation Center and nearby facilities")
    print()
    
    # Test with different bounding box sizes
    for size in [0.3, 0.5, 1.0]:  # 300m, 500m, 1km
        print(f"\n{'='*60}")
        print(f"Testing with {size}km bounding box")
        print(f"{'='*60}")
        results = test_bbox_search(court_lat, court_lon, size)
        
        # Check if we found Moscone Recreation Center
        moscone_rc = [r for r in results if 'moscone' in r['name'].lower() and 'recreation' in r['name'].lower()]
        if moscone_rc:
            print(f"\n✅ SUCCESS! Found Moscone Recreation Center with {size}km bbox!")
            break
