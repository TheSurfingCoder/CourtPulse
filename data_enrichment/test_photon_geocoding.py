"""
Synchronous Photon geocoding provider for court data enrichment
"""

import requests
from requests.exceptions import HTTPError
import json
import logging
import math
import time
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from shapely.geometry import Polygon, Point

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PhotonGeocodingProvider:
    """Synchronous Photon reverse geocoding provider"""
    
    def __init__(self, base_url: str = "https://photon.komoot.io", delay: float = 1.0):
        self.base_url = base_url
        self.delay = delay
        self.last_request_time = 0
        
        logger.info(json.dumps({
            'event': 'photon_provider_initialized',
            'base_url': base_url,
            'delay': delay
        }))
    
    def reverse_geocode(self, lat: float, lon: float, court_count: int = 1) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Main entry point for reverse geocoding
        
        CLOSEST RESULT APPROACH: Search all priority OSM tags and pick the closest result
        Priority order (all results collected, then closest selected):
        1. Sports clubs (osm_tag=club:sport, 1000 ft) - tennis clubs, athletic clubs
        2. Sports centres (osm_tag=leisure:sports_centre, 1000 ft) - rec centers  
        3. Community centres (osm_tag=amenity:community_centre, 1000 ft) - JCC, etc.
        4. Schools/Universities (osm_tag=amenity:school/university, 500 ft) - educational institutions
        5. Places of worship (osm_tag=amenity:place_of_worship, 500 ft) - churches with courts
        6. Parks/Playgrounds (osm_tag=leisure:park/playground, 1000 ft)
        
        NO ADDRESS FALLBACK: Only use OSM-tagged facilities, never street addresses
        """
        try:
            # Rate limiting
            self._rate_limit()
            
            # Collect all results from priority searches
            all_results = []
            
            # 1. Sports club search (1000ft radius)
            sports_club_results = self._try_sports_club_search_all_results(lat, lon)
            if sports_club_results:
                all_results.extend([{**result, 'endpoint': 'sports_club'} for result in sports_club_results])
            
            # 2. Sports centre search (1000ft radius)
            sports_centre_results = self._try_sports_centre_search_all_results(lat, lon)
            if sports_centre_results:
                all_results.extend([{**result, 'endpoint': 'sports_centre'} for result in sports_centre_results])
            
            # 3. Community centre search (1000ft radius)
            community_centre_results = self._try_community_centre_search_all_results(lat, lon)
            if community_centre_results:
                all_results.extend([{**result, 'endpoint': 'community_centre'} for result in community_centre_results])
            
            # 4. School search (500ft radius)
            school_results = self._try_school_search_all_results(lat, lon)
            if school_results:
                all_results.extend([{**result, 'endpoint': 'school'} for result in school_results])
            
            # 5. Place of worship search (500ft radius)
            place_of_worship_results = self._try_place_of_worship_search_all_results(lat, lon)
            if place_of_worship_results:
                all_results.extend([{**result, 'endpoint': 'place_of_worship'} for result in place_of_worship_results])
            
            # 6. Park/playground search (1000ft radius)
            park_results = self._try_search_fallback_all_results(lat, lon)
            if park_results:
                all_results.extend([{**result, 'endpoint': 'park'} for result in park_results])
            
            if all_results:
                # Sort by distance and pick the closest result
                sorted_results = sorted(all_results, key=lambda x: x['distance'])
                closest_result = sorted_results[0]
                
                # Add court count to name if multiple courts
                name = closest_result['name']
                if court_count > 1:
                    name = f"{name} ({court_count} Courts)"
                
                logger.info(json.dumps({
                    'event': 'closest_result_selected',
                    'name': name,
                    'endpoint': closest_result['endpoint'],
                    'distance_km': round(closest_result['distance'], 3),
                    'coordinates': {'lat': lat, 'lon': lon},
                    'court_count': court_count,
                    'total_results': len(all_results),
                    'is_high_quality': self._is_high_quality_name(closest_result['name']),
                    'reason': 'closest_priority_result'
                }))
                
                return name, closest_result['data']
            
            # No results from any priority search - geocoding failed
            logger.warning(json.dumps({
                'event': 'geocoding_failed',
                'coordinates': {'lat': lat, 'lon': lon},
                'court_count': court_count,
                'reason': 'no_priority_results_found'
            }))
            return None, None
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'reverse_geocode_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'court_count': court_count,
                'error': str(e)
            }))
            return None, None
    
    def _try_search_fallback_all_results(self, lat: float, lon: float) -> List[Dict[str, Any]]:
        """Try to find nearby named places using search API and return all valid results"""
        try:
            # Define leisure types
            leisure_types = [
                {'osm_tag': 'leisure:park', 'q': 'park'},
                {'osm_tag': 'leisure:playground', 'q': 'playground'}
            ]
            
            all_nearby_results = []
            
            for leisure_type in leisure_types:
                try:
                    params = {
                        'q': leisure_type['q'],
                        'lat': lat,
                        'lon': lon,
                        'osm_tag': leisure_type['osm_tag'],
                        'location_bias_scale': 0.1,
                        'zoom': 20,
                        'limit': 3  # Get more results to choose from
                    }
                    
                    response = requests.get(f"{self.base_url}/api", params=params, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    
                    features = data.get('features', [])
                    if not features:
                        continue
                    
                    # Collect all results within search radius (no distance filtering)
                    for feature in features:
                        properties = feature.get('properties', {})
                        name = properties.get('name')
                        
                        if name:
                            # Calculate distance
                            coords = feature.get('geometry', {}).get('coordinates', [0, 0])
                            result_lon, result_lat = coords[0], coords[1]
                            distance = self._calculate_distance(lat, lon, result_lat, result_lon)
                            
                            all_nearby_results.append({
                                'name': name,
                                'data': feature,
                                'distance': distance
                            })
                            
                            logger.info(json.dumps({
                                'event': 'result_found',
                                'name': name,
                                'leisure_type': leisure_type['osm_tag'],
                                'distance_km': round(distance, 3),
                                'coordinates': {'lat': lat, 'lon': lon}
                            }))
                
                except Exception as e:
                    logger.error(json.dumps({
                        'event': 'search_error',
                        'leisure_type': leisure_type['osm_tag'],
                        'coordinates': {'lat': lat, 'lon': lon},
                        'error': str(e)
                    }))
                    continue
            
            logger.info(json.dumps({
                'event': 'park_search_completed',
                'coordinates': {'lat': lat, 'lon': lon},
                'total_results': len(all_nearby_results)
            }))
            
            return all_nearby_results
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'search_fallback_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return []
    
    def _try_sports_centre_search_all_results(self, lat: float, lon: float) -> List[Dict[str, Any]]:
        """Try to find nearby sports centres using search API and return all valid results"""
        try:
            # Search by osm_tag=leisure:sports_centre to catch recreation centers
            params = {
                'q': 'sports',
                'lat': lat,
                'lon': lon,
                'osm_tag': 'leisure:sports_centre',  # Search by OSM tag
                'limit': 3,
                'location_bias_scale': 0.1,
                'zoom': 20
            }
            
            response = requests.get(f"{self.base_url}/api", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            features = data.get('features', [])
            if not features:
                return []
            
            # Collect all results within search radius (no distance filtering)
            all_nearby_results = []
            for feature in features:
                properties = feature.get('properties', {})
                name = properties.get('name')
                
                if name:
                    # Calculate distance
                    coords = feature.get('geometry', {}).get('coordinates', [0, 0])
                    result_lon, result_lat = coords[0], coords[1]
                    distance = self._calculate_distance(lat, lon, result_lat, result_lon)
                    
                    all_nearby_results.append({
                        'name': name,
                        'data': feature,
                        'distance': distance
                    })
                    
                    logger.info(json.dumps({
                        'event': 'result_found',
                        'name': name,
                        'osm_type': 'leisure:sports_centre',
                        'distance_km': round(distance, 3),
                        'coordinates': {'lat': lat, 'lon': lon}
                    }))
            
            logger.info(json.dumps({
                'event': 'sports_centre_search_completed',
                'coordinates': {'lat': lat, 'lon': lon},
                'total_results': len(all_nearby_results)
            }))
            
            return all_nearby_results
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'sports_centre_search_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return []
    
    def _try_sports_club_search_all_results(self, lat: float, lon: float) -> List[Dict[str, Any]]:
        """Try to find nearby sports clubs using search API and return all valid results"""
        try:
            # Search by osm_tag=club:sport to catch tennis clubs, athletic clubs, etc.
            params = {
                'q': 'club',
                'lat': lat,
                'lon': lon,
                'osm_tag': 'club:sport',
                'limit': 5,
                'location_bias_scale': 0.1,
                'zoom': 20
            }
            
            response = requests.get(f"{self.base_url}/api", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            features = data.get('features', [])
            if not features:
                return []
            
            # Collect all results within search radius (no distance filtering)
            all_nearby_results = []
            for feature in features:
                properties = feature.get('properties', {})
                name = properties.get('name')
                
                if name:
                    coords = feature.get('geometry', {}).get('coordinates', [0, 0])
                    result_lon, result_lat = coords[0], coords[1]
                    distance = self._calculate_distance(lat, lon, result_lat, result_lon)
                    
                    all_nearby_results.append({
                        'name': name,
                        'data': feature,
                        'distance': distance
                    })
                    
                    logger.info(json.dumps({
                        'event': 'result_found',
                        'name': name,
                        'osm_type': 'club:sport',
                        'distance_km': round(distance, 3),
                        'coordinates': {'lat': lat, 'lon': lon}
                    }))
            
            logger.info(json.dumps({
                'event': 'sports_club_search_completed',
                'coordinates': {'lat': lat, 'lon': lon},
                'total_results': len(all_nearby_results)
            }))
            
            return all_nearby_results
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'sports_club_search_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return []
    
    def _try_community_centre_search_all_results(self, lat: float, lon: float) -> List[Dict[str, Any]]:
        """Try to find nearby community centres using OSM tag search only"""
        try:
            # Only search by OSM tag - no name-based searches
            # Note: Some facilities (like JCC SF) are poorly tagged as just 'building:yes'
            # and won't be found. They'll get street names instead.
            params = {
                'q': 'community center',
                'lat': lat,
                'lon': lon,
                'osm_tag': 'amenity:community_centre',
                'limit': 5,
                'location_bias_scale': 0.1,
                'zoom': 20
            }
            
            response = requests.get(f"{self.base_url}/api", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            features = data.get('features', [])
            if not features:
                return []
            
            # Collect all results within search radius (no distance filtering)
            all_nearby_results = []
            for feature in features:
                properties = feature.get('properties', {})
                name = properties.get('name')
                
                if name:
                    coords = feature.get('geometry', {}).get('coordinates', [0, 0])
                    result_lon, result_lat = coords[0], coords[1]
                    distance = self._calculate_distance(lat, lon, result_lat, result_lon)
                    
                    all_nearby_results.append({
                        'name': name,
                        'data': feature,
                        'distance': distance
                    })
                    
                    logger.info(json.dumps({
                        'event': 'result_found',
                        'name': name,
                        'osm_type': 'amenity:community_centre',
                        'distance_km': round(distance, 3),
                        'coordinates': {'lat': lat, 'lon': lon}
                    }))
            
            logger.info(json.dumps({
                'event': 'community_centre_search_completed',
                'coordinates': {'lat': lat, 'lon': lon},
                'total_results': len(all_nearby_results)
            }))
            
            return all_nearby_results
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'community_centre_search_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return []
    
    def _try_place_of_worship_search_all_results(self, lat: float, lon: float) -> List[Dict[str, Any]]:
        """Try to find nearby places of worship using search API and return all valid results"""
        try:
            # Search by osm_tag=amenity:place_of_worship to catch churches with courts
            params = {
                'q': 'church',
                'lat': lat,
                'lon': lon,
                'osm_tag': 'amenity:place_of_worship',
                'limit': 5,
                'location_bias_scale': 0.1,
                'zoom': 18
            }
            
            response = requests.get(f"{self.base_url}/api", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            features = data.get('features', [])
            if not features:
                return []
            
            # Collect all results within search radius (no distance filtering)
            all_nearby_results = []
            for feature in features:
                properties = feature.get('properties', {})
                name = properties.get('name')
                
                if name:
                    coords = feature.get('geometry', {}).get('coordinates', [0, 0])
                    result_lon, result_lat = coords[0], coords[1]
                    distance = self._calculate_distance(lat, lon, result_lat, result_lon)
                    
                    all_nearby_results.append({
                        'name': name,
                        'data': feature,
                        'distance': distance
                    })
                    
                    logger.info(json.dumps({
                        'event': 'result_found',
                        'name': name,
                        'osm_type': 'amenity:place_of_worship',
                        'distance_km': round(distance, 3),
                        'coordinates': {'lat': lat, 'lon': lon}
                    }))
            
            logger.info(json.dumps({
                'event': 'place_of_worship_search_completed',
                'coordinates': {'lat': lat, 'lon': lon},
                'total_results': len(all_nearby_results)
            }))
            
            return all_nearby_results
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'place_of_worship_search_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return []
    
    def _try_reverse_geocoding_all_results(self, lat: float, lon: float) -> List[Dict[str, Any]]:
        """Try reverse geocoding and return all valid results"""
        try:
            # Add parameters for better results
            params = {
                'lon': lon, 
                'lat': lat,
                'limit': 5  # Get more results to choose from
            }
            
            response = requests.get(f"{self.base_url}/reverse", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            features = data.get('features', [])
            if not features:
                return []
            
            # Filter results by distance and quality
            valid_results = []
            for feature in features:
                # Check if result is within acceptable distance (1000 feet = 0.305 km)
                if self._is_nearby_result(feature, lat, lon, max_distance_km=0.305):
                    name = self._extract_name(feature)
                    if name:
                        # Calculate distance for sorting
                        coords = feature.get('geometry', {}).get('coordinates', [0, 0])
                        result_lon, result_lat = coords[0], coords[1]
                        distance = self._calculate_distance(lat, lon, result_lat, result_lon)
                        
                        valid_results.append({
                            'name': name,
                            'data': feature,
                            'distance': distance
                        })
            
            logger.info(json.dumps({
                'event': 'reverse_geocoding_completed',
                'coordinates': {'lat': lat, 'lon': lon},
                'total_results': len(valid_results),
                'total_features': len(features)
            }))
            
            return valid_results
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'reverse_geocoding_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return []
    
    def _try_building_search_all_results(self, lat: float, lon: float) -> List[Dict[str, Any]]:
        """Try to find nearby buildings using address-based reverse geocoding with radius parameter"""
        try:
            # Use radius parameter (supported by /reverse endpoint)
            # 0.1 km = ~328 feet (tight radius for very local addresses)
            params = {
                'lon': lon,
                'lat': lat,
                'limit': 10,
                'radius': 0.1  # Search within 0.1 km radius (328 feet)
            }
            
            response = requests.get(f"{self.base_url}/reverse", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            all_nearby_results = []
            features = data.get('features', [])
            
            for feature in features:
                if self._is_nearby_result(feature, lat, lon, max_distance_km=0.076):  # 250ft
                    # Extract address information
                    properties = feature.get('properties', {})
                    
                    # Look for address components
                    housenumber = properties.get('housenumber')
                    street = properties.get('street')
                    name = properties.get('name')
                    
                    # Create address-based name (remove street numbers)
                    address_name = None
                    if street:
                        # Always use just the street name, not the housenumber
                        address_name = street
                    elif name and ('Street' in name or 'Avenue' in name or 'Boulevard' in name):
                        address_name = name
                    
                    if address_name:
                        distance = self._calculate_distance(
                            lat, lon,
                            feature['geometry']['coordinates'][1],
                            feature['geometry']['coordinates'][0]
                        )
                        
                        # Determine if it's likely residential based on context
                        is_residential = self._is_likely_residential(properties)
                        
                        all_nearby_results.append({
                            'name': address_name,
                            'distance': distance,
                            'data': feature,
                            'type': 'address',
                            'is_residential': is_residential
                        })
            
            # Sort by distance
            all_nearby_results.sort(key=lambda x: x['distance'])
            
            logger.info(json.dumps({
                'event': 'address_search_completed',
                'coordinates': {'lat': lat, 'lon': lon},
                'total_results': len(all_nearby_results),
                'residential_results': len([r for r in all_nearby_results if r.get('is_residential', False)]),
                'parameters': {'radius_km': 0.1, 'limit': 10}
            }))
            
            return all_nearby_results
        
        except Exception as e:
            logger.error(json.dumps({
                'event': 'address_search_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return []
    
    def _is_likely_residential(self, properties: Dict[str, Any]) -> bool:
        """Determine if a location is likely residential based on properties"""
        # Check for residential indicators
        name = properties.get('name', '').lower()
        osm_key = properties.get('osm_key', '')
        osm_value = properties.get('osm_value', '')
        
        # Residential indicators
        residential_indicators = [
            'apartment', 'condo', 'house', 'residential', 'home',
            'street', 'avenue', 'boulevard', 'drive', 'lane', 'place', 'court'
        ]
        
        # Non-residential indicators  
        non_residential_indicators = [
            'school', 'park', 'playground', 'office', 'commercial', 'business',
            'hospital', 'church', 'library', 'gym', 'sports', 'center'
        ]
        
        # Check name for residential indicators
        if any(indicator in name for indicator in non_residential_indicators):
            return False
        
        if any(indicator in name for indicator in residential_indicators):
            return True
        
        # Check OSM tags
        if osm_key == 'amenity' and osm_value in ['school', 'hospital', 'library', 'place_of_worship']:
            return False
        
        if osm_key == 'leisure' and osm_value in ['park', 'playground', 'sports_centre']:
            return False
        
        # Default to residential if it has an address
        housenumber = properties.get('housenumber')
        street = properties.get('street')
        if housenumber and street:
            return True
        
        return False
    
    def _try_residential_search_all_results(self, lat: float, lon: float) -> List[Dict[str, Any]]:
        """Try to find nearby residential buildings and return all valid results"""
        try:
            # Search for residential buildings (apartments, houses, condos)
            residential_types = [
                {'osm_tag': 'building:apartments', 'q': 'apartments'},
                {'osm_tag': 'building:residential', 'q': 'residential'},
                {'osm_tag': 'building:house', 'q': 'house'},
                {'osm_tag': 'building:condominium', 'q': 'condo'}
            ]
            
            all_nearby_results = []
            
            for building_type in residential_types:
                try:
                    params = {
                        'q': building_type['q'],
                        'lat': lat,
                        'lon': lon,
                        'osm_tag': building_type['osm_tag'],
                        'location_bias_scale': 0.05,  # Very tight radius for residential
                        'zoom': 20,
                        'limit': 3
                    }
                    
                    response = requests.get(f"{self.base_url}/api", params=params, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    
                    features = data.get('features', [])
                    for feature in features:
                        if self._is_nearby_result(feature, lat, lon, max_distance_km=0.061):  # 200ft
                            name = self._extract_name_from_feature(feature)
                            if name:
                                distance = self._calculate_distance(
                                    lat, lon,
                                    feature['geometry']['coordinates'][1],
                                    feature['geometry']['coordinates'][0]
                                )
                                all_nearby_results.append({
                                    'name': name,
                                    'distance': distance,
                                    'data': feature,
                                    'type': 'residential'
                                })
                    
                    time.sleep(self.delay)  # Rate limiting
                    
                except Exception as e:
                    logger.error(json.dumps({
                        'event': 'residential_search_error',
                        'building_type': building_type['osm_tag'],
                        'coordinates': {'lat': lat, 'lon': lon},
                        'error': str(e)
                    }))
                    continue
            
            # Sort by distance
            all_nearby_results.sort(key=lambda x: x['distance'])
            
            logger.info(json.dumps({
                'event': 'residential_search_completed',
                'coordinates': {'lat': lat, 'lon': lon},
                'total_results': len(all_nearby_results)
            }))
            
            return all_nearby_results
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'residential_search_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return []
    
    def _try_school_search_all_results(self, lat: float, lon: float) -> List[Dict[str, Any]]:
        """Try searching for schools and universities by OSM tag and return all valid results"""
        try:
            all_valid_results = []
            
            # Search for both schools and universities (multiple OSM tag types and query terms)
            # Different query terms catch different school names (e.g., "academy" finds "International Studies Academy")
            educational_tags = [
                {'osm_tag': 'amenity:school', 'q': 'school'},
                {'osm_tag': 'amenity:school', 'q': 'academy'},  # Catches schools named "...Academy"
                {'osm_tag': 'building:school', 'q': 'school'},  # Some schools tagged as buildings
                {'osm_tag': 'amenity:university', 'q': 'university'},
                {'osm_tag': 'amenity:college', 'q': 'college'}
            ]
            
            for edu_type in educational_tags:
                try:
                    params = {
                        'q': edu_type['q'],
                        'lat': lat,
                        'lon': lon,
                        'osm_tag': edu_type['osm_tag'],
                        'limit': 15,  # Increased to catch more schools
                        'location_bias_scale': 0.1,
                        'zoom': 18
                    }
                    
                    response = requests.get(f"{self.base_url}/api", params=params, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    
                    features = data.get('features', [])
                    
                    # Collect all results within search radius (no distance filtering)
                    for feature in features:
                        name = self._extract_name(feature)
                        if name:
                            # Calculate distance for sorting
                            coords = feature.get('geometry', {}).get('coordinates', [0, 0])
                            result_lon, result_lat = coords[0], coords[1]
                            distance = self._calculate_distance(lat, lon, result_lat, result_lon)
                            
                            all_valid_results.append({
                                'name': name,
                                'data': feature,
                                'distance': distance
                            })
                    
                    time.sleep(self.delay)  # Rate limiting between searches
                    
                except Exception as e:
                    logger.error(json.dumps({
                        'event': 'educational_search_error',
                        'edu_type': edu_type['osm_tag'],
                        'coordinates': {'lat': lat, 'lon': lon},
                        'error': str(e)
                    }))
                    continue
            
            # Remove duplicates and sort by distance
            seen_names = set()
            unique_results = []
            for result in sorted(all_valid_results, key=lambda x: x['distance']):
                if result['name'] not in seen_names:
                    seen_names.add(result['name'])
                    unique_results.append(result)
            
            logger.info(json.dumps({
                'event': 'school_search_completed',
                'coordinates': {'lat': lat, 'lon': lon},
                'total_results': len(unique_results)
            }))
            
            return unique_results
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'school_search_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return []
    
    def _try_school_search(self, lat: float, lon: float) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Try searching for schools as final fallback (legacy method for backward compatibility)"""
        results = self._try_school_search_all_results(lat, lon)
        if not results:
            return None, None
        
        # Filter for high quality names and return the closest
        high_quality_results = [r for r in results if self._is_high_quality_name(r['name'])]
        results_to_consider = high_quality_results if high_quality_results else results
        
        closest_result = min(results_to_consider, key=lambda x: x['distance'])
        return closest_result['name'], closest_result['data']
    
    def _try_search_fallback(self, lat: float, lon: float, court_count: int) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Try to find nearby named places using search API (legacy method for backward compatibility)"""
        results = self._try_search_fallback_all_results(lat, lon)
        if not results:
            return None, None
        
        # Filter for high quality names and return the closest
        high_quality_results = [r for r in results if self._is_high_quality_name(r['name'])]
        results_to_consider = high_quality_results if high_quality_results else results
        
        closest_result = min(results_to_consider, key=lambda x: x['distance'])
        
        # Add court count to name if multiple courts
        name = closest_result['name']
        if court_count > 1:
            name = f"{name} ({court_count} Courts)"
        
        return name, closest_result['data']
    
    def _try_reverse_geocoding(self, lat: float, lon: float) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Try reverse geocoding as fallback with distance filtering (legacy method for backward compatibility)"""
        results = self._try_reverse_geocoding_all_results(lat, lon)
        if not results:
            return None, None
        
        # Filter for high quality names and return the closest
        high_quality_results = [r for r in results if self._is_high_quality_name(r['name'])]
        results_to_consider = high_quality_results if high_quality_results else results
        
        closest_result = min(results_to_consider, key=lambda x: x['distance'])
        return closest_result['name'], closest_result['data']
    
    def _is_high_quality_name(self, name: str) -> bool:
        """Check if a name is high quality (not just a street address)"""
        if not name or len(name.strip()) < 3:
            return False
        
        name_lower = name.lower()
        
        # Always accept school names, even if classified as 'house' in Photon
        school_keywords = ['school', 'academy', 'college', 'university', 'institute']
        for keyword in school_keywords:
            if keyword in name_lower:
                return True
        
        # Skip generic street names and numbers
        skip_patterns = [
            'unnamed', 'untitled', 'no name',
            'street', 'avenue', 'boulevard', 'road', 'way', 'drive',
            'st ', ' st', 'ave ', ' ave', 'blvd ', ' blvd'
        ]
        
        for pattern in skip_patterns:
            if pattern in name_lower:
                return False
        
        # Skip if it's mostly numbers
        if sum(c.isdigit() for c in name) > len(name) * 0.5:
            return False
        
        return True
    
    def _is_nearby_result(self, feature: Dict[str, Any], target_lat: float, target_lon: float, max_distance_km: float = 0.305) -> bool:
        """Check if result is within acceptable distance (1000 feet = 0.305 km)"""
        try:
            coords = feature.get('geometry', {}).get('coordinates', [0, 0])
            result_lon, result_lat = coords[0], coords[1]  # GeoJSON format
            
            distance = self._calculate_distance(target_lat, target_lon, result_lat, result_lon)
            is_nearby = distance <= max_distance_km
            
            logger.info(json.dumps({
                'event': 'distance_check',
                'target_coords': {'lat': target_lat, 'lon': target_lon},
                'result_coords': {'lat': result_lat, 'lon': result_lon},
                'distance_km': round(distance, 3),
                'max_distance_km': max_distance_km,
                'is_nearby': is_nearby
            }))
            
            return is_nearby
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'distance_check_error',
                'error': str(e)
            }))
            return False
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula (returns km)"""
        R = 6371.0  # Earth's radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def _extract_name(self, feature: Dict[str, Any]) -> Optional[str]:
        """Extract the best available name from a Photon feature"""
        try:
            properties = feature.get('properties', {})
            
            # Try different name fields in order of preference
            name_candidates = []
            
            # Primary name
            if properties.get('name'):
                name_candidates.append(f"name: {properties['name']}")
            
            # City + Country as fallback
            city = properties.get('city')
            country = properties.get('country')
            if city and country:
                name_candidates.append(f"city_country: {city}, {country}")
            
            # Street + City
            street = properties.get('street')
            if street and city:
                name_candidates.append(f"street_city: {street}, {city}")
            
            # House number + Street
            housenumber = properties.get('housenumber')
            if housenumber and street:
                name_candidates.append(f"housenumber_street: {housenumber} {street}")
            
            # Log all candidates for debugging
            logger.info(json.dumps({
                'event': 'name_candidates',
                'all_candidates': name_candidates
            }))
            
            # Return the first (best) candidate
            if name_candidates:
                best_candidate = name_candidates[0]
                extraction_type = best_candidate.split(':')[0]
                name = best_candidate.split(':', 1)[1].strip()
                
                logger.info(json.dumps({
                    'event': 'name_extracted',
                    'extraction_type': extraction_type,
                    'name': name,
                    'all_candidates': name_candidates
                }))
                
                return name
            
            return None
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'name_extraction_error',
                'error': str(e)
            }))
            return None
    
    def _rate_limit(self):
        """Simple rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.delay:
            sleep_time = self.delay - time_since_last
            logger.info(json.dumps({
                'event': 'rate_limiting',
                'sleep_time': sleep_time
            }))
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()

# Example usage
if __name__ == "__main__":
    # Test the provider
    provider = PhotonGeocodingProvider()
    
    # Test coordinates
    test_coords = [
        (37.75006984, -122.40645443999999),  # James Rolph Jr. Playground
        (37.7334692, -122.3762353),          # India Basin Shoreline Park
    ]
    
    for lat, lon in test_coords:
        name, data = provider.reverse_geocode(lat, lon, 2)
        print(f"Result: {name}")
