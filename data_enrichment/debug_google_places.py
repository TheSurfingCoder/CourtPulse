#!/usr/bin/env python3
"""
Debug Google Places API to see exactly what's being returned

This will help us understand why we're not getting the expected results
"""

import requests
import time
import json
import os
from dotenv import load_dotenv

load_dotenv()


def debug_google_places_search(lat: float, lon: float):
    """Debug Google Places API responses"""
    
    api_key = os.getenv('GOOGLE_PLACES_API_KEY')
    if not api_key:
        print("❌ No Google Places API key found")
        return
    
    print(f"🔍 Debugging Google Places API for {lat}, {lon}")
    print(f"API Key: {api_key[:10]}...")
    
    # Test 1: Nearby Search
    print("\n" + "="*50)
    print("TEST 1: Nearby Search")
    print("="*50)
    
    try:
        params = {
            'location': f"{lat},{lon}",
            'radius': 100,
            'type': 'establishment',
            'keyword': 'basketball court',
            'key': api_key
        }
        
        print(f"URL: https://maps.googleapis.com/maps/api/place/nearbysearch/json")
        print(f"Params: {params}")
        
        response = requests.get(
            "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
            params=params,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        data = response.json()
        
        print(f"Response Status: {data.get('status')}")
        print(f"Results Count: {len(data.get('results', []))}")
        
        if data.get('results'):
            print("\nResults:")
            for i, result in enumerate(data['results'][:5]):  # Show first 5
                print(f"  {i+1}. {result.get('name', 'No name')}")
                print(f"     Types: {result.get('types', [])}")
                print(f"     Place ID: {result.get('place_id', 'No ID')}")
                print(f"     Vicinity: {result.get('vicinity', 'No vicinity')}")
        else:
            print("No results found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    time.sleep(1)
    
    # Test 2: Text Search
    print("\n" + "="*50)
    print("TEST 2: Text Search")
    print("="*50)
    
    try:
        params = {
            'query': 'basketball court',
            'location': f"{lat},{lon}",
            'radius': 200,
            'key': api_key
        }
        
        print(f"URL: https://maps.googleapis.com/maps/api/place/textsearch/json")
        print(f"Params: {params}")
        
        response = requests.get(
            "https://maps.googleapis.com/maps/api/place/textsearch/json",
            params=params,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        data = response.json()
        
        print(f"Response Status: {data.get('status')}")
        print(f"Results Count: {len(data.get('results', []))}")
        
        if data.get('results'):
            print("\nResults:")
            for i, result in enumerate(data['results'][:5]):  # Show first 5
                print(f"  {i+1}. {result.get('name', 'No name')}")
                print(f"     Types: {result.get('types', [])}")
                print(f"     Place ID: {result.get('place_id', 'No ID')}")
                print(f"     Address: {result.get('formatted_address', 'No address')}")
        else:
            print("No results found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    time.sleep(1)
    
    # Test 3: Broader Search
    print("\n" + "="*50)
    print("TEST 3: Broader Search (sports)")
    print("="*50)
    
    try:
        params = {
            'location': f"{lat},{lon}",
            'radius': 300,
            'type': 'establishment',
            'keyword': 'sports',
            'key': api_key
        }
        
        print(f"URL: https://maps.googleapis.com/maps/api/place/nearbysearch/json")
        print(f"Params: {params}")
        
        response = requests.get(
            "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
            params=params,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        data = response.json()
        
        print(f"Response Status: {data.get('status')}")
        print(f"Results Count: {len(data.get('results', []))}")
        
        if data.get('results'):
            print("\nResults:")
            for i, result in enumerate(data['results'][:5]):  # Show first 5
                print(f"  {i+1}. {result.get('name', 'No name')}")
                print(f"     Types: {result.get('types', [])}")
                print(f"     Place ID: {result.get('place_id', 'No ID')}")
                print(f"     Vicinity: {result.get('vicinity', 'No vicinity')}")
        else:
            print("No results found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    time.sleep(1)
    
    # Test 4: Geocoding API (what we were using before)
    print("\n" + "="*50)
    print("TEST 4: Geocoding API (what we used before)")
    print("="*50)
    
    try:
        params = {
            'latlng': f"{lat},{lon}",
            'key': api_key
        }
        
        print(f"URL: https://maps.googleapis.com/maps/api/geocode/json")
        print(f"Params: {params}")
        
        response = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params=params,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        data = response.json()
        
        print(f"Response Status: {data.get('status')}")
        print(f"Results Count: {len(data.get('results', []))}")
        
        if data.get('results'):
            print("\nResults:")
            for i, result in enumerate(data['results'][:3]):  # Show first 3
                print(f"  {i+1}. {result.get('formatted_address', 'No address')}")
                print(f"     Types: {result.get('types', [])}")
                print(f"     Place ID: {result.get('place_id', 'No ID')}")
        else:
            print("No results found")
            
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Test with the problem coordinates"""
    
    print("🏀 Google Places API Debug Tool")
    print("=" * 60)
    
    # Test coordinates
    test_coords = [
        (37.750086, -122.406482, "James Rolph Basketball Court"),
        (37.823603, -122.372797, "Treasure Island Court"),
    ]
    
    for lat, lon, expected_name in test_coords:
        print(f"\n🎯 Testing coordinates: {lat}, {lon}")
        print(f"Expected: {expected_name}")
        debug_google_places_search(lat, lon)
        print("\n" + "="*60)


if __name__ == "__main__":
    main()

