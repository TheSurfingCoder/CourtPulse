#!/usr/bin/env python3
"""
Test the new bounding box geocoding integration
"""

import json
import sys
import os

# Add the data_enrichment directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bounding_box_geocoding import BoundingBoxGeocodingProvider

def test_way_32649024():
    """Test the Moscone Recreation Center way"""
    print("🔍 Testing Bounding Box Geocoding - Way 32649024")
    print("="*60)
    
    # Court coordinates from export.geojson
    court_lat = 37.80209232
    court_lon = -122.43441733999998
    court_count = 2
    
    print(f"📍 Court coordinates: {court_lat}, {court_lon}")
    print(f"🏀 Sport: basketball, Hoops: {court_count}")
    
    # Initialize provider
    provider = BoundingBoxGeocodingProvider()
    
    # Test geocoding
    facility_name, facility_data = provider.reverse_geocode(court_lat, court_lon, court_count)
    
    if facility_name:
        print(f"\n✅ SUCCESS!")
        print(f"   Facility: {facility_name}")
        print(f"   Distance: {facility_data['distance_km']:.3f} km")
        print(f"   Inside bbox: {facility_data['is_inside_bbox']}")
        print(f"   OSM ID: {facility_data['osm_id']}")
        print(f"   OSM Key/Value: {facility_data['osm_key']}:{facility_data['osm_value']}")
        
        if facility_data['is_inside_bbox']:
            print(f"   🎯 BOUNDING BOX MATCH!")
        else:
            print(f"   📏 Distance-based match")
    else:
        print(f"\n❌ No facility found")

def test_way_1106815330():
    """Test the Marina Middle School way"""
    print("\n" + "="*60)
    print("🔍 Testing Bounding Box Geocoding - Way 1106815330")
    print("="*60)
    
    # Court coordinates from export.geojson
    court_lat = 37.80179096
    court_lon = -122.43582388
    court_count = 2
    
    print(f"📍 Court coordinates: {court_lat}, {court_lon}")
    print(f"🏀 Sport: basketball, Hoops: {court_count}")
    
    # Initialize provider
    provider = BoundingBoxGeocodingProvider()
    
    # Test geocoding
    facility_name, facility_data = provider.reverse_geocode(court_lat, court_lon, court_count)
    
    if facility_name:
        print(f"\n✅ SUCCESS!")
        print(f"   Facility: {facility_name}")
        print(f"   Distance: {facility_data['distance_km']:.3f} km")
        print(f"   Inside bbox: {facility_data['is_inside_bbox']}")
        print(f"   OSM ID: {facility_data['osm_id']}")
        print(f"   OSM Key/Value: {facility_data['osm_key']}:{facility_data['osm_value']}")
        
        if facility_data['is_inside_bbox']:
            print(f"   🎯 BOUNDING BOX MATCH!")
        else:
            print(f"   📏 Distance-based match")
    else:
        print(f"\n❌ No facility found")

if __name__ == "__main__":
    test_way_32649024()
    test_way_1106815330()
