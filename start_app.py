#!/usr/bin/env python3
"""
Startup script for Sneaker Agent
This script ensures the database is initialized before starting the Flask app.
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_database():
    """Check if database file exists and initialize if needed."""
    db_file = Path("sneaker_agent.db")
    
    if not db_file.exists():
        print("📁 Database file not found. Initializing...")
        from init_database import init_database
        init_database()
    else:
        print(f"✅ Database file found: {db_file}")
        print(f"📊 Database size: {db_file.stat().st_size / 1024:.1f} KB")

def main():
    """Main startup function."""
    print("🚀 Starting Sneaker Agent...")
    
    # Check and initialize database
    check_database()
    
    # Import and run the Flask app
    from app import app
    
    print("🌐 Starting Flask development server...")
    print("📱 Access your app at: http://localhost:5000")
    print("🔑 Admin login: sdclark117@gmail.com / admin123")
    print("⏹️  Press Ctrl+C to stop the server")
    
    # Run the Flask app
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug_mode, host="0.0.0.0", port=5000)

if __name__ == "__main__":
    main() 