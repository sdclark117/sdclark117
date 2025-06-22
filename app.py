from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
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
import time
from functools import wraps
import click
from flask.cli import with_appcontext
from flask_migrate import Migrate
import googlemaps

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
migrate = Migrate(app, db)

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    db.drop_all()
    db.create_all()
    click.echo('Initialized the database.')

app.cli.add_command(init_db_command)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'

@login_manager.unauthorized_handler
def unauthorized_callback():
    """Handle unauthorized access attempts."""
    if request.path.startswith('/api/'):
        return jsonify(error='Authentication required to access this endpoint.'), 401
    
    flash('You must be logged in to view this page.')
    return redirect(url_for('index'))

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
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
    
    settings = db.relationship('UserSettings', backref='user', uselist=False, cascade='all, delete-orphan')

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class EmailVerificationToken(db.Model):
    __tablename__ = 'email_verification_tokens'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(128), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, user_id, token, expires_at):
        self.user_id = user_id
        self.token = token
        self.expires_at = expires_at

class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(128), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, user_id, token, expires_at):
        self.user_id = user_id
        self.token = token
        self.expires_at = expires_at

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
    return User.query.get(int(user_id))

def generate_token():
    return secrets.token_urlsafe(32)

def send_email(subject, recipients, body, html_body=None):
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
    token = generate_token()
    expires_at = datetime.utcnow() + timedelta(hours=24)
    new_token = EmailVerificationToken(user_id=user_id, token=token, expires_at=expires_at)
    db.session.add(new_token)
    db.session.commit()
    
    verification_url = url_for('verify_email', token=token, _external=True)
    subject = "Verify Your Email - Business Lead Finder"
    html_body = render_template('email_verification.html', name=name, verification_url=verification_url)
    body = f"Hello {name or 'there'}! Please verify your email by clicking this link: {verification_url}"
    
    return send_email(subject, [email], body, html_body)

def send_password_reset_email(user_id, email, name):
    token = generate_token()
    expires_at = datetime.utcnow() + timedelta(hours=1)
    new_token = PasswordResetToken(user_id=user_id, token=token, expires_at=expires_at)
    db.session.add(new_token)
    db.session.commit()
    
    reset_url = url_for('reset_password_page', token=token, _external=True)
    subject = "Password Reset - Business Lead Finder"
    html_body = render_template('password_reset.html', name=name, reset_url=reset_url)
    body = f"Hello {name or 'there'}! Please reset your password by clicking this link: {reset_url}"
    
    return send_email(subject, [email], body, html_body)

def cleanup_expired_tokens():
    EmailVerificationToken.query.filter(EmailVerificationToken.expires_at < datetime.utcnow()).delete()
    PasswordResetToken.query.filter(PasswordResetToken.expires_at < datetime.utcnow()).delete()
    db.session.commit()

def get_coordinates(location: str, api_key: str) -> Union[dict, None]:
    gmaps = googlemaps.Client(key=api_key)
    try:
        geocode_result = gmaps.geocode(location)
        if geocode_result:
            return geocode_result[0]['geometry']['location']
    except Exception as e:
        print(f"Error during geocoding: {e}")
    return None

def search_places(lat, lng, business_type, radius, api_key, max_reviews=None):
    gmaps = googlemaps.Client(key=api_key)
    all_leads = []
    seen_place_ids = set()

    try:
        places_result = gmaps.places_nearby(
            location=(lat, lng),
            radius=radius,
            keyword=business_type,
            language='en'
        )
    except Exception as e:
        print(f"Error calling Google Places API: {e}")
        return [], {'lat': lat, 'lng': lng}

    while True:
        api_response_data = places_result
        if not api_response_data or api_response_data.get('status') != 'OK':
            break 
            
        current_results = api_response_data.get('results', [])

        for place in current_results:
            place_id = place.get('place_id')
            if place_id in seen_place_ids:
                continue
            
            seen_place_ids.add(place_id)
            
            if is_potential_lead(place):
                try:
                    details = get_place_details(place_id, api_key)
                    if details:
                        user_ratings_total = details.get('user_ratings_total')
                        if max_reviews is not None and user_ratings_total is not None:
                            if user_ratings_total > max_reviews:
                                continue

                        lead_data = {
                            'place_id': place_id,
                            'name': details.get('name'),
                            'address': details.get('formatted_address'),
                            'lat': details['geometry']['location']['lat'],
                            'lng': details['geometry']['location']['lng'],
                            'rating': details.get('rating'),
                            'website': details.get('website'),
                            'phone': details.get('formatted_phone_number'),
                            'opening_hours': format_opening_hours(details.get('opening_hours', {})),
                            'reviews': user_ratings_total,
                            'business_type': format_business_types(details.get('types', [])),
                            'business_status': place.get('business_status')
                        }
                        all_leads.append(lead_data)
                except Exception as e:
                    print(f"Error processing place details for {place.get('name')}: {e}")

        next_page_token = api_response_data.get('next_page_token')
        if not next_page_token:
            break
        
        time.sleep(2)
        
        try:
            places_result = gmaps.places_nearby(page_token=next_page_token)
        except Exception as e:
            print(f"Error fetching next page from Google Places API: {e}")
            break

    final_leads = list({lead['place_id']: lead for lead in all_leads}.values())
    
    return final_leads, {'lat': lat, 'lng': lng}

def get_place_details(place_id: str, api_key: str) -> Union[dict, None]:
    gmaps = googlemaps.Client(key=api_key)
    try:
        fields = ['name', 'formatted_address', 'formatted_phone_number', 'website',
                  'rating', 'user_ratings_total', 'opening_hours', 'geometry',
                  'place_id', 'business_status', 'types']
        
        details = gmaps.place(place_id=place_id, fields=fields, language='en')
        return details.get('result')
    except Exception as e:
        print(f"Error getting place details: {e}")
        return None

def is_potential_lead(place):
    return place.get('business_status') == 'OPERATIONAL'

def format_opening_hours(hours_data):
    if not hours_data or not hours_data.get('weekday_text'):
        return 'Not available'
    return '\n'.join(hours_data['weekday_text'])

def format_business_types(types):
    if not types:
        return 'N/A'
    return ', '.join(t.replace('_', ' ').title() for t in types)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/verify-email/<token>')
def verify_email(token):
    verification_record = EmailVerificationToken.query.filter_by(token=token).first()
    if verification_record and verification_record.expires_at > datetime.utcnow():
        user = User.query.get(verification_record.user_id)
        user.is_verified = True
        db.session.delete(verification_record)
        db.session.commit()
        flash('Email verified successfully! You can now log in.', 'success')
    else:
        flash('Invalid or expired verification link.', 'danger')
    return redirect(url_for('index'))

@app.route('/reset-password/<token>')
def reset_password_page(token):
    reset_record = PasswordResetToken.query.filter_by(token=token).first()
    if reset_record and reset_record.expires_at > datetime.utcnow():
        return render_template('password_reset.html', token=token)
    else:
        flash('Invalid or expired password reset link.', 'danger')
        return redirect(url_for('index'))

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not all(k in data for k in ['email', 'password', 'name']):
        return jsonify(error='Missing data'), 400

    email = data['email'].lower().strip()
    if User.query.filter_by(email=email).first():
        return jsonify(error='Email already exists'), 409
        
    password_hash = generate_password_hash(data['password'])
    
    new_user = User(
        email=email,
        password_hash=password_hash,
        name=data['name'].strip(),
        trial_ends_at=datetime.utcnow() + timedelta(days=7)
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    send_verification_email(new_user.id, new_user.email, new_user.name)
    login_user(new_user, remember=True)
    
    return jsonify(message='Registration successful!'), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify(error="Missing email or password"), 400

    user = User.query.filter_by(email=data['email'].lower().strip()).first()

    if user and user.check_password(data['password']):
        login_user(user, remember=data.get('remember', False))
        return jsonify(message="Login successful"), 200
    
    return jsonify(error="Invalid email or password"), 401

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify(message="Logout successful"), 200

@app.route('/api/profile', methods=['PUT'])
@login_required
def update_profile():
    data = request.get_json()
    if not data:
        return jsonify(error="Invalid data"), 400
        
    current_user.name = data.get('name', current_user.name)
    current_user.business = data.get('business', current_user.business)
    current_user.phone = data.get('phone', current_user.phone)
    db.session.commit()
    
    return jsonify(message="Profile updated successfully"), 200

@app.route('/api/request-password-reset', methods=['POST'])
def request_password_reset():
    data = request.get_json()
    email = data.get('email', '').lower().strip()
    user = User.query.filter_by(email=email).first()
    if user:
        send_password_reset_email(user.id, user.email, user.name)
    return jsonify(message="If an account with that email exists, a reset link has been sent."), 200

@app.route('/api/reset-password/<token>', methods=['POST'])
def reset_password(token):
    reset_record = PasswordResetToken.query.filter_by(token=token).first()
    if not (reset_record and reset_record.expires_at > datetime.utcnow()):
        return jsonify(error='Invalid or expired token.'), 400
        
    data = request.get_json()
    password = data.get('password')
    if not password:
        return jsonify(error='Password is required.'), 400
        
    user = User.query.get(reset_record.user_id)
    user.password_hash = generate_password_hash(password)
    db.session.delete(reset_record)
    db.session.commit()
    
    return jsonify(message='Password has been reset successfully.'), 200

@app.route('/api/send-verification-email', methods=['POST'])
@login_required
def send_verification_email_api():
    if current_user.is_verified:
        return jsonify(error='Your email is already verified.'), 400
    send_verification_email(current_user.id, current_user.email, current_user.name)
    return jsonify(message='Verification email sent.'), 200

@app.route('/api/check-auth')
def check_auth():
    if current_user.is_authenticated:
        return jsonify({
            'is_logged_in': True,
            'user': {
                'name': current_user.name,
                'email': current_user.email,
                'is_verified': current_user.is_verified,
                'current_plan': current_user.current_plan
            }
        })
    return jsonify({'is_logged_in': False})

@app.route('/api/search', methods=['POST'])
@login_required
def search():
    data = request.get_json()
    if not data:
        return jsonify(error='No data provided'), 400

    business_type = data.get('business_type')
    radius = data.get('radius', 5000)
    max_reviews = data.get('max_reviews')
    
    try:
        if max_reviews:
            max_reviews = int(max_reviews)
    except (ValueError, TypeError):
        max_reviews = None
            
    lat = data.get('lat')
    lng = data.get('lng')

    if not (lat and lng):
        city = data.get('city')
        state = data.get('state')
        if not (city and state and business_type):
            return jsonify(error='City, State, and Business Type are required.'), 400
        
        location_query = f"{city}, {state}"
        coords = get_coordinates(location_query, app.config['GOOGLE_API_KEY'])
        if not coords:
            return jsonify(error='Could not find coordinates for the specified location.'), 400
        lat, lng = coords['lat'], coords['lng']
    
    if not business_type:
        return jsonify(error='Business type is required'), 400

    current_user.search_count = getattr(current_user, 'search_count', 0) + 1
    db.session.commit()

    try:
        leads, center = search_places(lat, lng, business_type, radius, app.config['GOOGLE_API_KEY'], max_reviews=max_reviews)
        
        session['last_search_results'] = leads
        
        return jsonify({
            'results': leads,
            'center': center
        })

    except Exception as e:
        print(f"An error occurred during search: {e}")
        import traceback
        traceback.print_exc()
        return jsonify(error='An unexpected error occurred during the search.'), 500

@app.route('/download', methods=['POST'])
@login_required
def download():
    leads = session.get('last_search_results')
    if not leads:
        return "No leads to download.", 400

    file_format = request.form.get('format', 'csv')
    if file_format == 'csv':
        df = pd.DataFrame(leads)
        output = BytesIO()
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        return send_file(output, mimetype='text/csv', as_attachment=True, download_name='leads.csv')
    elif file_format == 'xlsx':
        df = pd.DataFrame(leads)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Leads')
        output.seek(0)
        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='leads.xlsx')
    return "Invalid format", 400


@app.route('/export-to-google-sheets', methods=['POST'])
@login_required
def export_to_google_sheets():
    leads = session.get('last_search_results')
    if not leads:
        return jsonify(error='No leads data to export.'), 400

    try:
        gc = get_gspread_client()
        spreadsheet = gc.create(f"Leads - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        worksheet = spreadsheet.get_worksheet(0)
        
        df = pd.DataFrame(leads)
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        
        spreadsheet.share(current_user.email, perm_type='user', role='writer')
        
        return jsonify(message='Successfully exported to Google Sheets!', url=spreadsheet.url), 200
    except Exception as e:
        print(f"Google Sheets export error: {e}")
        return jsonify(error=f'Failed to export to Google Sheets: {e}'), 500

@app.route('/api/settings', methods=['GET', 'PUT'])
@login_required
def settings():
    user_settings = current_user.settings or UserSettings(user_id=current_user.id)
    if request.method == 'PUT':
        data = request.json
        for key, value in data.items():
            if hasattr(user_settings, key):
                setattr(user_settings, key, value)
        db.session.add(user_settings)
        db.session.commit()
        return jsonify(message='Settings updated successfully.')
    
    return jsonify({
        'default_radius': user_settings.default_radius,
        'default_business_type': user_settings.default_business_type,
        'remember_last_search': user_settings.remember_last_search,
        'results_per_page': user_settings.results_per_page,
        'show_map_by_default': user_settings.show_map_by_default,
        'email_notifications': user_settings.email_notifications,
        'search_reminders': user_settings.search_reminders,
        'last_search_city': user_settings.last_search_city,
        'last_search_state': user_settings.last_search_state,
        'last_search_business_type': user_settings.last_search_business_type,
        'last_search_radius': user_settings.last_search_radius,
    })

@app.route('/api/change-password', methods=['POST'])
@login_required
def change_password():
    data = request.json
    if not current_user.check_password(data.get('current_password', '')):
        return jsonify(error='Invalid current password.'), 400
    new_password = data.get('new_password')
    if not new_password or len(new_password) < 8:
        return jsonify(error='New password must be at least 8 characters long.'), 400
    current_user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    return jsonify(message='Password updated successfully.')

@app.route('/api/export-data', methods=['GET'])
@login_required
def export_user_data():
    user_data = {
        "profile": {
            "name": current_user.name,
            "email": current_user.email,
            "business": current_user.business,
            "phone": current_user.phone
        },
        "settings": {
            'default_radius': current_user.settings.default_radius,
            'default_business_type': current_user.settings.default_business_type,
        } if current_user.settings else {}
    }
    
    output = BytesIO()
    output.write(json.dumps(user_data, indent=4).encode('utf-8'))
    output.seek(0)
    
    return send_file(output, mimetype='application/json', as_attachment=True, download_name='user_data.json')

@app.route('/api/delete-account', methods=['POST'])
@login_required
def delete_account():
    data = request.json
    if not current_user.check_password(data.get('password', '')):
        return jsonify(error='Invalid password.'), 400
    
    # Optional: Cancel Stripe subscription before deleting
    if current_user.stripe_subscription_id:
        try:
            stripe.Subscription.delete(current_user.stripe_subscription_id)
        except stripe.error.StripeError as e:
            print(f"Stripe subscription cancellation failed for user {current_user.id}: {e}")
            # Decide if this should prevent account deletion
    
    db.session.delete(current_user)
    db.session.commit()
    logout_user()
    
    return jsonify(message='Your account has been permanently deleted.')

@app.route('/api/update-last-search', methods=['POST'])
@login_required
def update_last_search():
    data = request.json
    settings = current_user.settings or UserSettings(user_id=current_user.id)
    settings.last_search_city = data.get('city')
    settings.last_search_state = data.get('state')
    settings.last_search_business_type = data.get('business_type')
    settings.last_search_radius = data.get('radius')
    db.session.add(settings)
    db.session.commit()
    return jsonify(success=True)

@app.route('/api/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    data = request.json
    try:
        checkout_session = stripe.checkout.Session.create(
            customer=current_user.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{'price': data['priceId'], 'quantity': 1}],
            mode='subscription',
            success_url=url_for('index', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('pricing', _external=True),
        )
        return jsonify({'id': checkout_session.id})
    except Exception as e:
        return jsonify(error=str(e)), 403

@app.route('/api/create-portal-session', methods=['POST'])
@login_required
def create_portal_session():
    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=url_for('index', _external=True),
        )
        return jsonify({'url': portal_session.url})
    except Exception as e:
        return jsonify(error=str(e)), 403

@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError:
        return 'Invalid signature', 400

    if event['type'] == 'customer.subscription.updated' or event['type'] == 'customer.subscription.created':
        subscription = event['data']['object']
        customer_id = subscription['customer']
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        if user:
            user.stripe_subscription_id = subscription['id']
            user.current_plan = subscription['items']['data'][0]['price']['lookup_key']
            db.session.commit()
            
    return 'Success', 200

def get_gspread_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS_JSON')
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    users = User.query.all()
    return render_template('admin_dashboard.html', users=users)

if __name__ == '__main__':
    app.run(debug=True) 