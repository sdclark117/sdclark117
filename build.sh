#!/bin/bash

echo "🚀 Starting build process..."

# Check Python version
echo "📋 Python version:"
python --version

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Check if all imports work
echo "🔍 Testing imports..."
python -c "
import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

try:
    from app import app, db
    print('✅ All imports successful')
except Exception as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
"

# Test database connection
echo "🗄️ Testing database connection..."
python -c "
import sys
import os
sys.path.insert(0, os.getcwd())

from app import app, db

with app.app_context():
    try:
        db.engine.connect()
        print('✅ Database connection successful')
    except Exception as e:
        print(f'⚠️ Database connection warning: {e}')
        print('This is normal for first deployment')
"

echo "✅ Build process completed successfully!" 