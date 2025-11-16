#!/usr/bin/env python3
"""
Test script for debugging individual court geocoding.
Shows all search attempts and final result for a specific court.
"""

import argparse
import json
import sys
from test_photon_geocoding import PhotonGeocodingProvider

def test_single_court(lat: float, lon: float, sport: str = 'basketball', hoops: int = None):
    """Test geocoding for a single court with detailed breakdown"""
    
    print("="*80)
    print("🔍 TESTING GEOCODING FOR SINGLE COURT")
    print("="*80)
    print(f"📍 Coordinates: {lat}, {lon}")
    print(f"🏀 Sport: {sport}")
    if hoops:
        print(f"🎯 Hoops: {hoops}")
    print("="*80)
    
    # Initialize provider
    provider = PhotonGeocodingProvider()
    
    # Determine court count for naming
    court_count = hoops if hoops else 1
    
    # Run geocoding with detailed breakdown
    print("🔄 Running geocoding searches...")
    print()
    
    # Test each search method individually to show all attempts
    print("🔍 1. Sports Club Search (club:sport, 1000ft radius):")
    sports_club_results = provider._try_sports_club_search_all_results(lat, lon)
    for i, result in enumerate(sports_club_results, 1):
        print(f"   {i}. {result['name']} ({result['distance']:.3f}km = ~{result['distance']*3281:.0f}ft)")
    
    print(f"\n🔍 2. Sports Centre Search (leisure:sports_centre, 1000ft radius):")
    sports_centre_results = provider._try_sports_centre_search_all_results(lat, lon)
    for i, result in enumerate(sports_centre_results, 1):
        print(f"   {i}. {result['name']} ({result['distance']:.3f}km = ~{result['distance']*3281:.0f}ft)")
    
    print(f"\n🔍 3. Community Centre Search (amenity:community_centre, 1000ft radius):")
    community_centre_results = provider._try_community_centre_search_all_results(lat, lon)
    for i, result in enumerate(community_centre_results, 1):
        print(f"   {i}. {result['name']} ({result['distance']:.3f}km = ~{result['distance']*3281:.0f}ft)")
    
    print(f"\n🔍 4. School Search (amenity:school, 500ft radius):")
    school_results = provider._try_school_search_all_results(lat, lon)
    for i, result in enumerate(school_results, 1):
        print(f"   {i}. {result['name']} ({result['distance']:.3f}km = ~{result['distance']*3281:.0f}ft)")
    
    print(f"\n🔍 5. Place of Worship Search (amenity:place_of_worship, 500ft radius):")
    place_of_worship_results = provider._try_place_of_worship_search_all_results(lat, lon)
    for i, result in enumerate(place_of_worship_results, 1):
        print(f"   {i}. {result['name']} ({result['distance']:.3f}km = ~{result['distance']*3281:.0f}ft)")
    
    print(f"\n🔍 6. Park/Playground Search (leisure:park/playground, 1000ft radius):")
    park_results = provider._try_search_fallback_all_results(lat, lon)
    for i, result in enumerate(park_results, 1):
        print(f"   {i}. {result['name']} ({result['distance']:.3f}km = ~{result['distance']*3281:.0f}ft)")
    
    print(f"\n🔍 7. Building Search (all building types, 1000ft radius):")
    building_results = provider._try_building_search_all_results(lat, lon)
    for i, result in enumerate(building_results, 1):
        building_type = "🏠 Residential" if result.get('is_residential', False) else "🏢 Commercial"
        print(f"   {i}. {result['name']} ({result['distance']:.3f}km = ~{result['distance']*3281:.0f}ft) {building_type}")
    
    # Test the full geocoding (returns name, data, and API calls count)
    name, data, api_calls_made = provider.reverse_geocode(lat, lon, court_count)
    
    print()
    print("="*80)
    print("📊 FINAL RESULT:")
    print("="*80)
    if name:
        print(f"✅ Name: {name}")
        print(f"   Data available: {data is not None}")
    else:
        print("❌ Failed to geocode")
    print("="*80)
    print()
    
    return name, data

def test_by_osm_id(osm_id: str, geojson_file: str = 'export.geojson'):
    """Test geocoding by looking up OSM ID in GeoJSON file"""
    
    print(f"🔍 Looking up {osm_id} in {geojson_file}...")
    
    try:
        with open(geojson_file, 'r') as f:
            data = json.load(f)
        
        # Find the feature with matching OSM ID
        feature = None
        for feat in data['features']:
            if feat['properties'].get('osm_id') == osm_id:
                feature = feat
                break
        
        if not feature:
            print(f"❌ Court {osm_id} not found in {geojson_file}")
            return None, None
        
        geometry = feature['geometry']
        properties = feature['properties']
        
        if geometry['type'] == 'Polygon':
            ring = geometry['coordinates'][0]
            lat = sum(coord[1] for coord in ring) / len(ring)
            lon = sum(coord[0] for coord in ring) / len(ring)
        elif geometry['type'] == 'Point':
            lon, lat = geometry['coordinates']
        else:
            print(f"❌ Unsupported geometry type: {geometry['type']}")
            return None, None
        
        # Get sport and hoops
        sport = properties.get('sport', 'basketball')
        hoops = int(properties.get('hoops')) if properties.get('hoops') else None
        
        print(f"✅ Found court:")
        print(f"   OSM ID: {osm_id}")
        print(f"   Sport: {sport}")
        print(f"   Coordinates: {lat}, {lon}")
        if hoops:
            print(f"   Hoops: {hoops}")
        print()
        
        return test_single_court(lat, lon, sport, hoops)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None, None

def main():
    parser = argparse.ArgumentParser(description='Test geocoding for a single court')
    parser.add_argument('--lat', type=float, help='Latitude')
    parser.add_argument('--lon', type=float, help='Longitude')
    parser.add_argument('--osm-id', type=str, help='OSM ID (e.g., way/123456)')
    parser.add_argument('--sport', type=str, default='basketball', help='Sport type')
    parser.add_argument('--hoops', type=int, help='Number of hoops/courts')
    parser.add_argument('--geojson', type=str, default='export.geojson', help='GeoJSON file path')
    
    args = parser.parse_args()
    
    if args.osm_id:
        test_by_osm_id(args.osm_id, args.geojson)
    elif args.lat and args.lon:
        test_single_court(args.lat, args.lon, args.sport, args.hoops)
    else:
        print("❌ Please provide either --osm-id or --lat/--lon")
        sys.exit(1)

if __name__ == '__main__':
    main()
