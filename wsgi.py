from app import app, db

# This file is the new entry point for the gunicorn server.
# It ensures that the database tables are created before the app runs.

with app.app_context():
    db.create_all()

# To run this application in a production environment, use:
# gunicorn --bind 0.0.0.0:10000 wsgi:app 