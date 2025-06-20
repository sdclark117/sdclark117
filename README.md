# Business Lead Finder

A comprehensive web application for finding and managing business leads using Google Places API. Features include user authentication, email verification, password reset, and lead export functionality.

## Features

### 🔍 Business Lead Search
- Search for businesses by type, location, and radius
- Interactive Google Maps integration
- Detailed business information including ratings, reviews, and contact details
- Export results to Excel format

### 🔐 User Authentication & Profile Management
- **User Registration & Login**: Secure account creation and authentication
- **Email Verification**: Email verification system with secure tokens
- **Password Reset**: Secure password reset via email
- **Profile Management**: Update personal and business information
- **Session Management**: Persistent login sessions

### 📧 Email Features
- **Email Verification**: Automatic verification emails for new registrations
- **Password Reset**: Secure password reset emails with time-limited tokens
- **Resend Verification**: Users can request new verification emails
- **Professional Email Templates**: HTML-formatted emails with clear call-to-action

### 🗄️ Data Management
- **SQLite Database**: Local data storage for user accounts and tokens
- **Secure Password Hashing**: Passwords encrypted using Werkzeug
- **Token Management**: Automatic cleanup of expired verification and reset tokens
- **Data Export**: Excel export with professional formatting

## Quick Start

### Prerequisites
- Python 3.7+
- Google Maps API key
- Gmail account (for email functionality)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd business-lead-finder
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file in the project root:
   ```env
   GOOGLE_MAPS_API_KEY=your-google-maps-api-key
   SECRET_KEY=your-secret-key-here
   GMAIL_USERNAME=your.email@gmail.com
   GMAIL_APP_PASSWORD=your-16-character-app-password
   ```

4. **Configure Gmail SMTP** (for email functionality)
   - Follow the [Gmail Setup Guide](GMAIL_SETUP.md)
   - Enable 2-Factor Authentication
   - Generate an App Password
   - Add credentials to your `.env` file

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the application**
   Open your browser and go to `http://localhost:5000`

## Usage

### For Users

#### Registration & Login
1. Click "Login" in the top-right corner
2. Choose "Sign Up" tab for new accounts
3. Fill in your details and create account
4. Check your email for verification link
5. Click the verification link to verify your email

#### Password Reset
1. Click "Login" and then "Forgot Password?"
2. Enter your email address
3. Check your email for reset link
4. Click the link and set a new password

#### Profile Management
1. Click your name (top-right corner) when logged in
2. Update your name and business information
3. View email verification status
4. Resend verification email if needed

#### Business Lead Search
1. Enter city, state, and business type
2. Set search radius (1-50 miles)
3. Optionally drop a pin on the map for additional search area
4. Click "Search" to find businesses
5. Export results to Excel if needed

### For Developers

#### API Endpoints

**Authentication:**
- `POST /api/register` - User registration
- `POST /api/login` - User login
- `POST /api/logout` - User logout
- `GET /api/check-auth` - Check authentication status

**Profile Management:**
- `GET /api/profile` - Get user profile
- `PUT /api/profile` - Update user profile
- `POST /api/send-verification-email` - Resend verification email

**Password Reset:**
- `POST /api/request-password-reset` - Request password reset
- `POST /api/reset-password/<token>` - Reset password with token

**Email Verification:**
- `GET /verify-email/<token>` - Verify email with token

**Business Search:**
- `POST /search` - Search for businesses
- `POST /export` - Export results to Excel

#### Database Schema

**Users Table:**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT,
    business TEXT,
    is_verified BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Email Verification Tokens:**
```sql
CREATE TABLE email_verification_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

**Password Reset Tokens:**
```sql
CREATE TABLE password_reset_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_MAPS_API_KEY` | Google Maps API key for geocoding and places search | Yes |
| `SECRET_KEY` | Flask secret key for session management | Yes |
| `GMAIL_USERNAME` | Gmail address for sending emails | No* |
| `GMAIL_APP_PASSWORD` | Gmail app password for SMTP authentication | No* |

*Required for email functionality (verification and password reset)

### Email Configuration

The application supports multiple email providers:

**Gmail (Default):**
```python
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
```

**SendGrid:**
```python
app.config['MAIL_SERVER'] = 'smtp.sendgrid.net'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'apikey'
app.config['MAIL_PASSWORD'] = 'your-sendgrid-api-key'
```

## Security Features

- **Password Hashing**: All passwords are hashed using Werkzeug
- **Secure Tokens**: Email verification and password reset tokens are cryptographically secure
- **Token Expiration**: Verification tokens expire in 24 hours, reset tokens in 1 hour
- **SQL Injection Protection**: All database queries use parameterized statements
- **Session Security**: Flask-Login handles secure session management
- **Email Security**: Professional email templates with security warnings

## File Structure

```
business-lead-finder/
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── templates/
│   ├── index.html                 # Main application interface
│   ├── email_verification.html    # Email verification page
│   └── password_reset.html        # Password reset page
├── static/                        # Static assets
├── users.db                       # SQLite database (auto-created)
├── GMAIL_SETUP.md                 # Gmail configuration guide
├── AUTHENTICATION_README.md       # Authentication system documentation
└── test_auth.py                   # Authentication testing script
```

## Testing

Run the authentication test script:
```bash
python test_auth.py
```

## Deployment

### Local Development
```bash
python app.py
```

### Production Deployment
1. Set environment variables in your hosting platform
2. Use a production WSGI server (Gunicorn, uWSGI)
3. Configure a production database (PostgreSQL recommended)
4. Set up proper logging and monitoring

## Troubleshooting

### Common Issues

1. **Email not sending**: Check Gmail configuration in `GMAIL_SETUP.md`
2. **Database errors**: Ensure write permissions in the application directory
3. **API errors**: Verify Google Maps API key is valid and has proper permissions
4. **Import errors**: Install all dependencies with `pip install -r requirements.txt`

### Debug Mode

Enable debug mode for detailed error messages:
```python
app.run(debug=True)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
1. Check the documentation files
2. Review the troubleshooting section
3. Check the Gmail setup guide for email issues
4. Open an issue on the repository

## Changelog

### Version 2.0
- Added user authentication system
- Added email verification
- Added password reset functionality
- Added profile management
- Enhanced security features
- Added comprehensive documentation

### Version 1.0
- Basic business lead search functionality
- Google Maps integration
- Excel export feature 