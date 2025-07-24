#!/usr/bin/env python3
"""
Database backup script for Sneaker Agent
This script creates a backup of the database file.
"""

import os
import sys
import shutil
from datetime import datetime
from pathlib import Path

def backup_database():
    """Create a backup of the database file."""
    
    db_file = Path("sneaker_agent.db")
    if not db_file.exists():
        print("❌ Database file not found!")
        return False
    
    # Create backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = Path(f"sneaker_agent_backup_{timestamp}.db")
    
    try:
        # Copy the database file
        shutil.copy2(db_file, backup_file)
        
        print(f"✅ Database backed up successfully!")
        print(f"📁 Original: {db_file}")
        print(f"📁 Backup: {backup_file}")
        print(f"📊 Backup size: {backup_file.stat().st_size / 1024:.1f} KB")
        
        return True
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False

def list_backups():
    """List all available backups."""
    backup_files = list(Path(".").glob("sneaker_agent_backup_*.db"))
    
    if not backup_files:
        print("📁 No backup files found")
        return
    
    print("📁 Available backups:")
    for backup in sorted(backup_files, reverse=True):
        size = backup.stat().st_size / 1024
        modified = datetime.fromtimestamp(backup.stat().st_mtime)
        print(f"   {backup.name} ({size:.1f} KB, {modified.strftime('%Y-%m-%d %H:%M:%S')})")

def restore_backup(backup_filename):
    """Restore database from backup."""
    
    backup_file = Path(backup_filename)
    if not backup_file.exists():
        print(f"❌ Backup file not found: {backup_filename}")
        return False
    
    db_file = Path("sneaker_agent.db")
    
    try:
        # Create backup of current database if it exists
        if db_file.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            current_backup = Path(f"sneaker_agent_current_{timestamp}.db")
            shutil.copy2(db_file, current_backup)
            print(f"📁 Current database backed up as: {current_backup}")
        
        # Restore from backup
        shutil.copy2(backup_file, db_file)
        
        print(f"✅ Database restored successfully!")
        print(f"📁 Restored from: {backup_file}")
        print(f"📁 To: {db_file}")
        
        return True
    except Exception as e:
        print(f"❌ Restore failed: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Database backup utility")
    parser.add_argument("action", choices=["backup", "list", "restore"], 
                       help="Action to perform")
    parser.add_argument("--file", help="Backup file to restore from (for restore action)")
    
    args = parser.parse_args()
    
    if args.action == "backup":
        backup_database()
    elif args.action == "list":
        list_backups()
    elif args.action == "restore":
        if not args.file:
            print("❌ Please specify a backup file with --file")
            sys.exit(1)
        restore_backup(args.file) 