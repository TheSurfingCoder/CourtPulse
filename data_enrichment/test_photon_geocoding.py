#!/usr/bin/env python3
"""
Photon Geocoding Test Script

This script tests the Photon reverse geocoding API with 15 sample features
from the export.geojson file to evaluate name extraction quality and fallback options.
"""

import json
import logging
import requests
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from shapely.geometry import Polygon, Point
import geojson

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
    polygon_geojson: Optional[str] = None
    sport: Optional[str] = None
    hoops: Optional[str] = None
    fallback_name: Optional[str] = None


class PhotonGeocodingProvider:
    """Photon reverse geocoding provider"""
    
    def __init__(self, base_url: str = "https://photon.komoot.io", delay: float = 0.0):
        self.base_url = base_url
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CourtPulse/1.0 (https://github.com/your-repo/courtpulse)'
        })
        
        logger.info(json.dumps({
            'event': 'photon_provider_initialized',
            'base_url': base_url,
            'delay': delay
        }))
    
    def reverse_geocode(self, lat: float, lon: float, court_count: int = 1) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Search for nearby facilities using Photon API with priority: School → Park/Playground → Reverse Geocoding
        
        Args:
            lat: Latitude
            lon: Longitude
            court_count: Number of courts for school name formatting
            
        Returns:
            Tuple of (extracted_name, full_response_data)
        """
        try:
            # Step 1: Try school search first (HIGHEST PRIORITY)
            school_name, school_data = self._try_school_search(lat, lon)
            
            if school_name and self._is_high_quality_name(school_name):
                # Return clean school name without court count
                logger.info(json.dumps({
                    'event': 'school_search_successful',
                    'name': school_name,
                    'court_count': court_count,
                    'coordinates': {'lat': lat, 'lon': lon}
                }))
                return school_name, school_data
            
            # Step 2: Try park/playground search (SECOND PRIORITY)
            search_name, search_data = self._try_search_fallback(lat, lon, "recreation")
            
            if search_name and self._is_high_quality_name(search_name):
                logger.info(json.dumps({
                    'event': 'park_playground_search_successful',
                    'name': search_name,
                    'coordinates': {'lat': lat, 'lon': lon}
                }))
                return search_name, search_data
            
            # Step 3: Fallback to reverse geocoding if search didn't find good results
            reverse_name, reverse_data = self._try_reverse_geocoding(lat, lon)
            
            if reverse_name:
                logger.info(json.dumps({
                    'event': 'reverse_geocoding_fallback_used',
                    'name': reverse_name,
                    'coordinates': {'lat': lat, 'lon': lon},
                    'reason': 'search_did_not_find_high_quality_name'
                }))
                return reverse_name, reverse_data
            
            logger.info(json.dumps({
                'event': 'photon_geocoding_completed',
                'coordinates': {'lat': lat, 'lon': lon},
                'name_found': False,
                'response_type': 'unknown',
                'features_count': 0
            }))
            return None, None
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'photon_unexpected_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return None, None
        finally:
            time.sleep(self.delay)
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates using Haversine formula"""
        import math
        
        # Convert to radians
        lat1, lon1 = math.radians(lat1), math.radians(lon1)
        lat2, lon2 = math.radians(lat2), math.radians(lon2)
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth's radius in kilometers
        r = 6371
        return c * r
    
    def _try_school_search(self, lat: float, lon: float) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Search for nearby schools within 300 feet"""
        try:
            params = {
                'q': 'school',
                'lat': lat,
                'lon': lon,
                'osm_tag': 'amenity:school',
                'location_bias_scale': 0.1,  # Very strong bias toward coordinates
                'zoom': 19,  # Tight radius (~300 feet)
                'limit': 2   # Just 2 results for testing
            }
            
            response = self.session.get(
                f"{self.base_url}/api",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            features = data.get('features', [])
            
            if not features:
                logger.info(json.dumps({
                    'event': 'school_search_no_results',
                    'coordinates': {'lat': lat, 'lon': lon}
                }))
                return None, None
            
            # Find the closest school within 150 feet (0.046 km)
            closest_school = None
            min_distance = float('inf')
            
            for feature in features:
                properties = feature.get('properties', {})
                name = properties.get('name')
                
                if name and self._is_high_quality_name(name):
                    # Check if the result is geographically close (300 feet = 0.091 km)
                    if self._is_nearby_result(feature, lat, lon, max_distance_km=0.091):
                        coords = feature.get('geometry', {}).get('coordinates', [0, 0])
                        result_lon, result_lat = coords[0], coords[1]  # GeoJSON format is [lon, lat]
                        distance = self._calculate_distance(lat, lon, result_lat, result_lon)
                        
                        if distance < min_distance:
                            min_distance = distance
                            closest_school = {
                                'name': name,
                                'data': feature,
                                'distance': distance
                            }
            
            if closest_school:
                logger.info(json.dumps({
                    'event': 'school_found',
                    'name': closest_school['name'],
                    'distance_km': closest_school['distance'],
                    'coordinates': {'lat': lat, 'lon': lon}
                }))
                return closest_school['name'], closest_school['data']
            else:
                logger.info(json.dumps({
                    'event': 'school_search_no_nearby_results',
                    'coordinates': {'lat': lat, 'lon': lon},
                    'reason': 'no_schools_within_150_feet'
                }))
                return None, None
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'school_search_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return None, None
    
    def _try_reverse_geocoding(self, lat: float, lon: float) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Try reverse geocoding first"""
        try:
            params = {
                'lat': lat,
                'lon': lon
            }
            
            response = self.session.get(
                f"{self.base_url}/reverse",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            extracted_name = self._extract_name(data)
            
            return extracted_name, data
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'reverse_geocoding_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return None, None
    
    def _try_search_fallback(self, lat: float, lon: float, address: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Try to find nearby named places using search with leisure tags - always choose the closest result"""
        try:
            # Define leisure types to search for (optimized - only successful ones)
            leisure_types = [
                {'osm_tag': 'leisure:park', 'q': 'park'},
                {'osm_tag': 'leisure:playground', 'q': 'playground'}
            ]
            
            # Collect ALL nearby results from all leisure types
            all_nearby_results = []
            
            for leisure_type in leisure_types:
                search_name, search_data = self._perform_single_search(lat, lon, leisure_type)
                if search_name and self._is_high_quality_name(search_name):
                    # Calculate distance for this result
                    coords = search_data.get('geometry', {}).get('coordinates', [0, 0])
                    result_lon, result_lat = coords[0], coords[1]  # GeoJSON format is [lon, lat]
                    distance = self._calculate_distance(lat, lon, result_lat, result_lon)
                    all_nearby_results.append({
                        'name': search_name,
                        'data': search_data,
                        'distance': distance,
                        'leisure_type': leisure_type['osm_tag']
                    })
                
                time.sleep(0.1)  # Small delay between searches
            
            if not all_nearby_results:
                logger.info(json.dumps({
                    'event': 'search_fallback_no_results',
                    'coordinates': {'lat': lat, 'lon': lon},
                    'reason': 'no_nearby_recreational_facilities_found'
                }))
                return None, None
            
            # Sort by distance and choose the closest one
            closest_result = min(all_nearby_results, key=lambda x: x['distance'])
            
            logger.info(json.dumps({
                'event': 'search_fallback_successful',
                'leisure_type': closest_result['leisure_type'],
                'result': closest_result['name'],
                'distance_km': closest_result['distance'],
                'coordinates': {'lat': lat, 'lon': lon},
                'total_options': len(all_nearby_results)
            }))
            
            return closest_result['name'], closest_result['data']
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'search_fallback_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'address': address,
                'error': str(e)
            }))
            return None, None
    
    def _perform_single_search(self, lat: float, lon: float, leisure_type: Dict[str, str]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Perform a single search query for one leisure type"""
        try:
            params = {
                'q': leisure_type['q'],
                'lat': lat,
                'lon': lon,
                'osm_tag': leisure_type['osm_tag'],
                'location_bias_scale': 0.1,  # Very strong bias toward coordinates
                'zoom': 20,  # Very tight radius (~100 feet)
                'limit': 2   # Just 2 results for testing
            }
            
            response = self.session.get(
                f"{self.base_url}/api",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            features = data.get('features', [])
            
            if not features:
                return None, None
            
            # Find the best nearby result
            for feature in features:
                properties = feature.get('properties', {})
                name = properties.get('name')
                
                if name and self._is_high_quality_name(name):
                    # Check if the result is geographically close
                    if self._is_nearby_result(feature, lat, lon):
                        logger.info(json.dumps({
                            'event': 'nearby_result_found',
                            'name': name,
                            'leisure_type': leisure_type['osm_tag'],
                            'coordinates': {'lat': lat, 'lon': lon}
                        }))
                        return name, feature
                    else:
                        logger.info(json.dumps({
                            'event': 'result_too_far',
                            'name': name,
                            'leisure_type': leisure_type['osm_tag'],
                            'coordinates': {'lat': lat, 'lon': lon}
                        }))
            
            return None, None
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'search_request_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'leisure_type': leisure_type['osm_tag'],
                'error': str(e)
            }))
            return None, None
    
    def _is_nearby_result(self, feature: Dict[str, Any], target_lat: float, target_lon: float, max_distance_km: float = 0.198) -> bool:
        """Check if a search result is geographically close to our target coordinates"""
        try:
            geometry = feature.get('geometry', {})
            if geometry.get('type') != 'Point':
                return False
            
            coordinates = geometry.get('coordinates', [])
            if len(coordinates) != 2:
                return False
            
            result_lon, result_lat = coordinates
            
            # Calculate distance using Haversine formula
            import math
            
            # Convert to radians
            lat1, lon1 = math.radians(target_lat), math.radians(target_lon)
            lat2, lon2 = math.radians(result_lat), math.radians(result_lon)
            
            # Haversine formula
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            
            # Earth's radius in kilometers
            earth_radius_km = 6371
            distance_km = earth_radius_km * c
            
            is_nearby = distance_km <= max_distance_km
            
            logger.info(json.dumps({
                'event': 'distance_check',
                'target_coords': {'lat': target_lat, 'lon': target_lon},
                'result_coords': {'lat': result_lat, 'lon': result_lon},
                'distance_km': round(distance_km, 2),
                'max_distance_km': max_distance_km,
                'is_nearby': is_nearby
            }))
            
            return is_nearby
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'distance_calculation_error',
                'error': str(e)
            }))
            return False
    
    
    def _is_street_address(self, name: str) -> bool:
        """Check if a name looks like a street address"""
        if not name:
            return False
        
        # Check for street number pattern
        import re
        if re.match(r'^\d+\s+', name):
            return True
        
        # Check for common street suffixes
        street_suffixes = ['street', 'avenue', 'boulevard', 'road', 'way', 'drive', 'lane']
        name_lower = name.lower()
        return any(suffix in name_lower for suffix in street_suffixes)
    
    def _is_better_name(self, new_name: str, old_name: str) -> bool:
        """Check if the new name is better than the old one"""
        if not new_name or not old_name:
            return bool(new_name)
        
        # Prefer names that don't look like street addresses
        if self._is_street_address(new_name) and not self._is_street_address(old_name):
            return False
        
        if not self._is_street_address(new_name) and self._is_street_address(old_name):
            return True
        
        # Prefer longer, more descriptive names
        return len(new_name) > len(old_name)
    
    def _is_high_quality_name(self, name: str) -> bool:
        """Check if a name is high quality for court naming"""
        if not name or not self._is_valid_name(name):
            return False
        
        name_lower = name.lower()
        
        # Prefer names that suggest recreational facilities
        recreational_keywords = [
            'park', 'playground', 'recreation', 'community', 'center', 'centre',
            'sports', 'athletic', 'gym', 'fitness', 'school', 'elementary',
            'high school', 'middle school', 'university', 'college'
        ]
        
        return any(keyword in name_lower for keyword in recreational_keywords)
    
    def _extract_name(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Extract the best name from Photon response using fallback hierarchy
        
        Args:
            data: Photon API response data
            
        Returns:
            Best available name or None
        """
        try:
            features = data.get('features', [])
            if not features:
                return None
            
            # Get the first (closest) feature
            feature = features[0]
            properties = feature.get('properties', {})
            
            # Fallback hierarchy for name extraction
            name_candidates = []
            
            # 1. Primary: 'name' field
            if properties.get('name'):
                name_candidates.append(('name', properties['name']))
            
            # 2. Secondary: 'city' + 'country' combination
            city = properties.get('city')
            country = properties.get('country')
            if city and country:
                name_candidates.append(('city_country', f"{city}, {country}"))
            elif city:
                name_candidates.append(('city', city))
            
            # 3. Tertiary: 'street' + 'city' combination
            street = properties.get('street')
            if street and city:
                name_candidates.append(('street_city', f"{street}, {city}"))
            elif street:
                name_candidates.append(('street', street))
            
            # 4. Quaternary: 'housenumber' + 'street' combination
            housenumber = properties.get('housenumber')
            if housenumber and street:
                name_candidates.append(('housenumber_street', f"{housenumber} {street}"))
            
            # 5. Quinary: 'district' or 'county'
            district = properties.get('district')
            county = properties.get('county')
            if district:
                name_candidates.append(('district', district))
            elif county:
                name_candidates.append(('county', county))
            
            # Select the best candidate
            if name_candidates:
                selected_type, selected_name = name_candidates[0]
                
                # Validate name quality
                if self._is_valid_name(selected_name):
                    logger.info(json.dumps({
                        'event': 'name_extracted',
                        'extraction_type': selected_type,
                        'name': selected_name,
                        'all_candidates': [f"{t}: {n}" for t, n in name_candidates]
                    }))
                    return selected_name
                else:
                    # Try next candidate if first is invalid
                    for candidate_type, candidate_name in name_candidates[1:]:
                        if self._is_valid_name(candidate_name):
                            logger.info(json.dumps({
                                'event': 'name_extracted_fallback',
                                'extraction_type': candidate_type,
                                'name': candidate_name,
                                'original_type': selected_type
                            }))
                            return candidate_name
            
            return None
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'name_extraction_error',
                'error': str(e)
            }))
            return None
    
    def _is_valid_name(self, name: str) -> bool:
        """
        Validate if a name is suitable for court naming
        
        Args:
            name: Name to validate
            
        Returns:
            True if name is valid, False otherwise
        """
        if not name or not isinstance(name, str):
            return False
        
        name = name.strip()
        
        # Too short
        if len(name) < 3:
            return False
        
        # Generic location names to skip
        generic_names = [
            'san francisco', 'california', 'united states', 'usa',
            'sf', 'bay area', 'northern california', 'california, united states',
            'united states, california', 'california, usa'
        ]
        
        name_lower = name.lower()
        if any(generic in name_lower for generic in generic_names):
            return False
        
        # Skip if it's just a number or very generic
        if name.isdigit() or name in ['street', 'avenue', 'road', 'way', 'boulevard']:
            return False
        
        return True


class PhotonTester:
    """Main class for testing Photon geocoding"""
    
    def __init__(self):
        self.geocoding_provider = PhotonGeocodingProvider()
        
        logger.info(json.dumps({
            'event': 'photon_tester_initialized'
        }))
    
    def load_sample_features(self, file_path: str, num_features: int = 15) -> List[Dict[str, Any]]:
        """Load sample features from GeoJSON file"""
        try:
            with open(file_path, 'r') as f:
                data = geojson.load(f)
            
            features = data.get('features', [])[:num_features]
            
            logger.info(json.dumps({
                'event': 'sample_features_loaded',
                'file_path': file_path,
                'requested_count': num_features,
                'loaded_count': len(features)
            }))
            
            return features
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'feature_loading_error',
                'file_path': file_path,
                'error': str(e)
            }))
            raise
    
    def parse_feature(self, feature: Dict[str, Any]) -> Optional[CourtData]:
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
            
            # Calculate centroid
            coords = geometry['coordinates'][0]  # First ring of polygon
            poly = Polygon(coords)
            centroid = poly.centroid
            
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
                polygon_geojson=json.dumps(geometry),
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
    
    def test_geocoding(self, court: CourtData) -> Dict[str, Any]:
        """Test geocoding for a single court"""
        try:
            lat, lon = court.geom.y, court.geom.x
            
            logger.info(json.dumps({
                'event': 'testing_geocoding',
                'osm_id': court.osm_id,
                'coordinates': {'lat': lat, 'lon': lon},
                'sport': court.sport,
                'hoops': court.hoops
            }))
            
            # Perform reverse geocoding
            court_count = int(court.hoops) if court.hoops else 1
            extracted_name, full_response = self.geocoding_provider.reverse_geocode(lat, lon, court_count)
            
            # Analyze the response
            analysis = self._analyze_response(full_response)
            
            result = {
                'osm_id': court.osm_id,
                'coordinates': {'lat': lat, 'lon': lon},
                'sport': court.sport,
                'hoops': court.hoops,
                'fallback_name': court.fallback_name,
                'extracted_name': extracted_name,
                'response_analysis': analysis,
                'success': extracted_name is not None
            }
            
            logger.info(json.dumps({
                'event': 'geocoding_test_completed',
                'osm_id': court.osm_id,
                'success': result['success'],
                'extracted_name': extracted_name
            }))
            
            return result
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'geocoding_test_error',
                'osm_id': court.osm_id,
                'error': str(e)
            }))
            return {
                'osm_id': court.osm_id,
                'error': str(e),
                'success': False
            }
    
    def _analyze_response(self, response_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze Photon response to understand data quality"""
        if not response_data:
            return {'error': 'No response data'}
        
        features = response_data.get('features', [])
        if not features:
            return {'error': 'No features in response'}
        
        # Analyze the first feature (closest)
        feature = features[0]
        properties = feature.get('properties', {})
        
        analysis = {
            'response_type': response_data.get('type'),
            'features_count': len(features),
            'has_name': bool(properties.get('name')),
            'has_city': bool(properties.get('city')),
            'has_country': bool(properties.get('country')),
            'has_street': bool(properties.get('street')),
            'has_housenumber': bool(properties.get('housenumber')),
            'has_district': bool(properties.get('district')),
            'has_county': bool(properties.get('county')),
            'available_properties': list(properties.keys()),
            'geometry_type': feature.get('geometry', {}).get('type'),
            'coordinates': feature.get('geometry', {}).get('coordinates')
        }
        
        return analysis
    
    def _cluster_nearby_coordinates(self, courts: List[Tuple[int, CourtData]], max_distance_km: float = 0.05) -> List[List[Tuple[int, CourtData]]]:
        """
        Cluster nearby coordinates together to ensure consistent naming
        
        Args:
            courts: List of (feature_number, court_data) tuples
            max_distance_km: Maximum distance between coordinates to be in same cluster (~160 feet)
            
        Returns:
            List of clusters, where each cluster is a list of (feature_number, court_data) tuples
        """
        clusters = []
        processed = set()
        
        for i, (feature_num, court) in enumerate(courts):
            if i in processed:
                continue
                
            # Start a new cluster with this court
            cluster = [(feature_num, court)]
            processed.add(i)
            
            # Find all other courts within the distance threshold
            for j, (other_feature_num, other_court) in enumerate(courts[i+1:], i+1):
                if j in processed:
                    continue
                    
                distance = self._calculate_distance(
                    court.geom.y, court.geom.x,
                    other_court.geom.y, other_court.geom.x
                )
                
                if distance <= max_distance_km:
                    cluster.append((other_feature_num, other_court))
                    processed.add(j)
            
            clusters.append(cluster)
            
            logger.info(json.dumps({
                'event': 'coordinate_cluster_created',
                'cluster_size': len(cluster),
                'representative_osm_id': court.osm_id,
                'coordinates': {'lat': court.geom.y, 'lon': court.geom.x},
                'max_distance_km': max_distance_km
            }))
        
        return clusters
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates using Haversine formula"""
        import math
        
        # Convert to radians
        lat1, lon1 = math.radians(lat1), math.radians(lon1)
        lat2, lon2 = math.radians(lat2), math.radians(lon2)
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth's radius in kilometers
        earth_radius_km = 6371
        return earth_radius_km * c
    
    def run_test(self, file_path: str, num_features: int = 15) -> List[Dict[str, Any]]:
        """Run the complete test with coordinate clustering"""
        logger.info(json.dumps({
            'event': 'photon_test_started',
            'file_path': file_path,
            'num_features': num_features
        }))
        
        # Load sample features
        features = self.load_sample_features(file_path, num_features)
        
        # Parse all features first
        courts = []
        for i, feature in enumerate(features, 1):
            court = self.parse_feature(feature)
            if court:
                courts.append((i, court))
            else:
                print(f"❌ Failed to parse feature {i}")
        
        # Cluster nearby coordinates
        clusters = self._cluster_nearby_coordinates(courts, max_distance_km=0.05)  # ~160 feet
        
        print(f"\n🗺️  Coordinate Clustering Results:")
        print(f"   - Total features: {len(courts)}")
        print(f"   - Clusters created: {len(clusters)}")
        print(f"   - API calls saved: {len(courts) - len(clusters)}")
        
        results = []
        
        # Process each cluster
        for cluster_id, cluster_courts in enumerate(clusters, 1):
            print(f"\n{'='*60}")
            print(f"🏀 Processing Cluster {cluster_id}/{len(clusters)} ({len(cluster_courts)} courts)")
            print(f"{'='*60}")
            
            # Use the first court in cluster for geocoding
            first_court = cluster_courts[0][1]
            print(f"Representative Court: {first_court.osm_id}")
            print(f"Coordinates: {first_court.geom.y:.6f}, {first_court.geom.x:.6f}")
            print(f"Sport: {first_court.sport}, Hoops: {first_court.hoops}")
            print(f"Fallback Name: {first_court.fallback_name}")
            
            # Test geocoding for the cluster
            cluster_result = self.test_geocoding(first_court)
            
            # Apply the same result to all courts in the cluster
            for feature_num, court in cluster_courts:
                result = cluster_result.copy()
                result['osm_id'] = court.osm_id
                result['coordinates'] = {'lat': court.geom.y, 'lon': court.geom.x}
                result['sport'] = court.sport
                result['hoops'] = court.hoops
                result['fallback_name'] = court.fallback_name
                result['cluster_id'] = cluster_id
                result['cluster_size'] = len(cluster_courts)
                results.append(result)
                
                print(f"   - {court.osm_id}: {result['extracted_name']}")
            
            # Show response analysis
            analysis = cluster_result.get('response_analysis', {})
            print(f"📊 Response Analysis:")
            print(f"   - Has name: {analysis.get('has_name', False)}")
            print(f"   - Has city: {analysis.get('has_city', False)}")
            print(f"   - Has country: {analysis.get('has_county', False)}")
            print(f"   - Has street: {analysis.get('has_street', False)}")
            print(f"   - Available properties: {', '.join(analysis.get('available_properties', []))}")
        
        # Summary
        self._print_summary(results)
        
        return results
    
    def _print_summary(self, results: List[Dict[str, Any]]):
        """Print test summary"""
        print(f"\n{'='*60}")
        print("📊 ENHANCED PHOTON TEST SUMMARY")
        print(f"{'='*60}")
        
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r.get('success', False))
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Total tests: {total_tests}")
        print(f"Successful: {successful_tests}")
        print(f"Success rate: {success_rate:.1f}%")
        
        # Show successful extractions
        successful_results = [r for r in results if r.get('success', False)]
        if successful_results:
            print(f"\n✅ Successful Name Extractions:")
            for i, result in enumerate(successful_results, 1):
                print(f"   {i}. {result['extracted_name']} (OSM: {result['osm_id']})")
        
        # Show failed extractions
        failed_results = [r for r in results if not r.get('success', False)]
        if failed_results:
            print(f"\n❌ Failed Extractions:")
            for i, result in enumerate(failed_results, 1):
                print(f"   {i}. OSM: {result['osm_id']} - {result.get('error', 'No name found')}")
        
        # Analyze name quality improvements
        print(f"\n🎯 Name Quality Analysis:")
        high_quality_names = []
        street_addresses = []
        other_names = []
        
        for result in successful_results:
            name = result['extracted_name']
            if self.geocoding_provider._is_high_quality_name(name):
                high_quality_names.append(name)
            elif self.geocoding_provider._is_street_address(name):
                street_addresses.append(name)
            else:
                other_names.append(name)
        
        print(f"   - High-quality names (parks, recreation centers, etc.): {len(high_quality_names)}/{total_tests} ({len(high_quality_names)/total_tests*100:.1f}%)")
        print(f"   - Street addresses: {len(street_addresses)}/{total_tests} ({len(street_addresses)/total_tests*100:.1f}%)")
        print(f"   - Other names: {len(other_names)}/{total_tests} ({len(other_names)/total_tests*100:.1f}%)")
        
        if high_quality_names:
            print(f"\n🏆 High-Quality Names Found:")
            for i, name in enumerate(high_quality_names[:5], 1):  # Show top 5
                print(f"   {i}. {name}")
        
        # Analyze response patterns
        print(f"\n📈 Response Pattern Analysis:")
        has_name_count = sum(1 for r in results if r.get('response_analysis', {}).get('has_name', False))
        has_city_count = sum(1 for r in results if r.get('response_analysis', {}).get('has_city', False))
        has_street_count = sum(1 for r in results if r.get('response_analysis', {}).get('has_street', False))
        
        print(f"   - Features with 'name' property: {has_name_count}/{total_tests} ({has_name_count/total_tests*100:.1f}%)")
        print(f"   - Features with 'city' property: {has_city_count}/{total_tests} ({has_city_count/total_tests*100:.1f}%)")
        print(f"   - Features with 'street' property: {has_street_count}/{total_tests} ({has_street_count/total_tests*100:.1f}%)")


def main():
    """Main execution function"""
    print("🌍 Photon Geocoding Test")
    print("Testing reverse geocoding with 15 sample basketball courts")
    print("=" * 60)
    
    # Initialize tester
    tester = PhotonTester()
    
    # Run test
    results = tester.run_test('export.geojson', num_features=15)
    
    # Save results to file for analysis
    with open('photon_test_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: photon_test_results.json")
    print("🎉 Test completed!")


if __name__ == "__main__":
    main()
