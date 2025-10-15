"""
Fetch court data from OpenStreetMap Overpass API
Supports multiple sports and customizable bounding boxes
"""

import json
import logging
import argparse
import sys
import time
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Predefined regions
REGIONS = {
    'sf_bay': {
        'name': 'San Francisco Bay Area',
        'bbox': '37.2, -122.5, 38.0, -121.5'  # south, west, north, east
    },
    'sf_city': {
        'name': 'San Francisco City',
        'bbox': '37.7, -122.52, 37.83, -122.35'  # Just SF city proper
    },
    'sf_bay_test': {
        'name': 'SF Bay Test Area (Mission District)',
        'bbox': '37.75, -122.43, 37.78, -122.40'  # Small test area
    }
}

# Default sports to fetch
DEFAULT_SPORTS = ['basketball', 'tennis', 'soccer', 'volleyball', 'pickleball']

class OverpassAPIFetcher:
    """Fetches court data from Overpass API"""
    
    def __init__(self, base_url: str = 'https://overpass-api.de/api/interpreter'):
        self.base_url = base_url
        self.request_count = 0
        self.last_request_time = 0
    
    def _rate_limit(self, min_delay: float = 1.0):
        """Enforce rate limiting between requests"""
        if self.last_request_time > 0:
            elapsed = time.time() - self.last_request_time
            if elapsed < min_delay:
                sleep_time = min_delay - elapsed
                logger.info(json.dumps({
                    'event': 'rate_limit_delay',
                    'sleep_time': round(sleep_time, 2)
                }))
                time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def build_query(self, sports: List[str], bbox: str) -> str:
        """Build Overpass QL query for multiple sports"""
        # Build union of queries for each sport
        sport_queries = []
        for sport in sports:
            # Query for ways (areas) with leisure=pitch and sport=<sport>
            sport_queries.append(f'  way["leisure"="pitch"]["sport"="{sport}"]({bbox});')
        
        query = f"""[out:json][timeout:90];
(
{chr(10).join(sport_queries)}
);
out geom;"""
        
        return query
    
    def fetch_courts(self, sports: List[str], bbox: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """Fetch court data from Overpass API"""
        query = self.build_query(sports, bbox)
        
        logger.info(json.dumps({
            'event': 'overpass_query_started',
            'sports': sports,
            'bbox': bbox,
            'query_length': len(query)
        }))
        
        for attempt in range(max_retries):
            try:
                self._rate_limit()
                
                response = requests.post(
                    self.base_url,
                    data={'data': query},
                    timeout=120
                )
                
                self.request_count += 1
                
                if response.status_code == 200:
                    data = response.json()
                    
                    logger.info(json.dumps({
                        'event': 'overpass_query_success',
                        'elements_count': len(data.get('elements', [])),
                        'request_count': self.request_count,
                        'attempt': attempt + 1
                    }))
                    
                    return data
                
                elif response.status_code == 429:
                    # Rate limited - wait longer
                    wait_time = (attempt + 1) * 30
                    logger.warning(json.dumps({
                        'event': 'overpass_rate_limited',
                        'attempt': attempt + 1,
                        'wait_time': wait_time
                    }))
                    time.sleep(wait_time)
                    continue
                
                else:
                    logger.error(json.dumps({
                        'event': 'overpass_query_error',
                        'status_code': response.status_code,
                        'attempt': attempt + 1,
                        'response_text': response.text[:500]
                    }))
                    
                    if attempt < max_retries - 1:
                        time.sleep((attempt + 1) * 5)
                        continue
                    else:
                        return None
            
            except requests.exceptions.Timeout:
                logger.error(json.dumps({
                    'event': 'overpass_timeout',
                    'attempt': attempt + 1
                }))
                if attempt < max_retries - 1:
                    time.sleep((attempt + 1) * 10)
                    continue
                else:
                    return None
            
            except Exception as e:
                logger.error(json.dumps({
                    'event': 'overpass_fetch_error',
                    'error': str(e),
                    'attempt': attempt + 1
                }))
                if attempt < max_retries - 1:
                    time.sleep((attempt + 1) * 5)
                    continue
                else:
                    return None
        
        return None
    
    def convert_to_geojson(self, overpass_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Overpass JSON to GeoJSON format"""
        features = []
        
        elements = overpass_data.get('elements', [])
        
        for element in elements:
            try:
                # Only process ways with geometry
                if element.get('type') != 'way' or 'geometry' not in element:
                    continue
                
                # Extract coordinates from geometry
                coords = []
                for node in element.get('geometry', []):
                    if 'lat' in node and 'lon' in node:
                        coords.append([node['lon'], node['lat']])
                
                if len(coords) < 4:  # Need at least 4 points for a polygon
                    continue
                
                # Close the polygon if not already closed
                if coords[0] != coords[-1]:
                    coords.append(coords[0])
                
                # Build GeoJSON feature
                feature = {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Polygon',
                        'coordinates': [coords]
                    },
                    'properties': {
                        'osm_id': f"way/{element.get('id')}",
                        'sport': element.get('tags', {}).get('sport', 'other'),
                        'hoops': element.get('tags', {}).get('hoops'),
                        'surface': element.get('tags', {}).get('surface'),
                        'access': element.get('tags', {}).get('access'),
                        'fee': element.get('tags', {}).get('fee'),
                        'leisure': element.get('tags', {}).get('leisure'),
                        'name': element.get('tags', {}).get('name')
                    }
                }
                
                features.append(feature)
                
            except Exception as e:
                logger.error(json.dumps({
                    'event': 'element_conversion_error',
                    'element_id': element.get('id'),
                    'error': str(e)
                }))
                continue
        
        geojson = {
            'type': 'FeatureCollection',
            'generator': 'fetch_courts_data.py',
            'timestamp': datetime.now().isoformat(),
            'features': features
        }
        
        logger.info(json.dumps({
            'event': 'geojson_conversion_complete',
            'total_elements': len(elements),
            'converted_features': len(features),
            'conversion_rate': round(len(features) / len(elements) * 100, 1) if elements else 0
        }))
        
        return geojson

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Fetch court data from OpenStreetMap Overpass API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch all sports for SF Bay Area
  python fetch_courts_data.py

  # Fetch only basketball for test area
  python fetch_courts_data.py --region sf_bay_test --sports basketball

  # Fetch multiple sports with custom bbox
  python fetch_courts_data.py --bbox "37.75,-122.43,37.78,-122.40" --sports basketball,tennis

  # Use test region for quick validation
  python fetch_courts_data.py --test
"""
    )
    
    parser.add_argument(
        '--region',
        type=str,
        default='sf_bay',
        choices=list(REGIONS.keys()),
        help='Predefined region to fetch (default: sf_bay)'
    )
    
    parser.add_argument(
        '--bbox',
        type=str,
        help='Custom bounding box as "south,west,north,east" (overrides --region)'
    )
    
    parser.add_argument(
        '--sports',
        type=str,
        default=','.join(DEFAULT_SPORTS),
        help=f'Comma-separated list of sports to fetch (default: {",".join(DEFAULT_SPORTS)})'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='export.geojson',
        help='Output GeoJSON file path (default: export.geojson)'
    )
    
    parser.add_argument(
        '--test',
        action='store_true',
        help='Use small test region (sf_bay_test) for quick validation'
    )
    
    return parser.parse_args()

def main():
    """Main execution function"""
    args = parse_args()
    
    # Use test region if --test flag is set
    if args.test:
        args.region = 'sf_bay_test'
    
    # Determine bounding box
    if args.bbox:
        bbox = args.bbox
        region_name = 'Custom'
    else:
        region_data = REGIONS.get(args.region)
        bbox = region_data['bbox']
        region_name = region_data['name']
    
    # Parse sports list
    sports = [s.strip() for s in args.sports.split(',')]
    
    logger.info(json.dumps({
        'event': 'fetch_started',
        'region': region_name,
        'bbox': bbox,
        'sports': sports,
        'output_file': args.output,
        'timestamp': datetime.now().isoformat()
    }))
    
    # Initialize fetcher
    fetcher = OverpassAPIFetcher()
    
    # Fetch data
    print(f"🔍 Fetching court data for {region_name}...")
    print(f"   Sports: {', '.join(sports)}")
    print(f"   Bounding box: {bbox}")
    print()
    
    overpass_data = fetcher.fetch_courts(sports, bbox)
    
    if not overpass_data:
        logger.error(json.dumps({
            'event': 'fetch_failed',
            'reason': 'Failed to fetch data from Overpass API'
        }))
        print("❌ Failed to fetch data from Overpass API")
        return False
    
    # Convert to GeoJSON
    print("🔄 Converting to GeoJSON format...")
    geojson = fetcher.convert_to_geojson(overpass_data)
    
    # Save to file
    try:
        with open(args.output, 'w') as f:
            json.dump(geojson, f, indent=2)
        
        logger.info(json.dumps({
            'event': 'fetch_completed',
            'output_file': args.output,
            'feature_count': len(geojson['features']),
            'sports_fetched': sports
        }))
        
        print(f"✅ Successfully fetched {len(geojson['features'])} courts")
        print(f"   Output file: {args.output}")
        
        # Show breakdown by sport
        sport_counts = {}
        for feature in geojson['features']:
            sport = feature['properties'].get('sport', 'unknown')
            sport_counts[sport] = sport_counts.get(sport, 0) + 1
        
        print(f"\n📊 Courts by sport:")
        for sport, count in sorted(sport_counts.items()):
            print(f"   {sport}: {count}")
        
        return True
        
    except Exception as e:
        logger.error(json.dumps({
            'event': 'file_write_error',
            'error': str(e),
            'output_file': args.output
        }))
        print(f"❌ Failed to write output file: {e}")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

