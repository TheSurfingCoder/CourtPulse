"""
Populate cluster metadata for courts based on facility_name and sport
Groups courts with the same facility_name AND sport into clusters by assigning shared cluster_id (UUID)
Runs entirely in the database using SQL for efficiency
"""

import json
import logging
import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClusterMetadataPopulator:
    """Populates cluster metadata for courts based on facility_name and sport using SQL"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        
        logger.info(json.dumps({
            'event': 'cluster_metadata_populator_initialized',
            'method': 'database_sql'
        }))
    
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.connection_string)
    
    def populate_cluster_metadata(self) -> Dict[str, Any]:
        """
        Populate cluster_id for courts based on facility_name and sport
        Uses SQL to efficiently group and assign UUIDs in the database
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            logger.info(json.dumps({
                'event': 'cluster_metadata_population_started',
                'method': 'sql_based'
            }))
            
            # Step 1: Get statistics before clustering
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_courts,
                    COUNT(DISTINCT facility_name) as unique_facilities,
                    COUNT(DISTINCT (facility_name, sport)) as unique_facility_sport_combos,
                    COUNT(*) FILTER (WHERE facility_name IS NOT NULL) as courts_with_facility
                FROM osm_courts_temp;
            """)
            stats_before = cursor.fetchone()
            
            # Step 2: Assign cluster_id based on effective facility_name AND sport using SQL
            # Use court's own OSM name if available, else use containing facility name
            # This creates a UUID for each unique (effective_facility_name, sport) combination
            cursor.execute("""
                WITH facility_sport_clusters AS (
                    SELECT DISTINCT 
                        COALESCE(NULLIF(tags->>'name', ''), facility_name) as effective_facility_name,
                        sport,
                        gen_random_uuid() as cluster_id
                    FROM osm_courts_temp
                    WHERE COALESCE(NULLIF(tags->>'name', ''), facility_name) IS NOT NULL
                      AND sport IS NOT NULL
                )
                UPDATE osm_courts_temp oc
                SET cluster_id = fsc.cluster_id
                FROM facility_sport_clusters fsc
                WHERE COALESCE(NULLIF(oc.tags->>'name', ''), oc.facility_name) = fsc.effective_facility_name
                  AND oc.sport = fsc.sport
                  AND COALESCE(NULLIF(oc.tags->>'name', ''), oc.facility_name) IS NOT NULL
                  AND oc.sport IS NOT NULL;
            """)
            
            updated_count = cursor.rowcount
            
            # Step 3: Get statistics after clustering
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT cluster_id) as total_clusters,
                    COUNT(*) FILTER (WHERE cluster_id IS NOT NULL) as courts_with_cluster,
                    MAX(cluster_size) as largest_cluster_size
                FROM (
                    SELECT 
                        cluster_id,
                        COUNT(*) OVER (PARTITION BY cluster_id) as cluster_size
                    FROM osm_courts_temp
                    WHERE cluster_id IS NOT NULL
                ) cluster_stats;
            """)
            stats_after = cursor.fetchone()
            
            # Step 4: Get multi-court cluster count
            cursor.execute("""
                SELECT COUNT(*) as multi_court_clusters
                FROM (
                    SELECT cluster_id, COUNT(*) as court_count
                    FROM osm_courts_temp
                    WHERE cluster_id IS NOT NULL
                    GROUP BY cluster_id
                    HAVING COUNT(*) > 1
                ) multi_clusters;
            """)
            multi_cluster_stats = cursor.fetchone()
            
            conn.commit()
            
            summary = {
                'total_courts': stats_before['total_courts'],
                'unique_facilities': stats_before['unique_facilities'],
                'unique_facility_sport_combos': stats_before['unique_facility_sport_combos'],
                'courts_with_facility': stats_before['courts_with_facility'],
                'updated_courts': updated_count,
                'total_clusters': stats_after['total_clusters'] or 0,
                'courts_with_cluster': stats_after['courts_with_cluster'] or 0,
                'multi_court_clusters': multi_cluster_stats['multi_court_clusters'] or 0,
                'largest_cluster_size': stats_after['largest_cluster_size'] or 0
            }
            
            logger.info(json.dumps({
                'event': 'cluster_metadata_population_completed',
                'summary': summary
            }))
            
            return summary
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(json.dumps({
                'event': 'cluster_metadata_population_error',
                'error': str(e)
            }))
            raise
        finally:
            if conn:
                conn.close()
    
    def transfer_courts_to_production(self) -> Dict[str, Any]:
        """
        Transfer courts from osm_courts_temp to courts table
        Inserts new courts or updates existing ones by osm_id
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            logger.info(json.dumps({
                'event': 'courts_transfer_started',
                'source_table': 'osm_courts_temp',
                'target_table': 'courts'
            }))
            
            # Insert/update courts from staging to production table
            cursor.execute("""
                INSERT INTO courts (
                    osm_id, sport, geom, centroid, fallback_name, 
                    surface_type, cluster_id, facility_name, hoops, region, school, is_public
                )
                SELECT 
                    oc.osm_id,
                    oc.sport::sport_type,
                    oc.geom,
                    oc.centroid::geography,
                    -- Generic sport-based fallback name
                    CASE 
                        WHEN oc.sport = 'basketball' AND oc.tags->>'hoops' ~ '^[0-9]+$'
                        THEN 'basketball court (' || (oc.tags->>'hoops')::integer || ' hoops)'
                        WHEN oc.sport = 'basketball'
                        THEN 'basketball court'
                        WHEN oc.sport = 'tennis'
                        THEN 'tennis court'
                        WHEN oc.sport = 'soccer'
                        THEN 'soccer field'
                        WHEN oc.sport = 'volleyball'
                        THEN 'volleyball court'
                        WHEN oc.sport = 'pickleball'
                        THEN 'pickleball court'
                        ELSE oc.sport || ' court'
                    END as fallback_name,
                    CASE 
                        WHEN oc.tags->>'surface' IN ('asphalt', 'concrete', 'wood', 'synthetic', 'clay', 'grass') 
                        THEN (oc.tags->>'surface')::surface_type_enum
                        ELSE NULL
                    END as surface_type,
                    oc.cluster_id,
                    -- Use court's own OSM name as facility_name if available, else use containing facility
                    COALESCE(NULLIF(oc.tags->>'name', ''), oc.facility_name) as facility_name,
                    CASE 
                        WHEN oc.tags->>'hoops' ~ '^[0-9]+$' 
                        THEN (oc.tags->>'hoops')::integer
                        ELSE NULL
                    END as hoops,
                    'sf_bay' as region,
                    CASE 
                        WHEN EXISTS (
                            SELECT 1 FROM osm_facilities ofac
                            WHERE ofac.id = oc.facility_id
                            AND ofac.facility_type IN ('school', 'university', 'college')
                        ) THEN true
                        ELSE false
                    END as school,
                    -- Extract access tag from OSM: public/yes = true, private/no = false, else NULL
                    CASE 
                        WHEN LOWER(oc.tags->>'access') IN ('public', 'yes') THEN true
                        WHEN LOWER(oc.tags->>'access') IN ('private', 'no') THEN false
                        ELSE NULL
                    END as is_public
                FROM osm_courts_temp oc
                ON CONFLICT (osm_id) DO UPDATE SET
                    sport = EXCLUDED.sport,
                    geom = EXCLUDED.geom,
                    centroid = EXCLUDED.centroid,
                    fallback_name = EXCLUDED.fallback_name,
                    surface_type = EXCLUDED.surface_type,
                    cluster_id = EXCLUDED.cluster_id,
                    facility_name = EXCLUDED.facility_name,
                    hoops = EXCLUDED.hoops,
                    school = EXCLUDED.school,
                    is_public = EXCLUDED.is_public,
                    updated_at = NOW();
            """)
            
            inserted_count = cursor.rowcount
            
            conn.commit()
            
            logger.info(json.dumps({
                'event': 'courts_transfer_completed',
                'inserted_or_updated_courts': inserted_count
            }))
            
            return {'inserted_or_updated_courts': inserted_count}
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(json.dumps({
                'event': 'courts_transfer_error',
                'error': str(e)
            }))
            raise
        finally:
            if conn:
                conn.close()

    def transfer_cluster_ids_to_courts(self) -> Dict[str, Any]:
        """
        Transfer cluster_id from osm_courts_temp to courts table
        Matches courts by osm_id (updates existing rows only)
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            logger.info(json.dumps({
                'event': 'cluster_id_transfer_started',
                'source_table': 'osm_courts_temp',
                'target_table': 'courts'
            }))
            
            # Transfer cluster_id from staging to production table
            cursor.execute("""
                UPDATE courts c
                SET cluster_id = oc.cluster_id,
                    updated_at = NOW()
                FROM osm_courts_temp oc
                WHERE c.osm_id = oc.osm_id
                  AND oc.cluster_id IS NOT NULL;
            """)
            
            updated_count = cursor.rowcount
            
            conn.commit()
            
            logger.info(json.dumps({
                'event': 'cluster_id_transfer_completed',
                'updated_courts': updated_count
            }))
            
            return {'updated_courts': updated_count}
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(json.dumps({
                'event': 'cluster_id_transfer_error',
                'error': str(e)
            }))
            raise
        finally:
            if conn:
                conn.close()

def main():
    """Main function to populate cluster metadata"""
    
    # Database connection
    connection_string = os.getenv('DATABASE_URL')
    if not connection_string:
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'courtpulse-dev')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', 'password')
        connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    print("🗺️  POPULATING CLUSTER METADATA (Database-Side)")
    print("="*60)
    print("This will assign cluster_id to courts based on facility_name AND sport.")
    print("Clustering happens entirely in the database using SQL for efficiency.")
    print()
    
    try:
        populator = ClusterMetadataPopulator(connection_string)
        
        # Step 1: Populate cluster_id in staging table
        summary = populator.populate_cluster_metadata()
        
        print("📊 CLUSTER METADATA RESULTS (osm_courts_temp):")
        print(f"   Total Courts: {summary['total_courts']}")
        print(f"   Unique Facilities: {summary['unique_facilities']}")
        print(f"   Unique Facility-Sport Combos: {summary['unique_facility_sport_combos']}")
        print(f"   Courts with Facility: {summary['courts_with_facility']}")
        print(f"   Updated Courts: {summary['updated_courts']}")
        print(f"   Total Clusters: {summary['total_clusters']}")
        print(f"   Multi-Court Clusters: {summary['multi_court_clusters']}")
        print(f"   Largest Cluster: {summary['largest_cluster_size']} courts")
        print()
        
        # Step 2: Transfer to production table
        transfer_summary = populator.transfer_cluster_ids_to_courts()
        print(f"📤 TRANSFERRED TO COURTS TABLE:")
        print(f"   Updated Courts: {transfer_summary['updated_courts']}")
        print()
        
        print("✅ Cluster metadata populated successfully!")
        print("🗺️  Frontend can now display clustered markers.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error populating cluster metadata: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
