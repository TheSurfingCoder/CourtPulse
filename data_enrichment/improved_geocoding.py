#!/usr/bin/env python3
"""
Improved geocoding approach that prioritizes POI names over street addresses

This addresses the issue where Nominatim returns street names instead of 
basketball court names like "James Rolph Basketball Court"
"""

import requests
import time
import json
from typing import Optional, Tuple, Dict, Any


class ImprovedGeocodingProvider:
    """Enhanced geocoding provider that finds actual POI names"""
    
    def __init__(self, user_agent: str = "CourtPulse/1.0", delay: float = 1.0):
        self.user_agent = user_agent
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': user_agent})
    
    def reverse_geocode(self, lat: float, lon: float) -> Tuple[Optional[str], Optional[str]]:
        """
        Enhanced reverse geocoding that prioritizes POI names
        """
        print(f"🌍 Enhanced geocoding for {lat}, {lon}")
        
        # Strategy 1: Try to get the actual OSM object with name
        osm_data = self._get_osm_object_details(lat, lon)
        if osm_data and osm_data.get('name'):
            print(f"✅ Found OSM object name: {osm_data['name']}")
            return osm_data['name'], osm_data.get('osm_id')
        
        # Strategy 2: Search for nearby named basketball courts
        nearby_court = self._search_nearby_named_courts(lat, lon)
        if nearby_court:
            print(f"✅ Found nearby named court: {nearby_court['name']}")
            return nearby_court['name'], nearby_court.get('place_id')
        
        # Strategy 3: Fall back to standard reverse geocoding
        standard_result = self._standard_reverse_geocode(lat, lon)
        if standard_result:
            print(f"⚠️  Using standard result: {standard_result['address']}")
            return standard_result['address'], standard_result.get('place_id')
        
        print("❌ No geocoding result found")
        return None, None
    
    def _get_osm_object_details(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Get detailed OSM object information including name"""
        
        try:
            params = {
                'format': 'json',
                'lat': lat,
                'lon': lon,
                'zoom': 18,
                'addressdetails': 1,
                'extratags': 1,
                'namedetails': 1
            }
            
            response = self.session.get(
                "https://nominatim.openstreetmap.org/reverse",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Check if this is a leisure/sports facility
            if data.get('class') == 'leisure' and data.get('type') == 'pitch':
                # Look for name in various places
                name = None
                
                # Check namedetails first (most reliable)
                if 'namedetails' in data and 'name' in data['namedetails']:
                    name = data['namedetails']['name']
                # Check extratags
                elif 'extratags' in data and 'name' in data['extratags']:
                    name = data['extratags']['name']
                # Check if display_name contains a court name
                elif 'basketball' in data.get('display_name', '').lower():
                    name = data['display_name']
                
                if name:
                    return {
                        'name': name,
                        'osm_id': data.get('osm_id'),
                        'osm_type': data.get('osm_type'),
                        'class': data.get('class'),
                        'type': data.get('type')
                    }
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting OSM details: {e}")
            return None
        finally:
            time.sleep(self.delay)
    
    def _search_nearby_named_courts(self, lat: float, lon: float, radius: float = 0.005) -> Optional[Dict[str, Any]]:
        """Search for nearby basketball courts with names"""
        
        try:
            # Search for basketball courts in the area
            params = {
                'format': 'json',
                'q': 'basketball court',
                'lat': lat,
                'lon': lon,
                'radius': radius,  # ~500m radius
                'limit': 5,
                'addressdetails': 1,
                'extratags': 1
            }
            
            response = self.session.get(
                "https://nominatim.openstreetmap.org/search",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            results = response.json()
            
            # Find the closest court with a name
            for result in results:
                if result.get('class') == 'leisure' and result.get('type') == 'pitch':
                    # Check if it has a name
                    name = None
                    if 'extratags' in result and 'name' in result['extratags']:
                        name = result['extratags']['name']
                    elif 'display_name' in result and 'basketball' in result['display_name'].lower():
                        # Extract just the court name from display_name
                        name_parts = result['display_name'].split(',')
                        if len(name_parts) > 0:
                            name = name_parts[0].strip()
                    
                    if name and 'basketball' in name.lower():
                        return {
                            'name': name,
                            'place_id': result.get('place_id'),
                            'distance': result.get('distance'),
                            'osm_id': result.get('osm_id')
                        }
            
            return None
            
        except Exception as e:
            print(f"❌ Error searching nearby courts: {e}")
            return None
        finally:
            time.sleep(self.delay)
    
    def _standard_reverse_geocode(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Standard Nominatim reverse geocoding as fallback"""
        
        try:
            params = {
                'format': 'json',
                'lat': lat,
                'lon': lon,
                'zoom': 18,
                'addressdetails': 1
            }
            
            response = self.session.get(
                "https://nominatim.openstreetmap.org/reverse",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            return {
                'address': data.get('display_name'),
                'place_id': data.get('place_id'),
                'osm_id': data.get('osm_id')
            }
            
        except Exception as e:
            print(f"❌ Error in standard reverse geocoding: {e}")
            return None
        finally:
            time.sleep(self.delay)


def test_improved_geocoding():
    """Test the improved geocoding on the problem coordinates"""
    
    print("🏀 Testing Improved Geocoding")
    print("=" * 50)
    
    # Test coordinates from your example
    test_coords = [
        (37.750086, -122.406482, "James Rolph Basketball Court"),
        (37.823603, -122.372797, "Treasure Island Court"),
    ]
    
    provider = ImprovedGeocodingProvider(delay=0.5)
    
    for lat, lon, expected_name in test_coords:
        print(f"\n📍 Testing: {lat}, {lon}")
        print(f"Expected: {expected_name}")
        
        address, place_id = provider.reverse_geocode(lat, lon)
        
        print(f"Result: {address}")
        print(f"Place ID: {place_id}")
        
        # Check if we got a better result
        if address and expected_name.lower() in address.lower():
            print("✅ SUCCESS: Found expected court name!")
        elif address and 'basketball' in address.lower():
            print("✅ IMPROVED: Found basketball-related name")
        elif address:
            print("⚠️  PARTIAL: Got address but not court name")
        else:
            print("❌ FAILED: No result")


if __name__ == "__main__":
    test_improved_geocoding()

