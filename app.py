import json
import logging
import os
import secrets
import sys
import time
from datetime import datetime, timedelta
from functools import wraps
from io import BytesIO
from typing import Any, Dict, Optional

import click
import googlemaps
import gspread
import pandas as pd
import stripe
from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask.cli import with_appcontext
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_mail import Mail, Message
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from google.oauth2.service_account import Credentials
from openpyxl import Workbook
from werkzeug.security import check_password_hash, generate_password_hash

# Load environment variables
load_dotenv()

app = Flask(__name__)
secret_key = os.getenv("SECRET_KEY")
if not secret_key:
    # Generate a secure random key if none is provided
    secret_key = secrets.token_hex(32)
    print("WARNING: No SECRET_KEY environment variable set. Generated a temporary key.")
    print("Please set SECRET_KEY environment variable for production use.")
app.secret_key = secret_key

# Logging setup
app.logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
if not any(isinstance(h, logging.StreamHandler) for h in app.logger.handlers):
    app.logger.addHandler(handler)

# Gunicorn integration
if "gunicorn" in os.environ.get("SERVER_SOFTWARE", ""):
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

# Database Configuration
db_url = os.environ.get("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
elif not db_url:
    # Use persistent SQLite database file
    db_url = "sqlite:///sneaker_agent.db"
    print(f"📁 Using persistent database: {db_url}")

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=30)
app.config["REMEMBER_COOKIE_HTTPONLY"] = True
app.config["REMEMBER_COOKIE_SECURE"] = os.environ.get("FLASK_ENV") == "production"
app.config["GOOGLE_API_KEY"] = os.environ.get("GOOGLE_MAPS_API_KEY")

# Email configuration
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.getenv("GMAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("GMAIL_APP_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("GMAIL_USERNAME")

mail = Mail(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    db.drop_all()
    db.create_all()
    click.echo("Initialized the database.")


app.cli.add_command(init_db_command)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "index"  # type: ignore


@login_manager.unauthorized_handler
def unauthorized_callback():
    """Handle unauthorized access attempts."""
    if request.path.startswith("/api/"):
        return jsonify(error="Authentication required to access this endpoint."), 401
    flash("You must be logged in to view this page.")
    return redirect(url_for("index"))


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(512), nullable=False)
    name = db.Column(db.String(100))
    business = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    trial_ends_at = db.Column(db.DateTime)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    stripe_customer_id = db.Column(db.String(120), unique=True)
    stripe_subscription_id = db.Column(db.String(120), unique=True)
    current_plan = db.Column(db.String(50))
    search_count = db.Column(db.Integer, default=0)
    last_search_reset = db.Column(db.DateTime)
    settings = db.relationship(
        "UserSettings", backref="user", uselist=False, cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class EmailVerificationToken(db.Model):
    __tablename__ = "email_verification_tokens"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    token = db.Column(db.String(128), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, user_id, token, expires_at):
        self.user_id = user_id
        self.token = token
        self.expires_at = expires_at


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    token = db.Column(db.String(128), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, user_id, token, expires_at):
        self.user_id = user_id
        self.token = token
        self.expires_at = expires_at


class GuestUsage(db.Model):
    __tablename__ = "guest_usage"
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=False, index=True)  # IPv6 compatible
    user_agent = db.Column(db.String(500))
    search_count = db.Column(db.Integer, default=0)
    first_visit = db.Column(db.DateTime, default=datetime.utcnow)
    last_visit = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __init__(self, ip_address, user_agent):
        self.ip_address = ip_address
        self.user_agent = user_agent


class UserSettings(db.Model):
    __tablename__ = "user_settings"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False
    )
    default_radius = db.Column(db.Integer, default=5)
    default_business_type = db.Column(db.String(100))
    remember_last_search = db.Column(db.Boolean, default=False)
    results_per_page = db.Column(db.Integer, default=25)
    show_map_by_default = db.Column(db.Boolean, default=True)
    email_notifications = db.Column(db.Boolean, default=True)
    search_reminders = db.Column(db.Boolean, default=False)
    last_search_city = db.Column(db.String(100))
    last_search_state = db.Column(db.String(100))
    last_search_business_type = db.Column(db.String(100))
    last_search_radius = db.Column(db.Integer)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def generate_token():
    return secrets.token_urlsafe(32)


def get_client_ip():
    """Get the client's IP address, handling proxies."""
    # Check for forwarded headers first (common with proxies)
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    elif request.headers.get("X-Real-IP"):
        return request.headers.get("X-Real-IP")
    elif request.headers.get("X-Client-IP"):
        return request.headers.get("X-Client-IP")
    else:
        return request.remote_addr


def get_or_create_guest_usage():
    """Get or create guest usage tracking for the current IP."""
    if current_user.is_authenticated:
        return None

    ip_address = get_client_ip()
    user_agent = request.headers.get("User-Agent", "")

    # Try to find existing guest usage
    guest_usage = GuestUsage.query.filter_by(ip_address=ip_address).first()

    if guest_usage:
        # Update last visit
        guest_usage.last_visit = datetime.utcnow()
        db.session.commit()
        return guest_usage
    else:
        # Create new guest usage record
        guest_usage = GuestUsage(ip_address=ip_address, user_agent=user_agent)
        db.session.add(guest_usage)
        db.session.commit()
        return guest_usage


def send_email(subject, recipients, body, html_body=None):
    try:
        msg = Message(subject, recipients=recipients)
        msg.body = body
        if html_body:
            msg.html = html_body
        mail.send(msg)
        return True
    except Exception as e:
        app.logger.error(f"Email sending error: {e}")
        return False


def send_verification_email(user_id, email, name):
    token = generate_token()
    expires_at = datetime.utcnow() + timedelta(hours=24)
    new_token = EmailVerificationToken(
        user_id=user_id, token=token, expires_at=expires_at
    )
    db.session.add(new_token)
    db.session.commit()

    verification_url = url_for("verify_email", token=token, _external=True)
    subject = "Verify Your Email - Business Lead Finder"
    html_body = render_template(
        "email_verification.html", name=name, verification_url=verification_url
    )
    body = (
        f"Hello {name or 'there'}! Please verify your email by clicking this link: "
        f"{verification_url}"
    )

    return send_email(subject, [email], body, html_body)


def send_password_reset_email(user_id, email, name):
    token = generate_token()
    expires_at = datetime.utcnow() + timedelta(hours=1)
    new_token = PasswordResetToken(user_id=user_id, token=token, expires_at=expires_at)
    db.session.add(new_token)
    db.session.commit()

    reset_url = url_for("reset_password_page", token=token, _external=True)
    subject = "Password Reset - Business Lead Finder"
    html_body = render_template("password_reset.html", name=name, reset_url=reset_url)
    body = (
        f"Hello {name or 'there'}! Please reset your password by clicking this link: "
        f"{reset_url}"
    )

    return send_email(subject, [email], body, html_body)


def cleanup_expired_tokens():
    """Clean up expired verification and reset tokens."""
    try:
        now = datetime.utcnow()

        # Clean up expired verification tokens
        expired_verification_tokens = (
            db.session.query(EmailVerificationToken)
            .filter(EmailVerificationToken.expires_at < now)
            .all()
        )  # type: ignore
        for token in expired_verification_tokens:
            db.session.delete(token)

        # Clean up expired reset tokens
        expired_reset_tokens = (
            db.session.query(PasswordResetToken)
            .filter(PasswordResetToken.expires_at < now)
            .all()
        )  # type: ignore
        for token in expired_reset_tokens:
            db.session.delete(token)

        db.session.commit()
        app.logger.info(
            f"Cleaned up {len(expired_verification_tokens)} expired verification tokens "
            f"and {len(expired_reset_tokens)} expired reset tokens"
        )
    except Exception as e:
        app.logger.error(f"Error cleaning up expired tokens: {e}")
        db.session.rollback()


def reset_guest_usage_daily():
    """Reset guest usage counts daily to allow new free searches."""
    try:
        # Reset search counts for guest usage older than 24 hours
        yesterday = datetime.utcnow() - timedelta(days=1)

        guest_usage_to_reset = GuestUsage.query.filter(
            GuestUsage.updated_at < yesterday
        ).all()

        for guest_usage in guest_usage_to_reset:
            guest_usage.search_count = 0
            guest_usage.updated_at = datetime.utcnow()

        db.session.commit()

        if guest_usage_to_reset:
            app.logger.info(
                f"Reset search counts for {len(guest_usage_to_reset)} guest IPs"
            )

    except Exception as e:
        app.logger.error(f"Error resetting guest usage: {e}")
        db.session.rollback()


def get_coordinates(location_query: str, api_key: str) -> Optional[Dict[str, float]]:
    """Get coordinates for a location query using Google Maps Geocoding API."""
    if not api_key:
        app.logger.error("No Google API key provided for geocoding")
        return None

    # Log API key info (without exposing the full key)
    api_key_preview = api_key[:10] + "..." if len(api_key) > 10 else api_key
    app.logger.info(f"Using API key: {api_key_preview}")

    gmaps = googlemaps.Client(key=api_key)
    try:
        app.logger.info(f"Geocoding location query: '{location_query}'")
        geocode_result = gmaps.geocode(location_query)  # type: ignore

        # Log the raw response for debugging
        app.logger.info(f"Geocoding raw response: {geocode_result}")

        if geocode_result:
            location = geocode_result[0]["geometry"]["location"]
            app.logger.info(f"Geocoding result for '{location_query}': {location}")
            return {"lat": location["lat"], "lng": location["lng"]}
        else:
            app.logger.warning(
                f"Geocoding returned no results for query: '{location_query}'"
            )
            return None
    except googlemaps.exceptions.ApiError as e:
        app.logger.error(f"Geocoding API error for query '{location_query}': {e}")
        app.logger.error(f"API Error details: {str(e)}")
        return None
    except Exception as e:
        app.logger.error(
            f"An unexpected error occurred during geocoding for query "
            f"'{location_query}': {e}"
        )
        return None


# Add this near the top of app.py, after imports
CATEGORY_FALLBACKS = {
    "food": "restaurant",
    "shop": "store",
    "shopping": "store",
    "drinks": "bar",
    "coffee": "cafe",
    "eat": "restaurant",
    "groceries": "supermarket",
    "market": "supermarket",
    "gas": "gas_station",
    "gas station": "gas_station",
    "pharmacy": "pharmacy",
    "doctor": "doctor",
    "health": "hospital",
    "fitness": "gym",
    "workout": "gym",
    "hotel": "lodging",
    "stay": "lodging",
    "car": "car_repair",
    "auto": "car_repair",
    "mechanic": "car_repair",
    # Add more as needed
}


def search_places(lat, lng, business_type, radius, api_key, max_reviews=100):
    """Search for places using Google Places API."""
    if not api_key:
        app.logger.error("No Google API key provided for places search")
        return [], {"lat": lat, "lng": lng}

    gmaps = googlemaps.Client(key=api_key)
    all_leads = []
    seen_place_ids = set()

    # Fallback to a broader category if needed
    search_term = CATEGORY_FALLBACKS.get(
        str(business_type).strip().lower(), business_type
    )
    app.logger.info(
        f"Searching places: lat={lat}, lng={lng}, radius={radius}, "
        f"business_type='{business_type}', search_term='{search_term}', "
        f"max_reviews={max_reviews}"
    )

    # Initial search request
    try:
        places_result = gmaps.places_nearby(  # type: ignore
            location=(lat, lng), radius=radius, keyword=search_term, language="en"
        )
    except Exception as e:
        app.logger.error(f"Error calling Google Places API: {e}")
        return [], {"lat": lat, "lng": lng}

    total_google_results = 0
    total_after_filter = 0

    while True:
        api_response_data = places_result
        if not api_response_data or api_response_data.get("status") != "OK":
            break
        current_results = api_response_data.get("results", [])
        total_google_results += len(current_results)
        for place in current_results:
            place_id = place.get("place_id")
            if place_id in seen_place_ids:
                continue
            seen_place_ids.add(place_id)
            if is_potential_lead(place):
                try:
                    details = get_place_details(place_id, api_key)
                    if details:
                        user_ratings_total = details.get("user_ratings_total")
                        if max_reviews is not None and user_ratings_total is not None:
                            if user_ratings_total > max_reviews:
                                continue
                        lead_data = {
                            "place_id": place_id,
                            "name": details.get("name"),
                            "address": details.get("formatted_address"),
                            "lat": details["geometry"]["location"]["lat"],
                            "lng": details["geometry"]["location"]["lng"],
                            "rating": details.get("rating"),
                            "website": details.get("website"),
                            "phone": details.get("formatted_phone_number"),
                            "opening_hours": format_opening_hours(
                                details.get("opening_hours", {})
                            ),
                            "reviews": user_ratings_total,
                            "business_type": format_business_types(
                                details.get("types", [])
                            ),
                            "business_status": place.get("business_status"),
                        }
                        all_leads.append(lead_data)
                        total_after_filter += 1
                except Exception as e:
                    app.logger.error(
                        (
                            "Error processing place details for '"
                            + str(place.get("name"))[:40]
                            + str(place.get("name"))[40:]
                            + "': "
                            + str(e)[:40]
                            + str(e)[40:]
                        )
                    )
        next_page_token = api_response_data.get("next_page_token")
        if not next_page_token:
            break
        time.sleep(2)
        try:
            places_result = gmaps.places_nearby(page_token=next_page_token)  # type: ignore
        except Exception as e:
            app.logger.error(f"Error fetching next page from Google Places API: {e}")
            break
    final_leads = list({lead["place_id"]: lead for lead in all_leads}.values())
    app.logger.info(
        f"Total Google results: {total_google_results}, After filtering: "
        f"{total_after_filter}, Final unique leads: {len(final_leads)}"
    )
    return final_leads, {"lat": lat, "lng": lng}


def get_place_details(place_id: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Get detailed information about a place using Google Places API."""
    gmaps = googlemaps.Client(key=api_key)
    fields = [
        "name",
        "formatted_address",
        "international_phone_number",
        "website",
        "rating",
        "user_ratings_total",
        "opening_hours",
        "geometry",
    ]
    try:
        place_details = gmaps.place(place_id=place_id, fields=fields)  # type: ignore
        if place_details and place_details.get("result"):
            return place_details["result"]
        else:
            app.logger.warning(f"Could not get details for place_id: {place_id}")
            return None
    except googlemaps.exceptions.ApiError as e:
        app.logger.error(
            (
                "API Error getting place details for "
                + str(place_id)[:40]
                + str(place_id)[40:]
                + ": "
                + str(e)[:40]
                + str(e)[40:]
            )
        )
        return None
    except Exception as e:
        app.logger.error(f"Unexpected error getting place details for {place_id}: {e}")
        return None


def is_potential_lead(place):
    """Check if a place is a potential lead based on business status."""
    return place.get("business_status") == "OPERATIONAL"


def format_opening_hours(hours_data):
    """Format opening hours data for display."""
    if not hours_data or not hours_data.get("weekday_text"):
        return "Not available"
    return "\n".join(hours_data["weekday_text"])


def format_business_types(types):
    """Format business types for display."""
    if not types:
        return "N/A"
    return ", ".join(t.replace("_", " ").title() for t in types)


@app.route("/")
def index():
    # Restore the use of the environment variable for the API key
    google_maps_api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    return render_template("index.html", google_maps_api_key=google_maps_api_key)


@app.route("/verify-email/<token>")
def verify_email(token: str):
    """Verify user email with token."""
    try:
        verification_record = EmailVerificationToken.query.filter_by(
            token=token
        ).first()
        if verification_record and verification_record.expires_at > datetime.utcnow():
            user = User.query.get(verification_record.user_id)
            if user:
                user.is_verified = True
                db.session.delete(verification_record)
                db.session.commit()
                flash("Email verified successfully! You can now log in.", "success")
            else:
                flash("User not found.", "danger")
        else:
            flash("Invalid or expired verification link.", "danger")
    except Exception as e:
        app.logger.error(f"Error during email verification: {e}")
        flash("An error occurred during verification.", "danger")
    return redirect(url_for("index"))


@app.route("/reset-password/<token>")
def reset_password_page(token):
    """Display password reset page."""
    try:
        reset_record = PasswordResetToken.query.filter_by(token=token).first()
        if reset_record and reset_record.expires_at > datetime.utcnow():
            return render_template("password_reset.html", token=token)
        else:
            flash("Invalid or expired password reset link.", "danger")
    except Exception as e:
        app.logger.error(f"Error during password reset page access: {e}")
        flash("An error occurred.", "danger")
    return redirect(url_for("index"))


@app.route("/api/register", methods=["POST"])
def register():
    """Register a new user."""
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ["email", "password", "name"]):
            return jsonify(error="Missing required data"), 400

        email = data["email"].lower().strip()
        if User.query.filter_by(email=email).first():
            return jsonify(error="Email already exists"), 409

        password_hash = generate_password_hash(data["password"])

        new_user = User(
            email=email,
            password_hash=password_hash,
            name=data["name"].strip(),
            trial_ends_at=datetime.utcnow() + timedelta(days=7),
        )

        db.session.add(new_user)
        db.session.commit()

        send_verification_email(new_user.id, new_user.email, new_user.name)
        login_user(new_user, remember=True)

        return jsonify(message="Registration successful!"), 201
    except Exception as e:
        app.logger.error(f"Error during registration: {e}")
        db.session.rollback()
        return jsonify(error="An error occurred during registration."), 500


@app.route("/api/login", methods=["POST"])
def login():
    """Log in a user."""
    try:
        data = request.get_json()
        app.logger.info(f"Login attempt - data received: {bool(data)}")

        if not data or not data.get("email") or not data.get("password"):
            app.logger.warning("Login failed - missing email or password")
            return jsonify(error="Missing email or password"), 400

        email = data["email"].lower().strip()
        password = data["password"]
        app.logger.info(f"Login attempt for email: {email}")

        user = User.query.filter_by(email=email).first()
        app.logger.info(f"User found: {bool(user)}")

        if user:
            password_check = user.check_password(password)
            app.logger.info(f"Password check result: {password_check}")

            if password_check:
                login_user(user, remember=data.get("remember", False))
                app.logger.info(f"Login successful for user: {user.email}")
                return jsonify(message="Login successful"), 200
            else:
                app.logger.warning(
                    f"Login failed - incorrect password for user: {email}"
                )
        else:
            app.logger.warning(f"Login failed - user not found: {email}")

        return jsonify(error="Invalid email or password"), 401
    except Exception as e:
        app.logger.error(f"Error during login: {e}")
        return jsonify(error="An error occurred during login."), 500


@app.route("/api/logout", methods=["POST"])
@login_required
def logout():
    """Log out the current user."""
    try:
        app.logger.info(f"🔧 Logout attempt for user: {current_user.email}")
        logout_user()
        app.logger.info(f"✅ Logout successful for user: {current_user.email}")
        return jsonify(message="Logout successful"), 200
    except Exception as e:
        app.logger.error(f"❌ Logout error: {e}")
        return jsonify(error="Logout failed"), 500


@app.route("/api/profile", methods=["PUT"])
@login_required
def update_profile():
    """Update user profile information."""
    try:
        data = request.get_json()
        if not data:
            return jsonify(error="Invalid data"), 400

        current_user.name = data.get("name", current_user.name)
        current_user.business = data.get("business", current_user.business)
        current_user.phone = data.get("phone", current_user.phone)
        db.session.commit()

        return jsonify(message="Profile updated successfully"), 200
    except Exception as e:
        app.logger.error(f"Error updating profile: {e}")
        db.session.rollback()
        return jsonify(error="An error occurred while updating profile."), 500


@app.route("/api/request-password-reset", methods=["POST"])
def request_password_reset():
    """Request a password reset email."""
    try:
        data = request.get_json()
        if not data:
            return jsonify(error="No data provided"), 400

        email = data.get("email", "").lower().strip()
        user = User.query.filter_by(email=email).first()
        if user:
            send_password_reset_email(user.id, user.email, user.name)
        return (
            jsonify(
                message="If an account with that email exists, a reset link has been sent."
            ),
            200,
        )
    except Exception as e:
        app.logger.error(f"Error requesting password reset: {e}")
        return jsonify(error="An error occurred while processing your request."), 500


@app.route("/api/reset-password/<token>", methods=["POST"])
def reset_password(token):
    """Reset password using token."""
    try:
        reset_record = PasswordResetToken.query.filter_by(token=token).first()
        if not (reset_record and reset_record.expires_at > datetime.utcnow()):
            return jsonify(error="Invalid or expired token."), 400

        data = request.get_json()
        if not data:
            return jsonify(error="No data provided"), 400

        password = data.get("password")
        if not password:
            return jsonify(error="Password is required."), 400

        user = User.query.get(reset_record.user_id)
        if user:
            user.password_hash = generate_password_hash(password)
            db.session.delete(reset_record)
            db.session.commit()
            return jsonify(message="Password has been reset successfully."), 200
        else:
            return jsonify(error="User not found."), 404
    except Exception as e:
        app.logger.error(f"Error resetting password: {e}")
        db.session.rollback()
        return jsonify(error="An error occurred while resetting password."), 500


@app.route("/api/send-verification-email", methods=["POST"])
@login_required
def send_verification_email_api():
    """Send verification email to current user."""
    try:
        if current_user.is_verified:
            return jsonify(error="Your email is already verified."), 400
        send_verification_email(current_user.id, current_user.email, current_user.name)
        return jsonify(message="Verification email sent."), 200
    except Exception as e:
        app.logger.error(f"Error sending verification email: {e}")
        return jsonify(error="An error occurred while sending verification email."), 500


@app.route("/api/check-auth")
def check_auth():
    """Check if user is authenticated and return user info."""
    if current_user.is_authenticated:
        app.logger.info(f"🔧 Check-auth for user: {current_user.email}")
        app.logger.info(f"🔧 User is_admin: {current_user.is_admin}")
        app.logger.info(f"🔧 User current_plan: {current_user.current_plan}")

        return jsonify(
            {
                "is_logged_in": True,
                "user": {
                    "name": current_user.name,
                    "email": current_user.email,
                    "is_verified": current_user.is_verified,
                    "current_plan": current_user.current_plan,
                    "is_admin": current_user.is_admin,
                },
            }
        )
    return jsonify({"is_logged_in": False})


@app.route("/api/search", methods=["POST"])
def search():
    """Search for business leads."""
    try:
        data = request.get_json()
        if not data:
            return jsonify(error="No data provided"), 400

        business_type = data.get("business_type")
        radius_miles = data.get("radius", 3)  # Default to 3 miles
        max_reviews = data.get("max_reviews")

        try:
            radius_miles = int(radius_miles)
        except (ValueError, TypeError):
            radius_miles = 3  # Default to 3 if conversion fails

        # Convert miles to meters
        radius_meters = radius_miles * 1609.34

        try:
            if max_reviews:
                max_reviews = int(max_reviews)
            else:
                max_reviews = 100  # Default to 100 if not specified
        except (ValueError, TypeError):
            max_reviews = 100  # Default to 100 if conversion fails

        lat = data.get("lat")
        lng = data.get("lng")

        if not (lat and lng):
            if not (data.get("city") and data.get("state")):
                return (
                    jsonify({"error": "Either a map pin or city/state is required."}),
                    400,
                )

            city = data.get("city")
            state = data.get("state")
            location_query = f"{city}, {state}"

            # Log the geocoding attempt
            app.logger.info(f"Attempting to geocode: '{location_query}'")
            app.logger.info(f"API key available: {bool(app.config['GOOGLE_API_KEY'])}")
            app.logger.info(
                f"Environment variable GOOGLE_MAPS_API_KEY: {bool(os.environ.get('GOOGLE_MAPS_API_KEY'))}"
            )

            coords_dict = get_coordinates(location_query, app.config["GOOGLE_API_KEY"])
            if not coords_dict:
                app.logger.error(f"Geocoding failed for: '{location_query}'")
                return (
                    jsonify(
                        error=f"Could not find coordinates for '{location_query}'. "
                        "Please check the city and state spelling."
                    ),
                    400,
                )
            lat, lng = coords_dict["lat"], coords_dict["lng"]
            app.logger.info(
                f"Successfully geocoded '{location_query}' to lat={lat}, lng={lng}"
            )

        # coords = (lat, lng)  # Removed unused variable

        if not business_type:
            return jsonify(error="Business type is required"), 400

        # --- GUEST SEARCH LIMITS ---
        # Track guest usage by IP address to prevent abuse
        if not current_user.is_authenticated or current_user.current_plan is None:
            guest_usage = get_or_create_guest_usage()

            if guest_usage:
                # Check if guest has exceeded daily limit (5 searches per day)
                if guest_usage.search_count >= 5:
                    return (
                        jsonify(
                            error="You've reached the daily limit of 5 free searches. "
                            "Please sign up or log in for unlimited searches."
                        ),
                        403,
                    )

                # Increment search count for this IP
                guest_usage.search_count += 1
                db.session.commit()
                max_results = 15
            else:
                # Fallback to session-based tracking if database tracking fails
                session.setdefault("guest_search_count", 0)
                if session["guest_search_count"] >= 5:
                    return (
                        jsonify(
                            error="Guest users are limited to 5 searches. Please sign up or log in for more."
                        ),
                        403,
                    )
                session["guest_search_count"] += 1
                max_results = 15
        else:
            max_results = None  # No limit for authenticated users with a plan

        # Only update search count for authenticated users
        if current_user.is_authenticated:
            current_user.search_count = getattr(current_user, "search_count", 0) + 1
            db.session.commit()

        leads, center = search_places(
            lat,
            lng,
            business_type,
            radius_meters,
            app.config["GOOGLE_API_KEY"],
            max_reviews=max_reviews,
        )
        # Limit results for guests
        if max_results is not None:
            leads = leads[:max_results]
        session["last_search_results"] = leads
        return jsonify({"results": leads, "center": center})

    except Exception as e:
        app.logger.error(
            ("An error occurred during search: " + str(e)[:40] + str(e)[40:])
        )
        return jsonify(error="An unexpected error occurred during the search."), 500


@app.route("/download", methods=["POST"])
@login_required
def download():
    """Download search results as CSV or Excel file."""
    try:
        leads = session.get("last_search_results")
        if not leads:
            return "No leads to download.", 400

        file_format = request.form.get("format", "csv")
        if file_format == "csv":
            df = pd.DataFrame(leads)
            output = BytesIO()
            df.to_csv(output, index=False, encoding="utf-8")
            output.seek(0)
            return send_file(
                output,
                mimetype="text/csv",
                as_attachment=True,
                download_name="leads.csv",
            )
        elif file_format == "xlsx":
            df = pd.DataFrame(leads)
            # Fix for pandas ExcelWriter with BytesIO - use a different approach
            workbook = Workbook()
            worksheet = workbook.active
            if worksheet:
                worksheet.title = "Leads"

                # Write headers
                for col, header in enumerate(df.columns, 1):
                    worksheet.cell(row=1, column=col, value=header)

                # Write data
                for row_idx, row_data in enumerate(df.values, 2):
                    for col_idx, value in enumerate(row_data, 1):
                        worksheet.cell(row=row_idx, column=col_idx, value=value)

            output = BytesIO()
            workbook.save(output)
            output.seek(0)
            return send_file(
                output,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name="leads.xlsx",
            )
        return "Invalid format", 400
    except Exception as e:
        app.logger.error(("Error downloading file: " + str(e)[:40] + str(e)[40:]))
        return "An error occurred while downloading the file.", 500


@app.route("/export-to-google-sheets", methods=["POST"])
@login_required
def export_to_google_sheets():
    """Export search results to Google Sheets."""
    try:
        leads = session.get("last_search_results")
        if not leads:
            return jsonify(error="No leads data to export."), 400

        gc = get_gspread_client()
        spreadsheet = gc.create(f"Leads - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        worksheet = spreadsheet.get_worksheet(0)

        df = pd.DataFrame(leads)
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())

        spreadsheet.share(current_user.email, perm_type="user", role="writer")

        return (
            jsonify(
                message="Successfully exported to Google Sheets!", url=spreadsheet.url
            ),
            200,
        )
    except Exception as e:
        app.logger.error(("Google Sheets export error: " + str(e)[:40] + str(e)[40:]))
        return jsonify(error=f"Failed to export to Google Sheets: {e}"), 500


@app.route("/api/settings", methods=["GET", "PUT"])
@login_required
def settings():
    """Get or update user settings."""
    try:
        user_settings = current_user.settings
        if not user_settings:
            user_settings = UserSettings()
            user_settings.user_id = current_user.id
            db.session.add(user_settings)
            db.session.commit()

        if request.method == "PUT":
            data = request.get_json()
            if not data:
                return jsonify(error="No data provided"), 400

            for key, value in data.items():
                if hasattr(user_settings, key):
                    setattr(user_settings, key, value)
            db.session.add(user_settings)
            db.session.commit()
            return jsonify(message="Settings updated successfully.")

        return jsonify(
            {
                "default_radius": user_settings.default_radius,
                "default_business_type": user_settings.default_business_type,
                "remember_last_search": user_settings.remember_last_search,
                "results_per_page": user_settings.results_per_page,
                "show_map_by_default": user_settings.show_map_by_default,
                "email_notifications": user_settings.email_notifications,
                "search_reminders": user_settings.search_reminders,
                "last_search_city": user_settings.last_search_city,
                "last_search_state": user_settings.last_search_state,
                "last_search_business_type": user_settings.last_search_business_type,
                "last_search_radius": user_settings.last_search_radius,
            }
        )
    except Exception as e:
        app.logger.error(("Error in settings: " + str(e)[:40] + str(e)[40:]))
        db.session.rollback()
        return jsonify(error="An error occurred while processing settings."), 500


@app.route("/api/change-password", methods=["POST"])
@login_required
def change_password():
    """Change user password."""
    try:
        data = request.get_json()
        if not data:
            return jsonify(error="No data provided"), 400

        if not current_user.check_password(data.get("current_password", "")):
            return jsonify(error="Invalid current password."), 400
        new_password = data.get("new_password")
        if not new_password or len(new_password) < 8:
            return (
                jsonify(error="New password must be at least 8 characters long."),
                400,
            )
        current_user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        return jsonify(message="Password updated successfully.")
    except Exception as e:
        app.logger.error(f"Error changing password: {e}")
        db.session.rollback()
        return jsonify(error="An error occurred while changing password."), 500


@app.route("/api/export-data", methods=["GET"])
@login_required
def export_user_data():
    """Export user data as JSON."""
    try:
        user_data = {
            "profile": {
                "name": current_user.name,
                "email": current_user.email,
                "business": current_user.business,
                "phone": current_user.phone,
            },
            "settings": {
                "default_radius": (
                    current_user.settings.default_radius
                    if current_user.settings
                    else None
                ),
                "default_business_type": (
                    current_user.settings.default_business_type
                    if current_user.settings
                    else None
                ),
            },
        }

        output = BytesIO()
        output.write(json.dumps(user_data, indent=4).encode("utf-8"))
        output.seek(0)

        return send_file(
            output,
            mimetype="application/json",
            as_attachment=True,
            download_name="user_data.json",
        )
    except Exception as e:
        app.logger.error(f"Error exporting user data: {e}")
        return "An error occurred while exporting data.", 500


@app.route("/api/delete-account", methods=["POST"])
@login_required
def delete_account():
    """Delete user account."""
    try:
        data = request.get_json()
        if not data:
            return jsonify(error="No data provided"), 400

        if not current_user.check_password(data.get("password", "")):
            return jsonify(error="Invalid password."), 400

        # Optional: Cancel Stripe subscription before deleting
        if current_user.stripe_subscription_id:
            try:
                stripe.Subscription.delete(current_user.stripe_subscription_id)
            except Exception as e:
                app.logger.error(
                    f"Stripe subscription cancellation failed for user {current_user.id}: {e}"
                )
                # Decide if this should prevent account deletion

        db.session.delete(current_user)
        db.session.commit()
        logout_user()

        return jsonify(message="Your account has been permanently deleted.")
    except Exception as e:
        app.logger.error(f"Error deleting account: {e}")
        db.session.rollback()
        return jsonify(error="An error occurred while deleting your account."), 500


@app.route("/api/update-last-search", methods=["POST"])
@login_required
def update_last_search():
    """Update user's last search parameters."""
    try:
        data = request.get_json()
        if not data:
            return jsonify(error="No data provided"), 400

        user_settings = current_user.settings
        if not user_settings:
            user_settings = UserSettings()
            user_settings.user_id = current_user.id
            db.session.add(user_settings)

        user_settings.last_search_city = data.get("city")
        user_settings.last_search_state = data.get("state")
        user_settings.last_search_business_type = data.get("business_type")
        user_settings.last_search_radius = data.get("radius")
        db.session.add(user_settings)
        db.session.commit()
        return jsonify(success=True)
    except Exception as e:
        app.logger.error(f"Error updating last search: {e}")
        db.session.rollback()
        return jsonify(error="An error occurred while updating search parameters."), 500


@app.route("/api/create-checkout-session", methods=["POST"])
def create_checkout_session():
    """Create Stripe checkout session."""
    try:
        data = request.get_json()
        if not data:
            return jsonify(error="No data provided"), 400

        # Check if user is authenticated
        if current_user.is_authenticated:
            # User is logged in, use their customer ID
            customer_id = current_user.stripe_customer_id
            if not customer_id:
                # Create Stripe customer for authenticated user
                customer = stripe.Customer.create(
                    email=current_user.email,
                    name=current_user.name
                )
                current_user.stripe_customer_id = customer.id
                db.session.commit()
                customer_id = customer.id
        else:
            # Guest user, create temporary customer
            customer = stripe.Customer.create(
                email="guest@example.com",  # Will be updated after signup
                name="Guest User"
            )
            customer_id = customer.id

        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": data.get("priceId"), "quantity": 1}],
            mode="subscription",
            success_url=url_for("index", _external=True)
            + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=url_for("pricing", _external=True),
        )
        return jsonify({"id": checkout_session.id})
    except Exception as e:
        app.logger.error(f"Error creating checkout session: {e}")
        return jsonify(error=str(e)), 403


@app.route("/api/create-portal-session", methods=["POST"])
@login_required
def create_portal_session():
    """Create Stripe customer portal session."""
    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=url_for("index", _external=True),
        )
        return jsonify({"url": portal_session.url})
    except Exception as e:
        app.logger.error(f"Error creating portal session: {e}")
        return jsonify(error=str(e)), 403


@app.route("/stripe-webhook", methods=["POST"])
def stripe_webhook():
    """Handle Stripe webhook events."""
    try:
        payload = request.get_data(as_text=True)
        sig_header = request.headers.get("Stripe-Signature")
        endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        except ValueError:
            return "Invalid payload", 400
        except Exception:
            return "Invalid signature", 400

        if (
            event["type"] == "customer.subscription.updated"
            or event["type"] == "customer.subscription.created"
        ):
            subscription = event["data"]["object"]
            customer_id = subscription["customer"]
            user = User.query.filter_by(stripe_customer_id=customer_id).first()
            if user:
                user.stripe_subscription_id = subscription["id"]
                user.current_plan = subscription["items"]["data"][0]["price"][
                    "lookup_key"
                ]
                db.session.commit()

        return "Success", 200
    except Exception as e:
        app.logger.error(f"Error processing Stripe webhook: {e}")
        return "Error processing webhook", 500


def get_gspread_client():
    """Get Google Sheets client."""
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
    if not creds_json:
        raise ValueError("GOOGLE_SHEETS_CREDENTIALS_JSON environment variable not set")

    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)


@app.route("/pricing")
def pricing():
    """Display pricing page."""
    # Get Stripe publishable key from environment
    stripe_publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    
    # These would normally come from your Stripe dashboard
    # For now, using placeholder values
    basic_price_id = os.getenv("STRIPE_BASIC_PRICE_ID", "price_basic")
    premium_price_id = os.getenv("STRIPE_PREMIUM_PRICE_ID", "price_premium") 
    platinum_price_id = os.getenv("STRIPE_PLATINUM_PRICE_ID", "price_platinum")
    
    return render_template("pricing.html", 
                         stripe_publishable_key=stripe_publishable_key,
                         basic_price_id=basic_price_id,
                         premium_price_id=premium_price_id,
                         platinum_price_id=platinum_price_id)


def admin_required(f):
    """Decorator to require admin privileges."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        app.logger.info(f"🔧 Admin check for user: {current_user.email}")
        app.logger.info(f"🔧 User is_admin: {current_user.is_admin}")
        app.logger.info(f"🔧 User current_plan: {current_user.current_plan}")
        app.logger.info(f"🔧 User authenticated: {current_user.is_authenticated}")

        if not current_user.is_admin:
            app.logger.warning(f"❌ Admin access denied for user: {current_user.email}")
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for("index"))
        app.logger.info(f"✅ Admin access granted for user: {current_user.email}")
        return f(*args, **kwargs)

    return decorated_function


@app.route("/admin/dashboard")
@login_required
@admin_required
def admin_dashboard():
    """Admin dashboard page."""
    try:
        app.logger.info(f"Admin dashboard accessed by user: {current_user.email}")
        app.logger.info(f"User is_admin: {current_user.is_admin}")
        app.logger.info(f"User current_plan: {current_user.current_plan}")

        users = User.query.all()
        return render_template("admin_dashboard.html", users=users)
    except Exception as e:
        app.logger.error(f"Error accessing admin dashboard: {e}")
        flash("An error occurred while loading the dashboard.", "danger")
        return redirect(url_for("index"))


@app.route("/restore-admin/<email>")
def restore_admin(email):
    """Temporary route to restore admin privileges for a user."""
    try:
        user = User.query.filter_by(email=email.lower().strip()).first()
        if user:
            user.is_admin = True
            user.current_plan = "admin"
            db.session.commit()
            return jsonify(message=f"Admin privileges restored for {email}"), 200
        else:
            return jsonify(error=f"User {email} not found"), 404
    except Exception as e:
        app.logger.error(f"Error restoring admin: {e}")
        return jsonify(error="An error occurred"), 500


@app.route("/temp-admin-login")
def temp_admin_login():
    """Temporary route to log in as admin for testing."""
    try:
        admin_user = User.query.filter_by(email="sdclark117@gmail.com").first()
        if admin_user:
            login_user(admin_user)
            app.logger.info(f"🔧 Temporary admin login for: {admin_user.email}")
            return redirect(url_for("index"))
        else:
            return "Admin user not found", 404
    except Exception as e:
        app.logger.error(f"❌ Temp admin login error: {e}")
        return "Error logging in as admin", 500


# Add a scheduled task to clean up expired tokens
_cleanup_counter = 0


@app.before_request
def before_request():
    """Run before each request to clean up expired tokens and reset guest usage occasionally."""
    global _cleanup_counter
    # Only clean up tokens occasionally (every 100 requests) to avoid performance impact
    _cleanup_counter += 1

    if _cleanup_counter % 100 == 0:
        cleanup_expired_tokens()
        reset_guest_usage_daily()


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug_mode)
