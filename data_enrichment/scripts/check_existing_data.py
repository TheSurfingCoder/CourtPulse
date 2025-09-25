#!/usr/bin/env python3
"""
Check existing data in database before running pipeline
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

def check_existing_data(database_url: str):
    """Check what data already exists in the database"""
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check total records
        cur.execute("SELECT COUNT(*) as count FROM courts")
        total_records = cur.fetchone()['count']
        
        # Check records by region
        cur.execute("""
            SELECT 
                COALESCE(region, 'sf_bay') as region,
                COUNT(*) as count
            FROM courts 
            GROUP BY COALESCE(region, 'sf_bay')
            ORDER BY count DESC
        """)
        region_counts = cur.fetchall()
        
        # Check recent updates
        cur.execute("""
            SELECT 
                COUNT(*) as count,
                MAX(updated_at) as last_update
            FROM courts 
            WHERE updated_at > NOW() - INTERVAL '7 days'
        """)
        recent_updates = cur.fetchone()
        
        print("📊 EXISTING DATA SUMMARY")
        print("=" * 50)
        print(f"Total records: {total_records:,}")
        print()
        
        print("Records by region:")
        for row in region_counts:
            print(f"  {row['region']}: {row['count']:,}")
        print()
        
        print("Recent activity (last 7 days):")
        print(f"  Updated records: {recent_updates['count']:,}")
        print(f"  Last update: {recent_updates['last_update']}")
        print()
        
        # Check for data that might be overwritten
        if total_records > 0:
            print("⚠️  WARNING: Existing data will be updated/overwritten")
            print("   - Records with matching OSM IDs will be updated")
            print("   - New records will be inserted")
            print("   - Backup will be created before processing")
        else:
            print("✅ No existing data - safe to proceed")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        sys.exit(1)

def main():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        sys.exit(1)
    
    check_existing_data(database_url)

if __name__ == "__main__":
    main()
