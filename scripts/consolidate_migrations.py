# Migration Squashing Script
# This script consolidates all existing migrations into a single initial schema

import os
import shutil
from datetime import datetime

def backup_existing_migrations():
    """Backup existing migration files"""
    backup_dir = f"migrations/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    
    versions_dir = "migrations/versions"
    if os.path.exists(versions_dir):
        for file in os.listdir(versions_dir):
            if file.endswith('.py') and file != 'v1_initial_schema.py':
                shutil.move(os.path.join(versions_dir, file), os.path.join(backup_dir, file))
        print(f"Existing migrations backed up to: {backup_dir}")

def update_alembic_head():
    """Update alembic to point to the new consolidated migration"""
    # This would typically be done with: alembic stamp v1_initial_schema
    print("Run: alembic stamp v1_initial_schema to update the migration history")

if __name__ == "__main__":
    print("Starting migration consolidation...")
    backup_existing_migrations()
    update_alembic_head()
    print("Migration consolidation completed!")
    print("\nNext steps:")
    print("1. Review the new v1_initial_schema.py migration")
    print("2. Run: alembic stamp v1_initial_schema")
    print("3. Test the migration on a development database")
