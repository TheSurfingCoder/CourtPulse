#!/usr/bin/env python3
"""
Closest POI approach for Google Places API

Instead of filtering for basketball-specific names, we take the closest POI
to the coordinates, which is more likely to be the correct location.
"""

import requests
import time
import json
import os
from typing import Optional, Tuple, Dict, Any
from dotenv import load_dotenv

load_dotenv()


class ClosestPOIProvider:
    """Provider that finds the closest POI to the coordinates"""
    
    def __init__(self, api_key: str = None, delay: float = 0.1):
        self.api_key = api_key or os.getenv('GOOGLE_PLACES_API_KEY')
        self.delay = delay
        self.session = requests.Session()
        
        if not self.api_key:
            raise ValueError("Google API key is required")
    
    def reverse_geocode(self, lat: float, lon: float) -> Tuple[Optional[str], Optional[str]]:
        """
        Find the closest POI to the coordinates
        """
        print(f"🔍 Finding closest POI for {lat}, {lon}")
        
        # Strategy 1: Nearby search for any establishment
        closest_result = self._find_closest_poi(lat, lon)
        if closest_result:
            print(f"✅ Found closest POI: {closest_result['name']}")
            return closest_result['name'], closest_result.get('place_id')
        
        print("❌ No POI found")
        return None, None
    
    def _find_closest_poi(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Find the closest POI using Google Places Nearby Search"""
        try:
            # Try different search strategies to find the closest POI
            strategies = [
                {
                    "name": "Any Establishment (50m)",
                    "params": {
                        'location': f"{lat},{lon}",
                        'radius': 50,
                        'type': 'establishment',
                        'key': self.api_key
                    }
                },
                {
                    "name": "Any Establishment (100m)",
                    "params": {
                        'location': f"{lat},{lon}",
                        'radius': 100,
                        'type': 'establishment',
                        'key': self.api_key
                    }
                },
                {
                    "name": "Point of Interest (100m)",
                    "params": {
                        'location': f"{lat},{lon}",
                        'radius': 100,
                        'type': 'point_of_interest',
                        'key': self.api_key
                    }
                },
                {
                    "name": "Any Establishment (200m)",
                    "params": {
                        'location': f"{lat},{lon}",
                        'radius': 200,
                        'type': 'establishment',
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
            print(f"❌ Error finding closest POI: {e}")
            return None
    
    def _find_closest_poi_with_keywords(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Find closest POI using keyword searches for common court locations"""
        try:
            # Common keywords for places that might have basketball courts
            keywords = [
                'park',
                'playground', 
                'recreation',
                'community center',
                'sports',
                'gym'
            ]
            
            for keyword in keywords:
                print(f"  Trying keyword: {keyword}")
                
                params = {
                    'location': f"{lat},{lon}",
                    'radius': 200,
                    'type': 'establishment',
                    'keyword': keyword,
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
                
                time.sleep(self.delay)
            
            return None
            
        except Exception as e:
            print(f"❌ Error finding closest POI with keywords: {e}")
            return None


def test_closest_poi_approach():
    """Test the closest POI approach"""
    
    print("🏀 Testing Closest POI Approach")
    print("=" * 50)
    
    # Test coordinates
    test_coords = [
        (37.750086, -122.406482, "James Rolph Basketball Court"),
        (37.823603, -122.372797, "Treasure Island Court"),
    ]
    
    try:
        provider = ClosestPOIProvider()
        
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
                elif any(keyword in address.lower() for keyword in ['park', 'playground', 'center', 'court']):
                    print("✅ GOOD: Found relevant POI name")
                else:
                    print("⚠️  BASIC: Found generic POI name")
            else:
                print("❌ FAILED: No result")
                
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    test_closest_poi_approach()
