"""
Optimized court data processing pipeline with controlled parallelism
Processes features in chunks with rate limiting for maximum performance
"""

import json
import logging
import time
import asyncio
from typing import Dict, Any, List, Tuple, Optional, AsyncGenerator
from datetime import datetime
import os
import sys

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from validation import CourtDataValidator, ValidationError
from data_mapper import CourtDataMapper
from database_operations import DatabaseManager, CourtDatabaseOperations
from async_photon_geocoding import AsyncPhotonGeocodingProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OptimizedCourtPipeline:
    """Optimized pipeline with controlled parallelism for maximum performance"""
    
    def __init__(self, connection_string: str, 
                 concurrent_features: int = 20, 
                 db_batch_size: int = 100,
                 max_api_connections: int = 50):
        self.connection_string = connection_string
        self.concurrent_features = concurrent_features
        self.db_batch_size = db_batch_size
        self.max_api_connections = max_api_connections
        
        # Initialize components
        self.validator = CourtDataValidator()
        self.mapper = CourtDataMapper()
        self.db_manager = DatabaseManager(connection_string)
        self.db_ops = CourtDatabaseOperations(self.db_manager)
        self.geocoding_provider = AsyncPhotonGeocodingProvider(max_concurrent=max_api_connections)
        
        # Statistics
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'validation_failed': 0,
            'geocoding_failed': 0,
            'database_failed': 0,
            'skipped': 0,
            'chunks_processed': 0,
            'db_batches_processed': 0,
            'start_time': None,
            'end_time': None
        }
        
        logger.info(json.dumps({
            'event': 'optimized_pipeline_initialized',
            'concurrent_features': concurrent_features,
            'db_batch_size': db_batch_size,
            'max_api_connections': max_api_connections
        }))
    
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
    
    async def process_single_court(self, feature: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Process a single court feature through the entire pipeline"""
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
                    
                    # Get name from Photon (async with parallel API calls)
                    photon_name, photon_data = await self.geocoding_provider.reverse_geocode(total_lat, total_lon)
                    
                    if not photon_name:
                        self.stats['geocoding_failed'] += 1
                        return False, "Geocoding failed", None
                    
                    # Calculate distance if we have the data
                    distance_km = 0.0
                    if photon_data and 'geometry' in photon_data:
                        coords = photon_data['geometry'].get('coordinates', [0, 0])
                        result_lon, result_lat = coords[0], coords[1]
                        distance_km = self.geocoding_provider._calculate_distance(
                            total_lat, total_lon, result_lat, result_lon
                        )
                    
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
    
    async def process_chunk(self, features_chunk: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a chunk of features in parallel"""
        chunk_start_time = time.time()
        
        logger.info(json.dumps({
            'event': 'processing_chunk',
            'chunk_size': len(features_chunk),
            'concurrent_features': self.concurrent_features
        }))
        
        # Process all features in chunk simultaneously
        tasks = [self.process_single_court(feature) for feature in features_chunk]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect successful results
        successful_data = []
        
        for i, result in enumerate(results):
            feature = features_chunk[i]
            osm_id = feature.get('properties', {}).get('osm_id') or feature.get('properties', {}).get('@id', 'unknown')
            
            self.stats['total_processed'] += 1
            
            if isinstance(result, Exception):
                self.stats['skipped'] += 1
                logger.error(json.dumps({
                    'event': 'chunk_processing_error',
                    'osm_id': osm_id,
                    'error': str(result)
                }))
            else:
                success, message, mapped_data = result
                
                if success and mapped_data:
                    successful_data.append(mapped_data)
                    self.stats['successful'] += 1
                else:
                    self.stats['skipped'] += 1
                    logger.warning(json.dumps({
                        'event': 'chunk_feature_failed',
                        'osm_id': osm_id,
                        'error': message
                    }))
        
        chunk_time = time.time() - chunk_start_time
        self.stats['chunks_processed'] += 1
        
        logger.info(json.dumps({
            'event': 'chunk_completed',
            'chunk_number': self.stats['chunks_processed'],
            'chunk_size': len(features_chunk),
            'successful': len(successful_data),
            'failed': len(features_chunk) - len(successful_data),
            'chunk_time_seconds': round(chunk_time, 2),
            'features_per_second': round(len(features_chunk) / chunk_time, 2)
        }))
        
        return successful_data
    
    async def process_features_in_chunks(self, features: List[Dict[str, Any]]) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Process features in chunks, yielding results as they complete"""
        total_features = len(features)
        
        for i in range(0, total_features, self.concurrent_features):
            chunk_end = min(i + self.concurrent_features, total_features)
            features_chunk = features[i:chunk_end]
            
            # Log progress
            progress_percentage = round((i / total_features) * 100, 1)
            logger.info(json.dumps({
                'event': 'starting_chunk',
                'chunk_number': (i // self.concurrent_features) + 1,
                'chunk_start': i + 1,
                'chunk_end': chunk_end,
                'total_features': total_features,
                'progress_percentage': progress_percentage
            }))
            
            # Process chunk in parallel
            chunk_results = await self.process_chunk(features_chunk)
            
            yield chunk_results
    
    async def process_geojson_file(self, file_path: str, max_features: Optional[int] = None) -> Dict[str, Any]:
        """Process entire GeoJSON file with controlled parallelism"""
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
            expected_chunks = (total_features + self.concurrent_features - 1) // self.concurrent_features
            
            logger.info(json.dumps({
                'event': 'optimized_pipeline_started',
                'total_features': total_features,
                'concurrent_features': self.concurrent_features,
                'expected_chunks': expected_chunks,
                'db_batch_size': self.db_batch_size,
                'max_api_connections': self.max_api_connections
            }))
            
            # Process features in chunks and batch database operations
            db_buffer = []
            
            async for chunk_results in self.process_features_in_chunks(features):
                # Add chunk results to database buffer
                db_buffer.extend(chunk_results)
                
                # Process database batch when buffer is full
                while len(db_buffer) >= self.db_batch_size:
                    batch_to_process = db_buffer[:self.db_batch_size]
                    db_buffer = db_buffer[self.db_batch_size:]
                    
                    await self.process_database_batch(batch_to_process)
            
            # Process remaining records in buffer
            if db_buffer:
                await self.process_database_batch(db_buffer)
            
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
                'chunks_processed': self.stats['chunks_processed'],
                'db_batches_processed': self.stats['db_batches_processed'],
                'processing_time_seconds': processing_time,
                'features_per_second': round(self.stats['total_processed'] / processing_time, 2) if processing_time > 0 else 0,
                'success_rate': round((self.stats['successful'] / self.stats['total_processed']) * 100, 2) if self.stats['total_processed'] > 0 else 0,
                'concurrent_features': self.concurrent_features,
                'max_api_connections': self.max_api_connections
            }
            
            logger.info(json.dumps({
                'event': 'optimized_pipeline_completed',
                'final_stats': final_stats
            }))
            
            return final_stats
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'optimized_pipeline_error',
                'error': str(e)
            }))
            raise
        finally:
            # Clean up database connections
            self.db_manager.close_all_connections()
    
    async def process_database_batch(self, batch_data: List[Dict[str, Any]]):
        """Process a batch of data for database insertion"""
        if not batch_data:
            return
        
        try:
            logger.info(json.dumps({
                'event': 'processing_database_batch',
                'batch_size': len(batch_data),
                'batch_number': self.stats['db_batches_processed'] + 1
            }))
            
            # Use asyncio to run the synchronous database operation in a thread pool
            db_results = await asyncio.get_event_loop().run_in_executor(
                None, 
                self.db_ops.upsert_court_batch, 
                batch_data
            )
            
            self.stats['db_batches_processed'] += 1
            
            # Update statistics based on database results
            if db_results['error_count'] > 0:
                self.stats['database_failed'] += db_results['error_count']
                self.stats['successful'] -= db_results['error_count']
                self.stats['skipped'] += db_results['error_count']
            
            logger.info(json.dumps({
                'event': 'database_batch_completed',
                'batch_number': self.stats['db_batches_processed'],
                'batch_size': len(batch_data),
                'db_success': db_results['success_count'],
                'db_errors': db_results['error_count']
            }))
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'database_batch_error',
                'batch_size': len(batch_data),
                'error': str(e)
            }))
            self.stats['database_failed'] += len(batch_data)
            self.stats['successful'] -= len(batch_data)
            self.stats['skipped'] += len(batch_data)
    
    def chunks(self, lst: List, n: int):
        """Yield successive n-sized chunks from lst"""
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

# Example usage and testing
async def test_optimized_pipeline():
    """Test the optimized pipeline"""
    
    # Database connection string
    connection_string = os.getenv('DATABASE_URL')
    if not connection_string:
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'courtpulse-dev')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', 'password')
        connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Initialize optimized pipeline
    pipeline = OptimizedCourtPipeline(
        connection_string=connection_string,
        concurrent_features=20,    # Process 20 features per chunk
        db_batch_size=100,         # Database batches of 100
        max_api_connections=50     # Max 50 simultaneous API calls
    )
    
    try:
        # Test with 50 features to validate the approach
        logger.info(json.dumps({
            'event': 'optimized_test_started',
            'test_features': 50
        }))
        
        results = await pipeline.process_geojson_file(
            file_path='export.geojson',
            max_features=50
        )
        
        # Print results
        print("\n" + "="*70)
        print("🚀 OPTIMIZED PIPELINE TEST RESULTS")
        print("="*70)
        print(f"Total Features: {results['total_features']}")
        print(f"Successfully Processed: {results['successful']}")
        print(f"Chunks Processed: {results['chunks_processed']}")
        print(f"DB Batches Processed: {results['db_batches_processed']}")
        print(f"Success Rate: {results['success_rate']}%")
        print(f"Processing Time: {results['processing_time_seconds']:.2f} seconds")
        print(f"Features/Second: {results['features_per_second']:.2f}")
        print(f"Concurrent Features: {results['concurrent_features']}")
        print(f"Max API Connections: {results['max_api_connections']}")
        print("="*70)
        
        return results
        
    except Exception as e:
        logger.error(json.dumps({
            'event': 'optimized_test_error',
            'error': str(e)
        }))
        print(f"❌ Optimized pipeline test failed: {e}")
        return None

if __name__ == "__main__":
    results = asyncio.run(test_optimized_pipeline())
    if results and results['success_rate'] >= 80:
        print("✅ Optimized pipeline ready for full dataset!")
    else:
        print("❌ Optimized pipeline needs debugging")


