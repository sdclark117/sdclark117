from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import requests
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from dotenv import load_dotenv
from typing import Union, BinaryIO
import secrets
import urllib.parse
import gspread
from google.oauth2.service_account import Credentials
import stripe

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production')

# Database Configuration
db_url = os.environ.get('DATABASE_URL')
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SECURE'] = True
app.config['GOOGLE_API_KEY'] = os.environ.get('GOOGLE_API_KEY')

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('GMAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('GMAIL_APP_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('GMAIL_USERNAME')

mail = Mail(app)
db = SQLAlchemy(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'

@login_manager.unauthorized_handler
def unauthorized_callback():
    """Handle unauthorized access attempts."""
    # If the request is an API call, return a JSON error
    if request.path.startswith('/api/'):
        return jsonify(error='Authentication required to access this endpoint.'), 401
    
    # Otherwise, it's a browser navigation, so redirect to the login page
    flash('You must be logged in to view this page.')
    return redirect(url_for('index'))

# User class for Flask-Login
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(100))
    business = db.Column(db.String(100))
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    trial_ends_at = db.Column(db.DateTime)
    stripe_customer_id = db.Column(db.String(120), unique=True)
    stripe_subscription_id = db.Column(db.String(120), unique=True)
    current_plan = db.Column(db.String(50))
    search_count = db.Column(db.Integer, default=0)
    last_search_reset = db.Column(db.DateTime)

class EmailVerificationToken(db.Model):
    __tablename__ = 'email_verification_tokens'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(128), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(128), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserSettings(db.Model):
    __tablename__ = 'user_settings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
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
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    """Load user from database."""
    return User.query.get(int(user_id))

def generate_token():
    """Generate a secure random token."""
    return secrets.token_urlsafe(32)

def send_email(subject, recipients, body, html_body=None):
    """Send an email using Flask-Mail."""
    try:
        msg = Message(subject, recipients=recipients)
        msg.body = body
        if html_body:
            msg.html = html_body
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Email sending error: {e}")
        return False

def send_verification_email(user_id, email, name):
    """Send email verification email."""
    token = generate_token()
    expires_at = datetime.utcnow() + timedelta(hours=24)
    new_token = EmailVerificationToken(user_id=user_id, token=token, expires_at=expires_at)
    db.session.add(new_token)
    db.session.commit()
    
    verification_url = url_for('verify_email', token=token, _external=True)
    subject = "Verify Your Email - Business Lead Finder"
    body = f"""
    Hello {name or 'there'}!
    
    Thank you for registering with Business Lead Finder. Please verify your email address by clicking the link below:
    
    {verification_url}
    
    This link will expire in 24 hours.
    
    If you didn't create this account, you can safely ignore this email.
    
    Best regards,
    Business Lead Finder Team
    """
    
    html_body = f"""
    <html>
    <body>
        <h2>Welcome to Business Lead Finder!</h2>
        <p>Hello {name or 'there'}!</p>
        <p>Thank you for registering with Business Lead Finder. Please verify your email address by clicking the button below:</p>
        <p><a href="{verification_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Verify Email</a></p>
        <p>Or copy and paste this link into your browser: <a href="{verification_url}">{verification_url}</a></p>
        <p>This link will expire in 24 hours.</p>
        <p>If you didn't create this account, you can safely ignore this email.</p>
        <br>
        <p>Best regards,<br>Business Lead Finder Team</p>
    </body>
    </html>
    """
    
    return send_email(subject, [email], body, html_body)

def send_password_reset_email(user_id, email, name):
    """Send password reset email."""
    token = generate_token()
    expires_at = datetime.utcnow() + timedelta(hours=1)
    new_token = PasswordResetToken(user_id=user_id, token=token, expires_at=expires_at)
    db.session.add(new_token)
    db.session.commit()
    
    reset_url = url_for('reset_password_page', token=token, _external=True)
    subject = "Password Reset - Business Lead Finder"
    body = f"""
    Hello {name or 'there'}!
    
    You requested a password reset for your Business Lead Finder account. Click the link below to reset your password:
    
    {reset_url}
    
    This link will expire in 1 hour.
    
    If you didn't request this password reset, you can safely ignore this email.
    
    Best regards,
    Business Lead Finder Team
    """
    
    html_body = f"""
    <html>
    <body>
        <h2>Password Reset Request</h2>
        <p>Hello {name or 'there'}!</p>
        <p>You requested a password reset for your Business Lead Finder account. Click the button below to reset your password:</p>
        <p><a href="{reset_url}" style="background-color: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reset Password</a></p>
        <p>Or copy and paste this link into your browser: <a href="{reset_url}">{reset_url}</a></p>
        <p>This link will expire in 1 hour.</p>
        <p>If you didn't request this password reset, you can safely ignore this email.</p>
        <br>
        <p>Best regards,<br>Business Lead Finder Team</p>
    </body>
    </html>
    """
    
    return send_email(subject, [email], body, html_body)

def cleanup_expired_tokens():
    """Clean up expired tokens from database."""
    now = datetime.utcnow()
    
    # Clean up expired email verification tokens
    EmailVerificationToken.query.filter(EmailVerificationToken.expires_at < now).delete()
    
    # Clean up expired password reset tokens
    PasswordResetToken.query.filter(PasswordResetToken.expires_at < now).delete()
    
    db.session.commit()

def get_coordinates(location, api_key):
    """Get coordinates for a location using Google Geocoding API."""
    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'address': location,
            'key': api_key
        }
        print(f"Geocoding URL: {url}")  # Debug print
        print(f"Geocoding params: {params}")  # Debug print
        
        response = requests.get(url, params=params)
        print(f"Geocoding response status: {response.status_code}")  # Debug print
        data = response.json()
        print(f"Geocoding response data: {data}")  # Debug print
        
        if data.get('status') == 'REQUEST_DENIED':
            error_message = data.get('error_message', 'No error message provided')
            print(f"Geocoding request denied. Error message: {error_message}")  # Debug print
            raise Exception(f"Geocoding request denied: {error_message}")
            
        if data.get('status') != 'OK':
            error_msg = f"Geocoding failed: {data.get('status')}"
            if data.get('error_message'):
                error_msg += f" - {data.get('error_message')}"
            print(f"Error: {error_msg}")  # Debug print
            raise Exception(error_msg)
            
        location = data['results'][0]['geometry']['location']
        return location
        
    except requests.exceptions.RequestException as e:
        print(f"Geocoding request exception: {str(e)}")  # Debug print
        raise Exception(f"Network error: {str(e)}")
    except Exception as e:
        print(f"Unexpected error in get_coordinates: {str(e)}")  # Debug print
        raise

def search_places(lat, lng, business_type, radius, api_key):
    """Search for places using Google Places API."""
    try:
        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        
        # Convert business type to a format Google Places API understands
        # Remove any spaces and convert to lowercase
        business_type = business_type.lower().strip()
        
        params = {
            'location': f"{lat},{lng}",
            'radius': radius,
            'keyword': business_type,  # Use keyword instead of type for more flexible searching
            'key': api_key
        }
        print(f"Searching places with params: {params}")  # Debug print
        
        response = requests.get(url, params=params)
        print(f"Places API Response status: {response.status_code}")  # Debug print
        data = response.json()
        print(f"Places API Response data: {data}")  # Debug print
        
        if data.get('status') == 'REQUEST_DENIED':
            error_message = data.get('error_message', 'No error message provided')
            print(f"Places API request denied. Error message: {error_message}")  # Debug print
            raise Exception(f"Places API request denied: {error_message}")
            
        if data.get('status') != 'OK':
            error_msg = f"Places search failed: {data.get('status')}"
            if data.get('error_message'):
                error_msg += f" - {data.get('error_message')}"
            print(f"Error: {error_msg}")  # Debug print
            raise Exception(error_msg)
        
        leads = []
        for place in data.get('results', []):
            # Get place details for additional information
            try:
                place_id = place.get('place_id')
                if place_id:
                    details_url = f"https://maps.googleapis.com/maps/api/place/details/json"
                    details_params = {
                        'place_id': place_id,
                        'fields': 'name,formatted_address,formatted_phone_number,website,rating,opening_hours',
                        'key': api_key
                    }
                    details_response = requests.get(details_url, params=details_params)
                    details_data = details_response.json()
                    
                    if details_data.get('status') == 'OK':
                        details = details_data.get('result', {})
                        lead = {
                            'place_id': place_id,  # Add place_id for deduplication
                            'name': details.get('name', place.get('name', '')),
                            'address': details.get('formatted_address', place.get('vicinity', '')),
                            'lat': place['geometry']['location']['lat'],
                            'lng': place['geometry']['location']['lng'],
                            'rating': details.get('rating', place.get('rating', '')),
                            'website': details.get('website', ''),
                            'phone': details.get('formatted_phone_number', ''),
                            'opening_hours': details.get('opening_hours', {}).get('weekday_text', []),
                            'reviews': details.get('user_ratings_total', place.get('user_ratings_total', 0))
                        }
                    else:
                        # Fallback to basic place data if details request fails
                        lead = {
                            'place_id': place_id,
                            'name': place.get('name', ''),
                            'address': place.get('vicinity', ''),
                            'lat': place['geometry']['location']['lat'],
                            'lng': place['geometry']['location']['lng'],
                            'rating': place.get('rating', ''),
                            'website': '',
                            'phone': '',
                            'opening_hours': [],
                            'reviews': place.get('user_ratings_total', 0)
                        }
                else:
                    # Fallback to basic place data if no place_id
                    lead = {
                        'place_id': f"temp_{len(leads)}",  # Generate temporary ID
                        'name': place.get('name', ''),
                        'address': place.get('vicinity', ''),
                        'lat': place['geometry']['location']['lat'],
                        'lng': place['geometry']['location']['lng'],
                        'rating': place.get('rating', ''),
                        'website': '',
                        'phone': '',
                        'opening_hours': [],
                        'reviews': place.get('user_ratings_total', 0)
                    }
                
                leads.append(lead)
                print(f"Found lead: {lead}")  # Debug print
                
            except Exception as e:
                print(f"Error getting details for place: {str(e)}")  # Debug print
                continue
        
        return leads
        
    except requests.exceptions.RequestException as e:
        print(f"Places API request exception: {str(e)}")  # Debug print
        raise Exception(f"Network error: {str(e)}")
    except Exception as e:
        print(f"Unexpected error in search_places: {str(e)}")  # Debug print
        raise

def get_place_details(place_id, api_key):
    """Get detailed information about a place using Google Places API."""
    url = f"https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        'place_id': place_id,
        'fields': 'name,formatted_address,formatted_phone_number,rating,user_ratings_total,price_level,types,opening_hours,website,geometry',
        'key': api_key
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if data['status'] != 'OK':
        raise Exception(f"Place details failed: {data['status']}")
    
    return data['result']

def is_potential_lead(place):
    """Check if a place meets the criteria for a potential lead."""
    # Check if the place has fewer than 15 reviews or no reviews
    reviews = place.get('user_ratings_total', 0)
    if reviews >= 15:
        return False
    
    # Check if the place has a website
    if 'website' in place:
        return False
    
    # Check if the place is operational
    if place.get('business_status') != 'OPERATIONAL':
        return False
    
    return True

def format_opening_hours(hours):
    """Format opening hours into a readable string."""
    if not hours or 'weekday_text' not in hours:
        return 'Not available'
    return '\n'.join(hours['weekday_text'])

def format_business_types(types):
    """Format business types into a readable string."""
    if not types:
        return 'Not available'
    return ', '.join(types)

@app.route('/')
def index():
    """Render the main page."""
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    print(f"API Key present: {bool(api_key)}")  # Debug print
    if not api_key:
        print("Warning: Google Maps API key is not configured")  # Debug print
        return render_template('index.html', api_key='')
    return render_template('index.html', api_key=api_key)

# Email verification page
@app.route('/verify-email/<token>')
def verify_email(token):
    """Verify email with token."""
    token_data = EmailVerificationToken.query.filter_by(token=token).first()
    if token_data and token_data.expires_at > datetime.utcnow():
        user = User.query.get(token_data.user_id)
        if user:
            user.is_verified = True
            db.session.delete(token_data)
            db.session.commit()
            return render_template('email_verification.html', success=True, message="Email verified successfully! You can now log in.")
    return render_template('email_verification.html', success=False, message="Invalid or expired verification link.")

# Password reset page
@app.route('/reset-password/<token>')
def reset_password_page(token):
    """Show password reset form."""
    token_data = PasswordResetToken.query.filter_by(token=token).first()
    if token_data and token_data.expires_at > datetime.utcnow():
        return render_template('password_reset.html', valid=True, token=token)
    return render_template('password_reset.html', valid=False, message="Invalid or expired reset link.")

# Stripe configuration
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
stripe_webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
plan_price_ids = {
    'BASIC': os.environ.get('STRIPE_BASIC_PLAN_PRICE_ID'),
    'PREMIUM': os.environ.get('STRIPE_PREMIUM_PLAN_PRICE_ID'),
    'PLATINUM': os.environ.get('STRIPE_PLATINUM_PLAN_PRICE_ID')
}

plan_search_limits = {
    'BASIC': 50,
    'PREMIUM': 100,
    'PLATINUM': float('inf')
}

# Authentication routes
@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user and start a 14-day trial."""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'User already exists'}), 400
    
    new_user = User(
        email=email,
        password_hash=generate_password_hash(password, method='pbkdf2:sha256'),
        name=data.get('name', ''),
        business=data.get('business', ''),
        trial_ends_at=datetime.utcnow() + timedelta(days=14)
    )
    db.session.add(new_user)
    db.session.commit()
    
    if app.config['MAIL_USERNAME']:
        send_verification_email(new_user.id, new_user.email, new_user.name)
        
    login_user(new_user)
    
    return jsonify({
        'success': True,
        'user': {'id': new_user.id, 'email': new_user.email, 'name': new_user.name, 'is_verified': new_user.is_verified}
    })

@app.route('/api/login', methods=['POST'])
def login():
    """Authenticate user."""
    data = request.json
    user = User.query.filter_by(email=data.get('email')).first()
    if user and check_password_hash(user.password_hash, data.get('password')):
        login_user(user, remember=data.get('remember', False))
        return jsonify({
            'success': True,
            'user': {'id': user.id, 'email': user.email, 'name': user.name, 'is_verified': user.is_verified}
        })
    return jsonify({'error': 'Invalid email or password'}), 401

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    """Log out the current user."""
    logout_user()
    return jsonify({'success': True})

@app.route('/api/profile', methods=['PUT'])
@login_required
def update_profile():
    """Update the current user's profile."""
    data = request.json
    current_user.name = data.get('name', current_user.name)
    current_user.business = data.get('business', current_user.business)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Profile updated successfully', 'user': {'name': current_user.name, 'business': current_user.business}})

@app.route('/api/request-password-reset', methods=['POST'])
def request_password_reset():
    """Request a password reset."""
    data = request.json
    user = User.query.filter_by(email=data.get('email')).first()
    if user and app.config['MAIL_USERNAME']:
        send_password_reset_email(user.id, user.email, user.name)
    return jsonify({'success': True, 'message': 'If an account with that email exists, a password reset link has been sent.'})

@app.route('/api/reset-password/<token>', methods=['POST'])
def reset_password(token):
    """Reset password with token."""
    token_data = PasswordResetToken.query.filter_by(token=token).first()
    if token_data and token_data.expires_at > datetime.utcnow():
        user = User.query.get(token_data.user_id)
        data = request.json
        if user and data.get('password'):
            user.password_hash = generate_password_hash(data.get('password'), method='pbkdf2:sha256')
            db.session.delete(token_data)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Password reset successfully'})
    return jsonify({'error': 'Invalid or expired reset token'}), 400

@app.route('/api/send-verification-email', methods=['POST'])
@login_required
def send_verification_email_api():
    """Send verification email to current user."""
    if not current_user.is_verified and app.config['MAIL_USERNAME']:
        send_verification_email(current_user.id, current_user.email, current_user.name)
        return jsonify({'success': True, 'message': 'Verification email sent successfully'})
    return jsonify({'error': 'Email already verified or mail not configured'}), 400

@app.route('/api/check-auth')
def check_auth():
    """Check if user is authenticated."""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': current_user.id, 'email': current_user.email, 'name': current_user.name,
                'is_verified': current_user.is_verified, 'trial_ends_at': current_user.trial_ends_at.isoformat() if current_user.trial_ends_at else None,
                'current_plan': current_user.current_plan, 'search_count': current_user.search_count,
                'search_limit': plan_search_limits.get(current_user.current_plan, 'N/A')
            }
        })
    else:
        return jsonify({'authenticated': False})

@app.route('/search', methods=['POST'])
@login_required
def search():
    """Search for business leads."""
    
    # Check subscription status and search limits
    now = datetime.utcnow()
    
    # Reset monthly search count if a month has passed
    if current_user.last_search_reset and (now - current_user.last_search_reset).days >= 30:
        current_user.search_count = 0
        current_user.last_search_reset = now
        db.session.commit()

    # Check if user is on a paid plan
    if current_user.current_plan:
        limit = plan_search_limits.get(current_user.current_plan, 0)
        if current_user.search_count >= limit:
            return jsonify({'error': 'You have reached your monthly search limit. Please upgrade your plan.'}), 403
    
    # Check if user is on a trial plan
    elif current_user.trial_ends_at and now < current_user.trial_ends_at:
        # Allow unlimited searches during trial, or you can set a specific trial limit
        pass
    
    # If no plan and trial is over
    else:
        return jsonify({'error': 'Your free trial has ended. Please choose a plan to continue searching.'}), 403
        
    try:
        api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        if not api_key:
            raise Exception("Google Maps API key is not configured")
            
        data = request.json
        if not data:
            raise Exception("No data provided in request")
            
        city = data.get('city', '').strip()
        state = data.get('state', '').strip()
        business_type = data.get('business_type', '').strip()
        radius = float(data.get('radius', 5))  # Default to 5 miles
        lat = data.get('lat')
        lng = data.get('lng')
        
        print(f"Search API Key present: {bool(api_key)}")  # Debug print
        print(f"City: {city}, State: {state}")  # Debug print
        print(f"Business Type: {business_type}")  # Debug print
        print(f"Coordinates: {lat}, {lng}")  # Debug print
            
        if not business_type:
            raise Exception("Business type is required")
            
        if lat is not None and lng is not None:
            # Use provided coordinates
            center = {'lat': float(lat), 'lng': float(lng)}
        elif city:
            # Get coordinates for city
            location = f"{city}, {state}" if state else city
            center = get_coordinates(location, api_key)
        else:
            raise Exception("Either city or coordinates must be provided")
            
        # Convert radius from miles to meters
        radius_meters = radius * 1609.34
        
        # Search for places
        leads = search_places(center['lat'], center['lng'], business_type, radius_meters, api_key)
        
        # Increment search count after a successful search
        current_user.search_count += 1
        db.session.commit()
        
        return jsonify({
            'leads': leads,
            'center': center
        })
        
    except Exception as e:
        print(f"Search error: {str(e)}")  # Debug print
        return jsonify({'error': str(e)}), 400

@app.route('/download', methods=['POST'])
def download():
    try:
        data = request.json
        if not data or 'leads' not in data:
            raise Exception("No leads data provided")
            
        leads = data['leads']
        if not leads:
            raise Exception("No leads to export")
            
        # Create DataFrame
        df = pd.DataFrame(leads)
        
        # Create Excel file
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Leads')
            
            # Get workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['Leads']
            
            # Style the header
            header_font = Font(bold=True, color='FFFFFF')
            header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
            header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            
            for cell in worksheet[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
            
            # Style the data
            data_alignment = Alignment(vertical='center', wrap_text=True)
            border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            for row in worksheet.iter_rows(min_row=2):
                for cell in row:
                    cell.alignment = data_alignment
                    cell.border = border
            
            # Adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = get_column_letter(column[0].column)
                
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                
                adjusted_width = (max_length + 2)
                worksheet.column_dimensions[column_letter].width = adjusted_width
            
        output.seek(0)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'business_leads_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/export-to-google-sheets', methods=['POST'])
@login_required
def export_to_google_sheets():
    """Export leads to a new Google Sheet."""
    try:
        data = request.json
        leads = data.get('leads')
        
        if not leads:
            return jsonify({'error': 'No leads data provided'}), 400
            
        client = get_gspread_client()
        
        # Create a new spreadsheet
        business_type = leads[0].get('search_query', 'business').replace(" ", "_")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        sheet_title = f"leads_{business_type}_{timestamp}"
        
        folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
        
        spreadsheet = client.create(sheet_title, folder_id=folder_id)
        worksheet = spreadsheet.get_worksheet(0)
        
        # Prepare header and rows
        headers = ["Name", "Address", "Phone", "Website", "Rating", "Reviews", "Opening Hours"]
        rows = []
        for lead in leads:
            opening_hours = "\n".join(lead.get('opening_hours', [])) if lead.get('opening_hours') else 'N/A'
            rows.append([
                lead.get('name', 'N/A'),
                lead.get('address', 'N/A'),
                lead.get('phone', 'N/A'),
                lead.get('website', 'N/A'),
                lead.get('rating', 'N/A'),
                lead.get('reviews', 'N/A'),
                opening_hours
            ])
        
        # Write data to worksheet
        worksheet.append_row(headers)
        worksheet.append_rows(rows)
        
        # Share the spreadsheet so anyone with the link can view
        spreadsheet.share(None, perm_type='anyone', role='reader')
        
        return jsonify({
            'success': True,
            'sheet_url': spreadsheet.url
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings', methods=['GET', 'PUT'])
@login_required
def settings():
    """Get or update user settings."""
    settings_obj = UserSettings.query.filter_by(user_id=current_user.id).first()
    
    if not settings_obj:
        settings_obj = UserSettings(user_id=current_user.id)
        db.session.add(settings_obj)
        db.session.commit()
    
    if request.method == 'PUT':
        data = request.json
        for key, value in data.items():
            if hasattr(settings_obj, key):
                setattr(settings_obj, key, value)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Settings updated'})

    settings_dict = {
        c.name: getattr(settings_obj, c.name).isoformat() if isinstance(getattr(settings_obj, c.name), datetime) else getattr(settings_obj, c.name)
        for c in settings_obj.__table__.columns
    }
    return jsonify({
        'success': True,
        'settings': settings_dict
    })

@app.route('/api/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password."""
    try:
        data = request.json
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'error': 'Current password and new password are required'}), 400
        
        if not current_user.check_password(current_password):
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        current_user.password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Password changed successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export-data', methods=['GET'])
@login_required
def export_user_data():
    """Export user data."""
    try:
        # Get user data
        user_data = {
            'user_info': {
                'email': current_user.email,
                'name': current_user.name,
                'business': current_user.business,
                'is_verified': current_user.is_verified,
                'created_at': current_user.created_at.isoformat() if current_user.created_at else None
            },
            'settings': {
                'default_radius': current_user.settings.default_radius,
                'default_business_type': current_user.settings.default_business_type,
                'remember_last_search': current_user.settings.remember_last_search,
                'results_per_page': current_user.settings.results_per_page,
                'show_map_by_default': current_user.settings.show_map_by_default,
                'email_notifications': current_user.settings.email_notifications,
                'search_reminders': current_user.settings.search_reminders,
                'last_search_city': current_user.settings.last_search_city,
                'last_search_state': current_user.settings.last_search_state,
                'last_search_business_type': current_user.settings.last_search_business_type,
                'last_search_radius': current_user.settings.last_search_radius
            }
        }
        
        return jsonify({
            'success': True,
            'data': user_data,
            'message': 'Data exported successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Delete user account."""
    try:
        data = request.json
        password = data.get('password')
        
        if not password:
            return jsonify({'error': 'Password is required to delete account'}), 400
        
        if not current_user.check_password(password):
            return jsonify({'error': 'Password is incorrect'}), 401
        
        # Delete user data (cascade will handle related records)
        db.session.delete(current_user)
        db.session.commit()
        
        # Logout user
        logout_user()
        
        return jsonify({'success': True, 'message': 'Account deleted successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update-last-search', methods=['POST'])
@login_required
def update_last_search():
    """Update last search parameters."""
    try:
        data = request.json
        current_user.settings.last_search_city = data.get('city', '')
        current_user.settings.last_search_state = data.get('state', '')
        current_user.settings.last_search_business_type = data.get('business_type', '')
        current_user.settings.last_search_radius = float(data.get('radius', 5))
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    """Create a new Stripe checkout session for a subscription."""
    try:
        data = request.json
        price_id = data.get('price_id')
        
        if not price_id:
            return jsonify({'error': 'Price ID is required'}), 400
            
        checkout_session = stripe.checkout.Session.create(
            client_reference_id=current_user.id,
            customer_email=current_user.email,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.host_url + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.host_url,
        )
        return jsonify({'session_id': checkout_session.id})
    except Exception as e:
        print(f"STRIPE CHECKOUT ERROR: {str(e)}")
        error_message = str(e)
        if hasattr(e, 'user_message'):
            error_message = e.user_message
        return jsonify({'error': f"Stripe Error: {error_message}"}), 400

@app.route('/api/create-portal-session', methods=['POST'])
@login_required
def create_portal_session():
    """Create a new Stripe customer portal session."""
    try:
        if not current_user.stripe_customer_id:
            return jsonify({'error': 'User does not have a Stripe customer ID'}), 400
            
        portal_session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=request.host_url,
        )
        return jsonify({'url': portal_session.url})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    """Handle webhook events from Stripe."""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, stripe_webhook_secret
        )
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        return 'Invalid payload or signature', 400

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session.get('client_reference_id')
        customer_id = session.get('customer')
        subscription_id = session.get('subscription')
        
        user = User.query.get(user_id)
        if user:
            user.stripe_customer_id = customer_id
            user.stripe_subscription_id = subscription_id
            db.session.commit()

    elif event['type'] in ['customer.subscription.updated', 'customer.subscription.deleted']:
        subscription = event['data']['object']
        customer_id = subscription['customer']
        
        plan_id = subscription['items']['data'][0]['price']['id']
        plan_name = next((name for name, id in plan_price_ids.items() if id == plan_id), None)
        
        user = User.query.get(customer_id)
        if user:
            if event['type'] == 'customer.subscription.deleted':
                user.current_plan = None
                user.stripe_subscription_id = None
                user.search_count = 0
                user.last_search_reset = None
            else:
                user.current_plan = plan_name
            user.last_search_reset = datetime.utcnow()
            user.search_count = 0
            db.session.commit()

    return 'Success', 200

# Google Sheets API setup
def get_gspread_client():
    """Get gspread client using service account credentials."""
    creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS_JSON environment variable not set.")
    
    creds_dict = json.loads(creds_json)
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client

@app.route('/pricing')
@login_required
def pricing():
    """Render the pricing page."""
    return render_template(
        'pricing.html',
        stripe_publishable_key=os.environ.get('STRIPE_PUBLISHABLE_KEY'),
        basic_price_id=plan_price_ids['BASIC'],
        premium_price_id=plan_price_ids['PREMIUM'],
        platinum_price_id=plan_price_ids['PLATINUM']
    ) 