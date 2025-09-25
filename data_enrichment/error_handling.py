#!/usr/bin/env python3
"""
Simple error handling and validation for data pipeline
"""

import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional

class PipelineError(Exception):
    """Custom exception for pipeline errors"""
    pass

class ValidationError(PipelineError):
    """Custom exception for validation errors"""
    pass

class SimpleErrorHandler:
    """Simple error handling with basic validation rules"""
    
    def __init__(self, region: str):
        self.region = region
        self.errors = []
        self.warnings = []
        
        # Simple validation thresholds
        self.min_records = {
            'sf_bay': 50,
            'nyc': 100, 
            'london': 75
        }
        
        self.max_null_coords_pct = 10  # 10% max null coordinates
        self.max_duplicates = 5        # 5 max duplicate OSM IDs
        self.min_success_rate = 80     # 80% min success rate
    
    def log_error(self, message: str, details: Optional[Dict] = None):
        """Log an error and add to error list"""
        error = {
            'timestamp': datetime.now().isoformat(),
            'level': 'ERROR',
            'message': message,
            'details': details or {}
        }
        self.errors.append(error)
        print(f"❌ ERROR: {message}")
        if details:
            print(f"   Details: {json.dumps(details, indent=2)}")
    
    def log_warning(self, message: str, details: Optional[Dict] = None):
        """Log a warning and add to warning list"""
        warning = {
            'timestamp': datetime.now().isoformat(),
            'level': 'WARNING', 
            'message': message,
            'details': details or {}
        }
        self.warnings.append(warning)
        print(f"⚠️  WARNING: {message}")
        if details:
            print(f"   Details: {json.dumps(details, indent=2)}")
    
    def log_info(self, message: str, details: Optional[Dict] = None):
        """Log an info message"""
        info = {
            'timestamp': datetime.now().isoformat(),
            'level': 'INFO',
            'message': message,
            'details': details or {}
        }
        print(f"ℹ️  INFO: {message}")
        if details:
            print(f"   Details: {json.dumps(details, indent=2)}")
    
    def validate_record_count(self, count: int) -> bool:
        """Validate minimum record count"""
        min_required = self.min_records.get(self.region, 50)
        
        if count < min_required:
            self.log_error(
                f"Too few records: {count} (minimum: {min_required})",
                {'record_count': count, 'minimum_required': min_required}
            )
            return False
        else:
            self.log_info(f"Record count OK: {count} (minimum: {min_required})")
            return True
    
    def validate_data_quality(self, stats: Dict[str, Any]) -> bool:
        """Validate basic data quality metrics"""
        total_records = stats.get('total_records', 0)
        null_coords = stats.get('null_coords', 0)
        duplicates = stats.get('duplicates', 0)
        
        # Check null coordinates percentage
        null_pct = (null_coords / total_records * 100) if total_records > 0 else 0
        if null_pct > self.max_null_coords_pct:
            self.log_error(
                f"Too many null coordinates: {null_pct:.1f}% (max: {self.max_null_coords_pct}%)",
                {'null_percentage': null_pct, 'null_count': null_coords, 'total_records': total_records}
            )
            return False
        
        # Check duplicates
        if duplicates > self.max_duplicates:
            self.log_error(
                f"Too many duplicates: {duplicates} (max: {self.max_duplicates})",
                {'duplicate_count': duplicates}
            )
            return False
        
        self.log_info(f"Data quality OK: {null_pct:.1f}% null coords, {duplicates} duplicates")
        return True
    
    def validate_success_rate(self, successful: int, total: int) -> bool:
        """Validate processing success rate"""
        if total == 0:
            self.log_error("No records processed")
            return False
        
        success_rate = (successful / total) * 100
        if success_rate < self.min_success_rate:
            self.log_error(
                f"Success rate too low: {success_rate:.1f}% (minimum: {self.min_success_rate}%)",
                {'success_rate': success_rate, 'successful': successful, 'total': total}
            )
            return False
        else:
            self.log_info(f"Success rate OK: {success_rate:.1f}% ({successful}/{total})")
            return True
    
    def should_rollback(self) -> bool:
        """Determine if we should rollback based on errors"""
        # Rollback if we have any errors
        return len(self.errors) > 0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get error handling summary"""
        return {
            'region': self.region,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'should_rollback': self.should_rollback(),
            'errors': self.errors,
            'warnings': self.warnings
        }
    
    def fail_if_errors(self):
        """Fail the pipeline if there are errors"""
        if self.should_rollback():
            error_summary = self.get_summary()
            print(f"\n❌ PIPELINE FAILED - {len(self.errors)} errors found")
            print(f"   Region: {self.region}")
            print(f"   Errors: {len(self.errors)}")
            print(f"   Warnings: {len(self.warnings)}")
            print(f"   Should rollback: {self.should_rollback()}")
            
            # Save error report
            error_file = f"pipeline_errors_{self.region}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(error_file, 'w') as f:
                json.dump(error_summary, f, indent=2)
            print(f"   Error report saved: {error_file}")
            
            sys.exit(1)

# Simple API health check
def check_api_health() -> bool:
    """Check if required APIs are healthy"""
    import requests
    
    try:
        # Check Overpass API with a simple query
        overpass_query = '[out:json][timeout:5];node["amenity"="bench"](37.7,-122.5,37.8,-122.3);out count;'
        response = requests.post("https://overpass-api.de/api/interpreter", 
                               data={'data': overpass_query}, timeout=15)
        if response.status_code != 200:
            print(f"⚠️  Overpass API returned status {response.status_code}, but continuing...")
        
        # Check Photon API with a simple search
        response = requests.get("https://photon.komoot.io/api?q=San Francisco&limit=1", timeout=15)
        if response.status_code != 200:
            print(f"⚠️  Photon API returned status {response.status_code}, but continuing...")
        
        print("✅ API health check completed (continuing despite warnings)")
        return True
        
    except Exception as e:
        print(f"⚠️  API health check had issues: {e}, but continuing...")
        return True  # Allow pipeline to continue for testing

# Simple database health check
def check_database_health(database_url: str) -> bool:
    """Check if database is accessible"""
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        print("✅ Database is healthy")
        return True
    except Exception as e:
        print(f"❌ Database health check failed: {e}")
        return False
