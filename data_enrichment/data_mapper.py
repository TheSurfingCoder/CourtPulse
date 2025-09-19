"""
Data mapping and transformation module
Converts GeoJSON features and Photon data to database format
"""

import json
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import math

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CourtDataMapper:
    """Maps GeoJSON features and Photon data to database format"""
    
    def __init__(self):
        self.surface_type_mapping = {
            'asphalt': 'asphalt',
            'concrete': 'concrete',
            'wood': 'wood',
            'synthetic': 'synthetic',
            'clay': 'clay',
            'grass': 'grass',
            'dirt': 'other',
            'gravel': 'other',
            'sand': 'other'
        }
    
    def extract_geometry_data(self, geometry: Dict[str, Any]) -> Tuple[str, str]:
        """Extract geometry and centroid from GeoJSON geometry"""
        try:
            # Convert geometry to GeoJSON string for PostGIS
            geom_json = json.dumps(geometry)
            
            # Calculate centroid from polygon coordinates
            if geometry['type'] == 'Polygon' and geometry['coordinates']:
                # Get the first ring (exterior ring)
                ring = geometry['coordinates'][0]
                
                # Calculate centroid
                total_lat = 0
                total_lon = 0
                point_count = len(ring)
                
                for coord in ring:
                    total_lon += coord[0]  # longitude
                    total_lat += coord[1]  # latitude
                
                centroid_lon = total_lon / point_count
                centroid_lat = total_lat / point_count
                
                # Create centroid geometry
                centroid_geometry = {
                    "type": "Point",
                    "coordinates": [centroid_lon, centroid_lat]
                }
                centroid_json = json.dumps(centroid_geometry)
                
                return geom_json, centroid_json
            else:
                raise ValueError(f"Unsupported geometry type: {geometry['type']}")
                
        except Exception as e:
            logger.error(json.dumps({
                'event': 'geometry_extraction_error',
                'error': str(e)
            }))
            raise
    
    def determine_surface_type(self, properties: Dict[str, Any]) -> str:
        """Determine surface type from OSM properties"""
        try:
            # Check for explicit surface tag
            surface = properties.get('surface', '').lower()
            if surface in self.surface_type_mapping:
                return self.surface_type_mapping[surface]
            
            # Check for surface type variations
            surface_type = properties.get('surface_type', '').lower()
            if surface_type in self.surface_type_mapping:
                return self.surface_type_mapping[surface_type]
            
            # Check for material tag
            material = properties.get('material', '').lower()
            if material in self.surface_type_mapping:
                return self.surface_type_mapping[material]
            
            # Default to 'other' if no surface information
            return 'other'
            
        except Exception as e:
            logger.warning(json.dumps({
                'event': 'surface_type_determination_error',
                'error': str(e)
            }))
            return 'other'
    
    def generate_fallback_name(self, properties: Dict[str, Any]) -> str:
        """Generate fallback name from OSM properties"""
        try:
            sport = properties.get('sport', 'basketball')
            hoops = properties.get('hoops')
            
            if sport == 'basketball' and hoops:
                # Convert string hoops to int if needed
                hoops_int = int(hoops) if isinstance(hoops, str) else hoops
                return f"basketball court ({hoops_int} hoops)"
            elif sport == 'basketball':
                return "basketball court"
            elif sport == 'tennis':
                return "tennis court"
            elif sport == 'soccer':
                return "soccer field"
            elif sport == 'volleyball':
                return "volleyball court"
            else:
                return f"{sport} court"
                
        except Exception as e:
            logger.warning(json.dumps({
                'event': 'fallback_name_generation_error',
                'error': str(e)
            }))
            return "sports court"
    
    def map_photon_data(self, photon_name: str, photon_distance_km: float, 
                       photon_source: str) -> Dict[str, Any]:
        """Map Photon API response to database format"""
        return {
            'photon_name': photon_name,
            'photon_distance_km': round(photon_distance_km, 6),  # Round to 6 decimal places
            'photon_source': photon_source
        }
    
    def map_court_to_db_format(self, feature: Dict[str, Any], 
                              photon_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Map GeoJSON feature and Photon data to database format"""
        try:
            properties = feature['properties']
            geometry = feature['geometry']
            
            # Extract geometry data
            geom_json, centroid_json = self.extract_geometry_data(geometry)
            
            # Map basic properties
            court_data = {
                'osm_id': properties.get('osm_id') or properties.get('@id'),  # Handle both osm_id and @id
                'sport': properties['sport'],
                'hoops': int(properties.get('hoops')) if properties.get('hoops') else None,
                'geom': geom_json,
                'centroid': centroid_json,
            'fallback_name': self.generate_fallback_name(properties),
            'surface_type': self.determine_surface_type(properties)
            }
            
            # Add Photon data if available
            if photon_data:
                court_data.update(self.map_photon_data(
                    photon_data['name'],
                    photon_data['distance_km'],
                    photon_data['source']
                ))
            else:
                # Use fallback data if no Photon data
                court_data.update({
                    'photon_name': court_data['fallback_name'],
                    'photon_distance_km': None,
                    'photon_source': 'fallback'
                })
            
            logger.debug(json.dumps({
                'event': 'court_mapped',
                'osm_id': court_data['osm_id'],
                'photon_name': court_data['photon_name'],
                'photon_source': court_data['photon_source']
            }))
            
            return court_data
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'court_mapping_error',
                'osm_id': properties.get('osm_id', 'unknown'),
                'error': str(e)
            }))
            raise
    
    def validate_mapped_data(self, court_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate mapped court data before database insertion"""
        try:
            # Check required fields
            required_fields = ['osm_id', 'sport', 'geom', 'centroid']
            for field in required_fields:
                if field not in court_data or not court_data[field]:
                    return False, f"Missing required field: {field}"
            
            # Validate OSM ID format
            osm_id = court_data['osm_id']
            if not isinstance(osm_id, str) or not osm_id.startswith(('way/', 'node/', 'relation/')):
                return False, f"Invalid OSM ID format: {osm_id}"
            
            # Validate sport
            valid_sports = ['basketball', 'tennis', 'soccer', 'volleyball', 'handball', 'other']
            if court_data['sport'] not in valid_sports:
                return False, f"Invalid sport: {court_data['sport']}"
            
            # Validate hoops (if present)
            if court_data.get('hoops') is not None:
                if not isinstance(court_data['hoops'], int) or court_data['hoops'] <= 0:
                    return False, f"Invalid hoops count: {court_data['hoops']}"
            
            # Validate distance (if present)
            if court_data.get('photon_distance_km') is not None:
                if not isinstance(court_data['photon_distance_km'], (int, float)) or court_data['photon_distance_km'] < 0:
                    return False, f"Invalid distance: {court_data['photon_distance_km']}"
            
            return True, "Valid"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"

# Example usage
if __name__ == "__main__":
    mapper = CourtDataMapper()
    
    # Example GeoJSON feature
    sample_feature = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[-122.4, 37.7], [-122.4, 37.8], [-122.3, 37.8], [-122.3, 37.7], [-122.4, 37.7]]]
        },
        "properties": {
            "osm_id": "way/12345",
            "sport": "basketball",
            "hoops": 2,
            "surface": "asphalt"
        }
    }
    
    # Example Photon data
    sample_photon_data = {
        "name": "Test Basketball Court",
        "distance_km": 0.05,
        "source": "search_api"
    }
    
    # Map the data
    mapped_data = mapper.map_court_to_db_format(sample_feature, sample_photon_data)
    print("Mapped data:", json.dumps(mapped_data, indent=2, default=str))
    
    # Validate the mapped data
    is_valid, message = mapper.validate_mapped_data(mapped_data)
    print(f"Validation: {is_valid}, {message}")
