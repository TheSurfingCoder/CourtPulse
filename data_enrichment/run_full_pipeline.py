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
    
    args = parser.parse_args()
    
    # Override max_features if in test mode
    if args.test_mode:
        args.max_features = 50
        print("🧪 Running in TEST MODE - Limited to 50 features")
    
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
