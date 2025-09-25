"""
Test script for the clustered court processing pipeline
Tests clustering efficiency and performance with 75 features
"""

import json
import logging
import os
import sys
from datetime import datetime

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from court_pipeline import CourtProcessingPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_clustered_pipeline():
    """Test the clustered pipeline with 75 features"""
    
    # Database connection string
    connection_string = os.getenv('DATABASE_URL')
    if not connection_string:
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'courtpulse-dev')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', 'password')
        connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    logger.info(json.dumps({
        'event': 'clustered_pipeline_test_started',
        'timestamp': datetime.now().isoformat(),
        'test_features': 75
    }))
    
    try:
        # Initialize pipeline with clustering
        pipeline = CourtProcessingPipeline(
            connection_string=connection_string,
            batch_size=100
        )
        
        logger.info(json.dumps({
            'event': 'starting_clustered_test',
            'test_features': 75,
            'clustering_enabled': True
        }))
        
        # Run with 75 features
        results = pipeline.process_geojson_file(
            file_path='export.geojson',
            max_features=75
        )
        
        # Print detailed results
        print("\n" + "="*70)
        print("🏀 CLUSTERED PIPELINE TEST RESULTS")
        print("="*70)
        print(f"📊 Dataset Summary:")
        print(f"   Total Features: {results['total_features']}")
        print(f"   Clusters Created: {results['clusters_created']}")
        print(f"   API Calls Saved: {results['api_calls_saved']}")
        print(f"   Clustering Efficiency: {results['clustering_efficiency']}%")
        print()
        print(f"🎯 Processing Results:")
        print(f"   Successfully Processed: {results['successful']}")
        print(f"   Validation Failed: {results['validation_failed']}")
        print(f"   Geocoding Failed: {results['geocoding_failed']}")
        print(f"   Database Failed: {results['database_failed']}")
        print(f"   Success Rate: {results['success_rate']}%")
        print()
        print(f"⚡ Performance Metrics:")
        print(f"   Processing Time: {results['processing_time_seconds']:.1f} seconds")
        print(f"   Features per Second: {results['features_per_second']:.2f}")
        print()
        print(f"🔗 API Efficiency:")
        without_clustering = results['total_features'] * 2  # 2 calls per feature
        with_clustering = results['clusters_created'] * 2   # 2 calls per cluster
        print(f"   Without Clustering: {without_clustering} API calls")
        print(f"   With Clustering: {with_clustering} API calls")
        print(f"   API Calls Saved: {without_clustering - with_clustering}")
        print(f"   API Efficiency Gain: {((without_clustering - with_clustering) / without_clustering) * 100:.1f}%")
        print("="*70)
        
        # Log detailed results
        logger.info(json.dumps({
            'event': 'clustered_test_completed',
            'results': results
        }))
        
        # Check if test was successful
        if results['success_rate'] >= 80:
            logger.info(json.dumps({
                'event': 'clustered_test_passed',
                'success_rate': results['success_rate'],
                'clustering_efficiency': results['clustering_efficiency']
            }))
            print("✅ CLUSTERED TEST PASSED - Ready for full dataset!")
            
            # Show clustering benefits
            if results['api_calls_saved'] > 0:
                print(f"🎉 Clustering saved {results['api_calls_saved']} API calls ({results['clustering_efficiency']}% efficiency gain)!")
            
            return True
        else:
            logger.warning(json.dumps({
                'event': 'clustered_test_failed',
                'success_rate': results['success_rate'],
                'threshold': 80
            }))
            print("❌ CLUSTERED TEST FAILED - Pipeline needs debugging")
            return False
            
    except Exception as e:
        logger.error(json.dumps({
            'event': 'clustered_test_error',
            'error': str(e)
        }))
        print(f"❌ Clustered pipeline test error: {e}")
        return False

def main():
    """Run clustered pipeline test"""
    print("🧪 CLUSTERED COURT PIPELINE TEST")
    print("="*70)
    print("Testing coordinate clustering with 75 features...")
    print("This will show how many API calls clustering saves.")
    print()
    
    success = test_clustered_pipeline()
    
    if success:
        print("\n🚀 READY FOR NEXT STEPS:")
        print("1. Run full dataset (401 features) with clustering")
        print("2. Update existing database records with cluster consistency")
        print("3. Set up incremental update workflow for future OSM imports")
    else:
        print("\n🔧 NEEDS DEBUGGING:")
        print("Review logs to identify clustering or processing issues")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


