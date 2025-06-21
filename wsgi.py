from waitress import serve
from app import app, db

# This file is the new entry point for the gunicorn server.
# It ensures that the database tables are created before the app runs.

with app.app_context():
    db.create_all()

# To run this application in a production environment, use:
# gunicorn --bind 0.0.0.0:10000 wsgi:app

if __name__ == '__main__':
    print("Starting production server on http://localhost:8080")
    serve(app, host='0.0.0.0', port=8080, threads=4) 