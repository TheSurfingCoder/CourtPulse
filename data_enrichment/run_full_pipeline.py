"""
Production script for running the full court data processing pipeline
Processes the entire GeoJSON dataset with comprehensive monitoring
"""

import json
import logging
import os
import sys
from datetime import datetime
import argparse

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from court_pipeline import CourtProcessingPipeline
from test_photon_geocoding import PhotonGeocodingProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'court_pipeline_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_full_pipeline(connection_string: str, batch_size: int = 100, max_features: int = None):
    """Run the full pipeline with comprehensive monitoring"""
    
    logger.info(json.dumps({
        'event': 'full_pipeline_started',
        'timestamp': datetime.now().isoformat(),
        'batch_size': batch_size,
        'max_features': max_features,
        'connection_string': connection_string.replace(connection_string.split('@')[0].split('//')[1], '***') if '@' in connection_string else connection_string
    }))
    
    try:
        # Initialize pipeline
        pipeline = CourtProcessingPipeline(
            connection_string=connection_string,
            batch_size=batch_size
        )
        
        # Process the full dataset
        results = pipeline.process_geojson_file(
            file_path='export.geojson',
            max_features=max_features
        )
        
        # Generate comprehensive report
        generate_final_report(results)
        
        return results
        
    except Exception as e:
        logger.error(json.dumps({
            'event': 'full_pipeline_error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }))
        raise

def generate_final_report(results: dict):
    """Generate a comprehensive final report"""
    
    print("\n" + "="*80)
    print("🏀 COURT DATA PROCESSING PIPELINE - FINAL REPORT")
    print("="*80)
    print(f"📊 Processing Summary:")
    print(f"   Total Features Processed: {results['total_features']:,}")
    print(f"   Successfully Processed: {results['successful']:,}")
    print(f"   Validation Failed: {results['validation_failed']:,}")
    print(f"   Geocoding Failed: {results['geocoding_failed']:,}")
    print(f"   Database Failed: {results['database_failed']:,}")
    print(f"   Skipped: {results['skipped']:,}")
    print()
    print(f"📈 Performance Metrics:")
    print(f"   Success Rate: {results['success_rate']:.2f}%")
    print(f"   Processing Time: {results['processing_time_seconds']:.2f} seconds")
    print(f"   Features per Second: {results['features_per_second']:.2f}")
    print()
    
    # Display optimization stats if available
    if 'optimization_stats' in results:
        opt_stats = results['optimization_stats']
        print(f"🚀 Geocoding Optimization:")
        print(f"   Bounding Box Matches: {opt_stats['bounding_box_percentage']:.1f}%")
        print(f"   Distance-Based Fallback: {opt_stats['distance_based_percentage']:.1f}%")
        print(f"   Total API Calls: {opt_stats['total_requests']:,}")
        print()
    print(f"⏱️  Time Breakdown:")
    print(f"   Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Total Duration: {results['processing_time_seconds']:.2f} seconds")
    print("="*80)
    
    # Log the final report
    logger.info(json.dumps({
        'event': 'final_report_generated',
        'results': results
    }))
    
    # Save results to file
    results_file = f'pipeline_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"📄 Detailed results saved to: {results_file}")
    print("="*80)

def test_single_way(way_id: str, connection_string: str):
    """Test geocoding for a single way using the production pipeline logic"""
    
    print("="*80)
    print("🎯 TESTING SINGLE WAY WITH PRODUCTION PIPELINE")
    print("="*80)
    print(f"📍 Way ID: {way_id}")
    print("="*80)
    
    try:
        # Load the way from export.geojson
        with open('export.geojson', 'r') as f:
            geojson_data = json.load(f)
        
        # Find the specific way
        target_way = None
        for feature in geojson_data.get('features', []):
            properties = feature.get('properties', {})
            if properties.get('osm_id') == way_id:
                target_way = feature
                break
        
        if not target_way:
            print(f"❌ Way {way_id} not found in export.geojson")
            return
        
        # Extract coordinates
        geometry = target_way.get('geometry', {})
        if geometry.get('type') == 'Polygon':
            # Get centroid of polygon
            coords = geometry.get('coordinates', [[]])[0]
            if coords:
                lons = [coord[0] for coord in coords]
                lats = [coord[1] for coord in coords]
                lat = sum(lats) / len(lats)
                lon = sum(lons) / len(lons)
            else:
                print("❌ No coordinates found in polygon")
                return
        else:
            print(f"❌ Unsupported geometry type: {geometry.get('type')}")
            return
        
        # Extract properties
        properties = target_way.get('properties', {})
        sport = properties.get('sport', 'basketball')
        hoops = properties.get('hoops', 1)
        
        print(f"📍 Coordinates: {lat}, {lon}")
        print(f"🏀 Sport: {sport}")
        print(f"🎯 Hoops: {hoops}")
        print()
        
        # Test with production geocoding provider
        provider = PhotonGeocodingProvider()
        court_count = int(hoops) if hoops else 1
        
        print("🔄 Running production geocoding...")
        start_time = datetime.now()
        
        name, data = provider.reverse_geocode(lat, lon, court_count)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print()
        print("="*80)
        print("📊 RESULTS:")
        print("="*80)
        
        if name:
            print(f"✅ Name: {name}")
            print(f"📊 Data available: {data is not None}")
            print(f"⏱️  Duration: {duration:.2f} seconds")
            
            # Show optimization stats if available
            if data and 'optimization_stats' in data:
                stats = data['optimization_stats']
                print(f"🚀 Bounding Box: {stats['bounding_box_percentage']:.1f}%")
                print(f"📏 Distance-based: {stats['distance_based_percentage']:.1f}%")
                print(f"📞 Total API calls: {stats['total_requests']}")
        else:
            print("❌ No name found")
        
        print("="*80)
        
        # Generate pipeline results JSON for single way test
        if name and data:
            # Get optimization stats
            optimization_stats = provider.get_optimization_stats()
            
            # Create mock pipeline results
            pipeline_results = {
                'timestamp': datetime.now().isoformat(),
                'way_id': way_id,
                'coordinates': {'lat': lat, 'lon': lon},
                'sport': sport,
                'hoops': hoops,
                'geocoding_result': {
                    'name': name,
                    'data': data
                },
                'performance': {
                    'duration_seconds': duration,
                    'features_per_second': 1.0 / duration if duration > 0 else 0
                },
                'optimization_stats': optimization_stats,
                'success': True,
                'total_features': 1,
                'processed_features': 1,
                'success_rate': 100.0,
                'frontend_ready': True
            }
            
            # Save to file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'pipeline_results_single_way_{timestamp}.json'
            
            with open(filename, 'w') as f:
                json.dump(pipeline_results, f, indent=2)
            
            print(f"📄 Pipeline results saved to: {filename}")
            print(f"   Features/second: {pipeline_results['performance']['features_per_second']:.3f}")
            print(f"   Bounding Box: {optimization_stats['bounding_box_percentage']:.1f}%")
            print(f"   Distance-based: {optimization_stats['distance_based_percentage']:.1f}%")
        
    except Exception as e:
        logger.error(json.dumps({
            'event': 'single_way_test_error',
            'way_id': way_id,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }))
        print(f"❌ Error testing way {way_id}: {e}")

def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(description='Court Data Processing Pipeline')
    # Build default connection string from env vars (same as backend)
    default_connection = os.getenv('DATABASE_URL')
    if not default_connection:
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'courtpulse-dev')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', 'password')
        default_connection = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    parser.add_argument('--connection-string', 
                       default=default_connection,
                       help='Database connection string')
    parser.add_argument('--batch-size', 
                       type=int, 
                       default=100,
                       help='Batch size for processing (default: 100)')
    parser.add_argument('--max-features', 
                       type=int, 
                       default=None,
                       help='Maximum number of features to process (for testing)')
    parser.add_argument('--test-mode', 
                       action='store_true',
                       help='Run in test mode with limited features')
    parser.add_argument('--test-way', 
                       type=str,
                       help='Test a single way (e.g., "way/917299397")')
    
    args = parser.parse_args()
    
    # Override max_features if in test mode
    if args.test_mode:
        args.max_features = 50
        print("🧪 Running in TEST MODE - Limited to 50 features")
    
    # Handle single way test
    if args.test_way:
        print(f"🎯 Testing single way: {args.test_way}")
        test_single_way(args.test_way, args.connection_string)
        return
    
    print("🚀 Starting Court Data Processing Pipeline")
    print(f"   Batch Size: {args.batch_size}")
    print(f"   Max Features: {args.max_features or 'All'}")
    print(f"   Connection: {args.connection_string.split('@')[0].split('//')[1] if '@' in args.connection_string else 'Local'}")
    print()
    
    try:
        results = run_full_pipeline(
            connection_string=args.connection_string,
            batch_size=args.batch_size,
            max_features=args.max_features
        )
        
        # Check if pipeline was successful
        if results['success_rate'] >= 80:
            print("\n✅ PIPELINE COMPLETED SUCCESSFULLY!")
            print("   Ready for production use.")
        else:
            print("\n⚠️  PIPELINE COMPLETED WITH WARNINGS")
            print(f"   Success rate: {results['success_rate']:.2f}%")
            print("   Review logs for details.")
        
        return True
        
    except Exception as e:
        print(f"\n❌ PIPELINE FAILED: {e}")
        logger.error(json.dumps({
            'event': 'pipeline_failure',
            'error': str(e)
        }))
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
