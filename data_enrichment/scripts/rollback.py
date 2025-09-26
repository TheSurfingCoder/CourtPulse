#!/usr/bin/env python3
"""
Rollback database to previous state after pipeline failure
"""

import os
import sys
import asyncio
import argparse
import psycopg2
from psycopg2.extras import RealDictCursor

async def rollback(environment: str, region: str):
    """Rollback to previous state"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        sys.exit(1)
    
    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        print(f"🔄 Looking for backup to rollback for region: {region}")
        
        # Find latest backup for this region
        cur.execute("""
            SELECT backup_name, created_at FROM courts_backups 
            WHERE region = %s 
            ORDER BY created_at DESC 
            LIMIT 1
        """, [region])
        
        result = cur.fetchone()
        if not result:
            print(f"❌ No backup found for region: {region}")
            print(f"   Available regions: {get_available_regions(cur)}")
            sys.exit(1)
        
        backup_name = result['backup_name']
        backup_created = result['created_at']
        print(f"🔄 Found backup: {backup_name}")
        print(f"   Created: {backup_created}")
        
        # Check if backup table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = %s
            )
        """, [backup_name])
        
        if not cur.fetchone()[0]:
            print(f"❌ Backup table {backup_name} does not exist")
            print(f"   This backup may have been corrupted or manually deleted")
            sys.exit(1)
        
        # Get current record count (full table since we backup everything)
        cur.execute("SELECT COUNT(*) as count FROM courts")
        current_count = cur.fetchone()['count']
        
        # Get backup record count
        cur.execute(f"SELECT COUNT(*) as count FROM {backup_name}")
        backup_count = cur.fetchone()['count']
        
        print(f"📊 Current records: {current_count}")
        print(f"📊 Backup records: {backup_count}")
        
        # Verify backup has reasonable data
        if backup_count == 0:
            print(f"❌ Backup table {backup_name} is empty - cannot rollback")
            sys.exit(1)
        
        if backup_count < 10:  # Suspiciously low record count
            print(f"⚠️  Warning: Backup has only {backup_count} records - this seems low")
        
        # Perform rollback
        print("🔄 Starting rollback...")
        
        # Delete current records (full table)
        cur.execute("DELETE FROM courts")
        deleted_count = cur.rowcount
        
        # Restore from backup
        cur.execute(f"INSERT INTO courts SELECT * FROM {backup_name}")
        restored_count = cur.rowcount
        
        # Verify rollback success
        cur.execute("SELECT COUNT(*) as count FROM courts")
        final_count = cur.fetchone()['count']
        
        if final_count != backup_count:
            print(f"❌ Rollback verification failed!")
            print(f"   Expected: {backup_count} records")
            print(f"   Actual: {final_count} records")
            conn.rollback()
            sys.exit(1)
        
        # Clean up backup table
        cur.execute(f"DROP TABLE {backup_name}")
        
        # Remove backup record
        cur.execute("DELETE FROM courts_backups WHERE backup_name = %s", [backup_name])
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✅ Rollback completed successfully!")
        print(f"   Deleted records: {deleted_count}")
        print(f"   Restored records: {restored_count}")
        print(f"   Final verification: {final_count} records")
        print(f"   Region: {region}")
        print(f"   Environment: {environment}")
        
    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        sys.exit(1)

def get_available_regions(cursor):
    """Get list of available regions from backups table"""
    try:
        cursor.execute("SELECT DISTINCT region FROM courts_backups ORDER BY region")
        regions = cursor.fetchall()
        return [r['region'] for r in regions]
    except:
        return ["unknown"]

def main():
    parser = argparse.ArgumentParser(description='Rollback database after pipeline failure')
    parser.add_argument('--environment', required=True, help='Target environment (staging/production)')
    parser.add_argument('--region', required=True, help='Region being processed')
    
    args = parser.parse_args()
    
    print(f"🚀 Starting rollback for {args.environment} environment, region: {args.region}")
    
    # Run async function
    asyncio.run(rollback(args.environment, args.region))

if __name__ == "__main__":
    main()

