#!/usr/bin/env python3
"""
Hybrid geocoding approach that combines multiple sources for better POI names

This addresses the issue where OSM doesn't have names for basketball courts,
but Google Places or other sources might.
"""

import requests
import time
import json
import os
from typing import Optional, Tuple, Dict, Any
from dotenv import load_dotenv

load_dotenv()


class HybridGeocodingProvider:
    """Hybrid geocoding that tries multiple sources for best results"""
    
    def __init__(self, user_agent: str = "CourtPulse/1.0", delay: float = 1.0):
        self.user_agent = user_agent
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': user_agent})
        self.google_api_key = os.getenv('GOOGLE_PLACES_API_KEY')
    
    def reverse_geocode(self, lat: float, lon: float) -> Tuple[Optional[str], Optional[str]]:
        """
        Hybrid reverse geocoding that tries multiple sources
        """
        print(f"🌍 Hybrid geocoding for {lat}, {lon}")
        
        # Strategy 1: Try Google Places API (if available)
        if self.google_api_key:
            google_result = self._try_google_places(lat, lon)
            if google_result and self._is_basketball_related(google_result['name']):
                print(f"✅ Google Places found: {google_result['name']}")
                return google_result['name'], google_result.get('place_id')
        
        # Strategy 2: Enhanced OSM search with nearby POI lookup
        osm_result = self._enhanced_osm_lookup(lat, lon)
        if osm_result and self._is_basketball_related(osm_result['name']):
            print(f"✅ Enhanced OSM found: {osm_result['name']}")
            return osm_result['name'], osm_result.get('place_id')
        
        # Strategy 3: Smart fallback based on OSM data
        smart_fallback = self._create_smart_fallback(lat, lon)
        if smart_fallback:
            print(f"✅ Smart fallback: {smart_fallback}")
            return smart_fallback, None
        
        # Strategy 4: Standard Nominatim as last resort
        standard_result = self._standard_nominatim(lat, lon)
        if standard_result:
            print(f"⚠️  Standard Nominatim: {standard_result['name']}")
            return standard_result['name'], standard_result.get('place_id')
        
        print("❌ No geocoding result found")
        return None, None
    
    def _try_google_places(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Try Google Places API for better POI recognition"""
        
        try:
            params = {
                'latlng': f"{lat},{lon}",
                'key': self.google_api_key,
                'radius': 100,  # 100m radius
                'types': 'establishment|point_of_interest'
            }
            
            response = self.session.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'OK' and data.get('results'):
                # Look for basketball/sports related results
                for result in data['results']:
                    name = result.get('formatted_address', '')
                    if self._is_basketball_related(name):
                        return {
                            'name': name,
                            'place_id': result.get('place_id'),
                            'types': result.get('types', [])
                        }
            
            return None
            
        except Exception as e:
            print(f"❌ Google Places error: {e}")
            return None
        finally:
            time.sleep(self.delay * 0.1)  # Faster for Google
    
    def _enhanced_osm_lookup(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Enhanced OSM lookup that searches for nearby named basketball courts"""
        
        try:
            # First, get the OSM object details
            osm_data = self._get_osm_object(lat, lon)
            if not osm_data:
                return None
            
            # If it's a basketball court but has no name, search nearby
            if (osm_data.get('class') == 'leisure' and 
                osm_data.get('type') == 'pitch' and 
                osm_data.get('extratags', {}).get('sport') == 'basketball'):
                
                # Search for nearby named basketball courts
                nearby_court = self._search_nearby_named_courts(lat, lon, radius=0.01)  # 1km radius
                if nearby_court:
                    return nearby_court
            
            return None
            
        except Exception as e:
            print(f"❌ Enhanced OSM lookup error: {e}")
            return None
        finally:
            time.sleep(self.delay)
    
    def _get_osm_object(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Get OSM object details"""
        
        try:
            params = {
                'format': 'json',
                'lat': lat,
                'lon': lon,
                'zoom': 18,
                'extratags': 1
            }
            
            response = self.session.get(
                "https://nominatim.openstreetmap.org/reverse",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            print(f"❌ OSM object lookup error: {e}")
            return None
    
    def _search_nearby_named_courts(self, lat: float, lon: float, radius: float) -> Optional[Dict[str, Any]]:
        """Search for nearby basketball courts with names"""
        
        try:
            params = {
                'format': 'json',
                'q': 'basketball court',
                'lat': lat,
                'lon': lon,
                'radius': radius,
                'limit': 10,
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
                if (result.get('class') == 'leisure' and 
                    result.get('type') == 'pitch' and
                    result.get('extratags', {}).get('sport') == 'basketball'):
                    
                    # Check for name in extratags
                    name = result.get('extratags', {}).get('name')
                    if name and self._is_basketball_related(name):
                        return {
                            'name': name,
                            'place_id': result.get('place_id'),
                            'osm_id': result.get('osm_id'),
                            'distance': result.get('distance')
                        }
            
            return None
            
        except Exception as e:
            print(f"❌ Nearby courts search error: {e}")
            return None
    
    def _create_smart_fallback(self, lat: float, lon: float) -> Optional[str]:
        """Create a smart fallback name based on OSM data"""
        
        try:
            osm_data = self._get_osm_object(lat, lon)
            if not osm_data:
                return None
            
            # Check if it's a basketball court
            if (osm_data.get('class') == 'leisure' and 
                osm_data.get('type') == 'pitch' and 
                osm_data.get('extratags', {}).get('sport') == 'basketball'):
                
                extratags = osm_data.get('extratags', {})
                hoops = extratags.get('hoops', 'unknown')
                indoor = extratags.get('indoor', 'no')
                
                # Create a descriptive name
                court_type = "Indoor" if indoor == 'yes' else "Outdoor"
                hoop_info = f"({hoops} hoops)" if hoops != 'unknown' else ""
                
                fallback_name = f"{court_type} Basketball Court {hoop_info}".strip()
                
                # Try to get neighborhood/area name for context
                address = osm_data.get('address', {})
                area = (address.get('suburb') or 
                       address.get('neighbourhood') or 
                       address.get('quarter') or
                       'Area')
                
                return f"{fallback_name} - {area}"
            
            return None
            
        except Exception as e:
            print(f"❌ Smart fallback error: {e}")
            return None
    
    def _standard_nominatim(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Standard Nominatim reverse geocoding"""
        
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
                'name': data.get('display_name'),
                'place_id': data.get('place_id')
            }
            
        except Exception as e:
            print(f"❌ Standard Nominatim error: {e}")
            return None
        finally:
            time.sleep(self.delay)
    
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


def test_hybrid_geocoding():
    """Test the hybrid geocoding approach"""
    
    print("🏀 Testing Hybrid Geocoding")
    print("=" * 50)
    
    # Test coordinates
    test_coords = [
        (37.750086, -122.406482, "James Rolph Basketball Court"),
        (37.823603, -122.372797, "Treasure Island Court"),
    ]
    
    provider = HybridGeocodingProvider(delay=0.5)
    
    for lat, lon, expected_name in test_coords:
        print(f"\n📍 Testing: {lat}, {lon}")
        print(f"Expected: {expected_name}")
        
        address, place_id = provider.reverse_geocode(lat, lon)
        
        print(f"Result: {address}")
        print(f"Place ID: {place_id}")
        
        # Evaluate result quality
        if address:
            if expected_name.lower() in address.lower():
                print("✅ EXCELLENT: Found expected court name!")
            elif 'basketball' in address.lower() and 'court' in address.lower():
                print("✅ GOOD: Found basketball court name")
            elif 'basketball' in address.lower():
                print("✅ FAIR: Found basketball-related name")
            else:
                print("⚠️  BASIC: Got generic address")
        else:
            print("❌ FAILED: No result")


if __name__ == "__main__":
    test_hybrid_geocoding()

