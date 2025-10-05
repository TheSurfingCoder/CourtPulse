"""
Synchronous Photon geocoding provider for court data enrichment
"""

import requests
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
        
        PRIORITIZED APPROACH: Search schools and playgrounds first, reverse geocoding as fallback
        Priority order:
        1. School search + Park/playground search (pick closest from these two)
        2. Reverse geocoding (only if no schools/playgrounds found)
        """
        try:
            # Rate limiting
            self._rate_limit()
            
            # Search priority endpoints (schools and playgrounds)
            priority_results = []
            
            # 1. School search
            school_results = self._try_school_search_all_results(lat, lon)
            if school_results:
                priority_results.extend([{**result, 'endpoint': 'school'} for result in school_results])
            
            # 2. Park/playground search
            park_results = self._try_search_fallback_all_results(lat, lon)
            if park_results:
                priority_results.extend([{**result, 'endpoint': 'park'} for result in park_results])
            
            # Filter priority results for high quality names
            high_quality_priority = [
                result for result in priority_results 
                if self._is_high_quality_name(result['name'])
            ]
            
            # Use high quality priority results if available, otherwise use all priority results
            priority_to_consider = high_quality_priority if high_quality_priority else priority_results
            
            if priority_to_consider:
                # Pick the closest result from schools/playgrounds
                closest_result = min(priority_to_consider, key=lambda x: x['distance'])
                
                # Add court count to name if multiple courts
                name = closest_result['name']
                if court_count > 1:
                    name = f"{name} ({court_count} Courts)"
                
                logger.info(json.dumps({
                    'event': 'priority_result_selected',
                    'name': name,
                    'endpoint': closest_result['endpoint'],
                    'distance_km': round(closest_result['distance'], 3),
                    'coordinates': {'lat': lat, 'lon': lon},
                    'court_count': court_count,
                    'total_priority_results': len(priority_results),
                    'high_quality_priority_results': len(high_quality_priority),
                    'reason': 'found_school_or_playground_result'
                }))
                
                return name, closest_result['data']
            
            # Fallback: Try reverse geocoding if no schools/playgrounds found
            logger.info(json.dumps({
                'event': 'falling_back_to_reverse_geocoding',
                'coordinates': {'lat': lat, 'lon': lon},
                'court_count': court_count,
                'reason': 'no_school_or_playground_results_found'
            }))
            
            reverse_results = self._try_reverse_geocoding_all_results(lat, lon)
            if not reverse_results:
                logger.warning(json.dumps({
                    'event': 'geocoding_completely_failed',
                    'coordinates': {'lat': lat, 'lon': lon},
                    'court_count': court_count,
                    'reason': 'no_results_from_any_endpoint'
                }))
                return None, None
            
            # Filter reverse geocoding results for high quality names
            high_quality_reverse = [
                result for result in reverse_results 
                if self._is_high_quality_name(result['name'])
            ]
            
            # Use high quality reverse results if available, otherwise use all reverse results
            reverse_to_consider = high_quality_reverse if high_quality_reverse else reverse_results
            
            # Pick the closest reverse geocoding result
            closest_result = min(reverse_to_consider, key=lambda x: x['distance'])
            
            # Add court count to name if multiple courts
            name = closest_result['name']
            if court_count > 1:
                name = f"{name} ({court_count} Courts)"
            
            logger.info(json.dumps({
                'event': 'reverse_geocoding_fallback_used',
                'name': name,
                'endpoint': 'reverse',
                'distance_km': round(closest_result['distance'], 3),
                'coordinates': {'lat': lat, 'lon': lon},
                'court_count': court_count,
                'total_reverse_results': len(reverse_results),
                'high_quality_reverse_results': len(high_quality_reverse),
                'reason': 'no_school_or_playground_results_found'
            }))
            
            return name, closest_result['data']
            
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
                    
                    # Find all nearby results
                    for feature in features:
                        properties = feature.get('properties', {})
                        name = properties.get('name')
                        
                        if name:
                            if self._is_nearby_result(feature, lat, lon, max_distance_km=0.305):
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
                                    'event': 'nearby_result_found',
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
        """Try searching for schools and return all valid results"""
        try:
            params = {
                'q': 'school',
                'lat': lat,
                'lon': lon,
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
                'event': 'school_search_completed',
                'coordinates': {'lat': lat, 'lon': lon},
                'total_results': len(valid_results)
            }))
            
            return valid_results
            
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
