#!/usr/bin/env python3
"""
Test the full pipeline with simple error handling
"""

import os
import sys
import json
import asyncio
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from error_handling import SimpleErrorHandler, check_api_health, check_database_health
from optimized_court_pipeline import OptimizedCourtPipeline

async def test_pipeline_with_errors(region: str = 'sf_bay', environment: str = 'staging'):
    """Test the full pipeline with error handling"""
    
    print(f"🚀 Testing pipeline with error handling")
    print(f"   Region: {region}")
    print(f"   Environment: {environment}")
    print()
    
    # Initialize error handler
    error_handler = SimpleErrorHandler(region)
    
    try:
        # Step 1: Health checks
        print("🔍 Running health checks...")
        
        # Check APIs
        if not check_api_health():
            error_handler.log_error("API health check failed")
            error_handler.fail_if_errors()
        
        # Check database
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            error_handler.log_error("DATABASE_URL environment variable not set")
            error_handler.fail_if_errors()
        
        if not check_database_health(database_url):
            error_handler.log_error("Database health check failed")
            error_handler.fail_if_errors()
        
        print("✅ All health checks passed")
        print()
        
        # Step 2: Extract data from Overpass
        print("🌍 Extracting data from Overpass API...")
        from scripts.extract_overpass_data import extract_data_from_overpass
        
        data_file = f"data/export_{region}.geojson"
        feature_count = extract_data_from_overpass(region, data_file)
        
        # Validate record count
        if not error_handler.validate_record_count(feature_count):
            error_handler.fail_if_errors()
        
        print(f"✅ Data extraction successful: {feature_count} features")
        print()
        
        # Step 3: Run data pipeline
        print("🔄 Running data pipeline...")
        
        # Initialize pipeline with conservative settings for testing
        pipeline = OptimizedCourtPipeline(
            connection_string=database_url,
            concurrent_features=5,    # Small batch for testing
            db_batch_size=10,        # Small database batch
            max_api_connections=10   # Conservative API limit
        )
        
        # Process the data
        results = await pipeline.process_geojson_file(
            file_path=data_file,
            max_features=50  # Test with first 50 features only
        )
        
        # Validate results
        if not error_handler.validate_success_rate(results['successful'], results['total_processed']):
            error_handler.fail_if_errors()
        
        # Calculate data quality stats
        quality_stats = {
            'total_records': results['total_processed'],
            'null_coords': results.get('validation_failed', 0),
            'duplicates': 0,  # We'll add this later
            'successful': results['successful']
        }
        
        if not error_handler.validate_data_quality(quality_stats):
            error_handler.fail_if_errors()
        
        print("✅ Pipeline completed successfully!")
        print()
        
        # Step 4: Print summary
        print("📊 PIPELINE SUMMARY")
        print("=" * 50)
        print(f"Region: {region}")
        print(f"Environment: {environment}")
        print(f"Features extracted: {feature_count}")
        print(f"Features processed: {results['total_processed']}")
        print(f"Successfully processed: {results['successful']}")
        print(f"Success rate: {results['success_rate']:.1f}%")
        print(f"Processing time: {results['processing_time_seconds']:.1f} seconds")
        print(f"Features per second: {results['features_per_second']:.1f}")
        print()
        
        # Get error handler summary
        error_summary = error_handler.get_summary()
        print("🛡️ ERROR HANDLING SUMMARY")
        print("=" * 50)
        print(f"Errors: {error_summary['error_count']}")
        print(f"Warnings: {error_summary['warning_count']}")
        print(f"Should rollback: {error_summary['should_rollback']}")
        
        if error_summary['warnings']:
            print("\nWarnings:")
            for warning in error_summary['warnings']:
                print(f"  - {warning['message']}")
        
        print("\n✅ Test completed successfully!")
        return True
        
    except Exception as e:
        error_handler.log_error(f"Pipeline test failed: {str(e)}")
        error_handler.fail_if_errors()
        return False

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test pipeline with error handling')
    parser.add_argument('--region', default='sf_bay', help='Region to test')
    parser.add_argument('--environment', default='staging', help='Environment to test')
    
    args = parser.parse_args()
    
    print("🧪 PIPELINE TEST WITH ERROR HANDLING")
    print("=" * 50)
    
    # Run the test
    success = asyncio.run(test_pipeline_with_errors(args.region, args.environment))
    
    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
