"""
Main court data processing pipeline
Integrates validation, Photon geocoding, data mapping, and database operations
"""

import json
import logging
import time
import asyncio
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import os
import sys

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from validation import CourtDataValidator, ValidationError
from data_mapper import CourtDataMapper
from database_operations import DatabaseManager, CourtDatabaseOperations
from test_photon_geocoding import PhotonGeocodingProvider
from clustering import CoordinateClusterer, CourtClusterData

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CourtProcessingPipeline:
    """Main pipeline for processing court data from GeoJSON to database"""
    
    def __init__(self, connection_string: str, batch_size: int = 100):
        self.connection_string = connection_string
        self.batch_size = batch_size
        
        # Initialize components
        self.validator = CourtDataValidator()
        self.mapper = CourtDataMapper()
        self.db_manager = DatabaseManager(connection_string)
        self.db_ops = CourtDatabaseOperations(self.db_manager)
        self.geocoding_provider = PhotonGeocodingProvider()
        self.clusterer = CoordinateClusterer(max_distance_km=0.05)  # ~160 feet
        
        # Statistics
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'validation_failed': 0,
            'geocoding_failed': 0,
            'database_failed': 0,
            'skipped': 0,
            'clusters_created': 0,
            'api_calls_saved': 0,
            'start_time': None,
            'end_time': None
        }
    
    def load_geojson(self, file_path: str) -> List[Dict[str, Any]]:
        """Load GeoJSON file and return features"""
        try:
            logger.info(json.dumps({
                'event': 'loading_geojson',
                'file_path': file_path
            }))
            
            with open(file_path, 'r') as f:
                geojson_data = json.load(f)
            
            features = geojson_data.get('features', [])
            
            logger.info(json.dumps({
                'event': 'geojson_loaded',
                'file_path': file_path,
                'feature_count': len(features)
            }))
            
            return features
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'geojson_load_error',
                'file_path': file_path,
                'error': str(e)
            }))
            raise
    
    def process_single_court(self, feature: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Process a single court feature through the entire pipeline"""
        try:
            properties = feature.get('properties', {})
            osm_id = properties.get('osm_id', 'unknown')
            
            # Step 1: Validation
            is_valid, validation_results = self.validator.validate_court_data(feature)
            if not is_valid:
                self.validator.log_validation_results(osm_id)
                self.stats['validation_failed'] += 1
                return False, "Validation failed", None
            
            # Step 2: Geocoding with Photon
            try:
                # Extract coordinates from geometry
                geometry = feature['geometry']
                if geometry['type'] == 'Polygon' and geometry['coordinates']:
                    # Get centroid coordinates
                    ring = geometry['coordinates'][0]
                    total_lon = sum(coord[0] for coord in ring) / len(ring)
                    total_lat = sum(coord[1] for coord in ring) / len(ring)
                    
                    # Each individual way represents 1 court, regardless of hoops count
                    # (hoops count is for the number of basketball hoops, not courts)
                    court_count = 1
                    
                    # Get name from Photon
                    photon_name, photon_data = self.geocoding_provider.reverse_geocode(total_lat, total_lon, court_count)
                    
                    if not photon_name:
                        self.stats['geocoding_failed'] += 1
                        return False, "Geocoding failed", None
                    
                    # Calculate distance if we have the data
                    distance_km = 0.0
                    if photon_data and 'geometry' in photon_data:
                        # This would need to be implemented based on your Photon response structure
                        distance_km = 0.0  # Placeholder
                    
                    photon_data = {
                        'name': photon_name,
                        'distance_km': distance_km,
                        'source': 'search_api'  # or 'reverse_geocoding' based on your logic
                    }
                else:
                    self.stats['geocoding_failed'] += 1
                    return False, "Invalid geometry for geocoding", None
                    
            except Exception as e:
                logger.error(json.dumps({
                    'event': 'geocoding_error',
                    'osm_id': osm_id,
                    'error': str(e)
                }))
                self.stats['geocoding_failed'] += 1
                return False, f"Geocoding error: {str(e)}", None
            
            # Step 3: Data mapping
            try:
                mapped_data = self.mapper.map_court_to_db_format(feature, photon_data)
                
                # Validate mapped data
                is_valid, validation_msg = self.mapper.validate_mapped_data(mapped_data)
                if not is_valid:
                    self.stats['validation_failed'] += 1
                    return False, f"Mapping validation failed: {validation_msg}", None
                
            except Exception as e:
                logger.error(json.dumps({
                    'event': 'mapping_error',
                    'osm_id': osm_id,
                    'error': str(e)
                }))
                self.stats['validation_failed'] += 1
                return False, f"Mapping error: {str(e)}", None
            
            return True, "Success", mapped_data
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'court_processing_error',
                'osm_id': osm_id,
                'error': str(e)
            }))
            return False, f"Processing error: {str(e)}", None
    
    def process_batch(self, features_batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process a batch of court features"""
        batch_results = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'errors': [],
            'successful_data': []
        }
        
        logger.info(json.dumps({
            'event': 'processing_batch',
            'batch_size': len(features_batch)
        }))
        
        for feature in features_batch:
            try:
                batch_results['processed'] += 1
                self.stats['total_processed'] += 1
                
                success, message, mapped_data = self.process_single_court(feature)
                
                if success and mapped_data:
                    batch_results['successful'] += 1
                    batch_results['successful_data'].append(mapped_data)
                    self.stats['successful'] += 1
                else:
                    batch_results['failed'] += 1
                    batch_results['errors'].append({
                        'osm_id': feature.get('properties', {}).get('osm_id') or feature.get('properties', {}).get('@id', 'unknown'),
                        'error': message
                    })
                    self.stats['skipped'] += 1
                
            except Exception as e:
                batch_results['failed'] += 1
                batch_results['errors'].append({
                    'osm_id': feature.get('properties', {}).get('osm_id') or feature.get('properties', {}).get('@id', 'unknown'),
                    'error': str(e)
                })
                self.stats['skipped'] += 1
                
                logger.error(json.dumps({
                    'event': 'batch_processing_error',
                    'osm_id': feature.get('properties', {}).get('osm_id') or feature.get('properties', {}).get('@id', 'unknown'),
                    'error': str(e)
                }))
        
        # Insert successful records into database
        if batch_results['successful_data']:
            try:
                db_results = self.db_ops.upsert_court_batch(batch_results['successful_data'])
                
                # Update statistics based on database results
                if db_results['error_count'] > 0:
                    self.stats['database_failed'] += db_results['error_count']
                    self.stats['successful'] -= db_results['error_count']
                    self.stats['skipped'] += db_results['error_count']
                
                logger.info(json.dumps({
                    'event': 'batch_database_upsert',
                    'batch_size': len(batch_results['successful_data']),
                    'db_success': db_results['success_count'],
                    'db_errors': db_results['error_count']
                }))
                
            except Exception as e:
                logger.error(json.dumps({
                    'event': 'batch_database_error',
                    'error': str(e)
                }))
                self.stats['database_failed'] += len(batch_results['successful_data'])
                self.stats['successful'] -= len(batch_results['successful_data'])
                self.stats['skipped'] += len(batch_results['successful_data'])
        
        return batch_results
    
    def process_cluster(self, cluster: List[CourtClusterData]) -> List[Dict[str, Any]]:
        """Process a cluster of nearby courts with shared geocoding"""
        try:
            # Use the first court as representative for geocoding
            representative_court = cluster[0]
            
            logger.info(json.dumps({
                'event': 'processing_cluster',
                'cluster_size': len(cluster),
                'representative_osm_id': representative_court.osm_id,
                'coordinates': {'lat': representative_court.lat, 'lon': representative_court.lon}
            }))
            
            # Calculate total court count for the cluster
            total_court_count = sum(court.hoops or 1 for court in cluster)
            
            # Get geocoding result for the representative court
            photon_name, photon_data = self.geocoding_provider.reverse_geocode(
                representative_court.lat, representative_court.lon, total_court_count
            )
            
            if not photon_name:
                logger.warning(json.dumps({
                    'event': 'cluster_geocoding_failed',
                    'cluster_size': len(cluster),
                    'representative_osm_id': representative_court.osm_id
                }))
                return []
            
            # Calculate distance for representative court
            distance_km = 0.0
            if photon_data and 'geometry' in photon_data:
                coords = photon_data['geometry'].get('coordinates', [0, 0])
                result_lon, result_lat = coords[0], coords[1]
                distance_km = self.geocoding_provider._calculate_distance(
                    representative_court.lat, representative_court.lon, result_lat, result_lon
                )
            
            # Create photon data for all courts in cluster
            shared_photon_data = {
                'name': photon_name,
                'distance_km': distance_km,
                'source': 'search_api'  # or determine based on geocoding logic
            }
            
            # Process all courts in cluster with shared geocoding result
            cluster_results = []
            
            for court in cluster:
                try:
                    # Validate the feature
                    is_valid, validation_results = self.validator.validate_court_data(court.feature_data)
                    if not is_valid:
                        self.stats['validation_failed'] += 1
                        continue
                    
                    # Map to database format
                    mapped_data = self.mapper.map_court_to_db_format(court.feature_data, shared_photon_data)
                    
                    # Validate mapped data
                    is_valid, validation_msg = self.mapper.validate_mapped_data(mapped_data)
                    if not is_valid:
                        self.stats['validation_failed'] += 1
                        continue
                    
                    cluster_results.append(mapped_data)
                    self.stats['successful'] += 1
                    
                except Exception as e:
                    logger.error(json.dumps({
                        'event': 'cluster_court_processing_error',
                        'osm_id': court.osm_id,
                        'error': str(e)
                    }))
                    self.stats['skipped'] += 1
            
            logger.info(json.dumps({
                'event': 'cluster_processed',
                'cluster_size': len(cluster),
                'successful': len(cluster_results),
                'failed': len(cluster) - len(cluster_results),
                'shared_name': photon_name
            }))
            
            return cluster_results
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'cluster_processing_error',
                'cluster_size': len(cluster),
                'error': str(e)
            }))
            return []
    
    def process_geojson_file(self, file_path: str, max_features: Optional[int] = None) -> Dict[str, Any]:
        """Process entire GeoJSON file with individual court processing"""
        try:
            self.stats['start_time'] = datetime.now()
            
            # Load GeoJSON
            features = self.load_geojson(file_path)
            
            # Limit features if specified
            if max_features:
                features = features[:max_features]
                logger.info(json.dumps({
                    'event': 'limited_features',
                    'max_features': max_features,
                    'actual_count': len(features)
                }))
            
            total_features = len(features)
            
            # Step 1: Process each court individually
            logger.info(json.dumps({
                'event': 'individual_processing_phase_started',
                'total_features': total_features,
                'batch_size': self.batch_size
            }))
            
            all_successful_data = []
            
            # Process features in batches
            for i in range(0, len(features), self.batch_size):
                batch = features[i:i + self.batch_size]
                batch_results = self.process_individual_courts_batch(batch)
                all_successful_data.extend(batch_results['successful_data'])
                
                # Log progress
                if (i + len(batch)) % (self.batch_size * 5) == 0:  # Log every 5 batches
                    logger.info(json.dumps({
                        'event': 'batch_progress',
                        'processed': i + len(batch),
                        'total': total_features,
                        'successful': len(all_successful_data),
                        'percentage': round(((i + len(batch)) / total_features) * 100, 1)
                    }))
            
            # Step 2: Post-processing clustering
            logger.info(json.dumps({
                'event': 'post_processing_clustering_started',
                'total_courts': len(all_successful_data)
            }))
            
            # Add cluster metadata to all successful courts
            cluster_summary = self.add_cluster_metadata(all_successful_data)
            
            # Step 3: Add individual court names
            logger.info(json.dumps({
                'event': 'adding_individual_court_names',
                'message': 'Starting individual court name assignment'
            }))
            
            individual_names_added = self.add_individual_court_names()
            
            # Step 4: Final database batch processing
            if all_successful_data:
                logger.info(json.dumps({
                    'event': 'final_database_batch_processing',
                    'batch_size': len(all_successful_data)
                }))
                
                db_results = self.db_ops.upsert_court_batch(all_successful_data)
                db_success = db_results['success_count']
                db_errors = db_results['error_count']
                
                logger.info(json.dumps({
                    'event': 'final_database_batch_processed',
                    'batch_size': len(all_successful_data),
                    'db_success': db_success,
                    'db_errors': db_errors
                }))
            
            # Calculate final statistics
            self.stats['end_time'] = datetime.now()
            self.stats['processing_time_seconds'] = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            self.stats['features_per_second'] = round(self.stats['total_processed'] / self.stats['processing_time_seconds'], 2) if self.stats['processing_time_seconds'] > 0 else 0
            self.stats['success_rate'] = round((self.stats['successful'] / self.stats['total_processed']) * 100, 2) if self.stats['total_processed'] > 0 else 0
            
            # Get optimization stats from geocoding provider
            optimization_stats = self.geocoding_provider.get_optimization_stats()
            
            # Generate final report
            final_stats = {
                'total_features': total_features,
                'total_processed': self.stats['total_processed'],
                'successful': self.stats['successful'],
                'validation_failed': self.stats['validation_failed'],
                'geocoding_failed': self.stats['geocoding_failed'],
                'database_failed': self.stats['database_failed'],
                'skipped': self.stats['skipped'],
                'clusters_created': cluster_summary.get('geographic_clusters', 0),
                'api_calls_saved': 0,  # No longer applicable with individual processing
                'individual_names_added': individual_names_added,
                'processing_time_seconds': self.stats['processing_time_seconds'],
                'features_per_second': self.stats['features_per_second'],
                'success_rate': self.stats['success_rate'],
                'clustering_efficiency': cluster_summary.get('clustering_efficiency', 0),
                'frontend_ready': True,
                'optimization_stats': optimization_stats
            }
            
            logger.info(json.dumps({
                'event': 'integrated_pipeline_completed',
                'final_stats': final_stats
            }))
            
            return final_stats
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'pipeline_error',
                'error': str(e)
            }))
            raise
        finally:
            # Clean up database connections
            self.db_manager.close_all_connections()
    
    def process_individual_courts_batch(self, features_batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process a batch of individual court features"""
        batch_results = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'errors': [],
            'successful_data': []
        }
        
        logger.info(json.dumps({
            'event': 'processing_individual_batch',
            'batch_size': len(features_batch)
        }))
        
        for feature in features_batch:
            try:
                batch_results['processed'] += 1
                self.stats['total_processed'] += 1
                
                # Process individual court
                success, message, mapped_data = self.process_individual_court(feature)
                
                if success and mapped_data:
                    batch_results['successful'] += 1
                    batch_results['successful_data'].append(mapped_data)
                else:
                    batch_results['failed'] += 1
                    batch_results['errors'].append({
                        'osm_id': feature.get('properties', {}).get('osm_id', 'unknown'),
                        'error': message
                    })
                    
            except Exception as e:
                batch_results['failed'] += 1
                batch_results['errors'].append({
                    'osm_id': feature.get('properties', {}).get('osm_id', 'unknown'),
                    'error': str(e)
                })
                logger.error(json.dumps({
                    'event': 'individual_court_error',
                    'osm_id': feature.get('properties', {}).get('osm_id', 'unknown'),
                    'error': str(e)
                }))
        
        logger.info(json.dumps({
            'event': 'individual_batch_completed',
            'batch_size': len(features_batch),
            'successful': batch_results['successful'],
            'failed': batch_results['failed']
        }))
        
        return batch_results
    
    def process_individual_court(self, feature: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Process a single court feature individually"""
        try:
            properties = feature.get('properties', {})
            osm_id = properties.get('osm_id') or properties.get('@id', 'unknown')
            
            # Step 1: Validation
            is_valid, validation_results = self.validator.validate_court_data(feature)
            if not is_valid:
                self.stats['validation_failed'] += 1
                return False, "Validation failed", None
            
            # Step 2: Geocoding with Photon
            try:
                # Extract coordinates from geometry
                geometry = feature['geometry']
                if geometry['type'] == 'Polygon' and geometry['coordinates']:
                    # Get centroid coordinates
                    ring = geometry['coordinates'][0]
                    total_lon = sum(coord[0] for coord in ring) / len(ring)
                    total_lat = sum(coord[1] for coord in ring) / len(ring)
                    
                    # Each individual way represents 1 court, regardless of hoops count
                    # (hoops count is for the number of basketball hoops, not courts)
                    court_count = 1
                    
                    # Extract sport from feature properties
                    sport = properties.get('sport', 'basketball')
                    
                    # Get name from Photon (now returns API calls count too)
                    photon_name, photon_data, api_calls_made = self.geocoding_provider.reverse_geocode(total_lat, total_lon, court_count, sport)
                    
                    # Debug: log what's returned from geocoding
                    logger.info(json.dumps({
                        'event': 'geocoding_provider_debug',
                        'photon_name': photon_name,
                        'photon_data_keys': list(photon_data.keys()) if photon_data else [],
                        'facility_coords_from_geocoding': photon_data.get('facility_coords') if photon_data else None
                    }))
                    
                    if not photon_name:
                        self.stats['geocoding_failed'] += 1
                        return False, "Geocoding failed", None
                    
                    # Calculate distance if we have the data
                    distance_km = 0.0
                    if photon_data and 'distance_km' in photon_data:
                        distance_km = photon_data['distance_km']
                    
                    # Determine if this is a facility match or generic name
                    is_facility_match = photon_data is not None
                    
                    # Generate bounding box ID and coordinates
                    bounding_box_id = None
                    bounding_box_coords = None
                    
                    if is_facility_match:
                        # Use the facility's actual center coordinates from Photon API
                        facility_geometry = photon_data.get('feature', {}).get('geometry', {})
                        if facility_geometry.get('type') == 'Point':
                            facility_lon, facility_lat = facility_geometry['coordinates']
                        else:
                            # Fallback to court coordinates if no facility geometry
                            facility_lat, facility_lon = total_lat, total_lon
                        if photon_data and 'extent' in photon_data:
                            bounding_box_coords = photon_data['extent']
                        else:
                            bounding_box_coords = geometry
                        
                        # Generate UUID using facility coordinates
                        bounding_box_id = self.mapper.generate_bounding_box_uuid(facility_lat, facility_lon, photon_name)
                        
                        logger.info(json.dumps({
                            'event': 'facility_uuid_generation',
                            'facility_name': photon_name,
                            'court_coords': [total_lat, total_lon],
                            'facility_coords': [facility_lat, facility_lon],
                            'generated_uuid': bounding_box_id,
                            'source': 'photon_api_geometry'
                        }))
                    else:
                        # Generic name: use feature's own geometry as bounding box
                        bounding_box_coords = geometry
                    
                    # Update photon_data with new fields (preserve original data including facility_coords)
                    if photon_data:
                        photon_data.update({
                            'name': photon_name,
                            'distance_km': distance_km,
                            'source': 'search_api',  # Use valid constraint value
                            'bounding_box_id': bounding_box_id,
                            'bounding_box_coords': bounding_box_coords,
                            'is_facility_match': is_facility_match
                        })
                    else:
                        photon_data = {
                            'name': photon_name,
                            'distance_km': distance_km,
                            'source': 'search_api',
                            'bounding_box_id': bounding_box_id,
                            'bounding_box_coords': bounding_box_coords,
                            'is_facility_match': is_facility_match
                        }
                else:
                    self.stats['geocoding_failed'] += 1
                    return False, "Invalid geometry for geocoding", None
                    
            except Exception as e:
                logger.error(json.dumps({
                    'event': 'geocoding_error',
                    'osm_id': osm_id,
                    'error': str(e)
                }))
                self.stats['geocoding_failed'] += 1
                return False, f"Geocoding error: {str(e)}", None
            
            # Step 3: Data mapping
            try:
                mapped_data = self.mapper.map_court_to_db_format(feature, photon_data)
                
                # Validate mapped data
                is_valid, validation_msg = self.mapper.validate_mapped_data(mapped_data)
                if not is_valid:
                    self.stats['validation_failed'] += 1
                    return False, f"Mapping validation failed: {validation_msg}", None
                
            except Exception as e:
                logger.error(json.dumps({
                    'event': 'mapping_error',
                    'osm_id': osm_id,
                    'error': str(e)
                }))
                self.stats['validation_failed'] += 1
                return False, f"Mapping error: {str(e)}", None
            
            self.stats['successful'] += 1
            return True, "Success", mapped_data
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'individual_court_processing_error',
                'osm_id': osm_id,
                'error': str(e)
            }))
            return False, f"Processing error: {str(e)}", None
    
    def add_cluster_metadata(self, courts_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add cluster metadata to courts after individual processing"""
        try:
            # Import the cluster metadata populator
            from populate_cluster_metadata import ClusterMetadataPopulator
            
            # Create a temporary connection string for the populator
            populator = ClusterMetadataPopulator(self.connection_string, max_distance_km=0.05)
            
            # Get cluster summary
            summary = populator.populate_all_cluster_metadata()
            
            logger.info(json.dumps({
                'event': 'cluster_metadata_added',
                'summary': summary
            }))
            
            return summary
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'cluster_metadata_error',
                'error': str(e)
            }))
            return {'geographic_clusters': 0, 'clustering_efficiency': 0}
    
    def add_individual_court_names(self) -> int:
        """Add individual court names for clustered courts"""
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            
            # Add individual_court_name column if it doesn't exist
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'courts' AND column_name = 'individual_court_name'
            """)
            
            if not cursor.fetchone():
                cursor.execute("""
                    ALTER TABLE courts 
                    ADD COLUMN individual_court_name VARCHAR(255)
                """)
                logger.info("Added individual_court_name column to courts table")
            
            # Clean existing photon names by removing court counts
            cursor.execute("""
                UPDATE courts 
                SET photon_name = REGEXP_REPLACE(photon_name, '\\s*\\(\\d+\\s+Courts?\\)', '', 'g')
                WHERE photon_name LIKE '%(% Courts)' OR photon_name LIKE '%(% Court)'
            """)
            cleaned_count = cursor.rowcount
            logger.info(f"Cleaned {cleaned_count} photon_name values")
            
            # Clear individual_court_name for single-court clusters
            cursor.execute("""
                UPDATE courts 
                SET individual_court_name = NULL
                WHERE cluster_id IN (
                    SELECT cluster_id 
                    FROM courts 
                    WHERE cluster_id IS NOT NULL
                    GROUP BY cluster_id 
                    HAVING COUNT(*) = 1
                )
            """)
            cleared_count = cursor.rowcount
            logger.info(f"Cleared {cleared_count} individual_court_name values for single-court clusters")
            
            # Get all location-sport combinations that have multiple courts total
            cursor.execute("""
                SELECT 
                    photon_name, 
                    sport, 
                    COUNT(*) as court_count,
                    STRING_AGG(osm_id::text, ',' ORDER BY osm_id) as osm_ids
                FROM courts 
                WHERE photon_name IS NOT NULL 
                GROUP BY photon_name, sport 
                HAVING COUNT(*) > 1
                ORDER BY photon_name, sport
            """)
            
            multi_court_locations = cursor.fetchall()
            
            individual_names_added = 0
            
            for location in multi_court_locations:
                photon_name = location[0]
                sport = location[1]
                court_count = location[2]
                osm_ids = location[3].split(',')
                
                # Add individual court names
                for i, osm_id in enumerate(osm_ids, 1):
                    individual_name = f"{photon_name} Court {i}"
                    
                    cursor.execute("""
                        UPDATE courts 
                        SET individual_court_name = %s
                        WHERE osm_id = %s AND photon_name = %s AND sport = %s
                    """, (individual_name, osm_id, photon_name, sport))
                    
                    individual_names_added += 1
            
            conn.commit()
            
            logger.info(json.dumps({
                'event': 'individual_court_names_added',
                'total_updated': individual_names_added,
                'location_sports_processed': len(multi_court_locations)
            }))
            
            return individual_names_added
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(json.dumps({
                'event': 'individual_court_names_error',
                'error': str(e)
            }))
            return 0
        finally:
            if conn:
                conn.close()

# Example usage
if __name__ == "__main__":
    # Get connection string from environment variables
    connection_string = os.getenv('DATABASE_URL')
    if not connection_string:
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'courtpulse-dev')
        db_user = os.getenv('DB_USER', 'matthewmctighe')
        db_password = os.getenv('DB_PASSWORD', '')
        connection_string = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
    
    # Initialize pipeline
    pipeline = CourtProcessingPipeline(connection_string, batch_size=100)
    
    # Process GeoJSON file
    async def run_pipeline():
        try:
            results = await pipeline.process_geojson_file('data_enrichment/export.geojson', max_features=5)  # Test with 5 features
            print("Pipeline Results:", json.dumps(results, indent=2, default=str))
        except Exception as e:
            print(f"Pipeline failed: {e}")
    
    asyncio.run(run_pipeline())
