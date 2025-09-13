#!/usr/bin/env python3
"""
Simple Closest POI approach - no keywords, just the closest POI to lat/lng

This approach:
1. Finds the closest POI to the exact coordinates (no filtering)
2. If no POI found, falls back to OSM smart description
"""

import requests
import time
import json
import os
from typing import Optional, Tuple, Dict, Any
from dotenv import load_dotenv

load_dotenv()


class SimpleClosestPOIProvider:
    """Provider that finds the closest POI to coordinates with OSM fallback"""
    
    def __init__(self, api_key: str = None, delay: float = 0.1):
        self.api_key = api_key or os.getenv('GOOGLE_PLACES_API_KEY')
        self.delay = delay
        self.session = requests.Session()
        
        if not self.api_key:
            raise ValueError("Google API key is required")
    
    def reverse_geocode(self, lat: float, lon: float) -> Tuple[Optional[str], Optional[str]]:
        """
        Find the closest POI to coordinates, fallback to OSM smart description
        """
        print(f"🔍 Finding closest POI for {lat}, {lon}")
        
        # Strategy 1: Find closest POI using Google Places API
        closest_result = self._find_closest_poi(lat, lon)
        if closest_result:
            print(f"✅ Found closest POI: {closest_result['name']}")
            return closest_result['name'], closest_result.get('place_id')
        
        # Strategy 2: Fallback to OSM smart description
        osm_fallback = self._create_osm_fallback(lat, lon)
        if osm_fallback:
            print(f"⚠️  Using OSM fallback: {osm_fallback}")
            return osm_fallback, None
        
        print("❌ No result found")
        return None, None
    
    def _find_closest_poi(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Find the closest POI to the coordinates using Google Places API"""
        try:
            # Try different radius sizes to find the closest POI
            for radius in [25, 50, 100, 200, 500]:
                print(f"  Trying radius: {radius}m")
                
                params = {
                    'location': f"{lat},{lon}",
                    'radius': radius,
                    'type': 'establishment',
                    'key': self.api_key
                }
                
                response = self.session.get(
                    "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
                    params=params,
                    timeout=10
                )
                response.raise_for_status()
                
                data = response.json()
                
                if data.get('status') == 'OK' and data.get('results'):
                    # Take the first (closest) result
                    closest_result = data['results'][0]
                    
                    print(f"    Found {len(data['results'])} results")
                    print(f"    Closest: {closest_result.get('name', 'No name')}")
                    
                    return {
                        'name': closest_result.get('name'),
                        'place_id': closest_result.get('place_id'),
                        'types': closest_result.get('types', []),
                        'vicinity': closest_result.get('vicinity'),
                        'rating': closest_result.get('rating')
                    }
                else:
                    print(f"    No results found")
                
                time.sleep(self.delay)
            
            return None
            
        except Exception as e:
            print(f"❌ Error finding closest POI: {e}")
            return None
    
    def _create_osm_fallback(self, lat: float, lon: float) -> Optional[str]:
        """Create OSM smart fallback description"""
        try:
            print(f"  Creating OSM fallback description...")
            
            # Get OSM data for the coordinates
            params = {
                'format': 'json',
                'lat': lat,
                'lon': lon,
                'zoom': 18,
                'extratags': 1,
                'addressdetails': 1
            }
            
            response = self.session.get(
                "https://nominatim.openstreetmap.org/reverse",
                params=params,
                headers={'User-Agent': 'CourtPulse/1.0'},
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Check if it's a basketball court
            if (data.get('class') == 'leisure' and 
                data.get('type') == 'pitch' and 
                data.get('extratags', {}).get('sport') == 'basketball'):
                
                extratags = data.get('extratags', {})
                hoops = extratags.get('hoops', 'unknown')
                indoor = extratags.get('indoor', 'no')
                
                # Create a descriptive name
                court_type = "Indoor" if indoor == 'yes' else "Outdoor"
                hoop_info = f"({hoops} hoops)" if hoops != 'unknown' else ""
                
                fallback_name = f"{court_type} Basketball Court {hoop_info}".strip()
                
                # Try to get neighborhood/area name for context
                address = data.get('address', {})
                area = (address.get('suburb') or 
                       address.get('neighbourhood') or 
                       address.get('quarter') or
                       'Area')
                
                return f"{fallback_name} - {area}"
            
            return None
            
        except Exception as e:
            print(f"❌ Error creating OSM fallback: {e}")
            return None


def test_simple_closest_poi():
    """Test the simple closest POI approach"""
    
    print("🏀 Testing Simple Closest POI Approach")
    print("=" * 50)
    
    # Test coordinates
    test_coords = [
        (37.750086, -122.406482, "James Rolph Basketball Court"),
        (37.823603, -122.372797, "Treasure Island Court"),
    ]
    
    try:
        provider = SimpleClosestPOIProvider()
        
        for lat, lon, expected_name in test_coords:
            print(f"\n📍 Testing: {lat}, {lon}")
            print(f"Expected: {expected_name}")
            
            address, place_id = provider.reverse_geocode(lat, lon)
            
            print(f"Result: {address}")
            print(f"Place ID: {place_id}")
            
            # Evaluate result quality
            if address:
                if expected_name.lower() in address.lower():
                    print("🎉 EXCELLENT: Found expected court name!")
                elif any(keyword in address.lower() for keyword in ['park', 'playground', 'center', 'court', 'recreation']):
                    print("✅ GOOD: Found relevant POI name")
                elif 'basketball court' in address.lower():
                    print("✅ GOOD: Found basketball court description")
                else:
                    print("⚠️  BASIC: Found generic POI name")
            else:
                print("❌ FAILED: No result")
                
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    test_simple_closest_poi()

