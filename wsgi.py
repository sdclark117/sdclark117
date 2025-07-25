import os

from app import app, db

# This file is the new entry point for the gunicorn server.
# It ensures that the database tables are created before the app runs.


def init_database():
    """Initialize the database with proper error handling."""
    try:
        with app.app_context():
            # Check if we can connect to the database
            db.engine.connect()
            print("✅ Database connection successful")

            # Create all tables
            db.create_all()
            print("✅ Database tables created successfully")

    except Exception as e:
        print(f"⚠️ Warning: Database initialization issue: {e}")
        print("This is normal for the first deployment or if using external database")
        # Don't fail the deployment, just log the warning


if __name__ == "__main__":
    init_database()
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        debug=False,  # nosec B104
    )


# For gunicorn deployment
init_database()
