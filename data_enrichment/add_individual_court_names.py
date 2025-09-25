"""
Add individual court names to existing clustered courts
"""

import json
import logging
import psycopg2
from typing import Dict, Any, List
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IndividualCourtNameManager:
    """Manage individual court names for clustered courts"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
    
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.connection_string)
    
    def add_individual_court_name_column(self):
        """Add individual_court_name column to courts table"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if column already exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'courts' AND column_name = 'individual_court_name'
            """)
            
            if cursor.fetchone():
                logger.info("individual_court_name column already exists")
                return True
            
            # Add the column
            cursor.execute("""
                ALTER TABLE courts 
                ADD COLUMN individual_court_name VARCHAR(255)
            """)
            
            conn.commit()
            logger.info("Added individual_court_name column to courts table")
            return True
            
        except Exception as e:
            logger.error(f"Error adding column: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
    
    def populate_individual_court_names(self):
        """Populate individual court names for clustered courts"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get all clusters with more than 1 court
            cursor.execute("""
                SELECT cluster_id, COUNT(*) as court_count
                FROM courts 
                WHERE cluster_id IS NOT NULL
                GROUP BY cluster_id
                HAVING COUNT(*) > 1
                ORDER BY cluster_id
            """)
            
            clusters = cursor.fetchall()
            logger.info(f"Found {len(clusters)} clusters with multiple courts")
            
            total_updated = 0
            
            for cluster_id, court_count in clusters:
                logger.info(f"Processing cluster {cluster_id} with {court_count} courts")
                
                # Get all courts in this cluster, ordered by id for consistent naming
                cursor.execute("""
                    SELECT id, osm_id, photon_name, enriched_name, fallback_name
                    FROM courts 
                    WHERE cluster_id = %s
                    ORDER BY id
                """, (cluster_id,))
                
                courts = cursor.fetchall()
                
                # Assign individual court names
                for i, (court_id, osm_id, photon_name, enriched_name, fallback_name) in enumerate(courts, 1):
                    individual_name = f"Court {i}"
                    
                    cursor.execute("""
                        UPDATE courts 
                        SET individual_court_name = %s
                        WHERE id = %s
                    """, (individual_name, court_id))
                    
                    logger.info(f"  Updated court {court_id} ({osm_id}) to '{individual_name}'")
                    total_updated += 1
            
            conn.commit()
            logger.info(f"Successfully updated {total_updated} courts with individual names")
            return total_updated
            
        except Exception as e:
            logger.error(f"Error populating individual names: {e}")
            if conn:
                conn.rollback()
            return 0
        finally:
            if conn:
                conn.close()
    
    def clean_photon_names(self):
        """Remove court count from existing photon_name values"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Find photon_name values that contain court counts
            cursor.execute("""
                SELECT id, photon_name
                FROM courts 
                WHERE photon_name LIKE '%(% Courts)' OR photon_name LIKE '%(% Court)'
                ORDER BY id
            """)
            
            courts_to_update = cursor.fetchall()
            logger.info(f"Found {len(courts_to_update)} courts with court count in photon_name")
            
            updated_count = 0
            
            for court_id, photon_name in courts_to_update:
                # Remove court count from name
                import re
                clean_name = re.sub(r'\s*\(\d+\s+Courts?\)', '', photon_name)
                
                if clean_name != photon_name:
                    cursor.execute("""
                        UPDATE courts 
                        SET photon_name = %s
                        WHERE id = %s
                    """, (clean_name, court_id))
                    
                    logger.info(f"  Updated court {court_id}: '{photon_name}' -> '{clean_name}'")
                    updated_count += 1
            
            conn.commit()
            logger.info(f"Successfully cleaned {updated_count} photon_name values")
            return updated_count
            
        except Exception as e:
            logger.error(f"Error cleaning photon names: {e}")
            if conn:
                conn.rollback()
            return 0
        finally:
            if conn:
                conn.close()
    
    def test_changes(self):
        """Test the changes by querying the Gateway High School cluster"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    id, osm_id, photon_name, individual_court_name,
                    cluster_id, ST_AsText(ST_Centroid(geom)) as centroid
                FROM courts 
                WHERE cluster_id = '458bf3f2-ba6b-4c2a-a883-1bb62139d3b4' 
                ORDER BY id
            """)
            
            results = cursor.fetchall()
            
            print("🧪 TESTING CHANGES")
            print("=" * 60)
            print(f"Found {len(results)} courts in Gateway High School cluster")
            print()
            
            for row in results:
                id, osm_id, photon_name, individual_court_name, cluster_id, centroid = row
                print(f"Court ID: {id}")
                print(f"  OSM ID: {osm_id}")
                print(f"  Photon Name: {photon_name}")
                print(f"  Individual Name: {individual_court_name}")
                print(f"  Cluster ID: {cluster_id}")
                print()
            
            return results
            
        except Exception as e:
            logger.error(f"Error testing changes: {e}")
            return []
        finally:
            if conn:
                conn.close()

def main():
    """Main function to add individual court names"""
    print("🏀 INDIVIDUAL COURT NAME MANAGER")
    print("=" * 60)
    
    # Database connection
    connection_string = os.getenv('DATABASE_URL')
    if not connection_string:
        print("❌ DATABASE_URL not found in environment variables")
        return
    
    manager = IndividualCourtNameManager(connection_string)
    
    # Step 1: Add column
    print("1. Adding individual_court_name column...")
    if manager.add_individual_court_name_column():
        print("   ✅ Column added successfully")
    else:
        print("   ❌ Failed to add column")
        return
    
    # Step 2: Clean existing photon names
    print("\n2. Cleaning photon_name values...")
    updated_photon = manager.clean_photon_names()
    print(f"   ✅ Cleaned {updated_photon} photon_name values")
    
    # Step 3: Populate individual court names
    print("\n3. Populating individual court names...")
    updated_individual = manager.populate_individual_court_names()
    print(f"   ✅ Updated {updated_individual} courts with individual names")
    
    # Step 4: Test changes
    print("\n4. Testing changes...")
    manager.test_changes()
    
    print("\n✅ ALL CHANGES COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print("Next steps:")
    print("1. Update backend API to include individual_court_name")
    print("2. Update frontend to display cluster group + individual names")

if __name__ == "__main__":
    main()
