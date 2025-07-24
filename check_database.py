#!/usr/bin/env python3
"""
Database status checker for Sneaker Agent
This script shows the current database status and user information.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User

def check_database_status():
    """Check and display database status."""
    
    db_file = Path("sneaker_agent.db")
    
    print("🔍 Database Status Check")
    print("=" * 50)
    
    # Check if database file exists
    if db_file.exists():
        size_kb = db_file.stat().st_size / 1024
        modified = datetime.fromtimestamp(db_file.stat().st_mtime)
        print(f"✅ Database file found: {db_file}")
        print(f"📊 Size: {size_kb:.1f} KB")
        print(f"📅 Last modified: {modified.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("❌ Database file not found!")
        print("💡 Run 'python init_database.py' to create the database")
        return
    
    # Check database contents
    with app.app_context():
        try:
            total_users = User.query.count()
            admin_users = User.query.filter_by(is_admin=True).count()
            verified_users = User.query.filter_by(is_verified=True).count()
            
            print(f"\n👥 User Statistics:")
            print(f"   Total users: {total_users}")
            print(f"   Admin users: {admin_users}")
            print(f"   Verified users: {verified_users}")
            
            # Show admin users
            if admin_users > 0:
                print(f"\n👑 Admin Users:")
                admin_list = User.query.filter_by(is_admin=True).all()
                for user in admin_list:
                    print(f"   • {user.email} (Plan: {user.current_plan})")
            
            # Show recent users
            recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
            if recent_users:
                print(f"\n📅 Recent Users:")
                for user in recent_users:
                    created = user.created_at.strftime('%Y-%m-%d %H:%M')
                    print(f"   • {user.email} (Created: {created})")
            
            print(f"\n✅ Database is healthy and accessible!")
            
        except Exception as e:
            print(f"❌ Database error: {e}")
            print("💡 Try running 'python init_database.py' to fix the database")

if __name__ == "__main__":
    check_database_status() 