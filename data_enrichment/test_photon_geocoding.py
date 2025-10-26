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
from bounding_box_geocoding import BoundingBoxGeocodingProvider

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PhotonGeocodingProvider:
    """Synchronous Photon reverse geocoding provider"""
    
    def __init__(self, base_url: str = "https://photon.komoot.io", delay: float = 1.0):
        self.base_url = base_url
        self.delay = delay
        self.last_request_time = 0
        
        # Track optimization metrics
        self.bounding_box_count = 0
        self.distance_based_count = 0
        self.total_requests = 0
        
        # Initialize bounding box geocoding provider
        self.bbox_provider = BoundingBoxGeocodingProvider(base_url, delay)
        
        logger.info(json.dumps({
            'event': 'photon_provider_initialized',
            'base_url': base_url,
            'delay': delay
        }))
    
    def reverse_geocode(self, lat: float, lon: float, court_count: int = 1, sport: str = 'basketball') -> Tuple[Optional[str], Optional[Dict[str, Any]], int]:
        """Main entry point for reverse geocoding
        
        BOUNDING BOX ONLY APPROACH: Try bounding box search, return generic name if no match
        1. Bounding box search (primary method)
        2. Generic sport name (fallback - no clustering)
        """
        try:
            logger.info(json.dumps({
                'event': 'reverse_geocoding_started',
                'coordinates': {'lat': lat, 'lon': lon},
                'court_count': court_count
            }))
            
            # 1. Try bounding box search first
            bbox_result = self._try_bounding_box_search(lat, lon, court_count)
            if bbox_result[0]:  # If we found a result
                logger.info(json.dumps({
                    'event': 'bounding_box_search_success',
                    'coordinates': {'lat': lat, 'lon': lon},
                    'facility_name': bbox_result[0]
                }))
                return bbox_result[0], bbox_result[1], bbox_result[2]
            
            # 2. Return generic sport name (no clustering)
            generic_name = self._get_generic_sport_name(sport)
            logger.info(json.dumps({
                'event': 'bounding_box_search_failed',
                'coordinates': {'lat': lat, 'lon': lon},
                'reason': 'using_generic_sport_name',
                'generic_name': generic_name
            }))
            
            return generic_name, None, 0
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'reverse_geocode_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'court_count': court_count,
                'error': str(e)
            }))
            return None, None, 0
    
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
                        'location_bias_scale': 0.2,  # Default prominence bias
                        'zoom': 18,  # ~300m radius for 1000ft search
                        'limit': 3  # Get more results to choose from
                    }
                    
                    response = requests.get(f"{self.base_url}/api", params=params, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    self.total_requests += 1
                    
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
                            
                            # Check if court is inside park bounding box
                            park_extent = properties.get('extent')
                            is_inside_park = self._is_point_in_park_extent(lat, lon, park_extent)
                            
                            # If court is inside park, give it huge priority (almost zero distance)
                            if is_inside_park:
                                distance = 0.001  # Almost zero distance for courts inside parks
                                logger.info(json.dumps({
                                    'event': 'court_inside_park',
                                    'name': name,
                                    'leisure_type': leisure_type['osm_tag'],
                                    'original_distance_km': round(self._calculate_distance(lat, lon, result_lat, result_lon), 3),
                                    'adjusted_distance_km': 0.001,
                                    'coordinates': {'lat': lat, 'lon': lon},
                                    'park_extent': park_extent
                                }))
                            
                            all_nearby_results.append({
                                'name': name,
                                'data': feature,
                                'distance': distance,
                                'is_inside_park': is_inside_park
                            })
                            
                            logger.info(json.dumps({
                                'event': 'result_found',
                                'name': name,
                                'leisure_type': leisure_type['osm_tag'],
                                'distance_km': round(distance, 3),
                                'is_inside_park': is_inside_park,
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
                'location_bias_scale': 0.2,  # Default prominence bias
                'zoom': 20  # ~60m radius for 200ft search
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
                'location_bias_scale': 0.2,  # Default prominence bias
                'zoom': 20  # ~60m radius for 200ft search
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
                'location_bias_scale': 0.2,  # Default prominence bias
                'zoom': 20  # ~60m radius for 200ft search
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
                        'location_bias_scale': 0.0015,  # ~165m radius for 500ft search
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
                        'location_bias_scale': 0.2,  # Default prominence bias
                        'zoom': 18  # ~300m radius for 1000ft search
                    }
                    
                    response = requests.get(f"{self.base_url}/api", params=params, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    self.total_requests += 1
                    
                    features = data.get('features', [])
                    
                    # Collect results within 500 feet (0.152 km) radius
                    for feature in features:
                        name = self._extract_name(feature)
                        if name:
                            # Calculate distance for filtering
                            coords = feature.get('geometry', {}).get('coordinates', [0, 0])
                            result_lon, result_lat = coords[0], coords[1]
                            distance = self._calculate_distance(lat, lon, result_lat, result_lon)
                            
                            # Only include results within 500 feet (0.152 km)
                            if distance <= 0.152:
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
    
    def _is_point_in_park_extent(self, court_lat: float, court_lon: float, park_extent: List[float]) -> bool:
        """Check if court is inside park's bounding box
        
        Args:
            court_lat: Court latitude
            court_lon: Court longitude  
            park_extent: Park bounding box [min_lon, max_lat, max_lon, min_lat]
        
        Returns:
            True if court is inside park bounding box
        """
        if not park_extent or len(park_extent) != 4:
            return False
            
        min_lon, max_lat, max_lon, min_lat = park_extent
        return (min_lat <= court_lat <= max_lat and 
                min_lon <= court_lon <= max_lon)
    
    def _is_point_in_facility_extent(self, court_lat: float, court_lon: float, facility_extent: List[float]) -> bool:
        """Check if court is inside facility's bounding box
        
        Args:
            court_lat: Court latitude
            court_lon: Court longitude  
            facility_extent: Facility bounding box [min_lon, max_lat, max_lon, min_lat]
        
        Returns:
            True if court is inside facility bounding box
        """
        if not facility_extent or len(facility_extent) != 4:
            return False
            
        min_lon, max_lat, max_lon, min_lat = facility_extent
        return (min_lat <= court_lat <= max_lat and 
                min_lon <= court_lon <= max_lon)
    
    def _try_search_with_bounding_box(self, lat: float, lon: float, search_type: str, 
                                     leisure_types: List[Dict[str, str]], radius_ft: int) -> List[Dict[str, Any]]:
        """Generic search method with bounding box support"""
        try:
            all_results = []
            
            for leisure_type in leisure_types:
                try:
                    params = {
                        'q': leisure_type['q'],
                        'lat': lat,
                        'lon': lon,
                        'osm_tag': leisure_type['osm_tag'],
                        'location_bias_scale': 0.2,  # Default prominence bias
                        'zoom': 18,  # ~300m radius for 1000ft search
                        'limit': 3
                    }
                    
                    response = requests.get(f"{self.base_url}/api", params=params, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    self.total_requests += 1
                    
                    features = data.get('features', [])
                    if not features:
                        continue
                    
                    for feature in features:
                        properties = feature.get('properties', {})
                        name = properties.get('name')
                        
                        if name:
                            coords = feature.get('geometry', {}).get('coordinates', [0, 0])
                            result_lon, result_lat = coords[0], coords[1]
                            distance = self._calculate_distance(lat, lon, result_lat, result_lon)
                            
                            # Check if court is inside facility bounding box
                            facility_extent = properties.get('extent')
                            is_inside_facility = self._is_point_in_facility_extent(lat, lon, facility_extent)
                            
                            if is_inside_facility:
                                distance = 0.001  # Almost zero distance for courts inside facilities
                                logger.info(json.dumps({
                                    'event': 'court_inside_facility',
                                    'name': name,
                                    'search_type': search_type,
                                    'leisure_type': leisure_type['osm_tag'],
                                    'original_distance_km': round(self._calculate_distance(lat, lon, result_lat, result_lon), 3),
                                    'adjusted_distance_km': 0.001,
                                    'coordinates': {'lat': lat, 'lon': lon},
                                    'facility_extent': facility_extent
                                }))
                            
                            all_results.append({
                                'name': name,
                                'data': feature,
                                'distance': distance,
                                'is_inside_facility': is_inside_facility,
                                'search_type': search_type,
                                'leisure_type': leisure_type['osm_tag']
                            })
                
                except Exception as e:
                    logger.error(json.dumps({
                        'event': 'search_error',
                        'search_type': search_type,
                        'leisure_type': leisure_type['osm_tag'],
                        'coordinates': {'lat': lat, 'lon': lon},
                        'error': str(e)
                    }))
                    continue
            
            logger.info(json.dumps({
                'event': f'{search_type}_search_completed',
                'coordinates': {'lat': lat, 'lon': lon},
                'total_results': len(all_results)
            }))
            
            return all_results
            
        except Exception as e:
            logger.error(json.dumps({
                'event': f'{search_type}_search_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return []
    
    def _check_bounding_box_results(self, results: List[Dict[str, Any]], lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Check if any results have bounding box matches and return the best one"""
        bounding_box_results = [r for r in results if r.get('is_inside_facility', False)]
        
        if bounding_box_results:
            # Sort by distance and return the closest bounding box match
            sorted_results = sorted(bounding_box_results, key=lambda x: x['distance'])
            return sorted_results[0]
        
        return None
    
    def _format_result(self, result: Dict[str, Any], court_count: int, endpoint: str, reason: str) -> Tuple[str, Dict[str, Any]]:
        """Format the final result with proper naming and logging"""
        name = result['name']
        if court_count > 1:
            name = f"{name} ({court_count} Courts)"
        
        # Track optimization metrics
        optimization_type = "bounding_box" if reason == "bounding_box_match" else "distance_based"
        
        # Note: Counting is handled by the calling methods, not here
        
        logger.info(json.dumps({
            'event': 'result_selected',
            'name': name,
            'endpoint': endpoint,
            'distance_km': round(result['distance'], 3),
            'is_inside_facility': result.get('is_inside_facility', False),
            'reason': reason,
            'optimization_type': optimization_type,
            'is_high_quality': self._is_high_quality_name(result['name']),
            'optimization_stats': self.get_optimization_stats()
        }))
        
        return name, result['data']
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization statistics"""
        total_courts = self.bounding_box_count + self.distance_based_count
        
        if total_courts == 0:
            return {
                'total_requests': self.total_requests,
                'bounding_box_count': 0,
                'distance_based_count': 0,
                'bounding_box_percentage': 0.0,
                'distance_based_percentage': 0.0
            }
        
        return {
            'total_requests': self.total_requests,
            'bounding_box_count': self.bounding_box_count,
            'distance_based_count': self.distance_based_count,
            'bounding_box_percentage': round((self.bounding_box_count / total_courts) * 100, 1),
            'distance_based_percentage': round((self.distance_based_count / total_courts) * 100, 1)
        }
    
    def _fallback_to_distance_based_selection_with_results(self, collected_results: List[Dict[str, Any]], lat: float, lon: float, court_count: int) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Optimized fallback method: use collected results from bounding box phase for distance-based selection"""
        if collected_results:
            # Sort by distance and pick the closest result
            sorted_results = sorted(collected_results, key=lambda x: x['distance'])
            closest_result = sorted_results[0]
            
            logger.info(json.dumps({
                'event': 'distance_based_selection_completed',
                'coordinates': {'lat': lat, 'lon': lon},
                'court_count': court_count,
                'total_candidates': len(collected_results),
                'selected_result': {
                    'name': closest_result['name'],
                    'endpoint': closest_result['endpoint'],
                    'distance_km': round(closest_result['distance'], 3)
                }
            }))
            
            return self._format_result(closest_result, court_count, closest_result['endpoint'], 'distance_based_fallback')
        
        # No results from any priority search - geocoding failed
        logger.warning(json.dumps({
            'event': 'geocoding_failed',
            'coordinates': {'lat': lat, 'lon': lon},
            'court_count': court_count,
            'reason': 'no_priority_results_found'
        }))
        return None, None

    def _fallback_to_distance_based_selection(self, lat: float, lon: float, court_count: int) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Legacy fallback method: run all searches and use distance-based selection (DEPRECATED - use _fallback_to_distance_based_selection_with_results instead)"""
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
            
            return self._format_result(closest_result, court_count, closest_result['endpoint'], 'distance_based_fallback')
        
        # No results from any priority search - geocoding failed
        logger.warning(json.dumps({
            'event': 'geocoding_failed',
            'coordinates': {'lat': lat, 'lon': lon},
            'court_count': court_count,
            'reason': 'no_priority_results_found'
        }))
        return None, None
    
    def _try_school_search_with_bounding_box(self, lat: float, lon: float) -> List[Dict[str, Any]]:
        """School search with bounding box support"""
        try:
            all_results = []
            
            # Define school types - match the working old method
            school_types = [
                {'osm_tag': 'amenity:school', 'q': 'school'},
                {'osm_tag': 'amenity:school', 'q': 'academy'},  # Catches schools named "...Academy"
                {'osm_tag': 'building:school', 'q': 'school'},  # Some schools tagged as buildings
                {'osm_tag': 'amenity:university', 'q': 'university'},
                {'osm_tag': 'amenity:college', 'q': 'college'}
            ]
            
            for school_type in school_types:
                try:
                    params = {
                        'q': school_type['q'],
                        'lat': lat,
                        'lon': lon,
                        'osm_tag': school_type['osm_tag'],
                        'location_bias_scale': 0.2,  # Default prominence bias
                        'zoom': 18,  # ~300m radius for 1000ft search
                        'limit': 3  # Test with limit 3
                    }
                    
                    response = requests.get(f"{self.base_url}/api", params=params, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    self.total_requests += 1
                    
                    features = data.get('features', [])
                    if not features:
                        continue
                    
                    for feature in features:
                        properties = feature.get('properties', {})
                        name = properties.get('name')
                        
                        if name:
                            coords = feature.get('geometry', {}).get('coordinates', [0, 0])
                            result_lon, result_lat = coords[0], coords[1]
                            distance = self._calculate_distance(lat, lon, result_lat, result_lon)
                            
                            # Check if court is inside school bounding box
                            school_extent = properties.get('extent')
                            is_inside_school = self._is_point_in_facility_extent(lat, lon, school_extent)
                            
                            if is_inside_school:
                                distance = 0.001  # Almost zero distance for courts inside schools
                                logger.info(json.dumps({
                                    'event': 'court_inside_school',
                                    'name': name,
                                    'school_type': school_type['osm_tag'],
                                    'original_distance_km': round(self._calculate_distance(lat, lon, result_lat, result_lon), 3),
                                    'adjusted_distance_km': 0.001,
                                    'coordinates': {'lat': lat, 'lon': lon},
                                    'school_extent': school_extent
                                }))
                            
                            # Only include results within 500 feet (0.152 km) or inside bounding box
                            if distance <= 0.152 or is_inside_school:
                                all_results.append({
                                    'name': name,
                                    'data': feature,
                                    'distance': distance,
                                    'is_inside_facility': is_inside_school,
                                    'search_type': 'school',
                                    'leisure_type': school_type['osm_tag']
                                })
                
                except Exception as e:
                    logger.error(json.dumps({
                        'event': 'school_search_error',
                        'school_type': school_type['osm_tag'],
                        'coordinates': {'lat': lat, 'lon': lon},
                        'error': str(e)
                    }))
                    continue
            
            logger.info(json.dumps({
                'event': 'school_search_completed',
                'coordinates': {'lat': lat, 'lon': lon},
                'total_results': len(all_results)
            }))
            
            return all_results
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'school_search_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return []
    
    def _try_community_centre_search_with_bounding_box(self, lat: float, lon: float) -> List[Dict[str, Any]]:
        """Community centre search with bounding box support"""
        try:
            all_results = []
            
            # Define community centre types
            community_types = [
                {'osm_tag': 'amenity:community_centre', 'q': 'community center'},
                {'osm_tag': 'amenity:community_centre', 'q': 'community centre'}
            ]
            
            for community_type in community_types:
                try:
                    params = {
                        'q': community_type['q'],
                        'lat': lat,
                        'lon': lon,
                        'osm_tag': community_type['osm_tag'],
                        'location_bias_scale': 0.2,  # Default prominence bias
                        'zoom': 19,  # ~150m radius for 500ft search
                        'limit': 3
                    }
                    
                    response = requests.get(f"{self.base_url}/api", params=params, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    self.total_requests += 1
                    
                    features = data.get('features', [])
                    if not features:
                        continue
                    
                    for feature in features:
                        properties = feature.get('properties', {})
                        name = properties.get('name')
                        
                        if name:
                            coords = feature.get('geometry', {}).get('coordinates', [0, 0])
                            result_lon, result_lat = coords[0], coords[1]
                            distance = self._calculate_distance(lat, lon, result_lat, result_lon)
                            
                            # Check if court is inside community centre bounding box
                            community_extent = properties.get('extent')
                            is_inside_community = self._is_point_in_facility_extent(lat, lon, community_extent)
                            
                            if is_inside_community:
                                distance = 0.001  # Almost zero distance for courts inside community centres
                                logger.info(json.dumps({
                                    'event': 'court_inside_community_centre',
                                    'name': name,
                                    'community_type': community_type['osm_tag'],
                                    'original_distance_km': round(self._calculate_distance(lat, lon, result_lat, result_lon), 3),
                                    'adjusted_distance_km': 0.001,
                                    'coordinates': {'lat': lat, 'lon': lon},
                                    'community_extent': community_extent
                                }))
                            
                            all_results.append({
                                'name': name,
                                'data': feature,
                                'distance': distance,
                                'is_inside_facility': is_inside_community,
                                'search_type': 'community_centre',
                                'leisure_type': community_type['osm_tag']
                            })
                
                except Exception as e:
                    logger.error(json.dumps({
                        'event': 'community_search_error',
                        'community_type': community_type['osm_tag'],
                        'coordinates': {'lat': lat, 'lon': lon},
                        'error': str(e)
                    }))
                    continue
            
            logger.info(json.dumps({
                'event': 'community_centre_search_completed',
                'coordinates': {'lat': lat, 'lon': lon},
                'total_results': len(all_results)
            }))
            
            return all_results
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'community_centre_search_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return []
    
    def _try_sports_club_search_with_bounding_box(self, lat: float, lon: float) -> List[Dict[str, Any]]:
        """Sports club search with bounding box support"""
        try:
            all_results = []
            
            # Define sports club types
            sports_types = [
                {'osm_tag': 'club:sport', 'q': 'tennis club'},
                {'osm_tag': 'club:sport', 'q': 'athletic club'},
                {'osm_tag': 'club:sport', 'q': 'sports club'}
            ]
            
            for sports_type in sports_types:
                try:
                    params = {
                        'q': sports_type['q'],
                        'lat': lat,
                        'lon': lon,
                        'osm_tag': sports_type['osm_tag'],
                        'location_bias_scale': 0.2,  # Default prominence bias
                        'zoom': 19,  # ~150m radius for 500ft search
                        'limit': 3
                    }
                    
                    response = requests.get(f"{self.base_url}/api", params=params, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    self.total_requests += 1
                    
                    features = data.get('features', [])
                    if not features:
                        continue
                    
                    for feature in features:
                        properties = feature.get('properties', {})
                        name = properties.get('name')
                        
                        if name:
                            coords = feature.get('geometry', {}).get('coordinates', [0, 0])
                            result_lon, result_lat = coords[0], coords[1]
                            distance = self._calculate_distance(lat, lon, result_lat, result_lon)
                            
                            # Check if court is inside sports club bounding box
                            sports_extent = properties.get('extent')
                            is_inside_sports = self._is_point_in_facility_extent(lat, lon, sports_extent)
                            
                            if is_inside_sports:
                                distance = 0.001  # Almost zero distance for courts inside sports clubs
                                logger.info(json.dumps({
                                    'event': 'court_inside_sports_club',
                                    'name': name,
                                    'sports_type': sports_type['osm_tag'],
                                    'original_distance_km': round(self._calculate_distance(lat, lon, result_lat, result_lon), 3),
                                    'adjusted_distance_km': 0.001,
                                    'coordinates': {'lat': lat, 'lon': lon},
                                    'sports_extent': sports_extent
                                }))
                            
                            all_results.append({
                                'name': name,
                                'data': feature,
                                'distance': distance,
                                'is_inside_facility': is_inside_sports,
                                'search_type': 'sports_club',
                                'leisure_type': sports_type['osm_tag']
                            })
                
                except Exception as e:
                    logger.error(json.dumps({
                        'event': 'sports_club_search_error',
                        'sports_type': sports_type['osm_tag'],
                        'coordinates': {'lat': lat, 'lon': lon},
                        'error': str(e)
                    }))
                    continue
            
            logger.info(json.dumps({
                'event': 'sports_club_search_completed',
                'coordinates': {'lat': lat, 'lon': lon},
                'total_results': len(all_results)
            }))
            
            return all_results
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'sports_club_search_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return []
    
    def _try_place_of_worship_search_with_bounding_box(self, lat: float, lon: float) -> List[Dict[str, Any]]:
        """Place of worship search with bounding box support"""
        try:
            all_results = []
            
            # Define worship types
            worship_types = [
                {'osm_tag': 'amenity:place_of_worship', 'q': 'church'},
                {'osm_tag': 'amenity:place_of_worship', 'q': 'mosque'},
                {'osm_tag': 'amenity:place_of_worship', 'q': 'synagogue'}
            ]
            
            for worship_type in worship_types:
                try:
                    params = {
                        'q': worship_type['q'],
                        'lat': lat,
                        'lon': lon,
                        'osm_tag': worship_type['osm_tag'],
                        'location_bias_scale': 0.2,  # Default prominence bias
                        'zoom': 19,  # ~150m radius for 500ft search
                        'limit': 3
                    }
                    
                    response = requests.get(f"{self.base_url}/api", params=params, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    self.total_requests += 1
                    
                    features = data.get('features', [])
                    if not features:
                        continue
                    
                    for feature in features:
                        properties = feature.get('properties', {})
                        name = properties.get('name')
                        
                        if name:
                            coords = feature.get('geometry', {}).get('coordinates', [0, 0])
                            result_lon, result_lat = coords[0], coords[1]
                            distance = self._calculate_distance(lat, lon, result_lat, result_lon)
                            
                            # Check if court is inside place of worship bounding box
                            worship_extent = properties.get('extent')
                            is_inside_worship = self._is_point_in_facility_extent(lat, lon, worship_extent)
                            
                            if is_inside_worship:
                                distance = 0.001  # Almost zero distance for courts inside places of worship
                                logger.info(json.dumps({
                                    'event': 'court_inside_place_of_worship',
                                    'name': name,
                                    'worship_type': worship_type['osm_tag'],
                                    'original_distance_km': round(self._calculate_distance(lat, lon, result_lat, result_lon), 3),
                                    'adjusted_distance_km': 0.001,
                                    'coordinates': {'lat': lat, 'lon': lon},
                                    'worship_extent': worship_extent
                                }))
                            
                            all_results.append({
                                'name': name,
                                'data': feature,
                                'distance': distance,
                                'is_inside_facility': is_inside_worship,
                                'search_type': 'place_of_worship',
                                'leisure_type': worship_type['osm_tag']
                            })
                
                except Exception as e:
                    logger.error(json.dumps({
                        'event': 'worship_search_error',
                        'worship_type': worship_type['osm_tag'],
                        'coordinates': {'lat': lat, 'lon': lon},
                        'error': str(e)
                    }))
                    continue
            
            logger.info(json.dumps({
                'event': 'place_of_worship_search_completed',
                'coordinates': {'lat': lat, 'lon': lon},
                'total_results': len(all_results)
            }))
            
            return all_results
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'place_of_worship_search_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return []
    
    def _try_sports_centre_search_with_bounding_box(self, lat: float, lon: float) -> List[Dict[str, Any]]:
        """Sports centre search with bounding box support"""
        try:
            all_results = []
            
            # Define sports centre types
            sports_centre_types = [
                {'osm_tag': 'leisure:sports_centre', 'q': 'sports center'},
                {'osm_tag': 'leisure:sports_centre', 'q': 'recreation center'}
            ]
            
            for sports_centre_type in sports_centre_types:
                try:
                    params = {
                        'q': sports_centre_type['q'],
                        'lat': lat,
                        'lon': lon,
                        'osm_tag': sports_centre_type['osm_tag'],
                        'location_bias_scale': 0.2,  # Default prominence bias
                        'zoom': 19,  # ~150m radius for 500ft search
                        'limit': 3
                    }
                    
                    response = requests.get(f"{self.base_url}/api", params=params, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    self.total_requests += 1
                    
                    features = data.get('features', [])
                    if not features:
                        continue
                    
                    for feature in features:
                        properties = feature.get('properties', {})
                        name = properties.get('name')
                        
                        if name:
                            coords = feature.get('geometry', {}).get('coordinates', [0, 0])
                            result_lon, result_lat = coords[0], coords[1]
                            distance = self._calculate_distance(lat, lon, result_lat, result_lon)
                            
                            # Check if court is inside sports centre bounding box
                            sports_centre_extent = properties.get('extent')
                            is_inside_sports_centre = self._is_point_in_facility_extent(lat, lon, sports_centre_extent)
                            
                            if is_inside_sports_centre:
                                distance = 0.001  # Almost zero distance for courts inside sports centres
                                logger.info(json.dumps({
                                    'event': 'court_inside_sports_centre',
                                    'name': name,
                                    'sports_centre_type': sports_centre_type['osm_tag'],
                                    'original_distance_km': round(self._calculate_distance(lat, lon, result_lat, result_lon), 3),
                                    'adjusted_distance_km': 0.001,
                                    'coordinates': {'lat': lat, 'lon': lon},
                                    'sports_centre_extent': sports_centre_extent
                                }))
                            
                            all_results.append({
                                'name': name,
                                'data': feature,
                                'distance': distance,
                                'is_inside_facility': is_inside_sports_centre,
                                'search_type': 'sports_centre',
                                'leisure_type': sports_centre_type['osm_tag']
                            })
                
                except Exception as e:
                    logger.error(json.dumps({
                        'event': 'sports_centre_search_error',
                        'sports_centre_type': sports_centre_type['osm_tag'],
                        'coordinates': {'lat': lat, 'lon': lon},
                        'error': str(e)
                    }))
                    continue
            
            logger.info(json.dumps({
                'event': 'sports_centre_search_completed',
                'coordinates': {'lat': lat, 'lon': lon},
                'total_results': len(all_results)
            }))
            
            return all_results
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'sports_centre_search_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return []
    
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

    def _get_generic_sport_name(self, sport: str) -> str:
        """Generate generic sport name based on actual sport from OSM data"""
        sport_mapping = {
            'basketball': 'Basketball Court',
            'tennis': 'Tennis Court', 
            'soccer': 'Soccer Field',
            'volleyball': 'Volleyball Court',
            'pickleball': 'Pickleball Court',
            'baseball': 'Baseball Field',
            'football': 'Football Field',
            'hockey': 'Hockey Rink',
            'rugby': 'Rugby Field'
        }
        
        # Return mapped name or generic fallback
        return sport_mapping.get(sport.lower(), f'{sport.title()} Court')
    
    def _try_bounding_box_search(self, lat: float, lon: float, court_count: int) -> Tuple[Optional[str], Optional[Dict[str, Any]], int]:
        """Try bounding box search first (NEW METHOD)"""
        try:
            logger.info(json.dumps({
                'event': 'bounding_box_search_started',
                'coordinates': {'lat': lat, 'lon': lon},
                'court_count': court_count
            }))
            
            # Use the bounding box provider
            facility_name, facility_data, api_calls_made = self.bbox_provider.reverse_geocode(lat, lon, court_count)
            
            if facility_name:
                # Update metrics - only count bounding box matches here
                if facility_data.get('is_inside_bbox', False):
                    self.bounding_box_count += 1
                
                # Update total requests with actual API calls made
                self.total_requests += api_calls_made
                
                logger.info(json.dumps({
                    'event': 'bounding_box_search_success',
                    'coordinates': {'lat': lat, 'lon': lon},
                    'facility_name': facility_name,
                    'is_inside_bbox': facility_data.get('is_inside_bbox', False),
                    'api_calls_made': api_calls_made
                }))
                
                return facility_name, facility_data, api_calls_made
            else:
                logger.info(json.dumps({
                    'event': 'bounding_box_search_no_results',
                    'coordinates': {'lat': lat, 'lon': lon},
                    'api_calls_made': api_calls_made
                }))
                return None, None, api_calls_made
                
        except Exception as e:
            logger.error(json.dumps({
                'event': 'bounding_box_search_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return None, None, 0
    
    def _try_distance_based_search(self, lat: float, lon: float, court_count: int) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Fallback to current distance-based search (PROVEN METHOD)"""
        try:
            logger.info(json.dumps({
                'event': 'distance_based_search_started',
                'coordinates': {'lat': lat, 'lon': lon},
                'court_count': court_count
            }))
            
            # Rate limiting
            self._rate_limit()
            
            # Collect all results for potential distance-based fallback
            all_collected_results = []
            
            # 1. Parks/Playgrounds (highest priority for courts)
            park_results = self._try_search_with_bounding_box(lat, lon, 'park', [
                {'osm_tag': 'leisure:park', 'q': 'park'},
                {'osm_tag': 'leisure:playground', 'q': 'playground'}
            ], 1000)
            if park_results:
                all_collected_results.extend([{**result, 'endpoint': 'park'} for result in park_results])
            
            # 2. Schools/Universities
            school_results = self._try_school_search_with_bounding_box(lat, lon)
            if school_results:
                all_collected_results.extend([{**result, 'endpoint': 'school'} for result in school_results])
            
            # 3. Community centres
            community_results = self._try_community_centre_search_with_bounding_box(lat, lon)
            if community_results:
                all_collected_results.extend([{**result, 'endpoint': 'community_centre'} for result in community_results])
            
            # 4. Sports clubs
            sports_club_results = self._try_sports_club_search_with_bounding_box(lat, lon)
            if sports_club_results:
                all_collected_results.extend([{**result, 'endpoint': 'sports_club'} for result in sports_club_results])
            
            # 5. Places of worship
            worship_results = self._try_place_of_worship_search_with_bounding_box(lat, lon)
            if worship_results:
                all_collected_results.extend([{**result, 'endpoint': 'place_of_worship'} for result in worship_results])
            
            # 6. Sports centres
            sports_centre_results = self._try_sports_centre_search_with_bounding_box(lat, lon)
            if sports_centre_results:
                all_collected_results.extend([{**result, 'endpoint': 'sports_centre'} for result in sports_centre_results])
            
            # Use distance-based selection from collected results
            logger.info(json.dumps({
                'event': 'distance_based_search_completed',
                'coordinates': {'lat': lat, 'lon': lon},
                'court_count': court_count,
                'collected_results_count': len(all_collected_results)
            }))
            
            result = self._fallback_to_distance_based_selection_with_results(all_collected_results, lat, lon, court_count)
            
            # Update metrics
            if result[0]:  # If we found a result
                self.distance_based_count += 1
            
            return result
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'distance_based_search_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return None, None

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
