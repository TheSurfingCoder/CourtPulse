"""
Async version of Photon geocoding provider for parallel API calls
"""

import asyncio
import aiohttp
import json
import logging
import math
from typing import Dict, Any, List, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AsyncPhotonGeocodingProvider:
    """Async Photon reverse geocoding provider with parallel API calls"""
    
    def __init__(self, base_url: str = "https://photon.komoot.io", max_concurrent: int = 10):
        self.base_url = base_url
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        logger.info(json.dumps({
            'event': 'async_photon_provider_initialized',
            'base_url': base_url,
            'max_concurrent': max_concurrent
        }))
    
    async def reverse_geocode(self, lat: float, lon: float) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Main entry point for reverse geocoding with search-first approach"""
        try:
            # Try search API first (parallel calls)
            search_name, search_data = await self._try_search_fallback_parallel(lat, lon, "")
            
            if search_name and self._is_high_quality_name(search_name):
                logger.info(json.dumps({
                    'event': 'search_primary_successful',
                    'name': search_name,
                    'coordinates': {'lat': lat, 'lon': lon}
                }))
                return search_name, search_data
            
            # Fallback to reverse geocoding
            reverse_name, reverse_data = await self._try_reverse_geocoding(lat, lon)
            
            if reverse_name:
                logger.info(json.dumps({
                    'event': 'reverse_geocoding_fallback_used',
                    'name': reverse_name,
                    'coordinates': {'lat': lat, 'lon': lon},
                    'reason': 'search_did_not_find_high_quality_name'
                }))
                return reverse_name, reverse_data
            
            # Final fallback - should not happen with proper data
            logger.warning(json.dumps({
                'event': 'geocoding_completely_failed',
                'coordinates': {'lat': lat, 'lon': lon}
            }))
            return None, None
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'reverse_geocode_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return None, None
    
    async def _try_search_fallback_parallel(self, lat: float, lon: float, address: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Try to find nearby named places using parallel search calls"""
        try:
            # Define leisure types (optimized - only successful ones)
            leisure_types = [
                {'osm_tag': 'leisure:park', 'q': 'park'},
                {'osm_tag': 'leisure:playground', 'q': 'playground'}
            ]
            
            # Create tasks for parallel execution
            tasks = [
                self._perform_single_search_async(lat, lon, leisure_type)
                for leisure_type in leisure_types
            ]
            
            # Execute all searches in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect valid nearby results
            all_nearby_results = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(json.dumps({
                        'event': 'parallel_search_error',
                        'leisure_type': leisure_types[i]['osm_tag'],
                        'error': str(result)
                    }))
                    continue
                
                search_name, search_data = result
                if search_name and self._is_high_quality_name(search_name) and search_data:
                    # Calculate distance for this result
                    coords = search_data.get('geometry', {}).get('coordinates', [0, 0])
                    result_lon, result_lat = coords[0], coords[1]  # GeoJSON format
                    distance = self._calculate_distance(lat, lon, result_lat, result_lon)
                    
                    all_nearby_results.append({
                        'name': search_name,
                        'data': search_data,
                        'distance': distance
                    })
            
            if not all_nearby_results:
                logger.info(json.dumps({
                    'event': 'parallel_search_no_results',
                    'coordinates': {'lat': lat, 'lon': lon}
                }))
                return None, None
            
            # Select the closest result
            closest_result = min(all_nearby_results, key=lambda x: x['distance'])
            
            logger.info(json.dumps({
                'event': 'parallel_search_successful',
                'result': closest_result['name'],
                'distance_km': closest_result['distance'],
                'coordinates': {'lat': lat, 'lon': lon},
                'total_options': len(all_nearby_results)
            }))
            
            return closest_result['name'], closest_result['data']
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'parallel_search_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return None, None
    
    async def _perform_single_search_async(self, lat: float, lon: float, leisure_type: Dict[str, str]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Perform a single async search query for one leisure type"""
        async with self.semaphore:  # Limit concurrent requests
            try:
                params = {
                    'q': leisure_type['q'],
                    'lat': lat,
                    'lon': lon,
                    'osm_tag': leisure_type['osm_tag'],
                    'location_bias_scale': 0.1,
                    'zoom': 20,
                    'limit': 2
                }
                
                connector = aiohttp.TCPConnector(ssl=False)  # Disable SSL verification
                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.get(f"{self.base_url}/api", params=params, timeout=10) as response:
                        response.raise_for_status()
                        data = await response.json()
                        
                        features = data.get('features', [])
                        if not features:
                            return None, None
                        
                        # Find the best nearby result
                        for feature in features:
                            properties = feature.get('properties', {})
                            name = properties.get('name')
                            
                            if name and self._is_high_quality_name(name):
                                if self._is_nearby_result(feature, lat, lon):
                                    logger.info(json.dumps({
                                        'event': 'async_nearby_result_found',
                                        'name': name,
                                        'leisure_type': leisure_type['osm_tag'],
                                        'coordinates': {'lat': lat, 'lon': lon}
                                    }))
                                    return name, feature
                                else:
                                    logger.info(json.dumps({
                                        'event': 'async_result_too_far',
                                        'name': name,
                                        'leisure_type': leisure_type['osm_tag'],
                                        'coordinates': {'lat': lat, 'lon': lon}
                                    }))
                        
                        return None, None
                        
            except Exception as e:
                logger.error(json.dumps({
                    'event': 'async_search_error',
                    'leisure_type': leisure_type['osm_tag'],
                    'coordinates': {'lat': lat, 'lon': lon},
                    'error': str(e)
                }))
                return None, None
    
    async def _try_reverse_geocoding(self, lat: float, lon: float) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Try reverse geocoding as fallback"""
        try:
            params = {'lon': lon, 'lat': lat}
            
            connector = aiohttp.TCPConnector(ssl=False)  # Disable SSL verification
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(f"{self.base_url}/reverse", params=params, timeout=10) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    features = data.get('features', [])
                    if not features:
                        return None, None
                    
                    # Extract name from the first feature
                    feature = features[0]
                    name = self._extract_name(feature)
                    
                    return name, feature
                    
        except Exception as e:
            logger.error(json.dumps({
                'event': 'async_reverse_geocoding_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return None, None
    
    def _is_high_quality_name(self, name: str) -> bool:
        """Check if a name is high quality (not just a street address)"""
        if not name or len(name.strip()) < 3:
            return False
        
        # Skip generic street names and numbers
        skip_patterns = [
            'unnamed', 'untitled', 'no name',
            'street', 'avenue', 'boulevard', 'road', 'way', 'drive',
            'st ', ' st', 'ave ', ' ave', 'blvd ', ' blvd'
        ]
        
        name_lower = name.lower()
        for pattern in skip_patterns:
            if pattern in name_lower:
                return False
        
        # Skip if it's mostly numbers
        if sum(c.isdigit() for c in name) > len(name) * 0.5:
            return False
        
        return True
    
    def _is_nearby_result(self, feature: Dict[str, Any], target_lat: float, target_lon: float, max_distance_km: float = 0.198) -> bool:
        """Check if result is within acceptable distance (650 feet = 0.198 km)"""
        try:
            coords = feature.get('geometry', {}).get('coordinates', [0, 0])
            result_lon, result_lat = coords[0], coords[1]  # GeoJSON format
            
            distance = self._calculate_distance(target_lat, target_lon, result_lat, result_lon)
            is_nearby = distance <= max_distance_km
            
            logger.info(json.dumps({
                'event': 'async_distance_check',
                'target_coords': {'lat': target_lat, 'lon': target_lon},
                'result_coords': {'lat': result_lat, 'lon': result_lon},
                'distance_km': round(distance, 2),
                'max_distance_km': max_distance_km,
                'is_nearby': is_nearby
            }))
            
            return is_nearby
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'async_distance_check_error',
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
                'event': 'async_name_candidates',
                'all_candidates': name_candidates
            }))
            
            # Return the first (best) candidate
            if name_candidates:
                best_candidate = name_candidates[0]
                extraction_type = best_candidate.split(':')[0]
                name = best_candidate.split(':', 1)[1].strip()
                
                logger.info(json.dumps({
                    'event': 'async_name_extracted',
                    'extraction_type': extraction_type,
                    'name': name,
                    'all_candidates': name_candidates
                }))
                
                return name
            
            return None
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'async_name_extraction_error',
                'error': str(e)
            }))
            return None

# Example usage
async def test_async_geocoding():
    """Test the async geocoding provider"""
    provider = AsyncPhotonGeocodingProvider(max_concurrent=5)
    
    # Test coordinates
    test_coords = [
        (37.75006984, -122.40645443999999),  # James Rolph Jr. Playground
        (37.7334692, -122.3762353),          # India Basin Shoreline Park
    ]
    
    # Test parallel processing
    tasks = [provider.reverse_geocode(lat, lon) for lat, lon in test_coords]
    results = await asyncio.gather(*tasks)
    
    for i, (name, data) in enumerate(results):
        print(f"Result {i+1}: {name}")

if __name__ == "__main__":
    asyncio.run(test_async_geocoding())
