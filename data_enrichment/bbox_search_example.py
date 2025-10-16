#!/usr/bin/env python3
"""
Simple example showing how to integrate bounding box search into our pipeline
"""

import json
import requests
from typing import List, Dict, Any, Tuple

def create_bbox_around_courts(courts: List[Dict[str, Any]], buffer_km: float = 0.3) -> Tuple[float, float, float, float]:
    """
    Create a bounding box around a group of courts (could be a single court or cluster)
    
    Args:
        courts: List of court features from export.geojson
        buffer_km: Buffer distance in kilometers
    
    Returns:
        Tuple of (min_lon, min_lat, max_lon, max_lat)
    """
    if not courts:
        return None
    
    # Extract coordinates from all courts
    all_lats = []
    all_lons = []
    
    for court in courts:
        geometry = court.get('geometry', {})
        if geometry.get('type') == 'Polygon' and geometry.get('coordinates'):
            # Calculate centroid of polygon
            ring = geometry['coordinates'][0]
            total_lon = sum(coord[0] for coord in ring) / len(ring)
            total_lat = sum(coord[1] for coord in ring) / len(ring)
            all_lats.append(total_lat)
            all_lons.append(total_lon)
    
    if not all_lats:
        return None
    
    # Find min/max coordinates
    min_lat = min(all_lats)
    max_lat = max(all_lats)
    min_lon = min(all_lons)
    max_lon = max(all_lons)
    
    # Add buffer
    # Rough conversion: 1 degree ≈ 111 km
    lat_buffer = buffer_km / 111.0
    lon_buffer = buffer_km / (111.0 * abs((min_lat + max_lat) / 2 * 3.14159 / 180))
    
    return (
        min_lon - lon_buffer,  # min_lon
        min_lat - lat_buffer,  # min_lat  
        max_lon + lon_buffer,  # max_lon
        max_lat + lat_buffer   # max_lat
    )

def search_facilities_in_bbox(bbox: Tuple[float, float, float, float], search_terms: List[str]) -> List[Dict[str, Any]]:
    """
    Search for facilities within a bounding box using multiple search terms
    
    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat)
        search_terms: List of search terms like ['park', 'school', 'church']
    
    Returns:
        List of facility features found
    """
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
                'limit': 20  # Get more results
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

def find_best_facility_match(courts: List[Dict[str, Any]], facilities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Find the best facility match for the courts using bounding box logic
    
    Args:
        courts: List of court features
        facilities: List of facility features from Photon
    
    Returns:
        Best matching facility with distance and bounding box info
    """
    if not courts or not facilities:
        return None
    
    # Get court coordinates (use first court for simplicity)
    court = courts[0]
    geometry = court.get('geometry', {})
    if geometry.get('type') == 'Polygon' and geometry.get('coordinates'):
        ring = geometry['coordinates'][0]
        court_lon = sum(coord[0] for coord in ring) / len(ring)
        court_lat = sum(coord[1] for coord in ring) / len(ring)
    else:
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
                'score': score
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
    return 6371 * c  # Earth's radius in km

def example_usage():
    """Example of how this would work in our pipeline"""
    
    print("🔍 Bounding Box Search Example")
    print("="*50)
    
    # Example: Single court from export.geojson
    court_example = {
        "type": "Feature",
        "properties": {
            "osm_id": "way/32649024",
            "sport": "basketball",
            "hoops": "2"
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-122.43441733999998, 37.80209232],
                [-122.434400, 37.802100],
                [-122.434380, 37.802080],
                [-122.43441733999998, 37.80209232]
            ]]
        }
    }
    
    # Step 1: Create bounding box around court(s)
    courts = [court_example]
    bbox = create_bbox_around_courts(courts, buffer_km=0.3)
    
    print(f"📍 Court coordinates: 37.80209232, -122.43441733999998")
    print(f"📦 Bounding box: {bbox}")
    
    # Step 2: Search for facilities in bounding box
    search_terms = ['park', 'school', 'church', 'recreation', 'moscone']
    facilities = search_facilities_in_bbox(bbox, search_terms)
    
    print(f"🏢 Found {len(facilities)} total facilities")
    
    # Step 3: Find best match
    best_match = find_best_facility_match(courts, facilities)
    
    if best_match:
        print(f"\n🎯 Best Match:")
        print(f"   Name: {best_match['name']}")
        print(f"   Distance: {best_match['distance']:.3f} km")
        print(f"   Inside bounding box: {best_match['is_inside_bbox']}")
        print(f"   Score: {best_match['score']:.6f}")
    else:
        print("\n❌ No matches found")

if __name__ == "__main__":
    example_usage()
