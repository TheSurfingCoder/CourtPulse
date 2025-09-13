#!/usr/bin/env python3
"""
Debug script to investigate reverse geocoding accuracy

This script will help us understand:
1. What Nominatim is actually returning
2. Why it's choosing street names over POI names
3. How to improve the geocoding accuracy
"""

import json
import requests
import time
from typing import Dict, List, Any


def detailed_nominatim_lookup(lat: float, lon: float) -> Dict[str, Any]:
    """Get detailed Nominatim response with all available information"""
    
    # Test multiple Nominatim endpoints and parameters
    endpoints_to_test = [
        {
            "name": "Standard Reverse Geocoding",
            "url": "https://nominatim.openstreetmap.org/reverse",
            "params": {
                'format': 'json',
                'lat': lat,
                'lon': lon,
                'zoom': 18,
                'addressdetails': 1
            }
        },
        {
            "name": "Reverse with POI preference",
            "url": "https://nominatim.openstreetmap.org/reverse",
            "params": {
                'format': 'json',
                'lat': lat,
                'lon': lon,
                'zoom': 16,
                'addressdetails': 1,
                'extratags': 1,
                'namedetails': 1
            }
        },
        {
            "name": "Reverse with building preference",
            "url": "https://nominatim.openstreetmap.org/reverse",
            "params": {
                'format': 'json',
                'lat': lat,
                'lon': lon,
                'zoom': 15,
                'addressdetails': 1,
                'extratags': 1
            }
        }
    ]
    
    results = {}
    
    for endpoint in endpoints_to_test:
        print(f"\n🔍 Testing: {endpoint['name']}")
        print(f"URL: {endpoint['url']}")
        print(f"Params: {endpoint['params']}")
        
        try:
            response = requests.get(
                endpoint['url'], 
                params=endpoint['params'],
                headers={'User-Agent': 'CourtPulse/1.0'},
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            results[endpoint['name']] = data
            
            print(f"✅ Response received")
            print(f"Display Name: {data.get('display_name', 'N/A')}")
            print(f"Place ID: {data.get('place_id', 'N/A')}")
            print(f"Type: {data.get('type', 'N/A')}")
            print(f"Class: {data.get('class', 'N/A')}")
            
            # Show additional details if available
            if 'address' in data:
                print(f"Address Components:")
                for key, value in data['address'].items():
                    print(f"  {key}: {value}")
            
            if 'extratags' in data:
                print(f"Extra Tags:")
                for key, value in data['extratags'].items():
                    print(f"  {key}: {value}")
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            results[endpoint['name']] = None
        
        # Respect rate limits
        time.sleep(1)
    
    return results


def search_nearby_pois(lat: float, lon: float) -> Dict[str, Any]:
    """Search for nearby POIs using Nominatim search"""
    
    print(f"\n🔍 Searching for nearby POIs around {lat}, {lon}")
    
    # Try different search terms
    search_terms = [
        "basketball court",
        "basketball",
        "sports facility",
        "leisure=pitch",
        "sport=basketball"
    ]
    
    results = {}
    
    for term in search_terms:
        print(f"\nSearching for: '{term}'")
        
        try:
            params = {
                'format': 'json',
                'q': term,
                'lat': lat,
                'lon': lon,
                'radius': 0.01,  # ~1km radius
                'limit': 10,
                'addressdetails': 1
            }
            
            response = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params=params,
                headers={'User-Agent': 'CourtPulse/1.0'},
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            results[term] = data
            
            print(f"✅ Found {len(data)} results")
            
            for i, result in enumerate(data[:3]):  # Show first 3 results
                print(f"  {i+1}. {result.get('display_name', 'N/A')}")
                print(f"     Type: {result.get('type', 'N/A')}, Class: {result.get('class', 'N/A')}")
                print(f"     Distance: {result.get('distance', 'N/A')}")
                
        except Exception as e:
            print(f"❌ Error searching for '{term}': {e}")
            results[term] = None
        
        time.sleep(1)
    
    return results


def analyze_coordinate_accuracy(lat: float, lon: float):
    """Analyze if the coordinate is accurate for the POI"""
    
    print(f"\n📍 Coordinate Analysis for {lat}, {lon}")
    
    # Check if this coordinate is on OpenStreetMap
    try:
        params = {
            'format': 'json',
            'lat': lat,
            'lon': lon,
            'zoom': 18,
            'addressdetails': 1,
            'extratags': 1
        }
        
        response = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params=params,
            headers={'User-Agent': 'CourtPulse/1.0'},
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        
        print(f"✅ Coordinate exists on OSM")
        print(f"OSM Type: {data.get('osm_type', 'N/A')}")
        print(f"OSM ID: {data.get('osm_id', 'N/A')}")
        print(f"OSM Class: {data.get('class', 'N/A')}")
        
        if 'extratags' in data:
            print(f"OSM Tags:")
            for key, value in data['extratags'].items():
                if any(keyword in key.lower() for keyword in ['sport', 'leisure', 'name', 'basketball']):
                    print(f"  {key}: {value}")
        
        return data
        
    except Exception as e:
        print(f"❌ Error analyzing coordinate: {e}")
        return None


def main():
    """Main investigation function"""
    
    # The coordinates from your test
    lat, lon = 37.750086, -122.406482
    
    print("🏀 CourtPulse Geocoding Investigation")
    print("=" * 60)
    print(f"Investigating coordinates: {lat}, {lon}")
    print(f"Expected POI: James Rolph Basketball Court")
    
    # Step 1: Detailed Nominatim lookup
    print("\n" + "=" * 60)
    print("STEP 1: Detailed Nominatim Reverse Geocoding")
    print("=" * 60)
    
    reverse_results = detailed_nominatim_lookup(lat, lon)
    
    # Step 2: Search for nearby POIs
    print("\n" + "=" * 60)
    print("STEP 2: Search for Nearby POIs")
    print("=" * 60)
    
    search_results = search_nearby_pois(lat, lon)
    
    # Step 3: Analyze coordinate accuracy
    print("\n" + "=" * 60)
    print("STEP 3: Coordinate Accuracy Analysis")
    print("=" * 60)
    
    osm_data = analyze_coordinate_accuracy(lat, lon)
    
    # Step 4: Recommendations
    print("\n" + "=" * 60)
    print("STEP 4: Analysis & Recommendations")
    print("=" * 60)
    
    print("\n🔍 Key Findings:")
    
    # Check if we found the basketball court in search results
    found_basketball_court = False
    for search_term, results in search_results.items():
        if results:
            for result in results:
                display_name = result.get('display_name', '').lower()
                if 'james rolph' in display_name or 'basketball' in display_name:
                    print(f"✅ Found basketball court in '{search_term}' search: {result.get('display_name')}")
                    found_basketball_court = True
                    break
    
    if not found_basketball_court:
        print("❌ James Rolph Basketball Court not found in nearby POI search")
    
    # Check OSM data
    if osm_data and 'extratags' in osm_data:
        sport_tags = {k: v for k, v in osm_data['extratags'].items() if 'sport' in k.lower()}
        if sport_tags:
            print(f"✅ OSM has sport tags: {sport_tags}")
        else:
            print("❌ No sport tags found in OSM data")
    
    print("\n💡 Recommendations:")
    print("1. Check if the coordinate is exactly on the basketball court")
    print("2. Verify the court exists in OpenStreetMap with proper tags")
    print("3. Consider using Google Places API for better POI recognition")
    print("4. Implement coordinate offset or search radius for better results")
    
    # Save results for further analysis
    with open('geocoding_debug_results.json', 'w') as f:
        json.dump({
            'coordinates': {'lat': lat, 'lon': lon},
            'reverse_results': reverse_results,
            'search_results': search_results,
            'osm_data': osm_data
        }, f, indent=2)
    
    print(f"\n📁 Detailed results saved to: geocoding_debug_results.json")


if __name__ == "__main__":
    main()

