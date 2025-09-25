"""
Populate cluster metadata for existing records
Groups courts with same photon_name and nearby coordinates into clusters
"""

import json
import logging
import os
import sys
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any, List, Tuple
import math

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClusterMetadataPopulator:
    """Populates cluster metadata for existing database records"""
    
    def __init__(self, connection_string: str, max_distance_km: float = 0.05):
        self.connection_string = connection_string
        self.max_distance_km = max_distance_km  # ~160 feet
        
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.connection_string)
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula (returns km)"""
        R = 6371.0  # Earth's radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def get_courts_by_name(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all courts grouped by photon_name"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
            SELECT 
                id, osm_id, photon_name,
                ST_Y(centroid::geometry) as lat,
                ST_X(centroid::geometry) as lon,
                hoops, sport
            FROM courts 
            WHERE photon_name IS NOT NULL
            ORDER BY photon_name, osm_id;
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            # Group by photon_name
            courts_by_name = {}
            for court in results:
                name = court['photon_name']
                if name not in courts_by_name:
                    courts_by_name[name] = []
                courts_by_name[name].append(dict(court))
            
            logger.info(json.dumps({
                'event': 'courts_grouped_by_name',
                'unique_names': len(courts_by_name),
                'total_courts': len(results)
            }))
            
            return courts_by_name
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'get_courts_error',
                'error': str(e)
            }))
            raise
        finally:
            if conn:
                conn.close()
    
    def create_geographic_clusters(self, courts_by_name: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Create geographic clusters from courts with same name"""
        all_clusters = []
        
        for photon_name, courts in courts_by_name.items():
            if len(courts) == 1:
                # Single court - create cluster of 1
                cluster_id = str(uuid.uuid4())
                cluster = {
                    'cluster_id': cluster_id,
                    'photon_name': photon_name,
                    'courts': courts,
                    'representative': courts[0],
                    'size': 1
                }
                all_clusters.append(cluster)
                
                logger.debug(json.dumps({
                    'event': 'single_court_cluster',
                    'photon_name': photon_name,
                    'osm_id': courts[0]['osm_id']
                }))
                
            else:
                # Multiple courts with same name - cluster by distance
                clusters = self.cluster_courts_by_distance(courts, photon_name)
                all_clusters.extend(clusters)
        
        logger.info(json.dumps({
            'event': 'geographic_clustering_completed',
            'total_clusters': len(all_clusters),
            'total_courts': sum(len(cluster['courts']) for cluster in all_clusters)
        }))
        
        return all_clusters
    
    def cluster_courts_by_distance(self, courts: List[Dict[str, Any]], photon_name: str) -> List[Dict[str, Any]]:
        """Cluster courts with same name by geographic distance"""
        clusters = []
        processed = set()
        
        for i, court in enumerate(courts):
            if i in processed:
                continue
            
            # Start new cluster
            cluster_id = str(uuid.uuid4())
            cluster_courts = [court]
            processed.add(i)
            
            # Find nearby courts with same name
            for j, other_court in enumerate(courts[i+1:], i+1):
                if j in processed:
                    continue
                
                distance = self.calculate_distance(
                    court['lat'], court['lon'],
                    other_court['lat'], other_court['lon']
                )
                
                if distance <= self.max_distance_km:
                    cluster_courts.append(other_court)
                    processed.add(j)
            
            # Create cluster
            cluster = {
                'cluster_id': cluster_id,
                'photon_name': photon_name,
                'courts': cluster_courts,
                'representative': cluster_courts[0],  # First court as representative
                'size': len(cluster_courts)
            }
            clusters.append(cluster)
            
            logger.info(json.dumps({
                'event': 'geographic_cluster_created',
                'cluster_id': cluster_id,
                'photon_name': photon_name,
                'cluster_size': len(cluster_courts),
                'representative_osm_id': cluster_courts[0]['osm_id']
            }))
        
        return clusters
    
    def update_cluster_metadata(self, clusters: List[Dict[str, Any]]) -> Dict[str, int]:
        """Update database with cluster metadata"""
        stats = {'updated_courts': 0, 'created_clusters': 0}
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            for cluster in clusters:
                cluster_id = cluster['cluster_id']
                cluster_size = cluster['size']
                
                # Update all courts in cluster
                for i, court in enumerate(cluster['courts']):
                    is_representative = (i == 0)  # First court is representative
                    
                    update_query = """
                    UPDATE courts 
                    SET 
                        cluster_id = %s,
                        cluster_representative = %s,
                        cluster_size = %s,
                        updated_at = NOW()
                    WHERE id = %s;
                    """
                    
                    cursor.execute(update_query, (
                        cluster_id,
                        is_representative,
                        cluster_size,
                        court['id']
                    ))
                    
                    stats['updated_courts'] += 1
                
                stats['created_clusters'] += 1
                
                logger.debug(json.dumps({
                    'event': 'cluster_metadata_updated',
                    'cluster_id': cluster_id,
                    'cluster_size': cluster_size,
                    'photon_name': cluster['photon_name']
                }))
            
            conn.commit()
            
            logger.info(json.dumps({
                'event': 'cluster_metadata_population_completed',
                'stats': stats
            }))
            
            return stats
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(json.dumps({
                'event': 'cluster_metadata_update_error',
                'error': str(e)
            }))
            raise
        finally:
            if conn:
                conn.close()
    
    def populate_all_cluster_metadata(self) -> Dict[str, Any]:
        """Main method to populate cluster metadata"""
        try:
            logger.info(json.dumps({
                'event': 'cluster_metadata_population_started',
                'max_distance_km': self.max_distance_km
            }))
            
            # Step 1: Get courts grouped by name
            courts_by_name = self.get_courts_by_name()
            
            # Step 2: Create geographic clusters
            clusters = self.create_geographic_clusters(courts_by_name)
            
            # Step 3: Update database with cluster metadata
            stats = self.update_cluster_metadata(clusters)
            
            # Step 4: Generate summary
            summary = {
                'unique_names': len(courts_by_name),
                'geographic_clusters': len(clusters),
                'updated_courts': stats['updated_courts'],
                'multi_court_clusters': len([c for c in clusters if c['size'] > 1]),
                'largest_cluster_size': max(c['size'] for c in clusters) if clusters else 0,
                'clustering_efficiency': round(((stats['updated_courts'] - len(clusters)) / stats['updated_courts']) * 100, 1) if stats['updated_courts'] > 0 else 0
            }
            
            logger.info(json.dumps({
                'event': 'cluster_metadata_population_summary',
                'summary': summary
            }))
            
            return summary
            
        except Exception as e:
            logger.error(json.dumps({
                'event': 'cluster_metadata_population_error',
                'error': str(e)
            }))
            raise

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
    
    print("🗺️  POPULATING CLUSTER METADATA FOR FRONTEND")
    print("="*60)
    print("This will add cluster information to enable geographic")
    print("clustering on the frontend while keeping separate records.")
    print()
    
    try:
        populator = ClusterMetadataPopulator(connection_string, max_distance_km=0.05)
        summary = populator.populate_all_cluster_metadata()
        
        print("📊 CLUSTER METADATA RESULTS:")
        print(f"   Unique Names: {summary['unique_names']}")
        print(f"   Geographic Clusters: {summary['geographic_clusters']}")
        print(f"   Updated Courts: {summary['updated_courts']}")
        print(f"   Multi-Court Clusters: {summary['multi_court_clusters']}")
        print(f"   Largest Cluster: {summary['largest_cluster_size']} courts")
        print(f"   Clustering Efficiency: {summary['clustering_efficiency']}%")
        print()
        print("✅ Cluster metadata populated successfully!")
        print("🗺️  Frontend can now display clustered markers.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error populating cluster metadata: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


