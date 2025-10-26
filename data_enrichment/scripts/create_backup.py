#!/usr/bin/env python3
"""
Create database backup before running data pipeline
"""

import os
import sys
import asyncio
import argparse
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

async def create_backup(environment: str, region: str):
    """Create backup before processing"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        sys.exit(1)
    
    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Create backup table name
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"courts_backup_{region}_{timestamp}"
        
        print(f"🔄 Creating backup: {backup_name}")
        
        # Create backup table (full table backup)
        cur.execute(f"""
            CREATE TABLE {backup_name} AS 
            SELECT * FROM courts
        """)
        
        # Record backup metadata
        cur.execute("""
            INSERT INTO courts_backups (backup_name, region, created_at)
            VALUES (%s, %s, NOW())
        """, [backup_name, region])
        
        # Get backup stats
        cur.execute(f"SELECT COUNT(*) as count FROM {backup_name}")
        backup_count = cur.fetchone()['count']
        
        # Clean up old backups (keep only 10 most recent)
        cleanup_old_backups(cur, region, keep_count=10)
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✅ Backup created successfully: {backup_name}")
        print(f"   Records backed up: {backup_count}")
        print(f"   Region: {region}")
        print(f"   Environment: {environment}")
        
        return backup_name
        
    except Exception as e:
        print(f"❌ Backup creation failed: {e}")
        sys.exit(1)

def cleanup_old_backups(cursor, region: str, keep_count: int = 10):
    """Keep only the most recent backups, delete older ones"""
    try:
        # Get all backups for this region, ordered by created_at DESC
        cursor.execute("""
            SELECT backup_name FROM courts_backups 
            WHERE region = %s 
            ORDER BY created_at DESC
        """, [region])
        
        all_backups = cursor.fetchall()
        
        if len(all_backups) > keep_count:
            # Get backups to delete (keep only the first 'keep_count')
            backups_to_delete = all_backups[keep_count:]
            
            print(f"🧹 Cleaning up {len(backups_to_delete)} old backups...")
            
            for backup in backups_to_delete:
                backup_name = backup['backup_name']
                
                # Check if backup table exists before trying to drop it
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    )
                """, [backup_name])
                
                if cursor.fetchone()[0]:
                    # Drop the backup table
                    cursor.execute(f"DROP TABLE {backup_name}")
                    print(f"   🗑️  Dropped table: {backup_name}")
                
                # Remove from metadata table
                cursor.execute("DELETE FROM courts_backups WHERE backup_name = %s", [backup_name])
                print(f"   🗑️  Removed metadata: {backup_name}")
            
            print(f"✅ Cleanup completed: {len(backups_to_delete)} old backups removed")
        else:
            print(f"✅ No cleanup needed: {len(all_backups)} backups (limit: {keep_count})")
            
    except Exception as e:
        print(f"⚠️  Warning: Backup cleanup failed: {e}")
        # Don't fail the entire backup process if cleanup fails

def main():
    parser = argparse.ArgumentParser(description='Create database backup before data pipeline')
    parser.add_argument('--environment', required=True, help='Target environment (production)')
    parser.add_argument('--region', required=True, help='Region being processed')
    
    args = parser.parse_args()
    
    print(f"🚀 Starting backup for {args.environment} environment, region: {args.region}")
    
    # Run async function
    asyncio.run(create_backup(args.environment, args.region))

if __name__ == "__main__":
    main()

