#!/usr/bin/env python3
"""
Fixed Google Places API implementation for basketball court names

This addresses the issues with our current implementation:
1. Uses correct Google Places API endpoints
2. Uses proper search parameters
3. Implements proper nearby search strategy
"""

import requests
import time
import json
import os
from typing import Optional, Tuple, Dict, Any
from dotenv import load_dotenv

load_dotenv()


class FixedGooglePlacesProvider:
    """Fixed Google Places API provider that correctly finds POI names"""
    
    def __init__(self, api_key: str = None, delay: float = 0.1):
        self.api_key = api_key or os.getenv('GOOGLE_PLACES_API_KEY')
        self.delay = delay
        self.session = requests.Session()
        
        if not self.api_key:
            raise ValueError("Google Places API key is required")
    
    def reverse_geocode(self, lat: float, lon: float) -> Tuple[Optional[str], Optional[str]]:
        """
        Fixed reverse geocoding using Google Places API
        """
        print(f"🔍 Fixed Google Places search for {lat}, {lon}")
        
        # Strategy 1: Nearby Search for basketball courts
        nearby_result = self._nearby_search(lat, lon)
        if nearby_result:
            print(f"✅ Nearby search found: {nearby_result['name']}")
            return nearby_result['name'], nearby_result.get('place_id')
        
        # Strategy 2: Text Search with coordinates
        text_result = self._text_search(lat, lon)
        if text_result:
            print(f"✅ Text search found: {text_result['name']}")
            return text_result['name'], text_result.get('place_id')
        
        # Strategy 3: Broader nearby search
        broader_result = self._broader_search(lat, lon)
        if broader_result:
            print(f"✅ Broader search found: {broader_result['name']}")
            return broader_result['name'], broader_result.get('place_id')
        
        print("❌ No results from Google Places API")
        return None, None
    
    def _nearby_search(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Google Places Nearby Search API"""
        try:
            params = {
                'location': f"{lat},{lon}",
                'radius': 100,  # 100m radius
                'type': 'establishment',
                'keyword': 'basketball court',
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
                for result in data['results']:
                    name = result.get('name', '')
                    if self._is_basketball_related(name):
                        return {
                            'name': name,
                            'place_id': result.get('place_id'),
                            'types': result.get('types', []),
                            'rating': result.get('rating'),
                            'vicinity': result.get('vicinity')
                        }
            
            return None
            
        except Exception as e:
            print(f"❌ Nearby search error: {e}")
            return None
        finally:
            time.sleep(self.delay)
    
    def _text_search(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Google Places Text Search API"""
        try:
            params = {
                'query': 'basketball court',
                'location': f"{lat},{lon}",
                'radius': 200,  # 200m radius
                'key': self.api_key
            }
            
            response = self.session.get(
                "https://maps.googleapis.com/maps/api/place/textsearch/json",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'OK' and data.get('results'):
                for result in data['results']:
                    name = result.get('name', '')
                    if self._is_basketball_related(name):
                        return {
                            'name': name,
                            'place_id': result.get('place_id'),
                            'types': result.get('types', []),
                            'rating': result.get('rating'),
                            'formatted_address': result.get('formatted_address')
                        }
            
            return None
            
        except Exception as e:
            print(f"❌ Text search error: {e}")
            return None
        finally:
            time.sleep(self.delay)
    
    def _broader_search(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Broader search for sports/recreation facilities"""
        try:
            # Try different keywords
            keywords = [
                'basketball',
                'sports facility',
                'recreation center',
                'community center',
                'park'
            ]
            
            for keyword in keywords:
                params = {
                    'location': f"{lat},{lon}",
                    'radius': 300,  # 300m radius
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
                    for result in data['results']:
                        name = result.get('name', '')
                        types = result.get('types', [])
                        
                        # Check if it's sports/recreation related
                        if (self._is_basketball_related(name) or 
                            any(t in types for t in ['sports_complex', 'recreation', 'park'])):
                            return {
                                'name': name,
                                'place_id': result.get('place_id'),
                                'types': types,
                                'rating': result.get('rating'),
                                'vicinity': result.get('vicinity')
                            }
                
                time.sleep(self.delay)
            
            return None
            
        except Exception as e:
            print(f"❌ Broader search error: {e}")
            return None
    
    def _is_basketball_related(self, name: str) -> bool:
        """Check if a name is basketball-related"""
        if not name:
            return False
        
        basketball_keywords = [
            'basketball', 'court', 'hoops', 'sports', 'recreation',
            'playground', 'park', 'center', 'centre'
        ]
        
        name_lower = name.lower()
        return any(keyword in name_lower for keyword in basketball_keywords)


def test_fixed_google_places():
    """Test the fixed Google Places implementation"""
    
    print("🏀 Testing Fixed Google Places API")
    print("=" * 50)
    
    # Test coordinates
    test_coords = [
        (37.750086, -122.406482, "James Rolph Basketball Court"),
        (37.823603, -122.372797, "Treasure Island Court"),
    ]
    
    try:
        provider = FixedGooglePlacesProvider()
        
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
                elif 'basketball' in address.lower() and 'court' in address.lower():
                    print("✅ GOOD: Found basketball court name")
                elif 'basketball' in address.lower():
                    print("✅ FAIR: Found basketball-related name")
                else:
                    print("⚠️  BASIC: Got generic name")
            else:
                print("❌ FAILED: No result")
                
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    test_fixed_google_places()

