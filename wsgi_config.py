import sys
import os

# Add your project directory to the Python path
path = '/home/yourusername/sneaker-agent'
if path not in sys.path:
    sys.path.append(path)

# Set environment variables
os.environ['FLASK_ENV'] = 'production'

# Import your Flask app
from app import app as application 