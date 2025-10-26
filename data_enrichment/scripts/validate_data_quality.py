#!/usr/bin/env python3
"""
Validate data quality after pipeline processing
"""

import os
import sys
import asyncio
import argparse
import psycopg2
from psycopg2.extras import RealDictCursor

async def validate_data_quality(environment: str, region: str):
    """Validate data quality after processing"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        sys.exit(1)
    
    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        print(f"🔍 Validating data quality for region: {region}")
        
        # Check total record count
        cur.execute("SELECT COUNT(*) as count FROM courts WHERE region = %s OR region IS NULL", [region])
        total_records = cur.fetchone()['count']
        
        # Check for null coordinates
        cur.execute("""
            SELECT COUNT(*) as count FROM courts 
            WHERE (region = %s OR region IS NULL) AND centroid IS NULL
        """, [region])
        null_coords = cur.fetchone()['count']
        
        # Check for duplicate OSM IDs
        cur.execute("""
            SELECT osm_id, COUNT(*) as count FROM courts 
            WHERE region = %s OR region IS NULL
            GROUP BY osm_id HAVING COUNT(*) > 1
        """, [region])
        duplicates = cur.fetchall()
        
        # First, let's see what sport values actually exist
        cur.execute("""
            SELECT sport, COUNT(*) as count 
            FROM courts 
            WHERE (region = %s OR region IS NULL)
            GROUP BY sport 
            ORDER BY count DESC
        """, [region])
        sport_values = cur.fetchall()
        
        print(f"📊 Sport values in database:")
        for row in sport_values:
            print(f"   '{row['sport']}': {row['count']} records")
        
        # Check for records with missing required fields (NULL values only)
        cur.execute("""
            SELECT COUNT(*) as count FROM courts 
            WHERE (region = %s OR region IS NULL) 
            AND sport IS NULL
        """, [region])
        missing_sport = cur.fetchone()['count']
        
        if missing_sport > 0:
            print(f"🔧 Found {missing_sport} records with NULL sport values")
            # Fix NULL sport values by setting them to 'other'
            cur.execute("""
                UPDATE courts 
                SET sport = 'other' 
                WHERE (region = %s OR region IS NULL) 
                AND sport IS NULL
            """, [region])
            fixed_sport_count = cur.rowcount
            conn.commit()
            print(f"🔧 Fixed {fixed_sport_count} records with NULL sport values (set to 'other')")
            missing_sport = 0  # Reset after fixing
        
        # Check for records with invalid coordinates (outside reasonable bounds)
        cur.execute("""
            SELECT COUNT(*) as count FROM courts 
            WHERE (region = %s OR region IS NULL) 
            AND centroid IS NOT NULL
            AND (ST_Y(centroid::geometry) < -90 OR ST_Y(centroid::geometry) > 90
                 OR ST_X(centroid::geometry) < -180 OR ST_X(centroid::geometry) > 180)
        """, [region])
        invalid_coords = cur.fetchone()['count']
        
        # Calculate quality metrics
        null_coords_pct = (null_coords / total_records * 100) if total_records > 0 else 0
        missing_sport_pct = (missing_sport / total_records * 100) if total_records > 0 else 0
        invalid_coords_pct = (invalid_coords / total_records * 100) if total_records > 0 else 0
        
        # Print quality report
        print(f"\n📊 Data Quality Report for {region}:")
        print(f"   Total records: {total_records:,}")
        print(f"   Null coordinates: {null_coords:,} ({null_coords_pct:.1f}%)")
        print(f"   Missing sport: {missing_sport:,} ({missing_sport_pct:.1f}%)")
        print(f"   Invalid coordinates: {invalid_coords:,} ({invalid_coords_pct:.1f}%)")
        print(f"   Duplicate OSM IDs: {len(duplicates)}")
        
        if duplicates:
            print(f"   Duplicate OSM IDs: {[d['osm_id'] for d in duplicates[:5]]}")
            if len(duplicates) > 5:
                print(f"   ... and {len(duplicates) - 5} more")
        
        # Quality thresholds
        quality_issues = []
        
        if null_coords_pct > 10:  # >10% null coordinates
            quality_issues.append(f"Too many null coordinates: {null_coords_pct:.1f}%")
        
        if missing_sport_pct > 5:  # >5% missing sport
            quality_issues.append(f"Too many missing sport values: {missing_sport_pct:.1f}%")
        
        if invalid_coords_pct > 1:  # >1% invalid coordinates
            quality_issues.append(f"Too many invalid coordinates: {invalid_coords_pct:.1f}%")
        
        if len(duplicates) > 0:  # Any duplicates
            quality_issues.append(f"Duplicate OSM IDs found: {len(duplicates)}")
        
        if total_records < 10:  # Too few records
            quality_issues.append(f"Too few records: {total_records}")
        
        # Determine overall quality
        if quality_issues:
            print(f"\n❌ Data quality issues found:")
            for issue in quality_issues:
                print(f"   - {issue}")
            
            print(f"\n❌ Data quality validation FAILED")
            print(f"   Environment: {environment}")
            print(f"   Region: {region}")
            
            cur.close()
            conn.close()
            sys.exit(1)
        else:
            print(f"\n✅ Data quality validation PASSED")
            print(f"   Environment: {environment}")
            print(f"   Region: {region}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Data quality validation failed: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Validate data quality after pipeline processing')
    parser.add_argument('--environment', required=True, help='Target environment (production)')
    parser.add_argument('--region', required=True, help='Region being processed')
    
    args = parser.parse_args()
    
    print(f"🚀 Starting data quality validation for {args.environment} environment, region: {args.region}")
    
    # Run async function
    asyncio.run(validate_data_quality(args.environment, args.region))

if __name__ == "__main__":
    main()

