#!/usr/bin/env python3
"""
Refined Closest POI approach that prioritizes meaningful POI types

This approach finds the closest POI but prioritizes parks, playgrounds,
recreation centers, and other meaningful locations over street addresses.
"""

import requests
import time
import json
import os
from typing import Optional, Tuple, Dict, Any
from dotenv import load_dotenv

load_dotenv()


class RefinedClosestPOIProvider:
    """Provider that finds the closest meaningful POI to the coordinates"""
    
    def __init__(self, api_key: str = None, delay: float = 0.1):
        self.api_key = api_key or os.getenv('GOOGLE_PLACES_API_KEY')
        self.delay = delay
        self.session = requests.Session()
        
        if not self.api_key:
            raise ValueError("Google API key is required")
    
    def reverse_geocode(self, lat: float, lon: float) -> Tuple[Optional[str], Optional[str]]:
        """
        Find the closest meaningful POI to the coordinates
        """
        print(f"🔍 Finding closest meaningful POI for {lat}, {lon}")
        
        # Strategy 1: Look for specific POI types that are likely to have basketball courts
        meaningful_result = self._find_meaningful_poi(lat, lon)
        if meaningful_result:
            print(f"✅ Found meaningful POI: {meaningful_result['name']}")
            return meaningful_result['name'], meaningful_result.get('place_id')
        
        # Strategy 2: Fall back to closest establishment
        closest_result = self._find_closest_establishment(lat, lon)
        if closest_result:
            print(f"✅ Found closest establishment: {closest_result['name']}")
            return closest_result['name'], closest_result.get('place_id')
        
        print("❌ No POI found")
        return None, None
    
    def _find_meaningful_poi(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Find meaningful POI types that are likely to have basketball courts"""
        try:
            # Prioritized search strategies for meaningful POI types
            strategies = [
                {
                    "name": "Parks (100m)",
                    "params": {
                        'location': f"{lat},{lon}",
                        'radius': 100,
                        'type': 'park',
                        'key': self.api_key
                    }
                },
                {
                    "name": "Recreation Centers (100m)",
                    "params": {
                        'location': f"{lat},{lon}",
                        'radius': 100,
                        'keyword': 'recreation center',
                        'key': self.api_key
                    }
                },
                {
                    "name": "Community Centers (100m)",
                    "params": {
                        'location': f"{lat},{lon}",
                        'radius': 100,
                        'keyword': 'community center',
                        'key': self.api_key
                    }
                },
                {
                    "name": "Sports Facilities (100m)",
                    "params": {
                        'location': f"{lat},{lon}",
                        'radius': 100,
                        'keyword': 'sports',
                        'key': self.api_key
                    }
                },
                {
                    "name": "Playgrounds (100m)",
                    "params": {
                        'location': f"{lat},{lon}",
                        'radius': 100,
                        'keyword': 'playground',
                        'key': self.api_key
                    }
                },
                {
                    "name": "Gyms (100m)",
                    "params": {
                        'location': f"{lat},{lon}",
                        'radius': 100,
                        'keyword': 'gym',
                        'key': self.api_key
                    }
                },
                {
                    "name": "Schools (100m)",
                    "params": {
                        'location': f"{lat},{lon}",
                        'radius': 100,
                        'type': 'school',
                        'key': self.api_key
                    }
                }
            ]
            
            for strategy in strategies:
                print(f"  Trying: {strategy['name']}")
                
                response = self.session.get(
                    "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
                    params=strategy['params'],
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
            print(f"❌ Error finding meaningful POI: {e}")
            return None
    
    def _find_closest_establishment(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Find the closest establishment as fallback"""
        try:
            print(f"  Fallback: Looking for any establishment")
            
            # Try different radius sizes
            for radius in [50, 100, 200, 500]:
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
                    # Filter out street addresses and prioritize meaningful names
                    for result in data['results']:
                        name = result.get('name', '')
                        types = result.get('types', [])
                        
                        # Skip street addresses and generic locations
                        if any(skip_type in types for skip_type in ['street_address', 'route', 'intersection']):
                            continue
                        
                        # Skip generic names
                        if any(generic in name.lower() for generic in ['street', 'avenue', 'boulevard', 'road', 'way']):
                            continue
                        
                        print(f"    Found establishment: {name}")
                        
                        return {
                            'name': name,
                            'place_id': result.get('place_id'),
                            'types': types,
                            'vicinity': result.get('vicinity'),
                            'rating': result.get('rating')
                        }
                
                time.sleep(self.delay)
            
            return None
            
        except Exception as e:
            print(f"❌ Error finding closest establishment: {e}")
            return None


def test_refined_closest_poi():
    """Test the refined closest POI approach"""
    
    print("🏀 Testing Refined Closest POI Approach")
    print("=" * 50)
    
    # Test coordinates
    test_coords = [
        (37.750086, -122.406482, "James Rolph Basketball Court"),
        (37.823603, -122.372797, "Treasure Island Court"),
    ]
    
    try:
        provider = RefinedClosestPOIProvider()
        
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
                elif any(keyword in address.lower() for keyword in ['school', 'gym', 'sports']):
                    print("✅ FAIR: Found sports-related POI")
                else:
                    print("⚠️  BASIC: Found generic POI name")
            else:
                print("❌ FAILED: No result")
                
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    test_refined_closest_poi()
