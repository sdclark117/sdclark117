#!/usr/bin/env python3
"""
Database initialization script for Sneaker Agent
This script sets up the database and preserves existing user data.
"""

import os
import sys
from datetime import datetime
from werkzeug.security import generate_password_hash

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, UserSettings, EmailVerificationToken, PasswordResetToken, GuestUsage

def init_database():
    """Initialize the database with tables and default admin user."""
    
    with app.app_context():
        print("🔧 Initializing database...")
        
        # Create all tables
        db.create_all()
        print("✅ Database tables created")
        
        # Check if admin user exists
        admin_user = User.query.filter_by(email='sdclark117@gmail.com').first()
        
        if not admin_user:
            print("👤 Creating default admin user...")
            admin_user = User(
                email='sdclark117@gmail.com',
                password_hash=generate_password_hash('admin123'),
                name='Dylan',
                is_admin=True,
                current_plan='admin',
                is_verified=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print("✅ Default admin user created")
        else:
            print("✅ Admin user already exists")
        
        # Check if second admin user exists
        admin_user2 = User.query.filter_by(email='kasieewardd@gmail.com').first()
        
        if not admin_user2:
            print("👤 Creating second admin user...")
            admin_user2 = User(
                email='kasieewardd@gmail.com',
                password_hash=generate_password_hash('admin123'),
                name='Kasie',
                is_admin=True,
                current_plan='admin',
                is_verified=True
            )
            db.session.add(admin_user2)
            db.session.commit()
            print("✅ Second admin user created")
        else:
            print("✅ Second admin user already exists")
        
        # Count total users
        total_users = User.query.count()
        print(f"📊 Total users in database: {total_users}")
        
        print("\n🎉 Database initialization complete!")
        print("📁 Database file: sneaker_agent.db")
        print("\n🔑 Admin credentials:")
        print("   Email: sdclark117@gmail.com")
        print("   Password: admin123")
        print("   Email: kasieewardd@gmail.com")
        print("   Password: admin123")

if __name__ == "__main__":
    init_database() 