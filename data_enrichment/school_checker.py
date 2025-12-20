"""
Utility to check if a court is within a school facility
Uses PostGIS spatial queries to determine if a court's geometry is contained within a school
"""

import json
import logging
import psycopg2
from typing import Optional, Dict, Any
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SchoolChecker:
    """Checks if courts are within school facilities using PostGIS"""
    
    def __init__(self, connection_string: str):
        """
        Initialize school checker with database connection
        
        Args:
            connection_string: PostgreSQL connection string
        """
        self.conn = psycopg2.connect(connection_string)
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        
        logger.info(json.dumps({
            'event': 'school_checker_initialized'
        }))
    
    def is_court_within_school(self, court_geometry_wkt: str) -> Optional[Dict[str, Any]]:
        """
        Check if a court geometry is contained within a school facility
        
        Args:
            court_geometry_wkt: Well-Known Text representation of court geometry (Point or Polygon)
        
        Returns:
            Dict with school info if court is within a school, None otherwise
            Format: {'school_id': int, 'school_name': str, 'facility_type': str}
        """
        try:
            # Query for schools that contain this court geometry
            # Check both exact containment and centroid containment for flexibility
            self.cursor.execute("""
                SELECT 
                    id,
                    name,
                    facility_type,
                    osm_id
                FROM osm_facilities
                WHERE facility_type IN ('school', 'university', 'college')
                  AND (
                    ST_Contains(geom, ST_GeomFromText(%s, 4326))
                    OR ST_Contains(geom, ST_Centroid(ST_GeomFromText(%s, 4326)))
                  )
                LIMIT 1;
            """, (court_geometry_wkt, court_geometry_wkt))
            
            result = self.cursor.fetchone()
            
            if result:
                school_info = {
                    'school_id': result['id'],
                    'school_name': result['name'],
                    'facility_type': result['facility_type'],
                    'osm_id': result['osm_id']
                }
                
                logger.info(json.dumps({
                    'event': 'court_within_school_found',
                    'school_name': result['name'],
                    'facility_type': result['facility_type']
                }))
                
                return school_info
            
            return None
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'school_check_error',
                'error': str(e)
            }))
            return None
    
    def update_court_school_status(self, court_osm_id: str, court_geometry_wkt: str) -> bool:
        """
        Update the school status for a court in osm_courts_temp table
        
        Args:
            court_osm_id: OSM ID of the court
            court_geometry_wkt: Well-Known Text representation of court geometry
        
        Returns:
            True if court is within a school and was updated, False otherwise
        """
        school_info = self.is_court_within_school(court_geometry_wkt)
        
        if school_info:
            try:
                # Only update the court's facility info if:
                # 1. The found school has a name, OR
                # 2. The court currently has no facility_name
                # This prevents overwriting named facilities with unnamed schools
                if school_info['school_name']:
                    self.cursor.execute("""
                        UPDATE osm_courts_temp
                        SET facility_id = %s,
                            facility_name = %s
                        WHERE osm_id = %s
                          AND (facility_id IS NULL OR facility_id != %s);
                    """, (
                        school_info['school_id'],
                        school_info['school_name'],
                        court_osm_id,
                        school_info['school_id']
                    ))
                else:
                    # Found unnamed school - only update if court has no facility_name
                    self.cursor.execute("""
                        UPDATE osm_courts_temp
                        SET facility_id = %s,
                            facility_name = %s
                        WHERE osm_id = %s
                          AND facility_name IS NULL;
                    """, (
                        school_info['school_id'],
                        school_info['school_name'],
                        court_osm_id
                    ))
                
                self.conn.commit()
                
                logger.info(json.dumps({
                    'event': 'court_school_status_updated',
                    'court_osm_id': court_osm_id,
                    'school_name': school_info['school_name']
                }))
                
                return True
                
            except Exception as e:
                logger.error(json.dumps({
                    'event': 'court_school_status_update_error',
                    'court_osm_id': court_osm_id,
                    'error': str(e)
                }))
                self.conn.rollback()
                return False
        
        return False
    
    def batch_check_courts_in_schools(self) -> Dict[str, Any]:
        """
        Check all courts in osm_courts_temp and update school status
        
        Returns:
            Dict with summary statistics
        """
        try:
            # Get all courts that don't have a facility match or need re-checking
            self.cursor.execute("""
                SELECT 
                    osm_id,
                    ST_AsText(geom) as geometry_wkt
                FROM osm_courts_temp
                WHERE geom IS NOT NULL;
            """)
            
            courts = self.cursor.fetchall()
            total_courts = len(courts)
            courts_in_schools = 0
            
            for court in courts:
                school_info = self.is_court_within_school(court['geometry_wkt'])
                
                if school_info:
                    # Only update if:
                    # 1. The found school has a name, OR
                    # 2. The court currently has no facility_name
                    # This prevents overwriting named facilities with unnamed schools
                    if school_info['school_name']:
                        self.cursor.execute("""
                            UPDATE osm_courts_temp
                            SET facility_id = %s,
                                facility_name = %s
                            WHERE osm_id = %s
                              AND (facility_id IS NULL OR facility_id != %s);
                        """, (
                            school_info['school_id'],
                            school_info['school_name'],
                            court['osm_id'],
                            school_info['school_id']
                        ))
                    else:
                        # Found unnamed school - only update if court has no facility_name
                        self.cursor.execute("""
                            UPDATE osm_courts_temp
                            SET facility_id = %s,
                                facility_name = %s
                            WHERE osm_id = %s
                              AND facility_name IS NULL;
                        """, (
                            school_info['school_id'],
                            school_info['school_name'],
                            court['osm_id']
                        ))
                    courts_in_schools += 1
            
            self.conn.commit()
            
            summary = {
                'total_courts_checked': total_courts,
                'courts_in_schools': courts_in_schools,
                'courts_not_in_schools': total_courts - courts_in_schools
            }
            
            logger.info(json.dumps({
                'event': 'batch_school_check_completed',
                **summary
            }))
            
            return summary
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'batch_school_check_error',
                'error': str(e)
            }))
            self.conn.rollback()
            return {
                'total_courts_checked': 0,
                'courts_in_schools': 0,
                'courts_not_in_schools': 0,
                'error': str(e)
            }
    
    def close(self):
        """Close database connection"""
        self.cursor.close()
        self.conn.close()

# Example usage
if __name__ == "__main__":
    import os
    import sys
    
    connection_string = os.getenv('DATABASE_URL') or (sys.argv[1] if len(sys.argv) > 1 else None)
    
    if not connection_string:
        print("Error: DATABASE_URL environment variable not set, or provide as argument")
        print("Usage: python3 school_checker.py 'postgresql://user:pass@host:port/db'")
        sys.exit(1)
    
    checker = SchoolChecker(connection_string)
    
    # Example: Check a single court
    sample_geometry = "POINT(-122.4194 37.7749)"  # San Francisco coordinates
    result = checker.is_court_within_school(sample_geometry)
    
    if result:
        print(f"Court is within school: {result['school_name']} ({result['facility_type']})")
    else:
        print("Court is not within a school")
    
    # Example: Batch check all courts
    summary = checker.batch_check_courts_in_schools()
    print(f"\nBatch check summary:")
    print(f"  Total courts checked: {summary['total_courts_checked']}")
    print(f"  Courts in schools: {summary['courts_in_schools']}")
    print(f"  Courts not in schools: {summary['courts_not_in_schools']}")
    
    checker.close()
