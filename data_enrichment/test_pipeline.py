"""
Test script for the court processing pipeline
Tests with a small batch before running the full dataset
"""

import json
import logging
import os
import sys
import asyncio
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

def test_pipeline():
    """Test the pipeline with a small batch"""
    
    # Database connection string - uses same pattern as backend
    connection_string = os.getenv('DATABASE_URL')
    if not connection_string:
        # Build connection string from individual env vars (same as backend)
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'courtpulse-dev')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', 'password')
        connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    logger.info(json.dumps({
        'event': 'pipeline_test_started',
        'timestamp': datetime.now().isoformat(),
        'connection_string': connection_string.replace(connection_string.split('@')[0].split('//')[1], '***') if '@' in connection_string else connection_string
    }))
    
    try:
        # Initialize pipeline with small batch size for testing
        pipeline = CourtProcessingPipeline(
            connection_string=connection_string,
            batch_size=5  # Small batch size for testing
        )
        
        # Test with first 10 features
        logger.info(json.dumps({
            'event': 'starting_test_run',
            'test_features': 10,
            'batch_size': 5
        }))
        
        results = pipeline.process_geojson_file(
            file_path='export.geojson',
            max_features=10
        )
        
        # Print results
        print("\n" + "="*60)
        print("🏀 COURT PIPELINE TEST RESULTS")
        print("="*60)
        print(f"Total Features: {results['total_features']}")
        print(f"Successfully Processed: {results['successful']}")
        print(f"Validation Failed: {results['validation_failed']}")
        print(f"Geocoding Failed: {results['geocoding_failed']}")
        print(f"Database Failed: {results['database_failed']}")
        print(f"Skipped: {results['skipped']}")
        print(f"Success Rate: {results['success_rate']}%")
        print(f"Processing Time: {results['processing_time_seconds']:.2f} seconds")
        print(f"Features/Second: {results['features_per_second']:.2f}")
        print("="*60)
        
        # Log detailed results
        logger.info(json.dumps({
            'event': 'test_completed',
            'results': results
        }))
        
        # Check if test was successful
        if results['success_rate'] >= 80:  # 80% success rate threshold
            logger.info(json.dumps({
                'event': 'test_passed',
                'success_rate': results['success_rate']
            }))
            print("✅ Test PASSED - Pipeline is ready for full dataset!")
            return True
        else:
            logger.warning(json.dumps({
                'event': 'test_failed',
                'success_rate': results['success_rate'],
                'threshold': 80
            }))
            print("❌ Test FAILED - Pipeline needs debugging before full run")
            return False
            
    except Exception as e:
        logger.error(json.dumps({
            'event': 'test_error',
            'error': str(e)
        }))
        print(f"❌ Test ERROR: {e}")
        return False

def test_database_connection():
    """Test database connection before running pipeline"""
    try:
        from database_operations import DatabaseManager, CourtDatabaseOperations
        
        connection_string = os.getenv('DATABASE_URL')
        if not connection_string:
            # Build connection string from individual env vars (same as backend)
            db_host = os.getenv('DB_HOST', 'localhost')
            db_port = os.getenv('DB_PORT', '5432')
            db_name = os.getenv('DB_NAME', 'courtpulse-dev')
            db_user = os.getenv('DB_USER', 'postgres')
            db_password = os.getenv('DB_PASSWORD', 'password')
            connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        logger.info(json.dumps({
            'event': 'testing_database_connection'
        }))
        
        db_manager = DatabaseManager(connection_string, min_connections=1, max_connections=2)
        court_ops = CourtDatabaseOperations(db_manager)
        
        # Test connection
        count = court_ops.get_court_count()
        
        logger.info(json.dumps({
            'event': 'database_connection_success',
            'existing_courts': count
        }))
        
        print(f"✅ Database connection successful! Found {count} existing courts.")
        
        db_manager.close_all_connections()
        return True
        
    except Exception as e:
        logger.error(json.dumps({
            'event': 'database_connection_error',
            'error': str(e)
        }))
        print(f"❌ Database connection failed: {e}")
        return False

def test_validation():
    """Test validation module"""
    try:
        from validation import CourtDataValidator
        
        logger.info(json.dumps({
            'event': 'testing_validation_module'
        }))
        
        validator = CourtDataValidator()
        
        # Test with sample data
        sample_court = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[-122.4, 37.7], [-122.4, 37.8], [-122.3, 37.8], [-122.3, 37.7], [-122.4, 37.7]]]
            },
            "properties": {
                "osm_id": "way/12345",
                "sport": "basketball",
                "hoops": 2
            }
        }
        
        is_valid, results = validator.validate_court_data(sample_court)
        
        if is_valid:
            logger.info(json.dumps({
                'event': 'validation_test_success'
            }))
            print("✅ Validation module working correctly!")
            return True
        else:
            logger.error(json.dumps({
                'event': 'validation_test_failed',
                'results': [r.message for r in results]
            }))
            print(f"❌ Validation test failed: {[r.message for r in results]}")
            return False
            
    except Exception as e:
        logger.error(json.dumps({
            'event': 'validation_test_error',
            'error': str(e)
        }))
        print(f"❌ Validation test error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 COURT PIPELINE TEST SUITE")
    print("="*60)
    
    # Test 1: Database Connection
    print("\n1. Testing Database Connection...")
    if not test_database_connection():
        print("❌ Cannot proceed without database connection")
        return False
    
    # Test 2: Validation Module
    print("\n2. Testing Validation Module...")
    if not test_validation():
        print("❌ Cannot proceed without working validation")
        return False
    
    # Test 3: Full Pipeline
    print("\n3. Testing Full Pipeline...")
    if not test_pipeline():
        print("❌ Pipeline test failed - needs debugging")
        return False
    
    print("\n🎉 ALL TESTS PASSED! Pipeline is ready for production use.")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
