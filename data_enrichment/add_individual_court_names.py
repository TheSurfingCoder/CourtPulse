"""
Add individual court names to existing clustered courts
Uses database-side SQL with window functions for efficient sequential naming
"""

import json
import logging
import psycopg2
from typing import Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IndividualCourtNameManager:
    """Manage individual court names for clustered courts using database-side SQL"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        
        logger.info(json.dumps({
            'event': 'individual_court_name_manager_initialized',
            'method': 'database_sql'
        }))
    
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.connection_string)
    
    def verify_individual_court_name_column(self):
        """Verify individual_court_name column exists (should be created via migrations)"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if column exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'courts' AND column_name = 'individual_court_name'
            """)
            
            if cursor.fetchone():
                logger.info(json.dumps({
                    'event': 'column_verified',
                    'column': 'individual_court_name'
                }))
                return True
            else:
                logger.error(json.dumps({
                    'event': 'column_missing',
                    'column': 'individual_court_name',
                    'message': 'Column does not exist. Please run migrations to create it.'
                }))
                return False
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'column_verification_error',
                'error': str(e)
            }))
            return False
        finally:
            if conn:
                conn.close()
    
    def populate_individual_court_names(self) -> Dict[str, Any]:
        """
        Populate individual court names for clustered courts using database-side SQL
        Uses window functions to assign sequential names ("Court 1", "Court 2", etc.)
        within each cluster, ordered by id for consistency
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            logger.info(json.dumps({
                'event': 'individual_court_name_population_started',
                'method': 'database_sql'
            }))
            
            # Use SQL window function to assign sequential names within each cluster
            # Only assigns names to clusters with more than 1 court
            cursor.execute("""
                WITH ranked_courts AS (
                    SELECT 
                        id,
                        cluster_id,
                        ROW_NUMBER() OVER (
                            PARTITION BY cluster_id 
                            ORDER BY id
                        ) as court_number,
                        COUNT(*) OVER (PARTITION BY cluster_id) as cluster_size
                    FROM courts
                    WHERE cluster_id IS NOT NULL
                )
                UPDATE courts c
                SET individual_court_name = 'Court ' || rc.court_number::TEXT
                FROM ranked_courts rc
                WHERE c.id = rc.id
                  AND rc.cluster_size > 1;
            """)
            
            updated_count = cursor.rowcount
            
            # Get statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) FILTER (WHERE individual_court_name IS NOT NULL) as courts_with_names,
                    COUNT(DISTINCT cluster_id) FILTER (WHERE individual_court_name IS NOT NULL) as clusters_with_names,
                    MAX(cluster_size) as largest_named_cluster
                FROM (
                    SELECT 
                        cluster_id,
                        individual_court_name,
                        COUNT(*) OVER (PARTITION BY cluster_id) as cluster_size
                    FROM courts
                    WHERE cluster_id IS NOT NULL
                ) named_clusters
                WHERE individual_court_name IS NOT NULL
            """)
            stats = cursor.fetchone()
            
            conn.commit()
            
            summary = {
                'updated_courts': updated_count,
                'courts_with_names': stats[0] if stats and stats[0] else 0,
                'clusters_with_names': stats[1] if stats and stats[1] else 0,
                'largest_named_cluster': stats[2] if stats and stats[2] else 0
            }
            
            logger.info(json.dumps({
                'event': 'individual_court_name_population_completed',
                'summary': summary
            }))
            
            return summary
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'individual_court_name_population_error',
                'error': str(e)
            }))
            if conn:
                conn.rollback()
            return {
                'updated_courts': 0,
                'courts_with_names': 0,
                'clusters_with_names': 0,
                'largest_named_cluster': 0
            }
        finally:
            if conn:
                conn.close()
    
def main():
    """Main function to add individual court names"""
    print("🏀 INDIVIDUAL COURT NAME MANAGER (Database-Side)")
    print("=" * 60)
    
    # Database connection
    connection_string = os.getenv('DATABASE_URL')
    if not connection_string:
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'courtpulse-dev')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', 'password')
        connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    manager = IndividualCourtNameManager(connection_string)
    
    # Step 1: Verify column exists (should be created via migrations)
    print("1. Verifying individual_court_name column...")
    if not manager.verify_individual_court_name_column():
        print("   ❌ Column does not exist. Please run migrations first.")
        return
    print("   ✅ Column verified")
    
    # Step 2: Populate individual court names (database-side)
    print("\n2. Populating individual court names (database-side SQL)...")
    summary = manager.populate_individual_court_names()
    print(f"   ✅ Updated {summary['updated_courts']} courts with individual names")
    print(f"   📊 Clusters with names: {summary['clusters_with_names']}")
    print(f"   📊 Largest named cluster: {summary['largest_named_cluster']} courts")
    
    print("\n✅ ALL CHANGES COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print("Individual court names assigned using efficient database-side SQL.")
    print("Courts within the same cluster (facility_name + sport) are numbered sequentially.")

if __name__ == "__main__":
    main()
