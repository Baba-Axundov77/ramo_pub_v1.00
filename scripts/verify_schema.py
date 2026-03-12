#!/usr/bin/env python3
# Database Schema Verification Script

import psycopg2
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

def get_database_url():
    """Get database URL from environment"""
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    database = os.getenv("DB_DATABASE", "ramo_pub")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "password")
    
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"

def verify_database_schema():
    """Verify database schema after SQLAlchemy 2.0 migration"""
    try:
        db_url = get_database_url()
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Check enum types
        cursor.execute("""
            SELECT typname 
            FROM pg_type 
            WHERE typtype = 'e' 
            ORDER BY typname
        """)
        
        enums = cursor.fetchall()
        print('=== PostgreSQL Enum Types ===')
        for enum in enums:
            print(f'OK {enum[0]}')
        
        # Check JSON columns
        cursor.execute("""
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE data_type IN ('json', 'jsonb')
            ORDER BY table_name, column_name
        """)
        
        json_columns = cursor.fetchall()
        print('\n=== JSON/JSONB Columns ===')
        for col in json_columns:
            print(f'OK {col[0]}.{col[1]} ({col[2]})')
        
        # Test enum functionality
        cursor.execute("""
            SELECT 'admin'::userrole, 'available'::tablestatus, 'new'::orderstatus
        """)
        
        result = cursor.fetchone()
        print(f'\n=== Enum Test ===')
        print(f'OK UserRole: {result[0]}')
        print(f'OK TableStatus: {result[1]}')
        print(f'OK OrderStatus: {result[2]}')
        
        # Check indexes
        cursor.execute("""
            SELECT indexname, tablename 
            FROM pg_indexes 
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname
            LIMIT 20
        """)
        
        indexes = cursor.fetchall()
        print(f'\n=== Database Indexes (first 20) ===')
        for idx in indexes:
            print(f'OK {idx[1]}.{idx[0]}')
        
        cursor.close()
        conn.close()
        print('\n=== Database Schema Verification: PASSED ===')
        return True
        
    except Exception as e:
        print(f'Error: {e}')
        print('=== Database Schema Verification: FAILED ===')
        return False

if __name__ == "__main__":
    verify_database_schema()
