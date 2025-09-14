#!/usr/bin/env python3
"""
CourtPulse Data Enrichment Pipeline

This script processes OpenStreetMap court data from GeoJSON files,
enriches it with reverse geocoding, and stores it in a Postgres database.
"""

import json
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

import geojson
import psycopg2
from psycopg2.extras import RealDictCursor
from shapely.geometry import shape, Point
from sqlalchemy import create_engine, text
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CourtData:
    """Data class for court information"""
    osm_id: str
    geom: Point
    polygon_geojson: Optional[str] = None  # Store original polygon GeoJSON
    sport: Optional[str] = None
    hoops: Optional[str] = None
    fallback_name: Optional[str] = None
    google_place_id: Optional[str] = None
    enriched_name: Optional[str] = None
    address: Optional[str] = None


class GeocodingProvider(ABC):
    """Abstract base class for geocoding providers"""
    
    @abstractmethod
    def reverse_geocode(self, lat: float, lon: float) -> Tuple[Optional[str], Optional[str]]:
        """
        Reverse geocode coordinates to address and place_id
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Tuple of (address, place_id)
        """
        pass


class HybridGeocodingProvider(GeocodingProvider):
    """Hybrid geocoding provider that prioritizes Google Places API with smart fallback"""
    
    def __init__(self, base_url: str = "https://nominatim.openstreetmap.org", 
                 user_agent: str = "CourtPulse/1.0", delay: float = 1.0):
        self.base_url = base_url
        self.user_agent = user_agent
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': user_agent})
        self.google_api_key = os.getenv('GOOGLE_PLACES_API_KEY')
        
        logger.info(json.dumps({
            'event': 'geocoding_provider_initialized',
            'provider': 'HybridGeocoding',
            'google_api_available': bool(self.google_api_key),
            'base_url': base_url,
            'delay': delay
        }))
    
    def reverse_geocode(self, lat: float, lon: float) -> Tuple[Optional[str], Optional[str]]:
        """Hybrid reverse geocoding that prioritizes Google Places API with smart fallback"""
        try:
            # Strategy 1: Try Google Places API first (if available)
            if self.google_api_key:
                google_result = self._try_google_places(lat, lon)
                if google_result and self._is_basketball_related(google_result['name']):
                    logger.info(json.dumps({
                        'event': 'reverse_geocoding_completed',
                        'provider': 'GooglePlaces',
                        'coordinates': {'lat': lat, 'lon': lon},
                        'address_found': True,
                        'place_id_found': bool(google_result.get('place_id'))
                    }))
                    return google_result['name'], google_result.get('place_id')
            
            # Strategy 2: Enhanced OSM search with nearby POI lookup
            osm_result = self._enhanced_osm_lookup(lat, lon)
            if osm_result and self._is_basketball_related(osm_result['name']):
                logger.info(json.dumps({
                    'event': 'reverse_geocoding_completed',
                    'provider': 'EnhancedOSM',
                    'coordinates': {'lat': lat, 'lon': lon},
                    'address_found': True,
                    'place_id_found': bool(osm_result.get('place_id'))
                }))
                return osm_result['name'], osm_result.get('place_id')
            
            # Strategy 3: Smart fallback based on OSM data
            smart_fallback = self._create_smart_fallback(lat, lon)
            if smart_fallback:
                logger.info(json.dumps({
                    'event': 'reverse_geocoding_completed',
                    'provider': 'SmartFallback',
                    'coordinates': {'lat': lat, 'lon': lon},
                    'address_found': True,
                    'place_id_found': False
                }))
                return smart_fallback, None
            
            # Strategy 4: Standard Nominatim as last resort
            standard_result = self._standard_nominatim(lat, lon)
            if standard_result:
                logger.info(json.dumps({
                    'event': 'reverse_geocoding_completed',
                    'provider': 'StandardNominatim',
                    'coordinates': {'lat': lat, 'lon': lon},
                    'address_found': True,
                    'place_id_found': bool(standard_result.get('place_id'))
                }))
                return standard_result['name'], standard_result.get('place_id')
            
            logger.warning(json.dumps({
                'event': 'reverse_geocoding_failed',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': 'No geocoding result found from any provider'
            }))
            return None, None
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'reverse_geocoding_error',
                'provider': 'HybridGeocoding',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return None, None
        finally:
            time.sleep(self.delay)
    
    def _try_google_places(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Find the closest meaningful POI to coordinates using Google Places API"""
        try:
            # Try different radius sizes to find the closest meaningful POI
            for radius in [25, 50, 100, 200, 500]:
                params = {
                    'location': f"{lat},{lon}",
                    'radius': radius,
                    'type': 'establishment',
                    'key': self.google_api_key
                }
                
                response = self.session.get(
                    "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
                    params=params,
                    timeout=10
                )
                response.raise_for_status()
                
                data = response.json()
                
                if data.get('status') == 'OK' and data.get('results'):
                    # Look through results to find the first meaningful one
                    for result in data['results']:
                        name = result.get('name', '')
                        types = result.get('types', [])
                        
                        # Skip overly generic results
                        if self._is_generic_result(name, types):
                            continue
                        
                        # Found a meaningful result
                        return {
                            'name': name,
                            'place_id': result.get('place_id'),
                            'types': types,
                            'vicinity': result.get('vicinity'),
                            'rating': result.get('rating')
                        }
                
                time.sleep(0.1)  # Rate limiting
            
            return None
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'google_places_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
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
    
    def _find_meaningful_poi(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Find meaningful POI types that are likely to have basketball courts"""
        try:
            # Prioritized search strategies for meaningful POI types
            strategies = [
                {
                    "name": "Parks",
                    "params": {
                        'location': f"{lat},{lon}",
                        'radius': 100,
                        'type': 'park',
                        'key': self.google_api_key
                    }
                },
                {
                    "name": "Recreation Centers",
                    "params": {
                        'location': f"{lat},{lon}",
                        'radius': 100,
                        'keyword': 'recreation center',
                        'key': self.google_api_key
                    }
                },
                {
                    "name": "Community Centers",
                    "params": {
                        'location': f"{lat},{lon}",
                        'radius': 100,
                        'keyword': 'community center',
                        'key': self.google_api_key
                    }
                },
                {
                    "name": "Sports Facilities",
                    "params": {
                        'location': f"{lat},{lon}",
                        'radius': 100,
                        'keyword': 'sports',
                        'key': self.google_api_key
                    }
                },
                {
                    "name": "Playgrounds",
                    "params": {
                        'location': f"{lat},{lon}",
                        'radius': 100,
                        'keyword': 'playground',
                        'key': self.google_api_key
                    }
                },
                {
                    "name": "Schools",
                    "params": {
                        'location': f"{lat},{lon}",
                        'radius': 100,
                        'type': 'school',
                        'key': self.google_api_key
                    }
                }
            ]
            
            for strategy in strategies:
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
            logger.error(json.dumps({
                'event': 'find_meaningful_poi_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return None
    
    def _find_closest_establishment(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Find the closest establishment as fallback"""
        try:
            # Try different radius sizes
            for radius in [50, 100, 200, 500]:
                params = {
                    'location': f"{lat},{lon}",
                    'radius': radius,
                    'type': 'establishment',
                    'key': self.google_api_key
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
            logger.error(json.dumps({
                'event': 'find_closest_establishment_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return None
    
    def _google_places_text_search(self, lat: float, lon: float, query: str) -> Optional[Dict[str, Any]]:
        """Google Places Text Search API"""
        try:
            params = {
                'query': query,
                'location': f"{lat},{lon}",
                'radius': 200,  # 200m radius
                'key': self.google_api_key
            }
            
            response = self.session.get(
                "https://maps.googleapis.com/maps/api/place/textsearch/json",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'OK' and data.get('results'):
                # Prioritize results with more specific basketball court names
                results = data['results']
                
                # First, look for results with "basketball court" in the name
                for result in results:
                    name = result.get('name', '')
                    if 'basketball court' in name.lower():
                        return {
                            'name': name,
                            'place_id': result.get('place_id'),
                            'types': result.get('types', []),
                            'vicinity': result.get('vicinity')
                        }
                
                # Then look for other basketball-related results
                for result in results:
                    name = result.get('name', '')
                    if self._is_basketball_related(name):
                        return {
                            'name': name,
                            'place_id': result.get('place_id'),
                            'types': result.get('types', []),
                            'vicinity': result.get('vicinity')
                        }
            
            return None
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'google_places_text_search_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'query': query,
                'error': str(e)
            }))
            return None
    
    def _google_places_nearby_search(self, lat: float, lon: float, keyword: str) -> Optional[Dict[str, Any]]:
        """Google Places Nearby Search API"""
        try:
            params = {
                'location': f"{lat},{lon}",
                'radius': 100,  # 100m radius
                'type': 'establishment',
                'keyword': keyword,
                'key': self.google_api_key
            }
            
            response = self.session.get(
                "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'OK' and data.get('results'):
                # Prioritize results with more specific basketball court names
                results = data['results']
                
                # First, look for results with "basketball court" in the name
                for result in results:
                    name = result.get('name', '')
                    if 'basketball court' in name.lower():
                        return {
                            'name': name,
                            'place_id': result.get('place_id'),
                            'types': result.get('types', []),
                            'vicinity': result.get('vicinity')
                        }
                
                # Then look for other basketball-related results
                for result in results:
                    name = result.get('name', '')
                    if self._is_basketball_related(name):
                        return {
                            'name': name,
                            'place_id': result.get('place_id'),
                            'types': result.get('types', []),
                            'vicinity': result.get('vicinity')
                        }
            
            return None
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'google_places_nearby_search_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'keyword': keyword,
                'error': str(e)
            }))
            return None
    
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
            logger.error(json.dumps({
                'event': 'enhanced_osm_lookup_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return None
    
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
                f"{self.base_url}/reverse",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'osm_object_lookup_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
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
                f"{self.base_url}/search",
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
            logger.error(json.dumps({
                'event': 'nearby_courts_search_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
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
            logger.error(json.dumps({
                'event': 'smart_fallback_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
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
                f"{self.base_url}/reverse",
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
            logger.error(json.dumps({
                'event': 'standard_nominatim_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
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


class GooglePlacesProvider(GeocodingProvider):
    """Google Places API reverse geocoding provider"""
    
    def __init__(self, api_key: str, delay: float = 0.1):
        self.api_key = api_key
        self.delay = delay
        self.base_url = "https://maps.googleapis.com/maps/api/geocode/json"
        self.session = requests.Session()
        
        logger.info(json.dumps({
            'event': 'geocoding_provider_initialized',
            'provider': 'GooglePlaces',
            'delay': delay
        }))
    
    def reverse_geocode(self, lat: float, lon: float) -> Tuple[Optional[str], Optional[str]]:
        """Reverse geocode using Google Places API"""
        try:
            params = {
                'latlng': f"{lat},{lon}",
                'key': self.api_key
            }
            
            response = self.session.get(self.base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') != 'OK' or not data.get('results'):
                return None, None
            
            result = data['results'][0]
            address = result.get('formatted_address')
            place_id = result.get('place_id')
            
            logger.info(json.dumps({
                'event': 'reverse_geocoding_completed',
                'provider': 'GooglePlaces',
                'coordinates': {'lat': lat, 'lon': lon},
                'address_found': address is not None,
                'place_id_found': place_id is not None
            }))
            
            return address, place_id
            
        except requests.RequestException as e:
            logger.error(json.dumps({
                'event': 'reverse_geocoding_error',
                'provider': 'GooglePlaces',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return None, None
        except Exception as e:
            logger.error(json.dumps({
                'event': 'unexpected_error',
                'provider': 'GooglePlaces',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return None, None
        finally:
            time.sleep(self.delay)


class DatabaseManager:
    """Manages database operations for court data"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.engine = create_engine(connection_string)
        
        logger.info(json.dumps({
            'event': 'database_manager_initialized',
            'connection_string': connection_string.replace(connection_string.split('@')[0].split('//')[1], '***')
        }))
    
    def create_table_if_not_exists(self):
        """Create the courts table if it doesn't exist"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS courts (
            id SERIAL PRIMARY KEY,
            osm_id VARCHAR(255) UNIQUE NOT NULL,
            geom GEOMETRY(POINT, 4326),
            sport VARCHAR(100),
            hoops VARCHAR(10),
            fallback_name VARCHAR(255),
            google_place_id VARCHAR(255),
            enriched_name VARCHAR(255),
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_courts_osm_id ON courts(osm_id);
        CREATE INDEX IF NOT EXISTS idx_courts_geom ON courts USING GIST(geom);
        CREATE INDEX IF NOT EXISTS idx_courts_sport ON courts(sport);
        """
        
        try:
            with self.engine.connect() as conn:
                conn.execute(text(create_table_sql))
                conn.commit()
            
            logger.info(json.dumps({
                'event': 'database_table_created',
                'table': 'courts'
            }))
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'database_error',
                'operation': 'create_table',
                'error': str(e)
            }))
            raise
    
    def insert_court(self, court: CourtData) -> bool:
        """Insert a new court into the database"""
        insert_sql = """
        INSERT INTO courts (osm_id, geom, centroid, sport, hoops, fallback_name, 
                          google_place_id, enriched_name, address, source)
        VALUES (%s, ST_GeomFromGeoJSON(%s), ST_Centroid(ST_GeomFromGeoJSON(%s))::geography, 
                %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (osm_id) 
        DO UPDATE SET 
            geom = EXCLUDED.geom,
            centroid = EXCLUDED.centroid,
            sport = EXCLUDED.sport,
            hoops = EXCLUDED.hoops,
            fallback_name = EXCLUDED.fallback_name,
            google_place_id = EXCLUDED.google_place_id,
            enriched_name = EXCLUDED.enriched_name,
            address = EXCLUDED.address,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id;
        """
        
        try:
            # Use psycopg2 directly to avoid SQLAlchemy parameter binding issues
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            # Parse connection string
            import urllib.parse as urlparse
            url = urlparse.urlparse(self.connection_string)
            
            conn = psycopg2.connect(
                host=url.hostname,
                port=url.port,
                database=url.path[1:],
                user=url.username,
                password=url.password
            )
            
            with conn.cursor() as cursor:
                cursor.execute(insert_sql, (
                    court.osm_id,
                    court.polygon_geojson,  # geom - polygon geometry
                    court.polygon_geojson,  # centroid - calculated from same polygon
                    court.sport,
                    court.hoops,
                    court.fallback_name,
                    court.google_place_id,
                    court.enriched_name,
                    court.address,
                    'osm'  # source
                ))
                
                court_id = cursor.fetchone()[0]
                conn.commit()
                
                logger.info(json.dumps({
                    'event': 'court_inserted',
                    'osm_id': court.osm_id,
                    'court_id': court_id,
                    'sport': court.sport,
                    'has_address': court.address is not None
                }))
                
                return True
                
        except Exception as e:
            logger.error(json.dumps({
                'event': 'database_error',
                'operation': 'insert_court',
                'osm_id': court.osm_id,
                'error': str(e)
            }))
            return False
    
    def update_court_address(self, osm_id: str, address: str, place_id: Optional[str] = None) -> bool:
        """Update court address and place_id"""
        update_sql = """
        UPDATE courts 
        SET address = %(address)s, 
            google_place_id = COALESCE(%(place_id)s, google_place_id),
            updated_at = CURRENT_TIMESTAMP
        WHERE osm_id = %(osm_id)s
        RETURNING id;
        """
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(update_sql), {
                    'osm_id': osm_id,
                    'address': address,
                    'place_id': place_id
                })
                conn.commit()
                
                if result.rowcount > 0:
                    logger.info(json.dumps({
                        'event': 'court_address_updated',
                        'osm_id': osm_id,
                        'has_place_id': place_id is not None
                    }))
                    return True
                else:
                    logger.warning(json.dumps({
                        'event': 'court_not_found_for_update',
                        'osm_id': osm_id
                    }))
                    return False
                    
        except Exception as e:
            logger.error(json.dumps({
                'event': 'database_error',
                'operation': 'update_court_address',
                'osm_id': osm_id,
                'error': str(e)
            }))
            return False


class CourtDataEnricher:
    """Main class for enriching court data"""
    
    def __init__(self, db_manager: DatabaseManager, geocoding_provider: GeocodingProvider):
        self.db_manager = db_manager
        self.geocoding_provider = geocoding_provider
        
        logger.info(json.dumps({
            'event': 'court_data_enricher_initialized',
            'geocoding_provider': type(geocoding_provider).__name__
        }))
    
    def load_geojson(self, file_path: str) -> List[CourtData]:
        """Load and parse GeoJSON file"""
        try:
            with open(file_path, 'r') as f:
                data = geojson.load(f)
            
            courts = []
            for feature in data.get('features', []):
                try:
                    court = self._parse_feature(feature)
                    if court:
                        courts.append(court)
                except Exception as e:
                    logger.error(json.dumps({
                        'event': 'feature_parsing_error',
                        'feature_id': feature.get('id', 'unknown'),
                        'error': str(e)
                    }))
                    continue
            
            logger.info(json.dumps({
                'event': 'geojson_loaded',
                'file_path': file_path,
                'total_features': len(data.get('features', [])),
                'parsed_courts': len(courts)
            }))
            
            return courts
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'geojson_loading_error',
                'file_path': file_path,
                'error': str(e)
            }))
            raise
    
    def _parse_feature(self, feature: dict) -> Optional[CourtData]:
        """Parse a single GeoJSON feature into CourtData"""
        try:
            # Extract OSM ID
            osm_id = feature.get('id', '')
            if not osm_id:
                return None
            
            # Parse geometry
            geometry = feature.get('geometry')
            if not geometry:
                return None
            
            shapely_geom = shape(geometry)
            
            # Calculate centroid
            if hasattr(shapely_geom, 'centroid'):
                centroid = shapely_geom.centroid
            else:
                # For point geometries, use the point itself
                centroid = shapely_geom
            
            # Extract properties
            props = feature.get('properties', {})
            sport = props.get('sport')
            hoops = props.get('hoops')
            
            # Generate fallback name
            fallback_name = f"{sport} court" if sport else "Sports court"
            if hoops:
                fallback_name += f" ({hoops} hoops)"
            
            return CourtData(
                osm_id=osm_id,
                geom=centroid,
                sport=sport,
                hoops=hoops,
                fallback_name=fallback_name
            )
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'feature_parsing_error',
                'feature_id': feature.get('id', 'unknown'),
                'error': str(e)
            }))
            return None
    
    def enrich_court(self, court: CourtData) -> CourtData:
        """Enrich a court with reverse geocoding data"""
        try:
            lat, lon = court.geom.y, court.geom.x
            address, place_id = self.geocoding_provider.reverse_geocode(lat, lon)
            
            court.address = address
            court.google_place_id = place_id
            
            if address:
                # Store just the clean court name, not concatenated with fallback
                court.enriched_name = address.split(',')[0]
            
            logger.info(json.dumps({
                'event': 'court_enriched',
                'osm_id': court.osm_id,
                'coordinates': {'lat': lat, 'lon': lon},
                'has_address': address is not None,
                'has_place_id': place_id is not None
            }))
            
            return court
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'court_enrichment_error',
                'osm_id': court.osm_id,
                'error': str(e)
            }))
            return court


def main():
    """Main execution function"""
    logger.info(json.dumps({
        'event': 'data_enrichment_pipeline_started'
    }))
    
    # Database connection
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'courtpulse')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', '')
    
    connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Initialize components
    db_manager = DatabaseManager(connection_string)
    geocoding_provider = HybridGeocodingProvider()
    enricher = CourtDataEnricher(db_manager, geocoding_provider)
    
    try:
        # Create database table
        db_manager.create_table_if_not_exists()
        
        # Sample GeoJSON data (you can replace this with file loading)
        sample_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "@id": "way/28283137",
                        "sport": "basketball",
                        "leisure": "pitch",
                        "hoops": "2"
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [-122.4063442, 37.7500036],
                            [-122.406461, 37.7502223],
                            [-122.4066198, 37.7501692],
                            [-122.406503, 37.7499505],
                            [-122.4063442, 37.7500036]
                        ]]
                    },
                    "id": "way/28283137"
                }
            ]
        }
        
        # Write sample data to temporary file
        temp_file = '/tmp/sample_courts.geojson'
        with open(temp_file, 'w') as f:
            json.dump(sample_geojson, f)
        
        # Load and process courts
        courts = enricher.load_geojson(temp_file)
        
        # Process first 5 courts (as requested)
        processed_count = 0
        for court in courts[:5]:
            print(f"\nProcessing court: {court.osm_id}")
            print(f"Sport: {court.sport}")
            print(f"Hoops: {court.hoops}")
            print(f"Fallback name: {court.fallback_name}")
            print(f"Centroid: {court.geom.y:.6f}, {court.geom.x:.6f}")
            
            # Enrich with reverse geocoding
            enriched_court = enricher.enrich_court(court)
            
            print(f"Address: {enriched_court.address}")
            print(f"Place ID: {enriched_court.google_place_id}")
            print(f"Enriched name: {enriched_court.enriched_name}")
            
            # Insert into database
            success = db_manager.insert_court(enriched_court)
            print(f"Database insertion: {'Success' if success else 'Failed'}")
            
            processed_count += 1
        
        logger.info(json.dumps({
            'event': 'data_enrichment_pipeline_completed',
            'processed_courts': processed_count
        }))
        
        # Clean up temp file
        os.remove(temp_file)
        
    except Exception as e:
        logger.error(json.dumps({
            'event': 'pipeline_error',
            'error': str(e)
        }))
        raise


if __name__ == "__main__":
    main()
