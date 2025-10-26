"""
Data mapping and transformation module
Converts GeoJSON features and Photon data to database format
"""

import json
import logging
import uuid
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
    
    def generate_bounding_box_uuid(self, lat: float, lon: float, facility_name: str) -> str:
        """Generate a deterministic UUID based on location + facility name using RFC 4122 standard"""
        # Create a deterministic string from location and facility name
        uuid_input = f"{lat:.6f},{lon:.6f},{facility_name}"
        
        # Use uuid5 for deterministic UUID generation (RFC 4122 compliant)
        # Using NAMESPACE_DNS as a standard namespace for our application
        deterministic_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, uuid_input)
        
        logger.info(json.dumps({
            'event': 'bounding_box_uuid_generated',
            'facility_name': facility_name,
            'lat': lat,
            'lon': lon,
            'uuid_input': uuid_input,
            'generated_uuid': str(deterministic_uuid)
        }))
        
        return str(deterministic_uuid)
    
    def normalize_coordinates(self, coordinates: Any) -> Any:
        """Normalize coordinates to [lon, lat] format for PostGIS"""
        if isinstance(coordinates, dict):
            # Handle {lat: ..., lon: ...} format
            return [coordinates['lon'], coordinates['lat']]
        elif isinstance(coordinates, list) and len(coordinates) == 2:
            # Already in [lon, lat] format
            return coordinates
        elif isinstance(coordinates, list):
            # Handle arrays of coordinates
            return [self.normalize_coordinates(coord) for coord in coordinates]
        else:
            return coordinates

    def extract_geometry_data(self, geometry: Dict[str, Any]) -> Tuple[str, str]:
        """Extract geometry and centroid from GeoJSON geometry"""
        try:
            # Normalize coordinates to [lon, lat] format for PostGIS
            normalized_geometry = {
                'type': geometry['type'],
                'coordinates': self.normalize_coordinates(geometry['coordinates'])
            }
            
            # Convert geometry to GeoJSON string for PostGIS
            geom_json = json.dumps(normalized_geometry)
            
            if geometry['type'] == 'Point' and geometry['coordinates']:
                # Point geometry - use coordinates directly as centroid
                normalized_coords = self.normalize_coordinates(geometry['coordinates'])
                lon, lat = normalized_coords
                
                # Create centroid geometry (same as point for points)
                centroid_geometry = {
                    "type": "Point",
                    "coordinates": [lon, lat]
                }
                centroid_json = json.dumps(centroid_geometry)
                
                return geom_json, centroid_json
                
            elif geometry['type'] == 'Polygon' and geometry['coordinates']:
                # Get the first ring (exterior ring) - already normalized
                ring = normalized_geometry['coordinates'][0]
                
                # Calculate centroid
                total_lat = 0
                total_lon = 0
                point_count = len(ring)
                
                for coord in ring:
                    # Coordinates are now normalized to [lon, lat] format
                    total_lon += coord[0]
                    total_lat += coord[1]
                
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
            elif sport == 'pickleball':
                return "pickleball court"
            else:
                return f"{sport} court"
                
        except Exception as e:
            logger.warning(json.dumps({
                'event': 'fallback_name_generation_error',
                'error': str(e)
            }))
            return "sports court"
    
    def determine_public_access(self, properties: Dict[str, Any]) -> Optional[bool]:
        """Determine if a court is public based on OSM access tags"""
        try:
            # Check fee status - if fee is "no", it's likely public
            fee_raw = properties.get('fee')
            fee = fee_raw.lower() if fee_raw else ''
            if fee == 'no':
                return True
            
            # Check access restrictions
            access_raw = properties.get('access')
            access = access_raw.lower() if access_raw else ''
            if access in ['private', 'no', 'restricted']:
                return False
            if access in ['yes', 'public', 'permissive']:
                return True
            
            # Check leisure type - parks and playgrounds are typically public
            leisure_raw = properties.get('leisure')
            leisure = leisure_raw.lower() if leisure_raw else ''
            if leisure in ['park', 'playground', 'pitch']:
                return True
            if leisure in ['sports_centre', 'fitness_centre']:
                # Sports centers can be private, check other indicators
                # If we have fee info, use it
                if fee == 'yes':
                    return False
                # Otherwise, we don't know
                return None
            
            # If we have no clear indicators, return None (unknown)
            return None
            
        except Exception as e:
            logger.warning(json.dumps({
                'event': 'public_access_determination_error',
                'osm_id': properties.get('osm_id', 'unknown'),
                'error': str(e)
            }))
            # Return None on error (unknown)
            return None
    
    def _is_school_name(self, name: str) -> bool:
        """Check if a name indicates a school-based location"""
        if not name:
            return False
        
        name_lower = name.lower()
        school_keywords = ['school', 'academy', 'college', 'university', 'institute', 'high school', 'elementary', 'middle school']
        
        for keyword in school_keywords:
            if keyword in name_lower:
                return True
        
        return False
    
    def map_photon_data(self, photon_name: str, photon_distance_km: float, 
                       photon_source: str) -> Dict[str, Any]:
        """Map Photon API response to database format"""
        # Determine if this is a school-based name
        is_school = self._is_school_name(photon_name)
        
        return {
            'photon_name': photon_name,
            'photon_distance_km': round(photon_distance_km, 6),  # Round to 6 decimal places
            'photon_source': photon_source,
            'school': is_school
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
            'surface_type': self.determine_surface_type(properties),
            'is_public': self.determine_public_access(properties)
            }
            
            # Add Photon data if available
            if photon_data:
                court_data.update(self.map_photon_data(
                    photon_data['name'],
                    photon_data['distance_km'],
                    photon_data['source']
                ))
                
                # Add bounding box fields
                court_data['bounding_box_id'] = photon_data.get('bounding_box_id')
                court_data['bounding_box_coords'] = json.dumps(photon_data.get('bounding_box_coords')) if photon_data.get('bounding_box_coords') else None
            else:
                # Use fallback data if no Photon data
                court_data.update({
                    'photon_name': court_data['fallback_name'],
                    'photon_distance_km': None,
                    'photon_source': 'fallback',
                    'school': False,
                    'bounding_box_id': None,
                    'bounding_box_coords': None
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
            valid_sports = ['basketball', 'tennis', 'soccer', 'volleyball', 'handball', 'pickleball', 'other']
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
