#!/usr/bin/env python3
"""
Test bounding box search on Way 1106815330
"""

import json
import requests
from typing import List, Dict, Any, Tuple

def calculate_centroid(coordinates: List[List[List[float]]]) -> Tuple[float, float]:
    """Calculate centroid of a polygon"""
    ring = coordinates[0]  # Get the outer ring
    total_lon = sum(coord[0] for coord in ring) / len(ring)
    total_lat = sum(coord[1] for coord in ring) / len(ring)
    return total_lat, total_lon

def create_bbox_around_point(lat: float, lon: float, buffer_km: float = 0.3) -> Tuple[float, float, float, float]:
    """Create bounding box around a point"""
    lat_buffer = buffer_km / 111.0
    lon_buffer = buffer_km / (111.0 * abs(lat * 3.14159 / 180))
    
    return (
        lon - lon_buffer,  # min_lon
        lat - lat_buffer,  # min_lat  
        lon + lon_buffer,  # max_lon
        lat + lat_buffer   # max_lat
    )

def search_facilities_in_bbox(bbox: Tuple[float, float, float, float], search_terms: List[str]) -> List[Dict[str, Any]]:
    """Search for facilities within a bounding box"""
    if not bbox:
        return []
    
    base_url = "https://photon.komoot.io"
    bbox_str = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
    
    all_facilities = []
    
    for term in search_terms:
        try:
            params = {
                'q': term,
                'bbox': bbox_str,
                'limit': 20
            }
            
            response = requests.get(f"{base_url}/api", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            features = data.get('features', [])
            print(f"   Found {len(features)} results for '{term}'")
            
            all_facilities.extend(features)
            
        except Exception as e:
            print(f"   Error searching for '{term}': {e}")
    
    return all_facilities

def find_best_facility_match(court_lat: float, court_lon: float, facilities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Find the best facility match for the court"""
    if not facilities:
        return None
    
    best_match = None
    best_distance = float('inf')
    
    for facility in facilities:
        properties = facility.get('properties', {})
        name = properties.get('name', '')
        
        # Get facility coordinates
        coords = facility.get('geometry', {}).get('coordinates', [])
        if not coords:
            continue
            
        facility_lon, facility_lat = coords[0], coords[1]
        
        # Calculate distance
        distance = calculate_distance(court_lat, court_lon, facility_lat, facility_lon)
        
        # Check if court is inside facility's bounding box
        extent = properties.get('extent', [])
        is_inside_bbox = False
        if extent and len(extent) == 4:
            min_lon, max_lat, max_lon, min_lat = extent
            is_inside_bbox = (min_lat <= court_lat <= max_lat and min_lon <= court_lon <= max_lon)
        
        # Score this match (prioritize bounding box matches)
        score = distance
        if is_inside_bbox:
            score = 0.001  # Almost zero distance for bounding box matches
        
        if score < best_distance:
            best_distance = score
            best_match = {
                'facility': facility,
                'distance': distance,
                'is_inside_bbox': is_inside_bbox,
                'name': name,
                'score': score,
                'osm_id': properties.get('osm_id'),
                'osm_key': properties.get('osm_key'),
                'osm_value': properties.get('osm_value')
            }
    
    return best_match

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in kilometers"""
    from math import radians, cos, sin, asin, sqrt
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return 6371 * c

def test_way_1106815330():
    """Test bounding box search on Way 1106815330"""
    
    print("🔍 Testing Bounding Box Search on Way 1106815330")
    print("="*60)
    
    # Way 1106815330 coordinates from export.geojson
    coordinates = [
        [
            [-122.4359146, 37.8018241],
            [-122.43571, 37.8018502],
            [-122.4356878, 37.8017412],
            [-122.4358924, 37.8017152],
            [-122.4359146, 37.8018241]  # Close the polygon
        ]
    ]
    
    # Calculate centroid
    court_lat, court_lon = calculate_centroid(coordinates)
    print(f"📍 Court coordinates: {court_lat}, {court_lon}")
    print(f"🏀 Sport: basketball, Hoops: 2")
    
    # Create bounding box
    bbox = create_bbox_around_point(court_lat, court_lon, buffer_km=0.3)
    print(f"📦 Bounding box: {bbox}")
    
    # Search for facilities
    search_terms = ['park', 'school', 'church', 'recreation', 'playground', 'moscone']
    facilities = search_facilities_in_bbox(bbox, search_terms)
    
    print(f"\n🏢 Found {len(facilities)} total facilities")
    
    # Find best match
    best_match = find_best_facility_match(court_lat, court_lon, facilities)
    
    if best_match:
        print(f"\n🎯 Best Match:")
        print(f"   Name: {best_match['name']}")
        print(f"   OSM ID: {best_match['osm_id']}")
        print(f"   OSM Key/Value: {best_match['osm_key']}:{best_match['osm_value']}")
        print(f"   Distance: {best_match['distance']:.3f} km")
        print(f"   Inside bounding box: {best_match['is_inside_bbox']}")
        print(f"   Score: {best_match['score']:.6f}")
        
        if best_match['is_inside_bbox']:
            print(f"   ✅ BOUNDING BOX MATCH!")
        else:
            print(f"   📏 Distance-based match")
    else:
        print("\n❌ No matches found")
    
    # Show all close results
    print(f"\n📋 All results within 500m:")
    close_results = []
    for facility in facilities:
        properties = facility.get('properties', {})
        coords = facility.get('geometry', {}).get('coordinates', [])
        if coords:
            facility_lon, facility_lat = coords[0], coords[1]
            distance = calculate_distance(court_lat, court_lon, facility_lat, facility_lon)
            if distance < 0.5:  # Within 500m
                extent = properties.get('extent', [])
                is_inside = False
                if extent and len(extent) == 4:
                    min_lon, max_lat, max_lon, min_lat = extent
                    is_inside = (min_lat <= court_lat <= max_lat and min_lon <= court_lon <= max_lon)
                
                close_results.append({
                    'name': properties.get('name', 'Unknown'),
                    'distance': distance,
                    'is_inside': is_inside,
                    'osm_id': properties.get('osm_id')
                })
    
    close_results.sort(key=lambda x: x['distance'])
    for i, result in enumerate(close_results[:10]):  # Show top 10
        bbox_indicator = "🎯" if result['is_inside'] else "📏"
        print(f"   {i+1}. {bbox_indicator} {result['name']} ({result['distance']:.3f} km)")

if __name__ == "__main__":
    test_way_1106815330()
