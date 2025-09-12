#!/usr/bin/env python3
"""
Refined Simple Closest POI approach - filters out generic results

This approach:
1. Finds the closest POI to the exact coordinates
2. Filters out overly generic results (cities, states, etc.)
3. Falls back to OSM smart description if no good POI found
"""

import requests
import time
import json
import os
from typing import Optional, Tuple, Dict, Any
from dotenv import load_dotenv

load_dotenv()


class RefinedSimplePOIProvider:
    """Provider that finds the closest meaningful POI to coordinates"""
    
    def __init__(self, api_key: str = None, delay: float = 0.1):
        self.api_key = api_key or os.getenv('GOOGLE_PLACES_API_KEY')
        self.delay = delay
        self.session = requests.Session()
        
        if not self.api_key:
            raise ValueError("Google API key is required")
    
    def reverse_geocode(self, lat: float, lon: float) -> Tuple[Optional[str], Optional[str]]:
        """
        Find the closest meaningful POI to coordinates, fallback to OSM smart description
        """
        print(f"🔍 Finding closest meaningful POI for {lat}, {lon}")
        
        # Strategy 1: Find closest meaningful POI using Google Places API
        closest_result = self._find_closest_meaningful_poi(lat, lon)
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
    
    def _find_closest_meaningful_poi(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Find the closest meaningful POI to the coordinates"""
        try:
            # Try different radius sizes to find the closest meaningful POI
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
                    print(f"    Found {len(data['results'])} results")
                    
                    # Look through results to find the first meaningful one
                    for result in data['results']:
                        name = result.get('name', '')
                        types = result.get('types', [])
                        
                        # Skip overly generic results
                        if self._is_generic_result(name, types):
                            print(f"    Skipping generic result: {name}")
                            continue
                        
                        # Found a meaningful result
                        print(f"    Found meaningful POI: {name}")
                        
                        return {
                            'name': name,
                            'place_id': result.get('place_id'),
                            'types': types,
                            'vicinity': result.get('vicinity'),
                            'rating': result.get('rating')
                        }
                    
                    print(f"    No meaningful results found in {len(data['results'])} results")
                else:
                    print(f"    No results found")
                
                time.sleep(self.delay)
            
            return None
            
        except Exception as e:
            print(f"❌ Error finding closest POI: {e}")
            return None
    
    def _is_generic_result(self, name: str, types: list) -> bool:
        """Check if a result is too generic to be useful"""
        
        # Skip generic location types
        generic_types = [
            'locality', 'administrative_area_level_1', 'administrative_area_level_2',
            'administrative_area_level_3', 'administrative_area_level_4',
            'administrative_area_level_5', 'country', 'political'
        ]
        
        if any(t in types for t in generic_types):
            return True
        
        # Skip generic names
        generic_names = [
            'san francisco', 'california', 'united states', 'usa',
            'sf', 'bay area', 'northern california'
        ]
        
        name_lower = name.lower()
        if any(generic in name_lower for generic in generic_names):
            return True
        
        # Skip very short names (likely generic)
        if len(name.strip()) < 3:
            return True
        
        return False
    
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


def test_refined_simple_poi():
    """Test the refined simple POI approach"""
    
    print("🏀 Testing Refined Simple POI Approach")
    print("=" * 50)
    
    # Test coordinates
    test_coords = [
        (37.750086, -122.406482, "James Rolph Basketball Court"),
        (37.823603, -122.372797, "Treasure Island Court"),
    ]
    
    try:
        provider = RefinedSimplePOIProvider()
        
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
    test_refined_simple_poi()
