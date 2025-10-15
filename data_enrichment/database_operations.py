"""
Database operations module for court data processing
Handles PostgreSQL connections, UPSERT operations, and batch processing
"""

import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self, connection_string: str, min_connections: int = 1, max_connections: int = 10):
        self.connection_string = connection_string
        self.pool = None
        self._create_connection_pool(min_connections, max_connections)
    
    def _create_connection_pool(self, min_connections: int, max_connections: int):
        """Create connection pool for database operations"""
        try:
            self.pool = SimpleConnectionPool(
                min_connections, max_connections, self.connection_string
            )
            logger.info(json.dumps({
                'event': 'connection_pool_created',
                'min_connections': min_connections,
                'max_connections': max_connections
            }))
        except Exception as e:
            logger.error(json.dumps({
                'event': 'connection_pool_error',
                'error': str(e)
            }))
            raise
    
    def get_connection(self):
        """Get connection from pool"""
        try:
            return self.pool.getconn()
        except Exception as e:
            logger.error(json.dumps({
                'event': 'get_connection_error',
                'error': str(e)
            }))
            raise
    
    def return_connection(self, connection):
        """Return connection to pool"""
        try:
            self.pool.putconn(connection)
        except Exception as e:
            logger.error(json.dumps({
                'event': 'return_connection_error',
                'error': str(e)
            }))
    
    def close_all_connections(self):
        """Close all connections in pool"""
        if self.pool:
            self.pool.closeall()

class CourtDatabaseOperations:
    """Handles court-specific database operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def create_geometry_from_geojson(self, geometry: Dict[str, Any]) -> str:
        """Convert GeoJSON geometry to PostGIS format"""
        try:
            # Convert to GeoJSON string
            geojson_str = json.dumps(geometry)
            
            # Use PostGIS function to create geometry
            return f"ST_GeomFromGeoJSON('{geojson_str}')"
        except Exception as e:
            logger.error(json.dumps({
                'event': 'geometry_conversion_error',
                'error': str(e)
            }))
            raise
    
    def calculate_centroid(self, geometry: Dict[str, Any]) -> str:
        """Calculate centroid from polygon geometry"""
        try:
            geojson_str = json.dumps(geometry)
            return f"ST_Centroid(ST_GeomFromGeoJSON('{geojson_str}'))::GEOGRAPHY"
        except Exception as e:
            logger.error(json.dumps({
                'event': 'centroid_calculation_error',
                'error': str(e)
            }))
            raise
    
    def upsert_court(self, court_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Upsert a single court record"""
        connection = None
        try:
            connection = self.db_manager.get_connection()
            cursor = connection.cursor()
            
            # Prepare the UPSERT query
            upsert_query = """
            INSERT INTO courts (
                osm_id, sport, hoops, geom, centroid, 
                photon_name, photon_distance_km, photon_source,
                fallback_name, surface_type, is_public, school
            ) VALUES (
                %(osm_id)s, %(sport)s, %(hoops)s, 
                ST_GeomFromGeoJSON(%(geom)s), 
                ST_Centroid(ST_GeomFromGeoJSON(%(geom)s))::GEOGRAPHY,
                %(photon_name)s, %(photon_distance_km)s, %(photon_source)s,
                %(fallback_name)s, %(surface_type)s, %(is_public)s, %(school)s
            )
            ON CONFLICT (osm_id) DO UPDATE SET
                sport = EXCLUDED.sport,
                hoops = EXCLUDED.hoops,
                geom = EXCLUDED.geom,
                centroid = EXCLUDED.centroid,
                photon_name = EXCLUDED.photon_name,
                photon_distance_km = EXCLUDED.photon_distance_km,
                photon_source = EXCLUDED.photon_source,
                fallback_name = EXCLUDED.fallback_name,
                surface_type = EXCLUDED.surface_type,
                school = EXCLUDED.school,
                is_public = EXCLUDED.is_public,
                updated_at = NOW()
            RETURNING id, osm_id;
            """
            
            # Execute the query
            cursor.execute(upsert_query, court_data)
            result = cursor.fetchone()
            
            connection.commit()
            
            logger.info(json.dumps({
                'event': 'court_upserted',
                'osm_id': court_data['osm_id'],
                'db_id': result[0] if result else None
            }))
            
            return True, "Success"
            
        except Exception as e:
            if connection:
                connection.rollback()
            
            error_msg = f"Database error for {court_data.get('osm_id', 'unknown')}: {str(e)}"
            logger.error(json.dumps({
                'event': 'court_upsert_error',
                'osm_id': court_data.get('osm_id'),
                'error': str(e)
            }))
            
            return False, error_msg
            
        finally:
            if connection:
                self.db_manager.return_connection(connection)
    
    def upsert_court_batch(self, courts_batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Upsert a batch of court records in a single transaction"""
        connection = None
        results = {
            'success_count': 0,
            'error_count': 0,
            'errors': [],
            'successful_osm_ids': [],
            'failed_osm_ids': []
        }
        
        try:
            connection = self.db_manager.get_connection()
            cursor = connection.cursor()
            
            # Start transaction
            cursor.execute("BEGIN;")
            
            for court_data in courts_batch:
                try:
                    # Prepare the UPSERT query for this court
                    upsert_query = """
                    INSERT INTO courts (
                        osm_id, sport, hoops, geom, centroid, 
                        photon_name, photon_distance_km, photon_source,
                        fallback_name, surface_type, is_public, school
                    ) VALUES (
                        %(osm_id)s, %(sport)s, %(hoops)s, 
                        ST_GeomFromGeoJSON(%(geom)s), 
                        ST_Centroid(ST_GeomFromGeoJSON(%(geom)s))::GEOGRAPHY,
                        %(photon_name)s, %(photon_distance_km)s, %(photon_source)s,
                        %(fallback_name)s, %(surface_type)s, %(is_public)s, %(school)s
                    )
                    ON CONFLICT (osm_id) DO UPDATE SET
                        sport = EXCLUDED.sport,
                        hoops = EXCLUDED.hoops,
                        geom = EXCLUDED.geom,
                        centroid = EXCLUDED.centroid,
                        photon_name = EXCLUDED.photon_name,
                        photon_distance_km = EXCLUDED.photon_distance_km,
                        photon_source = EXCLUDED.photon_source,
                        fallback_name = EXCLUDED.fallback_name,
                        surface_type = EXCLUDED.surface_type,
                        is_public = EXCLUDED.is_public,
                        school = EXCLUDED.school,
                        updated_at = NOW()
                    RETURNING id, osm_id;
                    """
                    
                    cursor.execute(upsert_query, court_data)
                    result = cursor.fetchone()
                    
                    results['success_count'] += 1
                    results['successful_osm_ids'].append(court_data['osm_id'])
                    
                    logger.debug(json.dumps({
                        'event': 'court_upserted_in_batch',
                        'osm_id': court_data['osm_id'],
                        'db_id': result[0] if result else None
                    }))
                    
                except Exception as e:
                    results['error_count'] += 1
                    results['failed_osm_ids'].append(court_data['osm_id'])
                    results['errors'].append({
                        'osm_id': court_data['osm_id'],
                        'error': str(e)
                    })
                    
                    logger.error(json.dumps({
                        'event': 'court_upsert_error_in_batch',
                        'osm_id': court_data['osm_id'],
                        'error': str(e)
                    }))
            
            # Commit the transaction
            cursor.execute("COMMIT;")
            
            logger.info(json.dumps({
                'event': 'batch_upsert_completed',
                'batch_size': len(courts_batch),
                'success_count': results['success_count'],
                'error_count': results['error_count']
            }))
            
        except Exception as e:
            if connection:
                cursor.execute("ROLLBACK;")
            
            logger.error(json.dumps({
                'event': 'batch_upsert_error',
                'batch_size': len(courts_batch),
                'error': str(e)
            }))
            
            # If the entire batch failed, mark all as errors
            results['error_count'] = len(courts_batch)
            results['success_count'] = 0
            results['failed_osm_ids'] = [court['osm_id'] for court in courts_batch]
            results['errors'].append({
                'osm_id': 'batch_error',
                'error': str(e)
            })
            
        finally:
            if connection:
                self.db_manager.return_connection(connection)
        
        return results
    
    def get_court_count(self) -> int:
        """Get total number of courts in database"""
        connection = None
        try:
            connection = self.db_manager.get_connection()
            cursor = connection.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM courts;")
            count = cursor.fetchone()[0]
            
            return count
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'get_court_count_error',
                'error': str(e)
            }))
            return 0
            
        finally:
            if connection:
                self.db_manager.return_connection(connection)
    
    def get_court_by_osm_id(self, osm_id: str) -> Optional[Dict[str, Any]]:
        """Get court by OSM ID"""
        connection = None
        try:
            connection = self.db_manager.get_connection()
            cursor = connection.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("SELECT * FROM courts WHERE osm_id = %s;", (osm_id,))
            result = cursor.fetchone()
            
            if result:
                return dict(result)
            return None
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'get_court_by_osm_id_error',
                'osm_id': osm_id,
                'error': str(e)
            }))
            return None
            
        finally:
            if connection:
                self.db_manager.return_connection(connection)

# Example usage
if __name__ == "__main__":
    # Example connection string (replace with your actual connection details)
    connection_string = "postgresql://user:password@localhost:5432/courtpulse"
    
    # Initialize database manager
    db_manager = DatabaseManager(connection_string)
    court_ops = CourtDatabaseOperations(db_manager)
    
    # Example court data
    sample_court = {
        'osm_id': 'way/12345',
        'sport': 'basketball',
        'hoops': 2,
        'geom': '{"type": "Polygon", "coordinates": [[[-122.4, 37.7], [-122.4, 37.8], [-122.3, 37.8], [-122.3, 37.7], [-122.4, 37.7]]]}',
        'photon_name': 'Test Court',
        'photon_distance_km': 0.05,
        'photon_source': 'search_api',
        'fallback_name': 'basketball court (2 hoops)',
        'surface_type': 'asphalt',
        'import_timestamp': datetime.now()
    }
    
    # Test upsert
    success, message = court_ops.upsert_court(sample_court)
    print(f"Upsert result: {success}, {message}")
    
    # Clean up
    db_manager.close_all_connections()
