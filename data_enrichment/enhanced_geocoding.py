#!/usr/bin/env python3
"""
Enhanced Geocoding API approach that works with your current API key

Since Places API is not enabled, we'll use Geocoding API with better logic
to find basketball court names.
"""

import requests
import time
import json
import os
from typing import Optional, Tuple, Dict, Any
from dotenv import load_dotenv

load_dotenv()


class EnhancedGeocodingProvider:
    """Enhanced Geocoding API provider that finds basketball court names"""
    
    def __init__(self, api_key: str = None, delay: float = 0.1):
        self.api_key = api_key or os.getenv('GOOGLE_PLACES_API_KEY')
        self.delay = delay
        self.session = requests.Session()
        
        if not self.api_key:
            raise ValueError("Google API key is required")
    
    def reverse_geocode(self, lat: float, lon: float) -> Tuple[Optional[str], Optional[str]]:
        """
        Enhanced reverse geocoding using Geocoding API with basketball court detection
        """
        print(f"🔍 Enhanced Geocoding search for {lat}, {lon}")
        
        # Get all results from Geocoding API
        results = self._get_geocoding_results(lat, lon)
        if not results:
            return None, None
        
        # Look for basketball court names in the results
        basketball_result = self._find_basketball_court(results)
        if basketball_result:
            print(f"✅ Found basketball court: {basketball_result['name']}")
            return basketball_result['name'], basketball_result.get('place_id')
        
        # Look for sports/recreation facilities
        sports_result = self._find_sports_facility(results)
        if sports_result:
            print(f"✅ Found sports facility: {sports_result['name']}")
            return sports_result['name'], sports_result.get('place_id')
        
        # Return the most relevant result
        best_result = self._get_best_result(results)
        if best_result:
            print(f"✅ Best result: {best_result['name']}")
            return best_result['name'], best_result.get('place_id')
        
        print("❌ No suitable result found")
        return None, None
    
    def _get_geocoding_results(self, lat: float, lon: float) -> list:
        """Get all results from Geocoding API"""
        try:
            params = {
                'latlng': f"{lat},{lon}",
                'key': self.api_key,
                'result_type': 'establishment|point_of_interest|premise'
            }
            
            response = self.session.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'OK':
                return data.get('results', [])
            
            return []
            
        except Exception as e:
            print(f"❌ Geocoding error: {e}")
            return []
        finally:
            time.sleep(self.delay)
    
    def _find_basketball_court(self, results: list) -> Optional[Dict[str, Any]]:
        """Look for basketball court names in the results"""
        
        basketball_keywords = [
            'basketball', 'court', 'hoops', 'sports', 'recreation',
            'playground', 'park', 'center', 'centre'
        ]
        
        for result in results:
            address = result.get('formatted_address', '').lower()
            types = result.get('types', [])
            
            # Check if it's basketball-related
            if any(keyword in address for keyword in basketball_keywords):
                # Extract the name (first part before comma)
                name_parts = result.get('formatted_address', '').split(',')
                name = name_parts[0].strip()
                
                return {
                    'name': name,
                    'place_id': result.get('place_id'),
                    'types': types,
                    'formatted_address': result.get('formatted_address')
                }
        
        return None
    
    def _find_sports_facility(self, results: list) -> Optional[Dict[str, Any]]:
        """Look for sports/recreation facilities"""
        
        sports_types = [
            'establishment', 'point_of_interest', 'premise',
            'sports_complex', 'recreation', 'park'
        ]
        
        for result in results:
            types = result.get('types', [])
            address = result.get('formatted_address', '').lower()
            
            # Check if it's a sports facility
            if any(t in types for t in sports_types):
                # Look for sports-related keywords
                sports_keywords = ['sports', 'recreation', 'community', 'center', 'centre', 'park']
                if any(keyword in address for keyword in sports_keywords):
                    name_parts = result.get('formatted_address', '').split(',')
                    name = name_parts[0].strip()
                    
                    return {
                        'name': name,
                        'place_id': result.get('place_id'),
                        'types': types,
                        'formatted_address': result.get('formatted_address')
                    }
        
        return None
    
    def _get_best_result(self, results: list) -> Optional[Dict[str, Any]]:
        """Get the best result based on relevance"""
        
        # Prioritize results with better types
        priority_types = [
            'establishment',
            'point_of_interest', 
            'premise',
            'street_address'
        ]
        
        for priority_type in priority_types:
            for result in results:
                types = result.get('types', [])
                if priority_type in types:
                    name_parts = result.get('formatted_address', '').split(',')
                    name = name_parts[0].strip()
                    
                    return {
                        'name': name,
                        'place_id': result.get('place_id'),
                        'types': types,
                        'formatted_address': result.get('formatted_address')
                    }
        
        return None


def test_enhanced_geocoding():
    """Test the enhanced geocoding approach"""
    
    print("🏀 Testing Enhanced Geocoding API")
    print("=" * 50)
    
    # Test coordinates
    test_coords = [
        (37.750086, -122.406482, "James Rolph Basketball Court"),
        (37.823603, -122.372797, "Treasure Island Court"),
    ]
    
    try:
        provider = EnhancedGeocodingProvider()
        
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
    test_enhanced_geocoding()
