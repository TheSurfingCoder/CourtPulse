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
                    
                    # Get court count from properties
                    court_count = 1
                    if 'properties' in feature and 'hoops' in feature['properties']:
                        try:
                            court_count = int(feature['properties']['hoops'])
                        except (ValueError, TypeError):
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
        """Process entire GeoJSON file with coordinate clustering"""
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
            
            # Step 1: Extract court data and create clusters
            logger.info(json.dumps({
                'event': 'clustering_phase_started',
                'total_features': total_features
            }))
            
            courts = self.clusterer.extract_court_data(features)
            clusters = self.clusterer.cluster_courts(courts)
            
            self.stats['clusters_created'] = len(clusters)
            self.stats['api_calls_saved'] = total_features - len(clusters)
            
            logger.info(json.dumps({
                'event': 'clustering_completed',
                'total_features': total_features,
                'total_clusters': len(clusters),
                'api_calls_saved': self.stats['api_calls_saved'],
                'efficiency_improvement': round((self.stats['api_calls_saved'] / total_features) * 100, 1) if total_features > 0 else 0
            }))
            
            # Step 2: Process clusters in batches
            logger.info(json.dumps({
                'event': 'processing_phase_started',
                'total_clusters': len(clusters),
                'batch_size': self.batch_size
            }))
            
            all_successful_data = []
            
            for cluster in clusters:
                try:
                    self.stats['total_processed'] += len(cluster)
                    
                    # Process the cluster (1 API call for all courts in cluster)
                    cluster_results = self.process_cluster(cluster)
                    all_successful_data.extend(cluster_results)
                    
                    # Process database batch when we have enough records
                    while len(all_successful_data) >= self.batch_size:
                        batch_to_process = all_successful_data[:self.batch_size]
                        all_successful_data = all_successful_data[self.batch_size:]
                        
                        # Process database batch
                        db_results = self.db_ops.upsert_court_batch(batch_to_process)
                        
                        if db_results['error_count'] > 0:
                            self.stats['database_failed'] += db_results['error_count']
                            self.stats['successful'] -= db_results['error_count']
                            self.stats['skipped'] += db_results['error_count']
                        
                        logger.info(json.dumps({
                            'event': 'database_batch_processed',
                            'batch_size': len(batch_to_process),
                            'db_success': db_results['success_count'],
                            'db_errors': db_results['error_count']
                        }))
                    
                except Exception as e:
                    logger.error(json.dumps({
                        'event': 'cluster_batch_error',
                        'cluster_size': len(cluster),
                        'error': str(e)
                    }))
                    self.stats['skipped'] += len(cluster)
            
            # Process remaining records
            if all_successful_data:
                db_results = self.db_ops.upsert_court_batch(all_successful_data)
                
                if db_results['error_count'] > 0:
                    self.stats['database_failed'] += db_results['error_count']
                    self.stats['successful'] -= db_results['error_count']
                    self.stats['skipped'] += db_results['error_count']
                
                logger.info(json.dumps({
                    'event': 'final_database_batch_processed',
                    'batch_size': len(all_successful_data),
                    'db_success': db_results['success_count'],
                    'db_errors': db_results['error_count']
                }))
            
            # Step 3: Populate cluster metadata for frontend
            logger.info(json.dumps({
                'event': 'cluster_metadata_population_started'
            }))
            
            try:
                from populate_cluster_metadata import ClusterMetadataPopulator
                
                populator = ClusterMetadataPopulator(self.connection_string, max_distance_km=0.05)
                cluster_summary = populator.populate_all_cluster_metadata()
                
                logger.info(json.dumps({
                    'event': 'cluster_metadata_population_completed',
                    'cluster_summary': cluster_summary
                }))
                
            except Exception as e:
                logger.error(json.dumps({
                    'event': 'cluster_metadata_population_error',
                    'error': str(e)
                }))
                # Continue even if cluster metadata fails
            
            # Add individual court names for clustered courts
            logger.info(json.dumps({
                'event': 'adding_individual_court_names',
                'message': 'Starting individual court name assignment'
            }))
            
            individual_names_added = self.add_individual_court_names()
            
            self.stats['end_time'] = datetime.now()
            processing_time = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            
            # Final statistics
            final_stats = {
                'total_features': total_features,
                'total_processed': self.stats['total_processed'],
                'successful': self.stats['successful'],
                'validation_failed': self.stats['validation_failed'],
                'geocoding_failed': self.stats['geocoding_failed'],
                'database_failed': self.stats['database_failed'],
                'skipped': self.stats['skipped'],
                'clusters_created': self.stats['clusters_created'],
                'api_calls_saved': self.stats['api_calls_saved'],
                'individual_names_added': individual_names_added,
                'processing_time_seconds': processing_time,
                'features_per_second': round(self.stats['total_processed'] / processing_time, 2) if processing_time > 0 else 0,
                'success_rate': round((self.stats['successful'] / self.stats['total_processed']) * 100, 2) if self.stats['total_processed'] > 0 else 0,
                'clustering_efficiency': round((self.stats['api_calls_saved'] / total_features) * 100, 1) if total_features > 0 else 0,
                'frontend_ready': True
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
            # This handles cases where a location has multiple clusters of the same sport
            cursor.execute("""
                SELECT photon_name, sport, COUNT(*) as total_courts
                FROM courts 
                WHERE cluster_id IS NOT NULL AND photon_name IS NOT NULL
                GROUP BY photon_name, sport
                HAVING COUNT(*) > 1
                ORDER BY photon_name, sport
            """)
            
            location_sports = cursor.fetchall()
            logger.info(f"Found {len(location_sports)} location-sport combinations with multiple courts")
            
            total_updated = 0
            
            for photon_name, sport, total_courts in location_sports:
                # Get all courts for this location-sport combination, ordered by id
                cursor.execute("""
                    SELECT id, osm_id, cluster_id
                    FROM courts 
                    WHERE photon_name = %s AND sport = %s
                    ORDER BY id
                """, (photon_name, sport))
                
                courts = cursor.fetchall()
                
                # Assign sequential individual court names across ALL clusters
                for i, (court_id, osm_id, cluster_id) in enumerate(courts, 1):
                    individual_name = f"Court {i}"
                    
                    cursor.execute("""
                        UPDATE courts 
                        SET individual_court_name = %s
                        WHERE id = %s
                    """, (individual_name, court_id))
                    
                    total_updated += 1
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(json.dumps({
                'event': 'individual_court_names_added',
                'total_updated': total_updated,
                'location_sports_processed': len(location_sports)
            }))
            
            return total_updated
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'individual_court_names_error',
                'error': str(e)
            }))
            return 0

# Example usage
if __name__ == "__main__":
    # Example connection string (replace with your actual connection details)
    connection_string = "postgresql://user:password@localhost:5432/courtpulse"
    
    # Initialize pipeline
    pipeline = CourtProcessingPipeline(connection_string, batch_size=100)
    
    # Process GeoJSON file
    async def run_pipeline():
        try:
            results = await pipeline.process_geojson_file('export.geojson', max_features=15)  # Test with 15 features
            print("Pipeline Results:", json.dumps(results, indent=2, default=str))
        except Exception as e:
            print(f"Pipeline failed: {e}")
    
    asyncio.run(run_pipeline())
