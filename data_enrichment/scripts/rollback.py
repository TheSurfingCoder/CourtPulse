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
            SELECT backup_name FROM courts_backups 
            WHERE region = %s 
            ORDER BY created_at DESC 
            LIMIT 1
        """, [region])
        
        result = cur.fetchone()
        if not result:
            print(f"❌ No backup found for region: {region}")
            sys.exit(1)
        
        backup_name = result['backup_name']
        print(f"🔄 Found backup: {backup_name}")
        
        # Check if backup table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = %s
            )
        """, [backup_name])
        
        if not cur.fetchone()[0]:
            print(f"❌ Backup table {backup_name} does not exist")
            sys.exit(1)
        
        # Get current record count
        cur.execute("SELECT COUNT(*) as count FROM courts WHERE region = %s OR region IS NULL", [region])
        current_count = cur.fetchone()['count']
        
        # Get backup record count
        cur.execute(f"SELECT COUNT(*) as count FROM {backup_name}")
        backup_count = cur.fetchone()['count']
        
        print(f"📊 Current records: {current_count}")
        print(f"📊 Backup records: {backup_count}")
        
        # Perform rollback
        print("🔄 Starting rollback...")
        
        # Delete current records for this region
        cur.execute("DELETE FROM courts WHERE region = %s OR region IS NULL", [region])
        deleted_count = cur.rowcount
        
        # Restore from backup
        cur.execute(f"INSERT INTO courts SELECT * FROM {backup_name}")
        restored_count = cur.rowcount
        
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
        print(f"   Region: {region}")
        print(f"   Environment: {environment}")
        
    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        sys.exit(1)

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

