# User Authentication & Profile Management System

This document describes the user authentication and profile management system that has been integrated into the Business Lead Finder application.

## Features

### 🔐 User Authentication
- **User Registration**: New users can create accounts with email, password, name, and business information
- **User Login**: Secure login with email and password
- **Session Management**: Persistent login sessions using Flask-Login
- **Password Security**: Passwords are hashed using Werkzeug's security functions
- **Logout**: Secure logout functionality

### 👤 Profile Management
- **Profile Viewing**: Users can view their current profile information
- **Profile Editing**: Users can update their name and business information
- **Profile Persistence**: Profile data is stored in SQLite database
- **Real-time Updates**: Profile changes are immediately reflected in the UI

## Technical Implementation

### Backend (Flask)

#### Dependencies Added
- `Flask-Login==0.6.3` - Session management and user authentication
- `Werkzeug==3.0.1` - Password hashing and security utilities

#### Database Schema
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT,
    business TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### API Endpoints

| Endpoint | Method | Description | Authentication Required |
|----------|--------|-------------|------------------------|
| `/api/register` | POST | Register new user | No |
| `/api/login` | POST | Login user | No |
| `/api/logout` | POST | Logout user | Yes |
| `/api/profile` | GET | Get user profile | Yes |
| `/api/profile` | PUT | Update user profile | Yes |
| `/api/check-auth` | GET | Check authentication status | No |

#### Example API Usage

**Register a new user:**
```javascript
fetch('/api/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        email: 'user@example.com',
        password: 'securepassword',
        name: 'John Doe',
        business: 'My Business'
    })
});
```

**Login:**
```javascript
fetch('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        email: 'user@example.com',
        password: 'securepassword'
    })
});
```

**Update profile:**
```javascript
fetch('/api/profile', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        name: 'Updated Name',
        business: 'Updated Business'
    })
});
```

### Frontend (JavaScript)

#### Key Features
- **Automatic Authentication Check**: Checks login status on page load
- **Dynamic UI Updates**: Button text and functionality change based on login status
- **Modal Management**: Seamless switching between login and profile modals
- **Form Validation**: Client-side validation for registration and login
- **Error Handling**: Comprehensive error handling with user-friendly messages

#### User Interface Elements

1. **Authentication Button**: 
   - Shows "Login" when not authenticated
   - Shows user's name when authenticated
   - Opens login modal or profile modal accordingly

2. **Login Modal**:
   - Email and password fields
   - Form validation
   - Error message display

3. **Registration Modal**:
   - Email, password, confirm password fields
   - Optional name and business fields
   - Password confirmation validation

4. **Profile Modal**:
   - Read-only email field
   - Editable name and business fields
   - Save and logout buttons

## Security Features

### Password Security
- Passwords are hashed using Werkzeug's `generate_password_hash()`
- Password verification using `check_password_hash()`
- No plain text passwords stored in database

### Session Security
- Flask-Login handles secure session management
- Session cookies are secure and httpOnly
- Automatic session expiration

### Input Validation
- Server-side validation for all inputs
- SQL injection prevention through parameterized queries
- XSS protection through proper output encoding

## Database Management

### Automatic Database Creation
The system automatically creates the `users.db` SQLite database and required tables on first run.

### Database Location
- Database file: `users.db` (in the application root directory)
- This file should be backed up regularly
- For production, consider using a more robust database like PostgreSQL

## Usage Instructions

### For Users

1. **Registration**:
   - Click the "Login" button in the top-right corner
   - Click the "Sign Up" tab
   - Fill in your email, password, and optional name/business
   - Click "Sign Up"

2. **Login**:
   - Click the "Login" button
   - Enter your email and password
   - Click "Login"

3. **Profile Management**:
   - Click your name (top-right corner) to open profile
   - Edit your name and business information
   - Click "Save Profile" to update
   - Click "Logout" to sign out

### For Developers

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**:
   ```bash
   export SECRET_KEY="your-secret-key-here"
   export GOOGLE_MAPS_API_KEY="your-google-maps-api-key"
   export GMAIL_USERNAME=your.email@gmail.com
   export GMAIL_APP_PASSWORD=your-16-character-app-password
   ```

3. **Run the Application**:
   ```