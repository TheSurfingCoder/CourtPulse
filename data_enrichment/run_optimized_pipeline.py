"""
Production script for the optimized court processing pipeline
Uses controlled parallelism for maximum performance while maintaining reliability
"""

import json
import logging
import os
import sys
import asyncio
from datetime import datetime
import argparse

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from optimized_court_pipeline import OptimizedCourtPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'optimized_pipeline_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def run_optimized_pipeline(connection_string: str, 
                                concurrent_features: int = 20,
                                db_batch_size: int = 100, 
                                max_api_connections: int = 50,
                                max_features: int = None):
    """Run the optimized pipeline with controlled parallelism"""
    
    logger.info(json.dumps({
        'event': 'optimized_pipeline_started',
        'timestamp': datetime.now().isoformat(),
        'concurrent_features': concurrent_features,
        'db_batch_size': db_batch_size,
        'max_api_connections': max_api_connections,
        'max_features': max_features
    }))
    
    try:
        # Initialize pipeline
        pipeline = OptimizedCourtPipeline(
            connection_string=connection_string,
            concurrent_features=concurrent_features,
            db_batch_size=db_batch_size,
            max_api_connections=max_api_connections
        )
        
        # Process the dataset
        results = await pipeline.process_geojson_file(
            file_path='export.geojson',
            max_features=max_features
        )
        
        # Generate comprehensive report
        generate_optimized_report(results)
        
        return results
        
    except Exception as e:
        logger.error(json.dumps({
            'event': 'optimized_pipeline_error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }))
        raise

def generate_optimized_report(results: dict):
    """Generate a comprehensive performance report"""
    
    print("\n" + "="*80)
    print("🚀 OPTIMIZED COURT PIPELINE - PERFORMANCE REPORT")
    print("="*80)
    print(f"📊 Processing Summary:")
    print(f"   Total Features: {results['total_features']:,}")
    print(f"   Successfully Processed: {results['successful']:,}")
    print(f"   Failed: {results['skipped']:,}")
    print(f"   Success Rate: {results['success_rate']:.1f}%")
    print()
    print(f"⚡ Performance Metrics:")
    print(f"   Processing Time: {results['processing_time_seconds']:.1f} seconds")
    print(f"   Features per Second: {results['features_per_second']:.1f}")
    print(f"   Chunks Processed: {results['chunks_processed']}")
    print(f"   DB Batches: {results['db_batches_processed']}")
    print()
    print(f"🏗️ Architecture:")
    print(f"   Concurrent Features: {results['concurrent_features']}")
    print(f"   Max API Connections: {results['max_api_connections']}")
    print(f"   API Calls per Chunk: {results['concurrent_features'] * 2}")
    print()
    print(f"📈 Efficiency:")
    total_api_calls = results['total_features'] * 2
    api_calls_per_second = total_api_calls / results['processing_time_seconds'] if results['processing_time_seconds'] > 0 else 0
    print(f"   Total API Calls: {total_api_calls:,}")
    print(f"   API Calls per Second: {api_calls_per_second:.1f}")
    print(f"   Parallel Efficiency: {(api_calls_per_second / results['max_api_connections']) * 100:.1f}%")
    print("="*80)
    
    # Log the final report
    logger.info(json.dumps({
        'event': 'optimized_final_report',
        'results': results
    }))
    
    # Save results to file
    results_file = f'optimized_pipeline_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"📄 Detailed results saved to: {results_file}")

def main():
    """Main function with command line argument parsing"""
    parser = argparse.ArgumentParser(description='Optimized Court Data Processing Pipeline')
    
    # Build default connection string from env vars
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
    parser.add_argument('--concurrent-features', 
                       type=int, 
                       default=20,
                       help='Number of features to process concurrently (default: 20)')
    parser.add_argument('--db-batch-size', 
                       type=int, 
                       default=100,
                       help='Database batch size (default: 100)')
    parser.add_argument('--max-api-connections', 
                       type=int, 
                       default=50,
                       help='Maximum concurrent API connections (default: 50)')
    parser.add_argument('--max-features', 
                       type=int, 
                       default=None,
                       help='Maximum number of features to process (for testing)')
    parser.add_argument('--test-mode', 
                       action='store_true',
                       help='Run in test mode with 50 features')
    
    args = parser.parse_args()
    
    # Override max_features if in test mode
    if args.test_mode:
        args.max_features = 50
        print("🧪 Running in TEST MODE - Limited to 50 features")
    
    print("🚀 Starting Optimized Court Data Processing Pipeline")
    print(f"   Concurrent Features: {args.concurrent_features}")
    print(f"   DB Batch Size: {args.db_batch_size}")
    print(f"   Max API Connections: {args.max_api_connections}")
    print(f"   Max Features: {args.max_features or 'All (401)'}")
    print()
    
    async def run_pipeline():
        try:
            results = await run_optimized_pipeline(
                connection_string=args.connection_string,
                concurrent_features=args.concurrent_features,
                db_batch_size=args.db_batch_size,
                max_api_connections=args.max_api_connections,
                max_features=args.max_features
            )
            
            # Check if pipeline was successful
            if results['success_rate'] >= 80:
                print("\n✅ OPTIMIZED PIPELINE COMPLETED SUCCESSFULLY!")
                print(f"   🚀 {results['features_per_second']:.1f} features/second")
                print(f"   ⚡ {results['processing_time_seconds']:.1f} seconds total")
                print("   Ready for production use!")
            else:
                print("\n⚠️  PIPELINE COMPLETED WITH WARNINGS")
                print(f"   Success rate: {results['success_rate']:.1f}%")
                print("   Review logs for details.")
            
            return True
            
        except Exception as e:
            print(f"\n❌ OPTIMIZED PIPELINE FAILED: {e}")
            logger.error(json.dumps({
                'event': 'optimized_pipeline_failure',
                'error': str(e)
            }))
            return False
    
    try:
        success = asyncio.run(run_pipeline())
        return success
    except KeyboardInterrupt:
        print("\n🛑 Pipeline interrupted by user")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


