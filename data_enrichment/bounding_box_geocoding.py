#!/usr/bin/env python3
"""
Bounding box geocoding provider for improved facility matching
"""

import json
import logging
import requests
import time
from typing import Dict, Any, List, Tuple, Optional
from math import radians, cos, sin, asin, sqrt

logger = logging.getLogger(__name__)

class BoundingBoxGeocodingProvider:
    """
    Geocoding provider that uses Photon's bounding box search for better facility matching
    """
    
    def __init__(self, base_url: str = "https://photon.komoot.io", delay: float = 1.0):
        self.base_url = base_url
        self.delay = delay
        
        logger.info(json.dumps({
            'event': 'bounding_box_provider_initialized',
            'base_url': base_url,
            'delay': delay
        }))
    
    def reverse_geocode(self, lat: float, lon: float, court_count: int = 1) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Main geocoding method using bounding box search
        
        Args:
            lat: Court latitude
            lon: Court longitude
            court_count: Number of courts (for naming)
            
        Returns:
            Tuple of (facility_name, facility_data) or (None, None) if no match
        """
        try:
            logger.info(json.dumps({
                'event': 'bounding_box_geocoding_started',
                'coordinates': {'lat': lat, 'lon': lon},
                'court_count': court_count
            }))
            
            # Create bounding box around court
            bbox = self._create_bbox_around_point(lat, lon, buffer_km=0.3)
            
            # Search for facilities in bounding box
            facilities = self._search_facilities_in_bbox(bbox, lat, lon)
            
            if not facilities:
                logger.info(json.dumps({
                    'event': 'no_facilities_found',
                    'coordinates': {'lat': lat, 'lon': lon}
                }))
                return None, None
            
            # Find best match
            best_match = self._find_best_facility_match(lat, lon, facilities)
            
            if not best_match:
                logger.info(json.dumps({
                    'event': 'no_suitable_facility_found',
                    'coordinates': {'lat': lat, 'lon': lon},
                    'total_facilities': len(facilities)
                }))
                return None, None
            
            # Format result
            facility_name = self._format_facility_name(best_match['name'], court_count)
            facility_data = self._format_facility_data(best_match)
            
            logger.info(json.dumps({
                'event': 'bounding_box_geocoding_completed',
                'coordinates': {'lat': lat, 'lon': lon},
                'facility_name': facility_name,
                'is_inside_bbox': best_match['is_inside_bbox'],
                'distance_km': best_match['distance'],
                'match_type': 'bounding_box' if best_match['is_inside_bbox'] else 'distance_based'
            }))
            
            return facility_name, facility_data
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'bounding_box_geocoding_error',
                'coordinates': {'lat': lat, 'lon': lon},
                'error': str(e)
            }))
            return None, None
    
    def _create_bbox_around_point(self, lat: float, lon: float, buffer_km: float = 0.3) -> Tuple[float, float, float, float]:
        """
        Create bounding box around a point
        
        Args:
            lat: Latitude
            lon: Longitude
            buffer_km: Buffer distance in kilometers
            
        Returns:
            Tuple of (min_lon, min_lat, max_lon, max_lat)
        """
        # Rough conversion: 1 degree ≈ 111 km
        lat_buffer = buffer_km / 111.0
        lon_buffer = buffer_km / (111.0 * abs(lat * 3.14159 / 180))
        
        return (
            lon - lon_buffer,  # min_lon
            lat - lat_buffer,  # min_lat
            lon + lon_buffer,  # max_lon
            lat + lat_buffer   # max_lat
        )
    
    def _search_facilities_in_bbox(self, bbox: Tuple[float, float, float, float], lat: float, lon: float) -> List[Dict[str, Any]]:
        """
        Search for facilities within bounding box using multiple search terms
        
        Args:
            bbox: (min_lon, min_lat, max_lon, max_lat)
            lat: Court latitude (for distance calculation)
            lon: Court longitude (for distance calculation)
            
        Returns:
            List of facility features with distance and bounding box info
        """
        search_terms = [
            'park',
            'school', 
            'church',
            'recreation',
            'playground',
            'community center',
            'sports',
            'moscone'  # Specific to SF area
        ]
        
        all_facilities = []
        bbox_str = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
        
        for term in search_terms:
            try:
                params = {
                    'q': term,
                    'bbox': bbox_str,
                    'limit': 20
                }
                
                response = requests.get(f"{self.base_url}/api", params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                features = data.get('features', [])
                logger.debug(json.dumps({
                    'event': 'bbox_search_completed',
                    'search_term': term,
                    'results_count': len(features),
                    'bbox': bbox_str
                }))
                
                # Process each facility
                for feature in features:
                    facility = self._process_facility_feature(feature, lat, lon)
                    if facility:
                        all_facilities.append(facility)
                
                time.sleep(self.delay)  # Rate limiting
                
            except Exception as e:
                logger.error(json.dumps({
                    'event': 'bbox_search_error',
                    'search_term': term,
                    'bbox': bbox_str,
                    'error': str(e)
                }))
                continue
        
        # Remove duplicates based on OSM ID
        unique_facilities = {}
        for facility in all_facilities:
            osm_id = facility.get('osm_id')
            if osm_id and osm_id not in unique_facilities:
                unique_facilities[osm_id] = facility
        
        logger.info(json.dumps({
            'event': 'facilities_search_completed',
            'total_found': len(all_facilities),
            'unique_facilities': len(unique_facilities),
            'bbox': bbox_str
        }))
        
        return list(unique_facilities.values())
    
    def _process_facility_feature(self, feature: Dict[str, Any], court_lat: float, court_lon: float) -> Optional[Dict[str, Any]]:
        """
        Process a facility feature from Photon API
        
        Args:
            feature: Feature from Photon API
            court_lat: Court latitude
            court_lon: Court longitude
            
        Returns:
            Processed facility data or None if invalid
        """
        try:
            properties = feature.get('properties', {})
            name = properties.get('name', '').strip()
            
            if not name:
                return None
            
            # Get coordinates
            coords = feature.get('geometry', {}).get('coordinates', [])
            if not coords:
                return None
            
            facility_lon, facility_lat = coords[0], coords[1]
            
            # Calculate distance
            distance = self._calculate_distance(court_lat, court_lon, facility_lat, facility_lon)
            
            # Check if court is inside facility's bounding box
            extent = properties.get('extent', [])
            is_inside_bbox = False
            if extent and len(extent) == 4:
                min_lon, max_lat, max_lon, min_lat = extent
                is_inside_bbox = (min_lat <= court_lat <= max_lat and min_lon <= court_lon <= max_lon)
            
            return {
                'name': name,
                'osm_id': properties.get('osm_id'),
                'osm_key': properties.get('osm_key'),
                'osm_value': properties.get('osm_value'),
                'distance': distance,
                'is_inside_bbox': is_inside_bbox,
                'extent': extent,
                'feature': feature
            }
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'facility_processing_error',
                'error': str(e)
            }))
            return None
    
    def _find_best_facility_match(self, court_lat: float, court_lon: float, facilities: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Find the best facility match for the court
        
        Args:
            court_lat: Court latitude
            court_lon: Court longitude
            facilities: List of processed facilities
            
        Returns:
            Best matching facility or None
        """
        if not facilities:
            return None
        
        best_match = None
        best_score = float('inf')
        
        for facility in facilities:
            # Score this match (prioritize bounding box matches)
            if facility['is_inside_bbox']:
                score = 0.001  # Almost zero score for bounding box matches
            else:
                score = facility['distance']  # Use distance for non-bounding box matches
            
            if score < best_score:
                best_score = score
                best_match = facility
        
        return best_match
    
    def _format_facility_name(self, name: str, court_count: int) -> str:
        """
        Format facility name with court count
        
        Args:
            name: Facility name
            court_count: Number of courts
            
        Returns:
            Formatted name
        """
        if court_count > 1:
            return f"{name} ({court_count} Courts)"
        return name
    
    def _format_facility_data(self, facility: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format facility data for database storage
        
        Args:
            facility: Facility match data
            
        Returns:
            Formatted facility data
        """
        return {
            'name': facility['name'],
            'distance_km': round(facility['distance'], 6),
            'source': 'bounding_box_search',
            'is_inside_bbox': facility['is_inside_bbox'],
            'osm_id': facility['osm_id'],
            'osm_key': facility['osm_key'],
            'osm_value': facility['osm_value'],
            'feature': facility['feature']
        }
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points in kilometers using Haversine formula
        
        Args:
            lat1, lon1: First point coordinates
            lat2, lon2: Second point coordinates
            
        Returns:
            Distance in kilometers
        """
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        return 6371 * c  # Earth's radius in km
