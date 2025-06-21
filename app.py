from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
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
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import urllib.parse
import gspread
from google.oauth2.service_account import Credentials
import stripe

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production')
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SECURE'] = True  # Set to True in production with HTTPS
app.config['GOOGLE_API_KEY'] = os.environ.get('GOOGLE_API_KEY')

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('GMAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('GMAIL_APP_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('GMAIL_USERNAME')

mail = Mail(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    """Load user from database."""
    conn = get_db_connection()
    user_data = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user_data:
        user = User(user_data['id'])
        user.email = user_data['email']
        user.name = user_data['name']
        user.business = user_data['business']
        user.is_verified = bool(user_data['is_verified'])
        return user
    return None

def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    
    # Create users table with email verification
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT,
            business TEXT,
            is_verified BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            trial_ends_at TIMESTAMP,
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            current_plan TEXT, -- e.g., 'BASIC', 'PREMIUM', 'PLATINUM'
            search_count INTEGER DEFAULT 0,
            last_search_reset TIMESTAMP
        )
    ''')
    
    # Create email verification tokens table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS email_verification_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create password reset tokens table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create user settings table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            default_radius INTEGER DEFAULT 5,
            default_business_type TEXT,
            remember_last_search BOOLEAN DEFAULT 0,
            results_per_page INTEGER DEFAULT 25,
            show_map_by_default BOOLEAN DEFAULT 1,
            email_notifications BOOLEAN DEFAULT 1,
            search_reminders BOOLEAN DEFAULT 0,
            last_search_city TEXT,
            last_search_state TEXT,
            last_search_business_type TEXT,
            last_search_radius INTEGER,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

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
    conn = get_db_connection()
    
    # Generate verification token
    token = generate_token()
    expires_at = datetime.now() + timedelta(hours=24)
    
    # Store token in database
    conn.execute(
        'INSERT INTO email_verification_tokens (user_id, token, expires_at) VALUES (?, ?, ?)',
        (user_id, token, expires_at)
    )
    conn.commit()
    conn.close()
    
    # Create verification URL
    verification_url = f"{request.host_url.rstrip('/')}/verify-email/{token}"
    
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
    conn = get_db_connection()
    
    # Generate reset token
    token = generate_token()
    expires_at = datetime.now() + timedelta(hours=1)
    
    # Store token in database
    conn.execute(
        'INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (?, ?, ?)',
        (user_id, token, expires_at)
    )
    conn.commit()
    conn.close()
    
    # Create reset URL
    reset_url = f"{request.host_url.rstrip('/')}/reset-password/{token}"
    
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
    conn = get_db_connection()
    now = datetime.now()
    
    # Clean up expired email verification tokens
    conn.execute('DELETE FROM email_verification_tokens WHERE expires_at < ?', (now,))
    
    # Clean up expired password reset tokens
    conn.execute('DELETE FROM password_reset_tokens WHERE expires_at < ?', (now,))
    
    conn.commit()
    conn.close()

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
    try:
        conn = get_db_connection()
        
        # Find the token
        token_data = conn.execute(
            'SELECT * FROM email_verification_tokens WHERE token = ? AND expires_at > ?',
            (token, datetime.now())
        ).fetchone()
        
        if not token_data:
            conn.close()
            return render_template('email_verification.html', success=False, message="Invalid or expired verification link.")
        
        # Mark user as verified
        conn.execute('UPDATE users SET is_verified = 1 WHERE id = ?', (token_data['user_id'],))
        
        # Delete the used token
        conn.execute('DELETE FROM email_verification_tokens WHERE token = ?', (token,))
        
        conn.commit()
        conn.close()
        
        return render_template('email_verification.html', success=True, message="Email verified successfully! You can now log in.")
        
    except Exception as e:
        return render_template('email_verification.html', success=False, message=f"An error occurred: {str(e)}")

# Password reset page
@app.route('/reset-password/<token>')
def reset_password_page(token):
    """Show password reset form."""
    try:
        conn = get_db_connection()
        
        # Check if token is valid
        token_data = conn.execute(
            'SELECT * FROM password_reset_tokens WHERE token = ? AND expires_at > ?',
            (token, datetime.now())
        ).fetchone()
        
        conn.close()
        
        if not token_data:
            return render_template('password_reset.html', valid=False, message="Invalid or expired reset link.")
        
        return render_template('password_reset.html', valid=True, token=token)
        
    except Exception as e:
        return render_template('password_reset.html', valid=False, message=f"An error occurred: {str(e)}")

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
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        name = data.get('name', '')
        business = data.get('business', '')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        conn = get_db_connection()
        
        # Check if user already exists
        existing_user = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        if existing_user:
            conn.close()
            return jsonify({'error': 'User already exists'}), 400
        
        # Create new user
        password_hash = generate_password_hash(password)
        trial_ends_at = datetime.now() + timedelta(days=14)
        cursor = conn.execute(
            'INSERT INTO users (email, password_hash, name, business, trial_ends_at) VALUES (?, ?, ?, ?, ?)',
            (email, password_hash, name, business, trial_ends_at)
        )
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Send verification email
        if app.config['MAIL_USERNAME'] and app.config['MAIL_PASSWORD']:
            send_verification_email(user_id, email, name)
        
        # Create user object and log them in
        user = User(user_id)
        login_user(user)
        
        return jsonify({
            'success': True,
            'message': 'Registration successful! Please check your email to verify your account.',
            'user': {
                'id': user_id,
                'email': email,
                'name': name,
                'business': business,
                'is_verified': False
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    """Authenticate user."""
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        remember = data.get('remember', False)
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
            
        conn = get_db_connection()
        user_data = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if user_data and check_password_hash(user_data['password_hash'], password):
            user = User(user_data['id'])
            login_user(user, remember=remember)
            
            return jsonify({
                'success': True, 
                'user': {
                    'id': user_data['id'],
                    'email': user_data['email'],
                    'name': user_data['name'],
                    'business': user_data['business'],
                    'is_verified': bool(user_data['is_verified'])
                }
            })
        else:
            return jsonify({'error': 'Invalid email or password'}), 401
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    """Log out the current user."""
    logout_user()
    return jsonify({'success': True, 'message': 'Logout successful'})

@app.route('/api/profile', methods=['GET'])
@login_required
def get_profile():
    """Get the current user's profile."""
    return jsonify({
        'id': current_user.id,
        'email': current_user.email,
        'name': current_user.name,
        'business': current_user.business,
        'is_verified': current_user.is_verified
    })

@app.route('/api/profile', methods=['PUT'])
@login_required
def update_profile():
    """Update the current user's profile."""
    try:
        data = request.json
        name = data.get('name', '')
        business = data.get('business', '')
        
        conn = get_db_connection()
        conn.execute(
            'UPDATE users SET name = ?, business = ? WHERE id = ?',
            (name, business, current_user.id)
        )
        conn.commit()
        conn.close()
        
        # Update the current user object
        current_user.name = name
        current_user.business = business
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'user': {
                'id': current_user.id,
                'email': current_user.email,
                'name': name,
                'business': business,
                'is_verified': current_user.is_verified
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/request-password-reset', methods=['POST'])
def request_password_reset():
    """Request a password reset."""
    try:
        data = request.json
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        conn = get_db_connection()
        user_data = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if not user_data:
            # Don't reveal if email exists or not for security
            return jsonify({'success': True, 'message': 'If an account with that email exists, a password reset link has been sent.'})
        
        # Send password reset email
        if app.config['MAIL_USERNAME'] and app.config['MAIL_PASSWORD']:
            send_password_reset_email(user_data['id'], email, user_data['name'])
        
        return jsonify({'success': True, 'message': 'If an account with that email exists, a password reset link has been sent.'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset-password/<token>', methods=['POST'])
def reset_password(token):
    """Reset password with token."""
    try:
        data = request.json
        new_password = data.get('password')
        
        if not new_password:
            return jsonify({'error': 'New password is required'}), 400
        
        conn = get_db_connection()
        
        # Find the token
        token_data = conn.execute(
            'SELECT * FROM password_reset_tokens WHERE token = ? AND expires_at > ?',
            (token, datetime.now())
        ).fetchone()
        
        if not token_data:
            conn.close()
            return jsonify({'error': 'Invalid or expired reset token'}), 400
        
        # Update password
        password_hash = generate_password_hash(new_password)
        conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, token_data['user_id']))
        
        # Delete the used token
        conn.execute('DELETE FROM password_reset_tokens WHERE token = ?', (token,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Password reset successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/send-verification-email', methods=['POST'])
@login_required
def send_verification_email_api():
    """Send verification email to current user."""
    try:
        if current_user.is_verified:
            return jsonify({'error': 'Email is already verified'}), 400
        
        if app.config['MAIL_USERNAME'] and app.config['MAIL_PASSWORD']:
            send_verification_email(current_user.id, current_user.email, current_user.name)
            return jsonify({'success': True, 'message': 'Verification email sent successfully'})
        else:
            return jsonify({'error': 'Email service not configured'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/check-auth')
def check_auth():
    """Check if user is authenticated."""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': current_user.id,
                'email': current_user.email,
                'name': current_user.name,
                'business': current_user.business,
                'is_verified': current_user.is_verified
            }
        })
    else:
        return jsonify({'authenticated': False})

@app.route('/search', methods=['POST'])
@login_required
def search():
    """Search for business leads."""
    
    # Check subscription status and search limits
    now = datetime.now()
    
    # Reset monthly search count if a month has passed
    if current_user.last_search_reset and (now - datetime.fromisoformat(current_user.last_search_reset)).days >= 30:
        conn = get_db_connection()
        conn.execute('UPDATE users SET search_count = 0, last_search_reset = CURRENT_TIMESTAMP WHERE id = ?', (current_user.id,))
        conn.commit()
        conn.close()
        current_user.search_count = 0

    # Check if user is on a paid plan
    if current_user.current_plan:
        limit = plan_search_limits.get(current_user.current_plan, 0)
        if current_user.search_count >= limit:
            return jsonify({'error': 'You have reached your monthly search limit. Please upgrade your plan.'}), 403
    
    # Check if user is on a trial plan
    elif current_user.trial_ends_at and now < datetime.fromisoformat(current_user.trial_ends_at):
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
        conn = get_db_connection()
        conn.execute('UPDATE users SET search_count = search_count + 1 WHERE id = ?', (current_user.id,))
        conn.commit()
        conn.close()
        
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

@app.route('/api/settings', methods=['GET'])
@login_required
def get_settings():
    """Get user settings."""
    try:
        conn = get_db_connection()
        settings = conn.execute('SELECT * FROM user_settings WHERE user_id = ?', (current_user.id,)).fetchone()
        conn.close()
        
        if settings:
            return jsonify({
                'success': True,
                'settings': {
                    'default_radius': settings['default_radius'],
                    'default_business_type': settings['default_business_type'],
                    'remember_last_search': bool(settings['remember_last_search']),
                    'results_per_page': settings['results_per_page'],
                    'show_map_by_default': bool(settings['show_map_by_default']),
                    'email_notifications': bool(settings['email_notifications']),
                    'search_reminders': bool(settings['search_reminders']),
                    'last_search_city': settings['last_search_city'],
                    'last_search_state': settings['last_search_state'],
                    'last_search_business_type': settings['last_search_business_type'],
                    'last_search_radius': settings['last_search_radius']
                }
            })
        else:
            # Return default settings if none exist
            return jsonify({
                'success': True,
                'settings': {
                    'default_radius': 5,
                    'default_business_type': '',
                    'remember_last_search': False,
                    'results_per_page': 25,
                    'show_map_by_default': True,
                    'email_notifications': True,
                    'search_reminders': False,
                    'last_search_city': '',
                    'last_search_state': '',
                    'last_search_business_type': '',
                    'last_search_radius': 5
                }
            })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings', methods=['PUT'])
@login_required
def update_settings():
    """Update user settings."""
    try:
        data = request.json
        conn = get_db_connection()
        
        # Check if settings exist
        existing_settings = conn.execute('SELECT id FROM user_settings WHERE user_id = ?', (current_user.id,)).fetchone()
        
        if existing_settings:
            # Update existing settings
            conn.execute('''
                UPDATE user_settings SET 
                    default_radius = ?, default_business_type = ?, remember_last_search = ?,
                    results_per_page = ?, show_map_by_default = ?,
                    email_notifications = ?, search_reminders = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (
                data.get('default_radius', 5),
                data.get('default_business_type', ''),
                data.get('remember_last_search', False),
                data.get('results_per_page', 25),
                data.get('show_map_by_default', True),
                data.get('email_notifications', True),
                data.get('search_reminders', False),
                current_user.id
            ))
        else:
            # Create new settings
            conn.execute('''
                INSERT INTO user_settings (
                    user_id, default_radius, default_business_type, remember_last_search,
                    results_per_page, show_map_by_default,
                    email_notifications, search_reminders
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                current_user.id,
                data.get('default_radius', 5),
                data.get('default_business_type', ''),
                data.get('remember_last_search', False),
                data.get('results_per_page', 25),
                data.get('show_map_by_default', True),
                data.get('email_notifications', True),
                data.get('search_reminders', False)
            ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Settings updated successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
        
        conn = get_db_connection()
        user_data = conn.execute('SELECT password_hash FROM users WHERE id = ?', (current_user.id,)).fetchone()
        
        if not user_data or not check_password_hash(user_data['password_hash'], current_password):
            conn.close()
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Update password
        new_password_hash = generate_password_hash(new_password)
        conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_password_hash, current_user.id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Password changed successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export-data', methods=['GET'])
@login_required
def export_user_data():
    """Export user data."""
    try:
        conn = get_db_connection()
        
        # Get user data
        user_data = conn.execute('SELECT * FROM users WHERE id = ?', (current_user.id,)).fetchone()
        settings_data = conn.execute('SELECT * FROM user_settings WHERE user_id = ?', (current_user.id,)).fetchone()
        
        conn.close()
        
        # Prepare export data (exclude sensitive information)
        export_data = {
            'user_info': {
                'email': user_data['email'],
                'name': user_data['name'],
                'business': user_data['business'],
                'is_verified': bool(user_data['is_verified']),
                'created_at': user_data['created_at']
            },
            'settings': settings_data if settings_data else {}
        }
        
        return jsonify({
            'success': True,
            'data': export_data,
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
        
        conn = get_db_connection()
        user_data = conn.execute('SELECT password_hash FROM users WHERE id = ?', (current_user.id,)).fetchone()
        
        if not user_data or not check_password_hash(user_data['password_hash'], password):
            conn.close()
            return jsonify({'error': 'Password is incorrect'}), 401
        
        # Delete user data (cascade will handle related records)
        conn.execute('DELETE FROM users WHERE id = ?', (current_user.id,))
        conn.commit()
        conn.close()
        
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
        conn = get_db_connection()
        
        # Check if settings exist
        existing_settings = conn.execute('SELECT id FROM user_settings WHERE user_id = ?', (current_user.id,)).fetchone()
        
        if existing_settings:
            conn.execute('''
                UPDATE user_settings SET 
                    last_search_city = ?, last_search_state = ?, 
                    last_search_business_type = ?, last_search_radius = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (
                data.get('city', ''),
                data.get('state', ''),
                data.get('business_type', ''),
                data.get('radius', 5),
                current_user.id
            ))
        else:
            # Create settings with last search data
            conn.execute('''
                INSERT INTO user_settings (
                    user_id, last_search_city, last_search_state,
                    last_search_business_type, last_search_radius
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                current_user.id,
                data.get('city', ''),
                data.get('state', ''),
                data.get('business_type', ''),
                data.get('radius', 5)
            ))
        
        conn.commit()
        conn.close()
        
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
        return jsonify({'error': str(e)}), 400

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
        
        conn = get_db_connection()
        conn.execute(
            'UPDATE users SET stripe_customer_id = ?, stripe_subscription_id = ? WHERE id = ?',
            (customer_id, subscription_id, user_id)
        )
        conn.commit()
        conn.close()

    elif event['type'] in ['customer.subscription.updated', 'customer.subscription.deleted']:
        subscription = event['data']['object']
        customer_id = subscription['customer']
        
        plan_id = subscription['items']['data'][0]['price']['id']
        plan_name = next((name for name, id in plan_price_ids.items() if id == plan_id), None)
        
        conn = get_db_connection()
        if event['type'] == 'customer.subscription.deleted':
            conn.execute(
                "UPDATE users SET current_plan = NULL, stripe_subscription_id = NULL, search_count = 0, last_search_reset = NULL WHERE stripe_customer_id = ?",
                (customer_id,)
            )
        else:
            conn.execute(
                "UPDATE users SET current_plan = ?, last_search_reset = CURRENT_TIMESTAMP, search_count = 0 WHERE stripe_customer_id = ?",
                (plan_name, customer_id)
            )
        conn.commit()
        conn.close()

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
def pricing():
    """Render the pricing page."""
    return render_template(
        'pricing.html',
        stripe_publishable_key=os.environ.get('STRIPE_PUBLISHABLE_KEY'),
        basic_price_id=plan_price_ids['BASIC'],
        premium_price_id=plan_price_ids['PREMIUM'],
        platinum_price_id=plan_price_ids['PLATINUM']
    )

if __name__ == '__main__':
    # Clean up expired tokens on startup
    cleanup_expired_tokens()
    app.run(debug=True) 