"""
Coordinate clustering module for consistent court naming
Groups nearby courts that likely belong to the same facility
"""

import json
import logging
import math
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CourtClusterData:
    """Data structure for court clustering"""
    osm_id: str
    lat: float
    lon: float
    sport: str
    hoops: Optional[int]
    fallback_name: str
    feature_index: int
    feature_data: Dict[str, Any]

class CoordinateClusterer:
    """Clusters nearby court coordinates for consistent naming"""
    
    def __init__(self, max_distance_km: float = 0.05):
        """
        Initialize clusterer
        
        Args:
            max_distance_km: Maximum distance between coordinates to be in same cluster (~160 feet)
        """
        self.max_distance_km = max_distance_km
        
        logger.info(json.dumps({
            'event': 'clusterer_initialized',
            'max_distance_km': max_distance_km,
            'max_distance_feet': round(max_distance_km * 3280.84, 0)
        }))
    
    def extract_court_data(self, features: List[Dict[str, Any]]) -> List[CourtClusterData]:
        """Extract court data from GeoJSON features for clustering"""
        courts = []
        
        for i, feature in enumerate(features):
            try:
                properties = feature['properties']
                geometry = feature['geometry']
                
                # Extract coordinates (centroid of polygon)
                if geometry['type'] == 'Polygon' and geometry['coordinates']:
                    ring = geometry['coordinates'][0]
                    total_lon = sum(coord[0] for coord in ring) / len(ring)
                    total_lat = sum(coord[1] for coord in ring) / len(ring)
                    
                    court = CourtClusterData(
                        osm_id=properties.get('osm_id') or properties.get('@id'),
                        lat=total_lat,
                        lon=total_lon,
                        sport=properties.get('sport', 'basketball'),
                        hoops=int(properties.get('hoops')) if properties.get('hoops') else None,
                        fallback_name=self._generate_fallback_name(properties),
                        feature_index=i,
                        feature_data=feature
                    )
                    
                    courts.append(court)
                    
            except Exception as e:
                logger.error(json.dumps({
                    'event': 'court_data_extraction_error',
                    'feature_index': i,
                    'error': str(e)
                }))
                continue
        
        logger.info(json.dumps({
            'event': 'court_data_extracted',
            'total_features': len(features),
            'valid_courts': len(courts)
        }))
        
        return courts
    
    def cluster_courts(self, courts: List[CourtClusterData]) -> List[List[CourtClusterData]]:
        """
        Cluster nearby courts together for consistent naming
        
        Returns:
            List of clusters, where each cluster is a list of CourtClusterData
        """
        clusters = []
        processed = set()
        
        for i, court in enumerate(courts):
            if i in processed:
                continue
                
            # Start a new cluster with this court
            cluster = [court]
            processed.add(i)
            
            # Find all other courts within the distance threshold
            for j, other_court in enumerate(courts[i+1:], i+1):
                if j in processed:
                    continue
                    
                distance = self._calculate_distance(
                    court.lat, court.lon,
                    other_court.lat, other_court.lon
                )
                
                if distance <= self.max_distance_km:
                    cluster.append(other_court)
                    processed.add(j)
            
            clusters.append(cluster)
            
            logger.info(json.dumps({
                'event': 'cluster_created',
                'cluster_id': len(clusters),
                'cluster_size': len(cluster),
                'representative_osm_id': court.osm_id,
                'coordinates': {'lat': court.lat, 'lon': court.lon},
                'max_distance_km': self.max_distance_km
            }))
        
        # Log clustering summary
        total_courts = len(courts)
        total_clusters = len(clusters)
        api_calls_saved = total_courts - total_clusters
        
        logger.info(json.dumps({
            'event': 'clustering_completed',
            'total_courts': total_courts,
            'total_clusters': total_clusters,
            'api_calls_saved': api_calls_saved,
            'efficiency_improvement': round((api_calls_saved / total_courts) * 100, 1) if total_courts > 0 else 0
        }))
        
        return clusters
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates using Haversine formula (returns km)"""
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
    
    def _generate_fallback_name(self, properties: Dict[str, Any]) -> str:
        """Generate fallback name from OSM properties"""
        try:
            sport = properties.get('sport', 'basketball')
            hoops = properties.get('hoops')
            
            if sport == 'basketball' and hoops:
                hoops_int = int(hoops) if isinstance(hoops, str) else hoops
                return f"basketball court ({hoops_int} hoops)"
            elif sport == 'basketball':
                return "basketball court"
            elif sport == 'tennis':
                return "tennis court"
            elif sport == 'soccer':
                return "soccer field"
            elif sport == 'volleyball':
                return "volleyball court"
            else:
                return f"{sport} court"
                
        except Exception as e:
            logger.warning(json.dumps({
                'event': 'fallback_name_generation_error',
                'error': str(e)
            }))
            return "sports court"

# Example usage
if __name__ == "__main__":
    # Test clustering with sample data
    sample_features = [
        {
            "type": "Feature",
            "properties": {"@id": "way/1", "sport": "basketball", "hoops": "2"},
            "geometry": {"type": "Polygon", "coordinates": [[[-122.4, 37.7], [-122.4, 37.701], [-122.399, 37.701], [-122.399, 37.7], [-122.4, 37.7]]]}
        },
        {
            "type": "Feature", 
            "properties": {"@id": "way/2", "sport": "basketball", "hoops": "2"},
            "geometry": {"type": "Polygon", "coordinates": [[[-122.4001, 37.7001], [-122.4001, 37.7011], [-122.3991, 37.7011], [-122.3991, 37.7001], [-122.4001, 37.7001]]]}
        }
    ]
    
    clusterer = CoordinateClusterer(max_distance_km=0.05)
    courts = clusterer.extract_court_data(sample_features)
    clusters = clusterer.cluster_courts(courts)
    
    print(f"Extracted {len(courts)} courts")
    print(f"Created {len(clusters)} clusters")
    for i, cluster in enumerate(clusters, 1):
        print(f"Cluster {i}: {len(cluster)} courts")


