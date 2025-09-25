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
        
        # Create backup table
        cur.execute(f"""
            CREATE TABLE {backup_name} AS 
            SELECT * FROM courts WHERE region = %s OR region IS NULL
        """, [region])
        
        # Record backup metadata
        cur.execute("""
            INSERT INTO courts_backups (backup_name, region, created_at)
            VALUES (%s, %s, NOW())
        """, [backup_name, region])
        
        # Get backup stats
        cur.execute(f"SELECT COUNT(*) as count FROM {backup_name}")
        backup_count = cur.fetchone()['count']
        
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

def main():
    parser = argparse.ArgumentParser(description='Create database backup before data pipeline')
    parser.add_argument('--environment', required=True, help='Target environment (staging/production)')
    parser.add_argument('--region', required=True, help='Region being processed')
    
    args = parser.parse_args()
    
    print(f"🚀 Starting backup for {args.environment} environment, region: {args.region}")
    
    # Run async function
    asyncio.run(create_backup(args.environment, args.region))

if __name__ == "__main__":
    main()

