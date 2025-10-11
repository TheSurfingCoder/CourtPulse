"""
Data validation module for court data processing
Handles validation at script level before database operations
"""

import json
import logging
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

class ValidationLevel(Enum):
    """Validation severity levels"""
    ERROR = "error"      # Stop processing
    WARNING = "warning"  # Log but continue
    INFO = "info"        # Log for information

@dataclass
class ValidationResult:
    """Result of validation check"""
    is_valid: bool
    level: ValidationLevel
    message: str
    field: Optional[str] = None

class CourtDataValidator:
    """Validates court data at multiple levels"""
    
    def __init__(self):
        self.errors: List[ValidationResult] = []
        self.warnings: List[ValidationResult] = []
        self.info: List[ValidationResult] = []
    
    def validate_geojson_structure(self, feature: Dict[str, Any]) -> ValidationResult:
        """Validate GeoJSON feature structure"""
        try:
            # Check required top-level properties
            if not isinstance(feature, dict):
                return ValidationResult(
                    False, ValidationLevel.ERROR, 
                    "Feature must be a dictionary"
                )
            
            if 'geometry' not in feature:
                return ValidationResult(
                    False, ValidationLevel.ERROR,
                    "Missing 'geometry' property"
                )
            
            if 'properties' not in feature:
                return ValidationResult(
                    False, ValidationLevel.ERROR,
                    "Missing 'properties' property"
                )
            
            # Validate geometry structure
            geometry = feature['geometry']
            if not isinstance(geometry, dict):
                return ValidationResult(
                    False, ValidationLevel.ERROR,
                    "Geometry must be a dictionary"
                )
            
            # Accept both Point and Polygon geometries
            geometry_type = geometry.get('type')
            if geometry_type not in ['Point', 'Polygon']:
                return ValidationResult(
                    False, ValidationLevel.ERROR,
                    f"Unsupported geometry type: {geometry_type}. Must be Point or Polygon"
                )
            
            if 'coordinates' not in geometry:
                return ValidationResult(
                    False, ValidationLevel.ERROR,
                    "Missing coordinates in geometry"
                )
            
            return ValidationResult(True, ValidationLevel.INFO, "GeoJSON structure valid")
            
        except Exception as e:
            return ValidationResult(
                False, ValidationLevel.ERROR,
                f"GeoJSON validation error: {str(e)}"
            )
    
    def validate_coordinates(self, coordinates: List, geometry_type: str = "Polygon") -> ValidationResult:
        """Validate coordinate arrays for different geometry types"""
        try:
            if not coordinates or not isinstance(coordinates, list):
                return ValidationResult(
                    False, ValidationLevel.ERROR,
                    "Invalid coordinates structure"
                )
            
            if geometry_type == "Point":
                # Validate point coordinates [lon, lat]
                if not isinstance(coordinates, list) or len(coordinates) != 2:
                    return ValidationResult(
                        False, ValidationLevel.ERROR,
                        "Point coordinates must be [lon, lat]"
                    )
                
                lon, lat = coordinates
                if not isinstance(lon, (int, float)) or not isinstance(lat, (int, float)):
                    return ValidationResult(
                        False, ValidationLevel.ERROR,
                        "Point coordinates must be numbers"
                    )
                
                if not (-180 <= lon <= 180):
                    return ValidationResult(
                        False, ValidationLevel.ERROR,
                        f"Longitude out of range: {lon}"
                    )
                
                if not (-90 <= lat <= 90):
                    return ValidationResult(
                        False, ValidationLevel.ERROR,
                        f"Latitude out of range: {lat}"
                    )
                
                return ValidationResult(True, ValidationLevel.INFO, "Point coordinates valid")
            
            elif geometry_type == "Polygon":
                # Check if it's a valid polygon (array of rings)
                if not isinstance(coordinates[0], list):
                    return ValidationResult(
                        False, ValidationLevel.ERROR,
                        "Polygon coordinates must be array of rings"
                    )
                
                # Validate first ring (exterior ring)
                ring = coordinates[0]
                if len(ring) < 4:  # Polygon needs at least 4 points (closed)
                    return ValidationResult(
                        False, ValidationLevel.ERROR,
                        "Polygon must have at least 4 points"
                    )
                
                # Check if first and last points are the same (closed polygon)
                if ring[0] != ring[-1]:
                    return ValidationResult(
                        False, ValidationLevel.WARNING,
                        "Polygon should be closed (first and last points should match)"
                    )
            
            # Validate individual coordinates
            for i, coord in enumerate(ring):
                # Handle both [lon, lat] arrays and {lat: ..., lon: ...} objects
                if isinstance(coord, dict):
                    # Handle {lat: ..., lon: ...} format
                    if 'lat' not in coord or 'lon' not in coord:
                        return ValidationResult(
                            False, ValidationLevel.ERROR,
                            f"Coordinate object missing lat/lon at position {i}: {coord}"
                        )
                    lat, lon = coord['lat'], coord['lon']
                elif isinstance(coord, list) and len(coord) == 2:
                    # Handle [lon, lat] format
                    lon, lat = coord
                else:
                    return ValidationResult(
                        False, ValidationLevel.ERROR,
                        f"Invalid coordinate format at position {i}: {coord}"
                    )
                
                if not isinstance(lon, (int, float)) or not isinstance(lat, (int, float)):
                    return ValidationResult(
                        False, ValidationLevel.ERROR,
                        f"Coordinates must be numbers at position {i}"
                    )
                
                if not (-180 <= lon <= 180):
                    return ValidationResult(
                        False, ValidationLevel.ERROR,
                        f"Longitude out of range at position {i}: {lon}"
                    )
                
                if not (-90 <= lat <= 90):
                    return ValidationResult(
                        False, ValidationLevel.ERROR,
                        f"Latitude out of range at position {i}: {lat}"
                    )
            
            return ValidationResult(True, ValidationLevel.INFO, "Coordinates valid")
            
        except Exception as e:
            return ValidationResult(
                False, ValidationLevel.ERROR,
                f"Coordinate validation error: {str(e)}"
            )
    
    def validate_required_fields(self, properties: Dict[str, Any]) -> List[ValidationResult]:
        """Validate required fields in properties"""
        results = []
        
        # Check for osm_id or @id (GeoJSON uses @id)
        if 'osm_id' not in properties and '@id' not in properties:
            results.append(ValidationResult(
                False, ValidationLevel.ERROR,
                "Missing required field: osm_id or @id",
                field='osm_id'
            ))
        
        # Check for sport
        if 'sport' not in properties or not properties['sport']:
            results.append(ValidationResult(
                False, ValidationLevel.ERROR,
                "Missing required field: sport",
                field='sport'
            ))
        
        return results
    
    def validate_data_types(self, properties: Dict[str, Any]) -> List[ValidationResult]:
        """Validate data types of properties"""
        results = []
        
        # Validate osm_id or @id
        osm_id = properties.get('osm_id') or properties.get('@id')
        if osm_id:
            if not isinstance(osm_id, str) or not osm_id.strip():
                results.append(ValidationResult(
                    False, ValidationLevel.ERROR,
                    "osm_id must be a non-empty string",
                    field='osm_id'
                ))
            elif not osm_id.startswith(('way/', 'node/', 'relation/')):
                results.append(ValidationResult(
                    False, ValidationLevel.WARNING,
                    f"osm_id format unusual: {osm_id}",
                    field='osm_id'
                ))
        
        # Validate sport
        if 'sport' in properties:
            sport = properties['sport']
            valid_sports = ['basketball', 'tennis', 'soccer', 'volleyball', 'handball', 'pickleball', 'other']
            if sport not in valid_sports:
                results.append(ValidationResult(
                    False, ValidationLevel.ERROR,
                    f"Invalid sport: {sport}. Must be one of {valid_sports}",
                    field='sport'
                ))
        
        # Validate hoops (if present)
        if 'hoops' in properties and properties['hoops'] is not None:
            hoops = properties['hoops']
            # Convert string to int if possible
            try:
                hoops_int = int(hoops) if isinstance(hoops, str) else hoops
                if not isinstance(hoops_int, int) or hoops_int <= 0:
                    results.append(ValidationResult(
                        False, ValidationLevel.ERROR,
                        f"hoops must be a positive integer, got: {hoops}",
                        field='hoops'
                    ))
            except (ValueError, TypeError):
                results.append(ValidationResult(
                    False, ValidationLevel.ERROR,
                    f"hoops must be a valid number, got: {hoops}",
                    field='hoops'
                ))
        
        return results
    
    def validate_business_logic(self, properties: Dict[str, Any]) -> List[ValidationResult]:
        """Validate business logic rules"""
        results = []
        
        # Basketball courts should have hoops
        if properties.get('sport') == 'basketball' and not properties.get('hoops'):
            results.append(ValidationResult(
                False, ValidationLevel.WARNING,
                "Basketball courts should have hoops count specified",
                field='hoops'
            ))
        
        # Check for reasonable hoops count
        if properties.get('hoops'):
            try:
                hoops_int = int(properties['hoops']) if isinstance(properties['hoops'], str) else properties['hoops']
                if hoops_int > 10:
                    results.append(ValidationResult(
                        False, ValidationLevel.WARNING,
                        f"Unusually high hoops count: {properties['hoops']}",
                        field='hoops'
                    ))
            except (ValueError, TypeError):
                pass  # Skip validation if hoops is not a valid number
        
        return results
    
    def validate_photon_data(self, photon_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate Photon API response data"""
        results = []
        
        # Validate photon_name
        if 'photon_name' in photon_data:
            name = photon_data['photon_name']
            if not isinstance(name, str) or not name.strip():
                results.append(ValidationResult(
                    False, ValidationLevel.ERROR,
                    "photon_name must be a non-empty string",
                    field='photon_name'
                ))
        
        # Validate photon_distance_km
        if 'photon_distance_km' in photon_data:
            distance = photon_data['photon_distance_km']
            if not isinstance(distance, (int, float)) or distance < 0:
                results.append(ValidationResult(
                    False, ValidationLevel.ERROR,
                    f"photon_distance_km must be a non-negative number, got: {distance}",
                    field='photon_distance_km'
                ))
        
        # Validate photon_source
        if 'photon_source' in photon_data:
            source = photon_data['photon_source']
            valid_sources = ['search_api', 'reverse_geocoding', 'fallback']
            if source not in valid_sources:
                results.append(ValidationResult(
                    False, ValidationLevel.ERROR,
                    f"Invalid photon_source: {source}. Must be one of {valid_sources}",
                    field='photon_source'
                ))
        
        return results
    
    def validate_court_data(self, feature: Dict[str, Any], photon_data: Optional[Dict[str, Any]] = None) -> Tuple[bool, List[ValidationResult]]:
        """Main validation method - validates entire court data"""
        all_results = []
        
        # 1. GeoJSON structure validation
        geojson_result = self.validate_geojson_structure(feature)
        all_results.append(geojson_result)
        
        if not geojson_result.is_valid:
            return False, all_results
        
        # 2. Coordinate validation
        geometry = feature['geometry']
        geometry_type = geometry.get('type', 'Polygon')
        coord_result = self.validate_coordinates(geometry['coordinates'], geometry_type)
        all_results.append(coord_result)
        
        if not coord_result.is_valid:
            return False, all_results
        
        # 3. Properties validation
        properties = feature['properties']
        
        # Required fields
        required_results = self.validate_required_fields(properties)
        all_results.extend(required_results)
        
        # Data types
        type_results = self.validate_data_types(properties)
        all_results.extend(type_results)
        
        # Business logic
        business_results = self.validate_business_logic(properties)
        all_results.extend(business_results)
        
        # 4. Photon data validation (if provided)
        if photon_data:
            photon_results = self.validate_photon_data(photon_data)
            all_results.extend(photon_results)
        
        # Check if any errors exist
        has_errors = any(result.level == ValidationLevel.ERROR for result in all_results)
        
        # Categorize results
        self.errors = [r for r in all_results if r.level == ValidationLevel.ERROR]
        self.warnings = [r for r in all_results if r.level == ValidationLevel.WARNING]
        self.info = [r for r in all_results if r.level == ValidationLevel.INFO]
        
        return not has_errors, all_results
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of validation results"""
        return {
            'total_checks': len(self.errors) + len(self.warnings) + len(self.info),
            'errors': len(self.errors),
            'warnings': len(self.warnings),
            'info': len(self.info),
            'is_valid': len(self.errors) == 0,
            'error_details': [{'field': r.field, 'message': r.message} for r in self.errors],
            'warning_details': [{'field': r.field, 'message': r.message} for r in self.warnings]
        }
    
    def log_validation_results(self, osm_id: str):
        """Log validation results for a specific court"""
        summary = self.get_validation_summary()
        
        logger.info(json.dumps({
            'event': 'validation_completed',
            'osm_id': osm_id,
            'is_valid': summary['is_valid'],
            'errors': summary['errors'],
            'warnings': summary['warnings'],
            'info': summary['info']
        }))
        
        # Log individual errors
        for error in self.errors:
            logger.error(json.dumps({
                'event': 'validation_error',
                'osm_id': osm_id,
                'field': error.field,
                'message': error.message
            }))
        
        # Log individual warnings
        for warning in self.warnings:
            logger.warning(json.dumps({
                'event': 'validation_warning',
                'osm_id': osm_id,
                'field': warning.field,
                'message': warning.message
            }))

# Example usage
if __name__ == "__main__":
    validator = CourtDataValidator()
    
    # Example court data
    sample_court = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[-122.4, 37.7], [-122.4, 37.8], [-122.3, 37.8], [-122.3, 37.7], [-122.4, 37.7]]]
        },
        "properties": {
            "osm_id": "way/12345",
            "sport": "basketball",
            "hoops": 2
        }
    }
    
    # Validate
    is_valid, results = validator.validate_court_data(sample_court)
    print(f"Valid: {is_valid}")
    print(f"Summary: {validator.get_validation_summary()}")
